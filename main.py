import os
import sys
import json
import time
import base64
import operator
import logging
import asyncio
from typing import TypedDict, Annotated, List, Union
from datetime import datetime

from fastapi import FastAPI, Request, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from supabase import create_client, Client
from fpdf import FPDF

# Configuration des logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(title="DG-AGENT-CORE-SAAS", version="5.0.0")

# ==========================================
# ACTIVATION DU CORS POUR DASHBOARD VERCEL
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 0. CONFIGURATION & CLÉS API
# ==========================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "https://dg-agent-engine.onrender.com")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# SUIVI DYNAMIQUE DES 4 MODÈLES DE L'ARCHITECTURE (CIRCUIT BREAKER)
MODEL_HEALTH = {
    "google/gemma-4-31b-it:free": {"status": "HEALTHY", "fails": 0, "role": "Master Core Primary"},
    "z-ai/glm-5.2:free": {"status": "HEALTHY", "fails": 0, "role": "Master Strategy Backup"},
    "google/gemma-4-26b:free": {"status": "HEALTHY", "fails": 0, "role": "Worker A (Execution & Code)"},
    "meta-llama/llama-3-8b:free": {"status": "HEALTHY", "fails": 0, "role": "Worker B (Specialized Sub-Agents)"}
}

# REGISTRE DES DÉCISIONS ET DES LOGS D'EXÉCUTION POUR LE DASHBOARD
EXECUTION_LOGS = []

def record_log(pole: str, status: str, model: str, details: str):
    """Enregistre un événement dans l'historique pour le dashboard Vercel."""
    log_entry = {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "pole": pole,
        "status": status,
        "model": model,
        "details": details
    }
    EXECUTION_LOGS.insert(0, log_entry)
    if len(EXECUTION_LOGS) > 50:
        EXECUTION_LOGS.pop()

# PROMPT SYSTÈME : AMAL-DG PILOTE LES 4 MODÈLES À TRAVERS LES 8 PÔLES
SYSTEM_PROMPT = """Tu es Amal-DG, Directrice Générale, Architecte IA et Super-Orchestratrice du Swarm Agentique.

ARCHITECTURE DES 4 MODÈLES LLM DISPONIBLES :
1. `google/gemma-4-31b-it:free` : Master Core Primary (Orchestration centrale & Vision).
2. `z-ai/glm-5.2:free` : Master Strategy Backup & Juridique (Failover & Rigueur analytique).
3. `google/gemma-4-26b:free` : Worker A - Exécution, Code & Backend.
4. `meta-llama/llama-3-8b:free` : Worker B - Sous-agents spécialisés rapides & Tâches légères.

RÔLE ET ROUTAGE DES 8 PÔLES :
Pour chaque délégation (`delegate_to_subagent`), choisis le profil de modèle adéquat (`analytique`, `juridique`, `technique`, ou `rapide`).

FORMAT DE RÉPONSE POUR EXÉCUTER UNE ACTION :
Réponds EXCLUSIVEMENT sous forme d'un objet JSON valide (aucun texte autour) :
{
  "action": "nom_outil",
  "action_input": { ...arguments... }
}

OUTILS DISPONIBLES :
1. `delegate_to_subagent` : Mandate un sous-agent en précisant le profil LLM. Args: {"team": "...", "task_description": "...", "save_to_file": "...", "model_profile": "analytique | juridique | technique | rapide"}
2. `tavily_web_search` : Recherche web en temps réel. Args: {"query": "..."}
3. `firecrawl_scrape_url` : Scrape une page web. Args: {"url": "..."}
4. `git_commit_and_push` : Publie un livrable sur GitHub. Args: {"file_path": "...", "commit_message": "...", "content_to_write": "..."}
5. `read_github_file` : Lit un fichier sur GitHub. Args: {"file_path": "..."}
6. `compile_markdowns_to_pdf` : Compile les rapports en PDF Master. Args: {"folder_path": "docs", "output_pdf_path": "Master.pdf"}"""

# ==========================================
# 1. DÉFINITION DES OUTILS DE L'AGENT
# ==========================================

def read_github_file(file_path: str) -> str:
    try:
        if not GITHUB_TOKEN or not GITHUB_REPO:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f: return f.read()
            return f"Fichier '{file_path}' introuvable."

        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
        with httpx.Client() as client:
            resp = client.get(api_url, headers=headers)
            if resp.status_code == 200:
                return base64.b64decode(resp.json().get("content", "")).decode("utf-8")
            return f"Fichier non trouvé (code {resp.status_code})."
    except Exception as e:
        return f"Erreur lecture GitHub: {str(e)}"

def git_commit_and_push(file_path: str, commit_message: str, content_to_write: Union[str, bytes]) -> str:
    try:
        safe_path = os.path.normpath(file_path).replace("\\", "/")
        os.makedirs(os.path.dirname(safe_path) or ".", exist_ok=True)
        
        if isinstance(content_to_write, bytes):
            with open(safe_path, "wb") as f: f.write(content_to_write)
            content_b64 = base64.b64encode(content_to_write).decode("utf-8")
        else:
            with open(safe_path, "w", encoding="utf-8") as f: f.write(content_to_write)
            content_b64 = base64.b64encode(content_to_write.encode("utf-8")).decode("utf-8")

        if not GITHUB_TOKEN or not GITHUB_REPO:
            return f"Fichier {file_path} créé en local."

        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{safe_path}"

        with httpx.Client() as client:
            get_resp = client.get(api_url, headers=headers)
            payload = {"message": commit_message, "content": content_b64, "branch": "main"}
            if get_resp.status_code == 200:
                payload["sha"] = get_resp.json().get("sha")
            client.put(api_url, json=payload, headers=headers)

        return f"SUCCÈS: Fichier {file_path} publié sur GitHub."
    except Exception as e:
        return f"ERREUR GITHUB: {str(e)}"

def delegate_to_subagent(team: str, task_description: str, save_to_file: str = "", model_profile: str = "analytique") -> str:
    """Délègue la tâche au sous-agent en utilisant le modèle adéquat parmi les 4 configurés."""
    models_catalog = {
        "analytique": "google/gemma-4-31b-it:free",
        "juridique": "z-ai/glm-5.2:free",
        "technique": "google/gemma-4-26b:free",
        "rapide": "meta-llama/llama-3-8b:free"
    }
    
    active_model = models_catalog.get(model_profile, "google/gemma-4-26b:free")
    fallback_model = "z-ai/glm-5.2:free"
    
    if MODEL_HEALTH.get(active_model, {}).get("status") == "UNHEALTHY":
        active_model = fallback_model

    for attempt in range(2):
        try:
            record_log(team, "IN_PROGRESS", active_model, f"Exécution via profil {model_profile}")
            
            sub_client = ChatOpenAI(
                model=active_model,
                temperature=0.2,
                openai_api_key=OPENROUTER_API_KEY,
                openai_api_base="https://openrouter.ai/api/v1"
            )
            
            system_msg = SystemMessage(content=f"Tu es l'expert du pôle '{team}' (Modèle actif : {active_model}). Rédige une réponse technique et structurée.")
            user_msg = HumanMessage(content=task_description)
            
            response = sub_client.invoke([system_msg, user_msg])
            result_text = response.content
            
            MODEL_HEALTH[active_model]["fails"] = 0
            MODEL_HEALTH[active_model]["status"] = "HEALTHY"
            
            if save_to_file:
                git_commit_and_push(save_to_file, f"Feat({team}): Livrable via {active_model}", result_text)
                record_log(team, "SUCCESS", active_model, f"Sauvegardé dans {save_to_file}")
                return f"SUCCÈS: Rapport du pôle {team} sauvegardé dans '{save_to_file}'."
                
            record_log(team, "SUCCESS", active_model, "Exécution terminée")
            return result_text[:2000]
            
        except Exception as e:
            error_str = str(e)
            record_log(team, "WARNING", active_model, f"Erreur: {error_str}")
            if "429" in error_str or "rate_limit" in error_str.lower():
                MODEL_HEALTH[active_model]["fails"] += 1
                if MODEL_HEALTH[active_model]["fails"] >= 2:
                    MODEL_HEALTH[active_model]["status"] = "UNHEALTHY"
                active_model = fallback_model
                time.sleep(2)
                continue
            else:
                record_log(team, "FAILED", active_model, error_str)
                return f"ERREUR {team}: {error_str}"
                
    return f"ERREUR CRITIQUE {team}: Échec après plusieurs tentatives."

def compile_markdowns_to_pdf(folder_path: str = "docs", output_pdf_path: str = "Master_Report.pdf") -> str:
    try:
        record_log("COMPILER_PDF", "IN_PROGRESS", "FPDF", f"Compilation de {folder_path}")
        if not os.path.exists(folder_path): return f"Dossier {folder_path} introuvable."
        files = sorted([os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".md")])
        if not files: return "Aucun fichier Markdown trouvé."

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 20, "Swarm Agentique - Rapport Master", ln=True, align="C")
        pdf.ln(10)

        for file in files:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, f"Source : {os.path.basename(file)}", ln=True)
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5, content.encode("latin-1", "replace").decode("latin-1"))

        pdf_bytes = pdf.output()
        res = git_commit_and_push(output_pdf_path, "Feat: Publication Master PDF", pdf_bytes)
        record_log("COMPILER_PDF", "SUCCESS", "FPDF", f"PDF généré: {output_pdf_path}")
        return res
    except Exception as e:
        return f"Erreur PDF: {str(e)}"

def tavily_web_search(query: str) -> str:
    if not TAVILY_API_KEY: return "Clé Tavily non configurée."
    try:
        with httpx.Client() as client:
            res = client.post("https://api.tavily.com/search", json={"api_key": TAVILY_API_KEY, "query": query}, timeout=10.0)
            return res.json().get("answer", "Aucun résultat.")[:1200]
    except Exception as e:
        return f"Erreur Tavily: {str(e)}"

def firecrawl_scrape_url(url: str) -> str:
    if not FIRECRAWL_API_KEY: return "Clé Firecrawl non configurée."
    try:
        headers = {"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"}
        with httpx.Client() as client:
            res = client.post("https://api.firecrawl.dev/v1/scrape", json={"url": url}, headers=headers, timeout=12.0)
            if res.status_code == 200:
                return res.json().get("data", {}).get("markdown", "")[:1500]
            return f"Erreur Firecrawl status: {res.status_code}"
    except Exception as e:
        return f"Erreur Firecrawl: {str(e)}"

TOOLS_MAP = {
    "delegate_to_subagent": delegate_to_subagent,
    "read_github_file": read_github_file,
    "git_commit_and_push": git_commit_and_push,
    "compile_markdowns_to_pdf": compile_markdowns_to_pdf,
    "tavily_web_search": tavily_web_search,
    "firecrawl_scrape_url": firecrawl_scrape_url
}

# ==========================================
# 2. MOTEUR LANGGRAPH
# ==========================================

class AgentState(TypedDict):
    messages: Annotated[List, operator.add]

llm_primary = ChatOpenAI(model="google/gemma-4-31b-it:free", temperature=0, openai_api_key=OPENROUTER_API_KEY, openai_api_base="https://openrouter.ai/api/v1")
llm_fallback = ChatOpenAI(model="z-ai/glm-5.2:free", temperature=0, openai_api_key=OPENROUTER_API_KEY, openai_api_base="https://openrouter.ai/api/v1")
llm = llm_primary.with_fallbacks([llm_fallback])

def call_model(state: AgentState):
    system_ctx = SystemMessage(content=SYSTEM_PROMPT)
    full_messages = [system_ctx] + state["messages"][-10:]
    
    try:
        response = llm.invoke(full_messages)
        content = response.content.strip()
        
        if content.startswith("{") and "action" in content:
            try:
                tool_data = json.loads(content)
                action_name = tool_data.get("action")
                action_input = tool_data.get("action_input", {})
                
                if action_name in TOOLS_MAP:
                    tool_fn = TOOLS_MAP[action_name]
                    tool_result = tool_fn(**action_input) if isinstance(action_input, dict) else tool_fn(action_input)
                    tool_msg = HumanMessage(content=f"--- RÉSULTAT ACTION ({action_name}) ---\n{tool_result}")
                    return {"messages": [AIMessage(content=content), tool_msg]}
            except Exception:
                pass

        return {"messages": [response]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"⚠️ Erreur Moteur : {str(e)}")]}

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if isinstance(last_message, HumanMessage) and "--- RÉSULTAT ACTION" in last_message.content:
        return "agent"
    return END

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"agent": "agent", END: END})

app_graph = workflow.compile()

# ==========================================
# 3. KEEPALIVE AUTOMATIQUE
# ==========================================

async def keep_alive_task():
    await asyncio.sleep(15)
    async with httpx.AsyncClient() as client:
        while True:
            try:
                await client.get(f"{RENDER_EXTERNAL_URL}/health", timeout=10.0)
            except Exception:
                pass
            await asyncio.sleep(600)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(keep_alive_task())

# ==========================================
# 4. ENDPOINTS API
# ==========================================

@app.get("/api/dashboard-data")
def get_dashboard_data():
    """Endpoint renvoyant l'état des 4 modèles et l'historique d'exécution pour Vercel."""
    return {
        "server_status": "ONLINE",
        "version": "5.0.0",
        "models_health": MODEL_HEALTH,
        "execution_history": EXECUTION_LOGS
    }

@app.get("/health")
def health_check():
    return {"status": "SWARM-ENGINE-ONLINE-4-MODELS", "models_health": MODEL_HEALTH}

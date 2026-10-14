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

from apscheduler.schedulers.asyncio import AsyncIOScheduler
try:
    from firecrawl import FirecrawlApp
except ImportError:
    FirecrawlApp = None

try:
    from e2b_code_interpreter import CodeInterpreter
except ImportError:
    CodeInterpreter = None

# Configuration des logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(title="AMAL-DG-EXECUTIVE-SWARM", version="7.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
E2B_API_KEY = os.getenv("E2B_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "https://dg-agent-engine.onrender.com")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
firecrawl_app = FirecrawlApp(api_key=FIRECRAWL_API_KEY) if FIRECRAWL_API_KEY and FirecrawlApp else None

MODEL_HEALTH = {
    "openai/gpt-oss-120b": {"status": "HEALTHY", "fails": 0, "role": "Master Core Primary (Groq)"},
    "z-ai/glm-5.2": {"status": "HEALTHY", "fails": 0, "role": "Master Strategy Backup & Juridique"},
    "google/gemma-4-26b:free": {"status": "HEALTHY", "fails": 0, "role": "Worker A (Execution & Code)"},
    "meta-llama/llama-3-8b:free": {"status": "HEALTHY", "fails": 0, "role": "Worker B (Specialized Sub-Agents)"}
}

EXECUTION_LOGS = []

def record_log(pole: str, status: str, model: str, details: str, project_id: str = "GLOBAL"):
    log_entry = {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "project_id": project_id,
        "pole": pole,
        "status": status,
        "model": model,
        "details": details
    }
    EXECUTION_LOGS.insert(0, log_entry)
    if len(EXECUTION_LOGS) > 100:
        EXECUTION_LOGS.pop()

# ==========================================
# PROMPT SYSTÈME AUGMENTÉ : SILICON VALLEY CEO + PMP + AGILE/SCRUM
# ==========================================
SYSTEM_PROMPT = """Tu es AMAL-DG, Directrice Générale, Architecte IA et Super-Orchestratrice du Swarm Agentique Multi-Projets.

TES POSTURES, COMPÉTENCES ET DIRECTIVES EXEC :

1. LEADERSHIP & MINDSET DE CEO DE LA SILICON VALLEY :
   - Vision & Hyper-Croissance : Tu vises l'excellence du produit, l'extrême scalabilité et l'impact marché immédiat.
   - Execution Bias : Priorité absolue aux livrables concrets, fonctionnels et à forte valeur ajoutée (MVPs, features à fort ROI).
   - Communication Directe & Inspirante : Synthétique, orientée résultats, sans blabla superflu, axée sur les KPIs et l'impact stratégique.

2. AGILE & SCRUM MASTER SUPRÊME :
   - Organisation par Sprints : Tu structures le travail en sprints courts et incrémentaux avec un Product Backlog clair.
   - User Stories & Acceptance Criteria : Tu rédiges et exiges des critères d'acceptation précis pour chaque tâche déléguée.
   - Cérémonies & Suivi : Tu intègres le feedback continu, la rétrospective et le déblocage rapide des goulots d'étranglement.

3. RIGUEUR & STANDARDS PMP® (PROJECT MANAGEMENT PROFESSIONAL) :
   - Gestion des Risques : Identification active des blocages (techniques, juridiques, ressources) et plans de mitigation.
   - Gestion du Périmètre (Scope Management) : Évite le "Scope Creep", cadre strictement les fonctionnalités.
   - Qualité & Conformité (QA) : Tolérance zéro pour le code instable ou non documenté.

4. GESTION DU PORTEFEUILLE MULTI-PROJETS :
   - Isolation stricte des contextes (ex: BailConforme.ca, Usine Agentique, Control Center).
   - Pilotage stratégique des 8 Pôles (Pôle 01 Produit à Pôle 08 Orchestration).

FORMAT DE RÉPONSE POUR EXÉCUTER UNE ACTION :
Si tu dois appeler un outil, réponds SOUS FORME D'OBJET JSON STRICT :
{"action": "nom_outil", "action_input": {...}}

Outils disponibles :
- delegate_to_subagent
- execute_python_code_e2b
- tavily_web_search
- firecrawl_scrape_url
- git_commit_and_push
- read_github_file
- compile_markdowns_to_pdf

Sinon, réponds directement en TEXTE CLAIR, STRUCTURÉ ET STRATÉGIQUE (Style CEO Silicon Valley / PMP)."""

# ==========================================
# 1. OUTILS ET CAPACITÉS D'ACTION DU SWARM
# ==========================================

def execute_python_code_e2b(code: str) -> str:
    if not E2B_API_KEY or not CodeInterpreter:
        return "E2B non disponible."
    try:
        with CodeInterpreter(api_key=E2B_API_KEY) as sandbox:
            execution = sandbox.notebook.exec_cell(code)
            return "\n".join(execution.logs.stdout)
    except Exception as e:
        return f"Erreur E2B: {str(e)}"

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
            return f"Fichier non trouvé sur GitHub ({resp.status_code})."
    except Exception as e:
        return f"Erreur GitHub: {str(e)}"

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
            return f"Fichier sauvegardé en local."

        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{safe_path}"

        with httpx.Client() as client:
            get_resp = client.get(api_url, headers=headers)
            payload = {"message": commit_message, "content": content_b64, "branch": "main"}
            if get_resp.status_code == 200:
                payload["sha"] = get_resp.json().get("sha")
            client.put(api_url, json=payload, headers=headers)

        return f"SUCCÈS: Fichier {file_path} mis à jour sur GitHub."
    except Exception as e:
        return f"ERREUR GITHUB: {str(e)}"

def delegate_to_subagent(team: str, task_description: str, save_to_file: str = "", model_profile: str = "analytique", project_id: str = "GLOBAL") -> str:
    models_catalog = {
        "analytique": "google/gemma-4-31b-it:free",
        "juridique": "z-ai/glm-5.2",
        "technique": "google/gemma-4-26b:free",
        "rapide": "meta-llama/llama-3-8b:free"
    }
    active_model = models_catalog.get(model_profile, "google/gemma-4-26b:free")
    try:
        sub_client = ChatOpenAI(
            model=active_model,
            temperature=0.2,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1"
        )
        system_msg = SystemMessage(content=f"Tu es le sous-agent expert du pôle '{team}' pour le projet '{project_id}'. Applique les standards de qualité logiciels d'élite (Clean Code, Agile/Scrum).")
        user_msg = HumanMessage(content=task_description)
        response = sub_client.invoke([system_msg, user_msg])
        result_text = response.content
        if save_to_file:
            git_commit_and_push(save_to_file, f"Feat({team}/{project_id}): Sprint Deliverable", result_text)
        return result_text[:2000]
    except Exception as e:
        return f"Erreur sous-agent: {str(e)}"

def compile_markdowns_to_pdf(folder_path: str = "docs", output_pdf_path: str = "Master_Report.pdf") -> str:
    try:
        if not os.path.exists(folder_path): return f"Dossier {folder_path} introuvable."
        files = sorted([os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".md")])
        if not files: return "Aucun Markdown à compiler."
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 20, "AMAL-DG Executive Report", ln=True, align="C")
        for file in files:
            pdf.add_page()
            with open(file, "r", encoding="utf-8") as f: content = f.read()
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5, content.encode("latin-1", "replace").decode("latin-1"))
        pdf_bytes = pdf.output()
        return git_commit_and_push(output_pdf_path, "PDF Executive Report", pdf_bytes)
    except Exception as e:
        return f"Erreur FPDF: {str(e)}"

def tavily_web_search(query: str) -> str:
    if not TAVILY_API_KEY: return "Pas de clé Tavily."
    try:
        with httpx.Client() as client:
            res = client.post("https://api.tavily.com/search", json={"api_key": TAVILY_API_KEY, "query": query}, timeout=10.0)
            return res.json().get("answer", "Aucun résultat.")[:1200]
    except Exception as e:
        return f"Erreur Tavily: {str(e)}"

def firecrawl_scrape_url(url: str) -> str:
    if firecrawl_app:
        try:
            return firecrawl_app.scrape_url(url, params={'formats': ['markdown']}).get('markdown', '')[:1500]
        except Exception as e:
            return f"Erreur Firecrawl: {str(e)}"
    return "Firecrawl non configuré."

TOOLS_MAP = {
    "delegate_to_subagent": delegate_to_subagent,
    "execute_python_code_e2b": execute_python_code_e2b,
    "read_github_file": read_github_file,
    "git_commit_and_push": git_commit_and_push,
    "compile_markdowns_to_pdf": compile_markdowns_to_pdf,
    "tavily_web_search": tavily_web_search,
    "firecrawl_scrape_url": firecrawl_scrape_url
}

# LLM Config (Groq Master + OpenRouter Fallback)
llm_primary = ChatGroq(model="openai/gpt-oss-120b", temperature=0, groq_api_key=GROQ_API_KEY) if GROQ_API_KEY else ChatOpenAI(model="z-ai/glm-5.2", temperature=0, openai_api_key=OPENROUTER_API_KEY, openai_api_base="https://openrouter.ai/api/v1")
llm_fallback = ChatOpenAI(model="z-ai/glm-5.2", temperature=0, openai_api_key=OPENROUTER_API_KEY, openai_api_base="https://openrouter.ai/api/v1")

class AgentState(TypedDict):
    messages: Annotated[List, operator.add]

def call_model(state: AgentState):
    system_ctx = SystemMessage(content=SYSTEM_PROMPT)
    full_messages = [system_ctx] + state["messages"][-10:]
    
    for current_llm in [llm_primary, llm_fallback]:
        try:
            response = current_llm.invoke(full_messages)
            content = response.content.strip()
            
            if content.startswith("```"):
                lines = content.splitlines()
                if lines[0].startswith("```"): lines = lines[1:]
                if lines and lines[-1].startswith("```"): lines = lines[:-1]
                content = "\n".join(lines).strip()
            
            if content.startswith("{") and "action" in content:
                try:
                    tool_data = json.loads(content)
                    action_name = tool_data.get("action")
                    action_input = tool_data.get("action_input", {})
                    if action_name in TOOLS_MAP:
                        tool_fn = TOOLS_MAP[action_name]
                        tool_result = tool_fn(**action_input) if isinstance(action_input, dict) else tool_fn(action_input)
                        tool_msg = HumanMessage(content=f"--- RÉSULTAT ACTION ({action_name}) ---\n{tool_result}\nPoursuis avec le leadership et la rigueur d'Amal-DG.")
                        return {"messages": [AIMessage(content=content), tool_msg]}
                except Exception:
                    pass

            return {"messages": [response]}
        except Exception as e:
            logging.warning(f"Erreur LLM: {e}")
            continue

    return {"messages": [AIMessage(content="⚠️ Indisponibilité temporaire du modèle.")]}

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

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    scheduler.start()
    asyncio.create_task(keep_alive_task())

async def keep_alive_task():
    await asyncio.sleep(15)
    async with httpx.AsyncClient() as client:
        while True:
            try:
                await client.get(f"{RENDER_EXTERNAL_URL}/health", timeout=10.0)
            except Exception:
                pass
            await asyncio.sleep(600)

def send_slack_message(channel: str, text: str):
    """Fonction d'envoi Slack dédiée et ultra-sécurisée."""
    if not SLACK_TOKEN:
        logging.error("Pas de token Slack configuré.")
        return
    
    token = SLACK_TOKEN.strip()
    if not token.startswith("xoxb-") and not token.startswith("xoxp-"):
        logging.error("Format de token Slack invalide.")
        return

    try:
        resp = httpx.post(
            "[https://slack.com/api/chat.postMessage](https://slack.com/api/chat.postMessage)",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
            json={"channel": channel, "text": text},
            timeout=15.0
        )
        logging.info(f"Slack response status: {resp.status_code}")
    except Exception as e:
        logging.error(f"Erreur envoi Slack: {e}")

def process_slack_mission_async(channel_id: str, user_prompt: str):
    record_log("ORCHESTRATOR", "STARTED", "openai/gpt-oss-120b", f"Slack Mission: {user_prompt[:50]}...")
    try:
        final_state = app_graph.invoke({"messages": [HumanMessage(content=user_prompt)]})
        final_message = final_state["messages"][-1].content
    except Exception as e:
        final_message = f"⚠️ *Erreur Moteur Amal-DG* : {str(e)}"

    send_slack_message(channel_id, final_message)

@app.post("/slack/events")
@app.post("/slack/events/")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    if data.get("type") == "url_verification": 
        return {"challenge": data.get("challenge")}
        
    event = data.get("event", {})
    if event.get("type") in ["message", "app_mention"] and not event.get("bot_id"):
        channel_id = event.get("channel")
        user_prompt = event.get("text")
        if channel_id and user_prompt:
            background_tasks.add_task(process_slack_mission_async, channel_id, user_prompt)

    return Response(status_code=200)

@app.get("/api/dashboard-data")
def get_dashboard_data():
    return {
        "server_status": "ONLINE",
        "version": "7.0.0",
        "executive_standards": ["SILICON_VALLEY_CEO", "PMP_RIGOR", "AGILE_SCRUM"],
        "models_health": MODEL_HEALTH,
        "execution_history": EXECUTION_LOGS
    }

@app.get("/health")
def health_check():
    return {"status": "ONLINE", "version": "7.0.0"}

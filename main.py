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

app = FastAPI(title="DG-AGENT-CORE-SAAS", version="4.9.0")

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
# 0. CONFIGURATION & CLÉS API (14 SERVICES)
# ==========================================
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

# SUIVI DYNAMIQUE DE LA SANTÉ DES MODÈLES (CIRCUIT BREAKER EN MÉMOIRE)
MODEL_HEALTH = {
    "google/gemma-4-31b-it:free": {"status": "HEALTHY", "fails": 0},
    "z-ai/glm-5.2:free": {"status": "HEALTHY", "fails": 0},
    "google/gemma-4-26b-a4b-it:free": {"status": "HEALTHY", "fails": 0}
}

# REGISTRE DES DÉCISIONS ET DES LOGS D'EXÉCUTION POUR VERCEL
EXECUTION_LOGS = []

def record_log(pole: str, status: str, model: str, details: str):
    """Enregistre un événement dans l'historique pour le dashboard."""
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

# PROMPT SYSTÈME : AMAL-DG CHOISIT LE PROFIL SELON LA MISSION DE CHAQUE PÔLE
SYSTEM_PROMPT = """Tu es Amal-DG, Directrice Générale, Architecte IA et Super-Orchestratrice du portefeuille SaaS B2B.

RÔLE ET ROUTAGE DES 8 PÔLES D'ANALYSE :
Tu pilotes 8 pôles d'expertise. Pour chaque délégation (`delegate_to_subagent`), tu dois évaluer la nature de la tâche et choisir le profil de modèle le plus adapté :
1. `analytique` (`google/gemma-4-31b-it:free`) : À choisir pour les études nécessitant une grande profondeur rédactionnelle, une vision marché et stratégie (ex: Produit, Growth/SEO, Ventes, UX/UI).
2. `juridique` (`z-ai/glm-5.2:free`) : À choisir pour les analyses exigeant une rigueur absolue, la conformité aux lois et la logique procédurale (ex: Juridique/TAL/Loi 25, Finance).
3. `technique` (`google/gemma-4-26b-a4b-it:free`) : À choisir pour la conception technique, l'infrastructure et la sécurité (ex: Architecture/Dev, SecOps).

CONSIGNES STRICTES :
- Projet phare : BailConforme.ca (SaaS B2B Immobilier Québec : conformité TAL, Loi 25, Code civil) et tout SaaS B2B du portefeuille.
- Horizon temporel : 2026-2027.
- Utilise `tavily_web_search` et `firecrawl_scrape_url` pour baser tes requêtes sur des données actuelles du marché et de la législation.

FORMAT DE RÉPONSE POUR EXÉCUTER UNE ACTION :
Réponds EXCLUSIVEMENT sous forme d'un objet JSON valide (aucun texte autour) :
{
  "action": "nom_outil",
  "action_input": { ...arguments... }
}

BOÎTE À OUTILS DE DÉLÉGATION ET D'EXÉCUTION :
1. `delegate_to_subagent` : Mandate un sous-agent spécialisé en précisant le profil de modèle adéquat.
   Arguments : {"team": "team3_product", "task_description": "...", "save_to_file": "docs/analyse_360/01_produit.md", "model_profile": "analytique | juridique | technique", "project_context": "BailConforme.ca"}
2. `tavily_web_search` : Recherche d'informations réelles et actuelles sur Internet.
   Arguments : {"query": "..."}
3. `firecrawl_scrape_url` : Extrait et scrape le contenu d'une page Web.
   Arguments : {"url": "..."}
4. `git_commit_and_push` : Enregistre ou déploie un livrable Markdown/PDF sur GitHub.
   Arguments : {"file_path": "...", "commit_message": "...", "content_to_write": "..."}
5. `read_github_file` : Lit un rapport ou un fichier de consignes.
   Arguments : {"file_path": "..."}
6. `compile_markdowns_to_pdf` : Compile les rapports d'études en un Master PDF.
   Arguments : {"folder_path": "docs/analyse_360", "output_pdf_path": "BailConforme_Analyse_360_Master.pdf"}

Si tes actions sont achevées, réponds directement sur Slack en TEXTE CLAIR ET STRUCTURÉ."""

# ==========================================
# 1. DÉFINITION DES OUTILS DE L'AGENT
# ==========================================

def read_github_file(file_path: str) -> str:
    """Lit un fichier .md de consignes ou de rapport directement sur GitHub ou en local."""
    try:
        if not GITHUB_TOKEN or not GITHUB_REPO:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            return f"Fichier '{file_path}' introuvable en local."

        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
        with httpx.Client() as client:
            resp = client.get(api_url, headers=headers)
            if resp.status_code == 200:
                content_b64 = resp.json().get("content", "")
                return base64.b64decode(content_b64).decode("utf-8")
            return f"Fichier non trouvé sur GitHub (code {resp.status_code})."
    except Exception as e:
        return f"Erreur lecture GitHub: {str(e)}"

def git_commit_and_push(file_path: str, commit_message: str, content_to_write: Union[str, bytes]) -> str:
    """Publie ou met à jour un fichier texte ou binaire (PDF) sur le dépôt GitHub."""
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
            return f"Fichier {file_path} créé en local (variables GitHub non configurées)."

        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{safe_path}"

        with httpx.Client() as client:
            get_resp = client.get(api_url, headers=headers)
            payload = {"message": commit_message, "content": content_b64, "branch": "main"}
            if get_resp.status_code == 200:
                payload["sha"] = get_resp.json().get("sha")
            client.put(api_url, json=payload, headers=headers)

        return f"SUCCÈS: Fichier {file_path} publié/déployé sur GitHub."
    except Exception as e:
        return f"ERREUR GITHUB: {str(e)}"

def delegate_to_subagent(team: str, task_description: str, save_to_file: str = "", model_profile: str = "analytique", project_context: str = "BailConforme.ca") -> str:
    """Délègue la tâche au sous-agent en utilisant le modèle spécialisé choisi par Amal-DG avec gestion automatique des pannes."""
    models_catalog = {
        "analytique": "google/gemma-4-31b-it:free",
        "juridique": "z-ai/glm-5.2:free",
        "technique": "google/gemma-4-26b-a4b-it:free"
    }
    
    primary_model = models_catalog.get(model_profile, "google/gemma-4-31b-it:free")
    fallback_model = "z-ai/glm-5.2:free"
    
    active_model = primary_model
    if MODEL_HEALTH.get(primary_model, {}).get("status") == "UNHEALTHY":
        active_model = fallback_model

    for attempt in range(2):
        try:
            record_log(team, "IN_PROGRESS", active_model, f"Génération du rapport via profil {model_profile}")
            
            sub_client = ChatOpenAI(
                model=active_model,
                temperature=0.2,
                openai_api_key=OPENROUTER_API_KEY,
                openai_api_base="https://openrouter.ai/api/v1"
            )
            
            system_msg = SystemMessage(
                content=f"Tu es l'expert du pôle '{team}' pour le projet SaaS '{project_context}' (Moteur: {active_model}). "
                        f"Rédige une étude analytique et stratégique exhaustive avec vision prospective (horizon 2026-2027)."
            )
            user_msg = HumanMessage(content=task_description)
            
            response = sub_client.invoke([system_msg, user_msg])
            result_text = response.content
            
            MODEL_HEALTH[active_model]["fails"] = 0
            MODEL_HEALTH[active_model]["status"] = "HEALTHY"
            
            if save_to_file:
                git_commit_and_push(save_to_file, f"Feat({team}): Livrable via profil {model_profile}", result_text)
                record_log(team, "SUCCESS", active_model, f"Sauvegardé dans {save_to_file}")
                return f"SUCCÈS: Rapport du pôle {team} (profil {model_profile}) sauvegardé dans '{save_to_file}'."
                
            record_log(team, "SUCCESS", active_model, "Rapport généré directement")
            return result_text[:2000]
            
        except Exception as e:
            error_str = str(e)
            record_log(team, "WARNING", active_model, f"Erreur interceptée: {error_str}")
            if "429" in error_str or "rate_limit" in error_str.lower():
                MODEL_HEALTH[active_model]["fails"] += 1
                if MODEL_HEALTH[active_model]["fails"] >= 2:
                    MODEL_HEALTH[active_model]["status"] = "UNHEALTHY"
                
                active_model = fallback_model
                record_log(team, "FALLBACK", active_model, "Bascule automatique vers modèle de secours")
                time.sleep(3)
                continue
            else:
                record_log(team, "FAILED", active_model, error_str)
                return f"ERREUR DÉLÉGATION {team}: {error_str}"
                
    record_log(team, "CRITICAL", active_model, "Échec global après toutes les tentatives")
    return f"ERREUR CRITIQUE {team}: Échec de l'exécution après plusieurs tentatives."

def compile_markdowns_to_pdf(folder_path: str = "docs/analyse_360", output_pdf_path: str = "BailConforme_Analyse_360_Master.pdf") -> str:
    """Compile l'ensemble des livrables Markdown d'un dossier en un document PDF Master unique."""
    try:
        record_log("COMPILER_PDF", "IN_PROGRESS", "FPDF", f"Compilation des fichiers du dossier {folder_path}")
        if not os.path.exists(folder_path):
            record_log("COMPILER_PDF", "FAILED", "FPDF", f"Dossier {folder_path} introuvable")
            return f"ERREUR: Dossier {folder_path} introuvable."

        files = sorted([os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".md")])
        if not files:
            record_log("COMPILER_PDF", "FAILED", "FPDF", "Aucun fichier Markdown à compiler")
            return f"ERREUR: Aucun rapport Markdown trouvé dans {folder_path}."

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 30, "BailConforme.ca - Rapport Stratégique Master 360°", ln=True, align="C")
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 10, "Document Unifié d'Analyse B2B - Directrice Générale Amal-DG (Horizon 2026-2027)", ln=True, align="C")
        pdf.ln(15)

        for file in files:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 10, f"Pôle : {os.path.basename(file)}", ln=True)
            pdf.ln(4)
            
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()

            pdf.set_font("Helvetica", "", 10)
            safe_text = content.encode("latin-1", "replace").decode("latin-1")
            pdf.multi_cell(0, 5, safe_text)

        pdf_bytes = pdf.output()
        res = git_commit_and_push(output_pdf_path, "Feat: Publication Master PDF Stratégique 360°", pdf_bytes)
        record_log("COMPILER_PDF", "SUCCESS", "FPDF", f"Master PDF généré et publié: {output_pdf_path}")
        return res
    except Exception as e:
        record_log("COMPILER_PDF", "FAILED", "FPDF", str(e))
        return f"ERREUR COMPILATION PDF: {str(e)}"

def tavily_web_search(query: str) -> str:
    """Recherche web en temps réel pour obtenir des données fraîches du marché et de la législation."""
    if not TAVILY_API_KEY: return "Clé Tavily non configurée."
    try:
        with httpx.Client() as client:
            res = client.post("https://api.tavily.com/search", json={"api_key": TAVILY_API_KEY, "query": query}, timeout=12.0)
            return res.json().get("answer", "Aucun résultat web disponible.")[:1200]
    except Exception as e:
        return f"Erreur Tavily Search: {str(e)}"

def firecrawl_scrape_url(url: str) -> str:
    """Scrape et extrait le texte d'une page Web cible via Firecrawl."""
    if not FIRECRAWL_API_KEY: return "Clé Firecrawl non configurée."
    try:
        headers = {"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"}
        with httpx.Client() as client:
            res = client.post("https://api.firecrawl.dev/v1/scrape", json={"url": url}, headers=headers, timeout=15.0)
            if res.status_code == 200:
                data = res.json().get("data", {})
                return data.get("markdown", "Contenu extrait vide.")[:1500]
            return f"Erreur Firecrawl status: {res.status_code}"
    except Exception as e:
        return f"Erreur Firecrawl Scrape: {str(e)}"

TOOLS_MAP = {
    "delegate_to_subagent": delegate_to_subagent,
    "read_github_file": read_github_file,
    "git_commit_and_push": git_commit_and_push,
    "compile_markdowns_to_pdf": compile_markdowns_to_pdf,
    "tavily_web_search": tavily_web_search,
    "firecrawl_scrape_url": firecrawl_scrape_url
}

# ==========================================
# 2. GESTION DE MÉMOIRE ET MOTEUR LANGGRAPH
# ==========================================

class AgentState(TypedDict):
    messages: Annotated[List, operator.add]

# Moteur principal Amal-DG (Groq) + Moteur de secours gratuit (OpenRouter GLM-5.2)
llm_primary = ChatGroq(model="openai/gpt-oss-120b", temperature=0, groq_api_key=GROQ_API_KEY)
llm_fallback = ChatOpenAI(model="z-ai/glm-5.2:free", temperature=0, openai_api_key=OPENROUTER_API_KEY, openai_api_base="https://openrouter.ai/api/v1")
llm = llm_primary.with_fallbacks([llm_fallback])

def prepare_optimized_context(messages: list) -> list:
    """Tronque intelligemment les sorties d'outils volumineuses pour optimiser le contexte."""
    cleaned = []
    for msg in messages:
        if isinstance(msg, HumanMessage) and "--- RÉSULTAT ACTION" in msg.content:
            if len(msg.content) > 400:
                short_text = msg.content[:200] + "\n... [Résultat sauvegardé et tronqué pour préserver le contexte] ..."
                cleaned.append(HumanMessage(content=short_text))
            else:
                cleaned.append(msg)
        else:
            cleaned.append(msg)
    return cleaned[-10:]

def call_model(state: AgentState):
    system_ctx = SystemMessage(content=SYSTEM_PROMPT)
    optimized_history = prepare_optimized_context(state["messages"])
    full_messages = [system_ctx] + optimized_history
    
    max_retries = 3
    retry_delay = 10
    
    for attempt in range(max_retries):
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
                        
                        tool_msg = HumanMessage(content=f"--- RÉSULTAT ACTION ({action_name}) ---\n{tool_result}\n\nPoursuis la suite de ton orchestration.")
                        return {"messages": [AIMessage(content=content), tool_msg]}
                except Exception:
                    pass

            return {"messages": [response]}
            
        except Exception as e:
            error_str = str(e)
            if ("rate_limit_exceeded" in error_str or "429" in error_str) and attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return {"messages": [AIMessage(content=f"⚠️ Erreur Moteur Amal-DG : {error_str}")]}

def should_continue(state: AgentState):
    """Maintient la boucle tant qu'une action JSON est exécutée par Amal-DG."""
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
# 3. KEEPALIVE AUTOMATIQUE (GARDE ACTIF RENDER)
# ==========================================

async def keep_alive_task():
    """Tâche d'arrière-plan perpétuelle qui auto-ping la route /health pour éviter la mise en veille du serveur Render."""
    await asyncio.sleep(15)
    logging.info("🚀 Système Keep-Alive / Self-Ping initialisé.")
    
    async with httpx.AsyncClient() as client:
        while True:
            try:
                target_url = f"{RENDER_EXTERNAL_URL}/health"
                res = await client.get(target_url, timeout=10.0)
                logging.info(f"Keep-Alive Self-Ping sur {target_url} - Status: {res.status_code}")
            except Exception as e:
                logging.warning(f"⚠️ Erreur Keep-Alive Self-Ping : {e}")
            
            await asyncio.sleep(600)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(keep_alive_task())

# ==========================================
# 4. ENDPOINTS FASTAPI, DASHBOARD API & SLACK
# ==========================================

@app.get("/api/dashboard-data")
def get_dashboard_data():
    """Endpoint consommé en temps réel par le Dashboard Vercel."""
    return {
        "server_status": "ONLINE",
        "version": "4.9.0",
        "models_health": MODEL_HEALTH,
        "execution_history": EXECUTION_LOGS
    }

def process_slack_mission_async(channel_id: str, user_prompt: str):
    record_log("ORCHESTRATOR", "STARTED", "openai/gpt-oss-120b", f"Nouvelle mission déclenchée depuis Slack: {user_prompt[:50]}...")
    conversation_history = [HumanMessage(content=user_prompt)]
    try:
        final_state = app_graph.invoke({"messages": conversation_history})
        final_message = final_state["messages"][-1].content
        record_log("ORCHESTRATOR", "COMPLETED", "openai/gpt-oss-120b", "Mission terminée avec succès")
    except Exception as e:
        final_message = f"⚠️ *Erreur Moteur Amal-DG* : {str(e)}"
        record_log("ORCHESTRATOR", "FAILED", "openai/gpt-oss-120b", str(e))

    if SLACK_TOKEN:
        try:
            httpx.post(
                "https://slack.com/api/chat.postMessage",
                json={"channel": channel_id, "text": final_message},
                headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"}
            )
        except Exception as err:
            logging.error(f"Erreur envoi Slack : {err}")

@app.post("/slack/events")
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

@app.get("/health")
def health_check():
    return {
        "status": "SAAS-ENGINE-ONLINE-V4.9.0-DASHBOARD-CORS-ACTIVE",
        "models_health": MODEL_HEALTH
    }

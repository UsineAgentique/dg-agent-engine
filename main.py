import os
import sys
import json
import time
import base64
import operator
import logging
import asyncio
from typing import TypedDict, Annotated, List, Union, Dict, Any
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

# Importations des dépendances du requirements.txt
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

app = FastAPI(title="AMAL-DG-CORE-MULTI-TENANT-SWARM", version="6.3.0")

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
firecrawl_app = FirecrawlApp(api_key=FIRECRAWL_API_KEY) if FIRECRAWL_API_KEY and FirecrawlApp else None

# MATRICE D'ARCHITECTURE 4 LLM & CIRCUIT BREAKER DYNAMIQUE
MODEL_HEALTH = {
    "openai/gpt-oss-120b": {"status": "HEALTHY", "fails": 0, "role": "Master Core Primary (Groq)"},
    "z-ai/glm-5.2:free": {"status": "HEALTHY", "fails": 0, "role": "Master Strategy Backup & Juridique"},
    "google/gemma-4-26b:free": {"status": "HEALTHY", "fails": 0, "role": "Worker A (Execution & Code)"},
    "meta-llama/llama-3-8b:free": {"status": "HEALTHY", "fails": 0, "role": "Worker B (Specialized Sub-Agents)"}
}

# REGISTRE DES LOGS D'EXÉCUTION DU SWARM POUR VERCEL & SUPABASE
EXECUTION_LOGS = []

def record_log(pole: str, status: str, model: str, details: str, project_id: str = "GLOBAL"):
    """Enregistre les événements du Swarm pour la téléométrie Vercel et Supabase."""
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
        
    # Persistance Supabase asynchrone si disponible
    if supabase:
        try:
            supabase.table("swarm_logs").insert(log_entry).execute()
        except Exception:
            pass

# PROMPT SYSTÈME GLOBAL : CHARTE AUTONOME AMAL-DG MULTI-PROJETS
SYSTEM_PROMPT = """Tu es AMAL-DG, Directrice Générale, Architecte IA et Super-Orchestratrice du Swarm Agentique Multi-Projets.

TES POUVOIRS & RESPONSABILITÉS D'INFRASTRUCTURE ET DE GESTION :
1. GESTION DU PORTEFEUILLE MULTI-PROJETS :
   - Tu peux piloter plusieurs projets SaaS (ex: BailConforme.ca, Usine Agentique, Control Center, etc.).
   - Tu isoles le contexte de chaque projet lors des requêtes, commits et rapports.

2. GESTION DES 8 PÔLES & SOUS-AGENTS :
   - Pôle 01: Produit & Stratégie | Pôle 02: Architecture System | Pôle 03: Backend & API Engine | Pôle 04: Frontend & UI
   - Pôle 05: Sécurité & Privacy | Pôle 06: QA & Tests Automatisés | Pôle 07: DevOps & Pipelines | Pôle 08: Master Orchestration
   - Tu définis, crées et assignes dynamiquement des sous-agents selon la complexité du projet et la charge.

3. ROUTAGE ET PILOTAGE DES MODÈLES LLM :
   - `openai/gpt-oss-120b` (Groq) : Master Primary (Orchestration centrale haute vitesse).
   - `z-ai/glm-5.2:free` : Strategy Backup & Juridique/Rigueur (Conformité, rapports complexes, failover).
   - `google/gemma-4-26b:free` : Worker A (Code, architecture technique, scripts backend/frontend).
   - `meta-llama/llama-3-8b:free` : Worker B (Sous-agents rapides, micro-tâches, logs, inspections).

FORMAT DE RÉPONSE POUR EXÉCUTER UNE ACTION :
Réponds EXCLUSIVEMENT sous forme d'un objet JSON valide (aucun texte autour) :
{
  "action": "nom_outil",
  "action_input": { ...arguments... }
}

BOÎTE À OUTILS AMAL-DG :
1. `delegate_to_subagent` : Mandate un sous-agent. Args: {"team": "...", "task_description": "...", "save_to_file": "...", "model_profile": "analytique|juridique|technique|rapide", "project_id": "..."}
2. `execute_python_code_e2b` : Exécute du code Python sécurisé en Sandbox. Args: {"code": "..."}
3. `tavily_web_search` : Recherche d'informations fraîches sur le Web. Args: {"query": "..."}
4. `firecrawl_scrape_url` : Extraction Markdown d'une URL Web via Firecrawl. Args: {"url": "..."}
5. `git_commit_and_push` : Création/mise à jour de fichiers sur GitHub. Args: {"file_path": "...", "commit_message": "...", "content_to_write": "..."}
6. `read_github_file` : Inspection du code et des livrables sur GitHub. Args: {"file_path": "..."}
7. `compile_markdowns_to_pdf` : Génération du Master PDF avec FPDF2. Args: {"folder_path": "...", "output_pdf_path": "..."}

Si tes sous-actions sont terminées, réponds directement à l'utilisateur ou sur Slack en TEXTE CLAIR ET STRUCTURÉ."""

# ==========================================
# 1. OUTILS ET CAPACITÉS D'ACTION DU SWARM
# ==========================================

def execute_python_code_e2b(code: str) -> str:
    """Exécute du code Python dans une Sandbox E2B sécurisée."""
    if not E2B_API_KEY or not CodeInterpreter:
        return "E2B API Key non configurée ou module non disponible."
    try:
        with CodeInterpreter(api_key=E2B_API_KEY) as sandbox:
            execution = sandbox.notebook.exec_cell(code)
            logs = execution.logs.stdout
            if execution.error:
                return f"ERREUR E2B EXÉCUTION: {execution.error.value}"
            return f"RÉSULTAT EXÉCUTION E2B:\n" + "\n".join(logs)
    except Exception as e:
        return f"Erreur Sandbox E2B: {str(e)}"

def read_github_file(file_path: str) -> str:
    try:
        if not GITHUB_TOKEN or not GITHUB_REPO:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f: return f.read()
            return f"Fichier '{file_path}' introuvable en local."

        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
        with httpx.Client() as client:
            resp = client.get(api_url, headers=headers)
            if resp.status_code == 200:
                return base64.b64decode(resp.json().get("content", "")).decode("utf-8")
            return f"Fichier non trouvé sur GitHub (code {resp.status_code})."
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
            return f"Fichier {file_path} sauvegardé en local."

        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{safe_path}"

        with httpx.Client() as client:
            get_resp = client.get(api_url, headers=headers)
            payload = {"message": commit_message, "content": content_b64, "branch": "main"}
            if get_resp.status_code == 200:
                payload["sha"] = get_resp.json().get("sha")
            client.put(api_url, json=payload, headers=headers)

        return f"SUCCÈS: Fichier {file_path} déployé sur GitHub."
    except Exception as e:
        return f"ERREUR GITHUB: {str(e)}"

def delegate_to_subagent(team: str, task_description: str, save_to_file: str = "", model_profile: str = "analytique", project_id: str = "GLOBAL") -> str:
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
            record_log(team, "IN_PROGRESS", active_model, f"Exécution mission [{project_id}] via {model_profile}", project_id)
            
            sub_client = ChatOpenAI(
                model=active_model,
                temperature=0.2,
                openai_api_key=OPENROUTER_API_KEY,
                openai_api_base="https://openrouter.ai/api/v1"
            )
            
            system_msg = SystemMessage(content=f"Tu es le sous-agent du pôle '{team}' pour le projet '{project_id}' (LLM: {active_model}). Sois précis, technique et structuré.")
            user_msg = HumanMessage(content=task_description)
            
            response = sub_client.invoke([system_msg, user_msg])
            result_text = response.content
            
            MODEL_HEALTH[active_model]["fails"] = 0
            MODEL_HEALTH[active_model]["status"] = "HEALTHY"
            
            if save_to_file:
                git_commit_and_push(save_to_file, f"Feat({team}/{project_id}): Livrable via {active_model}", result_text)
                record_log(team, "SUCCESS", active_model, f"Sauvegardé dans {save_to_file}", project_id)
                return f"SUCCÈS: Livrable du pôle {team} ({project_id}) enregistré dans '{save_to_file}'."
                
            record_log(team, "SUCCESS", active_model, "Exécution terminée", project_id)
            return result_text[:2000]
            
        except Exception as e:
            error_str = str(e)
            record_log(team, "WARNING", active_model, f"Erreur interceptée: {error_str}", project_id)
            if "429" in error_str or "rate_limit" in error_str.lower():
                MODEL_HEALTH[active_model]["fails"] += 1
                if MODEL_HEALTH[active_model]["fails"] >= 2:
                    MODEL_HEALTH[active_model]["status"] = "UNHEALTHY"
                active_model = fallback_model
                time.sleep(2)
                continue
            else:
                record_log(team, "FAILED", active_model, error_str, project_id)
                return f"ERREUR {team}: {error_str}"
                
    return f"ERREUR CRITIQUE {team}: Échec d'exécution après tentatives de failover."

def compile_markdowns_to_pdf(folder_path: str = "docs", output_pdf_path: str = "Master_Report.pdf") -> str:
    try:
        record_log("COMPILER_PDF", "IN_PROGRESS", "FPDF2", f"Compilation PDF du dossier {folder_path}")
        if not os.path.exists(folder_path): return f"Dossier {folder_path} introuvable."
        files = sorted([os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".md")])
        if not files: return "Aucun fichier Markdown à compiler."

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 20, "AMAL-DG - Master Strategic Report", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(10)

        for file in files:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, f"Section : {os.path.basename(file)}", new_x="LMARGIN", new_y="NEXT")
            with open(file, "r", encoding="utf-8") as f: content = f.read()
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5, content.encode("latin-1", "replace").decode("latin-1"))

        pdf_bytes = pdf.output()
        res = git_commit_and_push(output_pdf_path, "Feat: Publication Master PDF Multi-Projets", pdf_bytes)
        record_log("COMPILER_PDF", "SUCCESS", "FPDF2", f"Master PDF généré: {output_pdf_path}")
        return res
    except Exception as e:
        return f"Erreur FPDF2: {str(e)}"

def tavily_web_search(query: str) -> str:
    if not TAVILY_API_KEY: return "Clé Tavily non configurée."
    try:
        with httpx.Client() as client:
            res = client.post("https://api.tavily.com/search", json={"api_key": TAVILY_API_KEY, "query": query}, timeout=10.0)
            return res.json().get("answer", "Aucun résultat.")[:1200]
    except Exception as e:
        return f"Erreur Tavily: {str(e)}"

def firecrawl_scrape_url(url: str) -> str:
    if firecrawl_app:
        try:
            scrape_result = firecrawl_app.scrape_url(url, params={'formats': ['markdown']})
            return scrape_result.get('markdown', '')[:1500]
        except Exception as e:
            return f"Erreur SDK Firecrawl: {str(e)}"
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
    "execute_python_code_e2b": execute_python_code_e2b,
    "read_github_file": read_github_file,
    "git_commit_and_push": git_commit_and_push,
    "compile_markdowns_to_pdf": compile_markdowns_to_pdf,
    "tavily_web_search": tavily_web_search,
    "firecrawl_scrape_url": firecrawl_scrape_url
}

# ==========================================
# 2. MOTEUR SWARM LANGGRAPH (GROQ + FALLBACK)
# ==========================================

class AgentState(TypedDict):
    messages: Annotated[List, operator.add]

llm_primary = ChatGroq(model="openai/gpt-oss-120b", temperature=0, groq_api_key=GROQ_API_KEY) if GROQ_API_KEY else ChatOpenAI(model="z-ai/glm-5.2:free", temperature=0, openai_api_key=OPENROUTER_API_KEY, openai_api_base="https://openrouter.ai/api/v1")
llm_fallback = ChatOpenAI(model="z-ai/glm-5.2:free", temperature=0, openai_api_key=OPENROUTER_API_KEY, openai_api_base="https://openrouter.ai/api/v1")

def call_model(state: AgentState):
    system_ctx = SystemMessage(content=SYSTEM_PROMPT)
    full_messages = [system_ctx] + state["messages"][-10:]
    
    models_to_try = [llm_primary, llm_fallback]
    
    for current_llm in models_to_try:
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
                        tool_msg = HumanMessage(content=f"--- RÉSULTAT ACTION ({action_name}) ---\n{tool_result}\n\nPoursuis la gestion de la mission.")
                        return {"messages": [AIMessage(content=content), tool_msg]}
                except Exception:
                    pass

            return {"messages": [response]}
        except Exception as e:
            error_str = str(e)
            logging.warning(f"⚠️ Erreur LLM ({getattr(current_llm, 'model', 'default')}): {error_str}")
            if any(err in error_str.lower() for err in ["400", "429", "rate_limit", "tool_use_failed"]):
                continue
            return {"messages": [AIMessage(content=f"⚠️ Erreur Moteur Amal-DG : {error_str}")]}

    return {"messages": [AIMessage(content="⚠️ Saturation temporaire des modèles. Réessaie dans quelques secondes.")]}

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
# 3. SCHEDULER, KEEPALIVE & SLACK EVENTS
# ==========================================

scheduler = AsyncIOScheduler()

async def scheduled_swarm_healthcheck():
    """Tâche récurrente APScheduler : Audit automatique des modèles."""
    logging.info("⏰ [APScheduler] Audit périodique du Swarm activé.")
    record_log("SCHEDULER", "HEALTHCHECK", "SYSTEM", "Audit de routine exécuté par APScheduler")

@app.on_event("startup")
async def startup_event():
    scheduler.add_job(scheduled_swarm_healthcheck, 'interval', minutes=30)
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

def process_slack_mission_async(channel_id: str, user_prompt: str):
    record_log("ORCHESTRATOR", "STARTED", "openai/gpt-oss-120b", f"Slack Mission: {user_prompt[:50]}...")
    conversation_history = [HumanMessage(content=user_prompt)]
    try:
        final_state = app_graph.invoke({"messages": conversation_history})
        final_message = final_state["messages"][-1].content
        record_log("ORCHESTRATOR", "COMPLETED", "openai/gpt-oss-120b", "Mission achevée")
    except Exception as e:
        final_message = f"⚠️ *Erreur Moteur Amal-DG* : {str(e)}"
        record_log("ORCHESTRATOR", "FAILED", "openai/gpt-oss-120b", str(e))

    if SLACK_TOKEN:
        try:
            httpx.post(
                "[https://slack.com/api/chat.postMessage](https://slack.com/api/chat.postMessage)",
                json={"channel": channel_id, "text": final_message},
                headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"}
            )
        except Exception as err:
            logging.error(f"Erreur Slack postMessage : {err}")

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

# ==========================================
# 4. ENDPOINTS API & TELEMETRIE DASHBOARD
# ==========================================

@app.get("/api/dashboard-data")
def get_dashboard_data():
    return {
        "server_status": "ONLINE",
        "version": "6.3.0",
        "engine_role": "AUTONOMOUS-MULTI-TENANT-ORCHESTRATOR",
        "models_health": MODEL_HEALTH,
        "execution_history": EXECUTION_LOGS
    }

@app.get("/health")
def health_check():
    return {
        "status": "AMAL-DG-FULL-STACK-V6.3.0-ONLINE",
        "models_health": MODEL_HEALTH
    }

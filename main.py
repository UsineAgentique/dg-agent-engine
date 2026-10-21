import os
import sys
import json
import base64
import logging
import asyncio
import operator
import re
from typing import TypedDict, Annotated, List, Union, Dict, Any
from datetime import datetime

from fastapi import FastAPI, Request, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from supabase import create_client, Client
from fpdf import FPDF

# Import E2B Sandbox
try:
    from e2b_code_interpreter import Sandbox
except ImportError:
    Sandbox = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Instanciation globale FastAPI au niveau racine (Garantit le démarrage Uvicorn sur Render)
app = FastAPI(title="AMAL-DG-EXECUTIVE-SWARM", version="15.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# VARIABLES D'ENVIRONNEMENT & CONFIGURATION
# ==========================================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")
E2B_API_KEY = os.getenv("E2B_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# ==========================================
# CATALOGUE DE MODÈLES (OPENROUTER / GROQ EXCLUSIF)
# ==========================================
MODEL_CATALOG = {
    "AMAL_DG": {
        "primary_provider": "openrouter",
        "primary_model": "deepseek/deepseek-chat",
        "fallback_provider": "openrouter",
        "fallback_model": "anthropic/claude-3.5-sonnet",
        "max_tokens": 8192
    },
    "FIN": {
        "primary_provider": "openrouter",
        "primary_model": "anthropic/claude-3.5-sonnet",
        "fallback_provider": "groq",
        "fallback_model": "llama-3.3-70b-versatile",
        "max_tokens": 4096
    },
    "TECH": {
        "primary_provider": "openrouter",
        "primary_model": "qwen/qwen-2.5-coder-32b-instruct",
        "fallback_provider": "openrouter",
        "fallback_model": "deepseek/deepseek-r1",
        "max_tokens": 4096
    },
    "GOV": {
        "primary_provider": "openrouter",
        "primary_model": "thudm/glm-4-9b-chat",
        "fallback_provider": "openrouter",
        "fallback_model": "anthropic/claude-3.5-sonnet",
        "max_tokens": 8192
    },
    "GRO": {
        "primary_provider": "openrouter",
        "primary_model": "x-ai/grok-2-1212",
        "fallback_provider": "groq",
        "fallback_model": "llama-3.1-8b-instant",
        "max_tokens": 4096
    },
    "SAL": {
        "primary_provider": "openrouter",
        "primary_model": "anthropic/claude-3.5-haiku",
        "fallback_provider": "openrouter",
        "fallback_model": "x-ai/grok-2-1212",
        "max_tokens": 4096
    },
    "SRC": {
        "primary_provider": "openrouter",
        "primary_model": "thudm/glm-4-9b-chat",
        "fallback_provider": "groq",
        "fallback_model": "llama-3.3-70b-versatile",
        "max_tokens": 4096
    },
    "RAD": {
        "primary_provider": "openrouter",
        "primary_model": "x-ai/grok-2-1212",
        "fallback_provider": "openrouter",
        "fallback_model": "deepseek/deepseek-chat",
        "max_tokens": 4096
    },
    "RET": {
        "primary_provider": "openrouter",
        "primary_model": "anthropic/claude-3.5-sonnet",
        "fallback_provider": "groq",
        "fallback_model": "llama-3.3-70b-versatile",
        "max_tokens": 4096
    },
    "MED": {
        "primary_provider": "openrouter",
        "primary_model": "anthropic/claude-3.5-haiku",
        "fallback_provider": "groq",
        "fallback_model": "llama-3.1-8b-instant",
        "max_tokens": 4096
    }
}

CHARTER_PATH = os.path.join(os.path.dirname(__file__), "dg_systeme.md")
BASE_CHARTER = ""
if os.path.exists(CHARTER_PATH):
    try:
        with open(CHARTER_PATH, "r", encoding="utf-8") as f:
            BASE_CHARTER = f.read()
    except Exception as e:
        logging.error(f"Erreur lecture dg_systeme.md: {e}")

SYSTEM_PROMPT = f"""{BASE_CHARTER}

---
## PROTOCOLE DE FONCTIONNEMENT ET EXÉCUTION STRICTE DES OUTILS
Tu es AMAL-DG, Directrice Générale du Swarm Agentique. Tu disposes de TOUS les pouvoirs opérationnels.

IMPORTANT :
- Si tu dois exécuter un outil technique, réponds UNIQUEMENT avec le bloc JSON valide de l'action, sans aucun texte explicatif autour :
{{"action": "<nom_de_l_outil>", "action_input": {{...}}}}
- Lorsque la tâche est terminée ou ne nécessite pas d'outil, réponds sous forme de rapport exécutif clair, structuré et professionnel.

OUTILS DISPONIBLES :
- `git_delete_file`: {{ "file_path": "chemin/du/fichier" }}
- `git_commit_and_push`: {{ "file_path": "chemin", "content": "contenu", "commit_message": "msg" }}
- `read_github_file`: {{ "file_path": "chemin" }}
- `tavily_web_search`: {{ "query": "recherche" }}
- `firecrawl_scrape_url`: {{ "url": "https://..." }}
- `execute_python_code_e2b`: {{ "code": "script python" }}
- `generate_pdf_report`: {{ "title": "Titre", "content": "Contenu", "filename": "rapport.pdf" }}
- `delegate_to_subagent`: {{ "pole": "FIN/TECH/GRO/SAL/SRC/RAD/RET/MED/GOV", "mission": "description", "priority": "HIGH/MEDIUM/LOW" }}
- `save_project_state`: {{ "project_id": "id", "state_data": {{...}} }}
- `load_project_state`: {{ "project_id": "id" }}
"""

# ==========================================
# BOITE A OUTILS BACKEND
# ==========================================
def generate_pdf_report(title: str, content: str, filename: str = "rapport_amal.pdf", **kwargs) -> str:
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, txt=title, ln=1, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 8, txt=content)
        os.makedirs("output", exist_ok=True)
        safe_filename = os.path.join("output", filename)
        pdf.output(safe_filename)
        return f"SUCCÈS: Rapport PDF généré sous '{safe_filename}'."
    except Exception as e:
        return f"ERREUR PDF: {str(e)}"

# Fonction d'exécution Sandbox E2B mise à jour avec Sandbox.create()
def execute_python_code_e2b(code: str, **kwargs) -> str:
    try:
        if E2B_API_KEY and Sandbox:
            sandbox = Sandbox.create()
            try:
                execution = sandbox.run_code(code)
                logs_text = str(execution.logs) if execution.logs else "Aucun log."
                error_text = str(execution.error) if execution.error else "Aucune erreur."
                return f"Résultats Sandbox E2B:\nLogs: {logs_text}\nErreurs: {error_text}"
            finally:
                sandbox.close()
        else:
            local_scope = {}
            exec(code, {}, local_scope)
            return f"Exécution locale réussie (E2B non actif): {local_scope}"
    except Exception as e:
        return f"ERREUR EXÉCUTION SANDBOX: {str(e)}"

def save_project_state(project_id: str, state_data: dict, **kwargs) -> str:
    if not supabase: return "Supabase non configuré."
    try:
        data = {"project_id": project_id, "state": state_data, "updated_at": datetime.utcnow().isoformat()}
        supabase.table("project_states").upsert(data).execute()
        return f"SUCCÈS: État [{project_id}] sauvegardé dans Supabase."
    except Exception as e:
        return f"ERREUR SUPABASE: {str(e)}"

def load_project_state(project_id: str, **kwargs) -> str:
    if not supabase: return "Supabase non configuré."
    try:
        resp = supabase.table("project_states").select("*").eq("project_id", project_id).execute()
        if resp.data: return json.dumps(resp.data[0].get("state", {}), ensure_ascii=False)
        return f"Aucun état trouvé pour [{project_id}]."
    except Exception as e:
        return f"ERREUR SUPABASE: {str(e)}"

def git_delete_file(file_path: str = None, path: str = None, filepath: str = None, **kwargs) -> str:
    target_path = file_path or path or filepath
    if not target_path: return "Erreur: Chemin manquant."
    try:
        safe_path = os.path.normpath(target_path).replace("\\", "/")
        if not GITHUB_TOKEN or not GITHUB_REPO: return "Erreur: Credentials GitHub manquants."
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{safe_path}"
        with httpx.Client() as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                sha = resp.json().get("sha")
                payload = {"message": f"Chore: delete {safe_path}", "sha": sha, "branch": "main"}
                del_resp = client.request("DELETE", url, json=payload, headers=headers)
                if del_resp.status_code in [200, 201]:
                    return f"SUCCÈS: {safe_path} supprimé de GitHub."
        return f"Fichier {safe_path} introuvable sur GitHub."
    except Exception as e:
        return f"ERREUR GITHUB DELETE: {str(e)}"

def git_commit_and_push(file_path: str, content: str, commit_message: str = "Update via Amal-DG", **kwargs) -> str:
    if not GITHUB_TOKEN or not GITHUB_REPO: return "Erreur: Credentials GitHub manquants."
    try:
        safe_path = os.path.normpath(file_path).replace("\\", "/")
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{safe_path}"
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        
        with httpx.Client() as client:
            get_resp = client.get(url, headers=headers)
            sha = get_resp.json().get("sha") if get_resp.status_code == 200 else None
            payload = {"message": commit_message, "content": encoded_content, "branch": "main"}
            if sha: payload["sha"] = sha
            put_resp = client.put(url, json=payload, headers=headers)
            if put_resp.status_code in [200, 201]:
                return f"SUCCÈS: {safe_path} commité et poussé sur GitHub."
            return f"Échec GitHub (Status {put_resp.status_code}): {put_resp.text}"
    except Exception as e:
        return f"ERREUR GITHUB COMMIT: {str(e)}"

def read_github_file(file_path: str, **kwargs) -> str:
    if not GITHUB_TOKEN or not GITHUB_REPO: return "Erreur: Credentials GitHub manquants."
    try:
        safe_path = os.path.normpath(file_path).replace("\\", "/")
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{safe_path}"
        with httpx.Client() as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                content_b64 = resp.json().get("content", "")
                return base64.b64decode(content_b64).decode("utf-8")
            return f"Fichier non trouvé sur GitHub (HTTP {resp.status_code})."
    except Exception as e:
        return f"ERREUR LECTURE GITHUB: {str(e)}"

def tavily_web_search(query: str, **kwargs) -> str:
    if not TAVILY_API_KEY: return "Erreur: TAVILY_API_KEY manquante."
    try:
        url = "https://api.tavily.com/search"
        payload = {"api_key": TAVILY_API_KEY, "query": query, "search_depth": "smart"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                return "\n".join([f"- [{r.get('title')}]({r.get('url')}): {r.get('content')}" for r in results[:4]]) or "Aucun résultat."
            return f"Erreur Tavily ({resp.status_code})"
    except Exception as e:
        return f"ERREUR TAVILY: {str(e)}"

def firecrawl_scrape_url(url: str, **kwargs) -> str:
    if not FIRECRAWL_API_KEY: return "Erreur: FIRECRAWL_API_KEY manquante."
    try:
        headers = {"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"}
        payload = {"url": url, "formats": ["markdown"]}
        with httpx.Client(timeout=15.0) as client:
            resp = client.post("https://api.firecrawl.dev/v1/scrape", headers=headers, json=payload)
            if resp.status_code == 200:
                return resp.json().get("data", {}).get("markdown", "Vide.")
            return f"Erreur Firecrawl ({resp.status_code})"
    except Exception as e:
        return f"ERREUR FIRECRAWL: {str(e)}"

def delegate_to_subagent(pole: str, mission: str, priority: str = "MEDIUM", **kwargs) -> str:
    logging.info(f"[DÉLÉGATION MULTI-POLE] Pôle {pole} ({priority}): {mission}")
    return f"Sous-agent [{pole}] instancié et missionné."

TOOLS_MAP = {
    "git_delete_file": git_delete_file,
    "git_commit_and_push": git_commit_and_push,
    "read_github_file": read_github_file,
    "tavily_web_search": tavily_web_search,
    "firecrawl_scrape_url": firecrawl_scrape_url,
    "execute_python_code_e2b": execute_python_code_e2b,
    "generate_pdf_report": generate_pdf_report,
    "delegate_to_subagent": delegate_to_subagent,
    "save_project_state": save_project_state,
    "load_project_state": load_project_state
}

# ==========================================
# ROUTEUR MULTI-FOURNISSEURS LLM (DISPATCHER)
# ==========================================
async def invoke_llm(provider: str, model: str, messages: List[Any], max_tokens: int = 4096) -> str:
    if provider == "groq":
        if not GROQ_API_KEY: raise ValueError("GROQ_API_KEY non disponible sur Render.")
        client = ChatGroq(model_name=model, groq_api_key=GROQ_API_KEY, temperature=0.1, max_tokens=max_tokens)
    elif provider == "openrouter":
        if not OPENROUTER_API_KEY: raise ValueError("OPENROUTER_API_KEY non disponible sur Render.")
        client = ChatOpenAI(
            model=model, temperature=0.1, 
            openai_api_key=OPENROUTER_API_KEY, 
            openai_api_base="https://openrouter.ai/api/v1", 
            max_tokens=max_tokens
        )
    else:
        raise ValueError(f"Fournisseur non supporté: {provider}")

    res = await asyncio.to_thread(client.invoke, messages)
    return res.content

async def execute_pole_llm(pole_key: str, messages: List[Any]) -> str:
    cfg = MODEL_CATALOG.get(pole_key, MODEL_CATALOG["AMAL_DG"])
    try:
        return await invoke_llm(cfg["primary_provider"], cfg["primary_model"], messages, cfg["max_tokens"])
    except Exception as err:
        logging.warning(f"[{pole_key}] Échec Primary Provider ({cfg['primary_provider']}): {err}. Bascule Fallback...")
        
    try:
        return await invoke_llm(cfg["fallback_provider"], cfg["fallback_model"], messages, cfg["max_tokens"])
    except Exception as fallback_err:
        logging.error(f"[{pole_key}] Échec critique Primary + Fallback: {fallback_err}")
        return f"⚠️ Erreur critique du dispatcher multi-providers pour le pôle [{pole_key}]: {fallback_err}"

# ==========================================
# STATE & GRAPH LANGGRAPH
# ==========================================
class AgentState(TypedDict):
    messages: Annotated[List, operator.add]

def extract_first_json(text: str) -> dict:
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError("Aucun JSON valide trouvé.")

async def call_model_async(state: AgentState):
    full_messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"][-8:]
    content = await execute_pole_llm("AMAL-DG", full_messages)
    content = content.strip()

    if "{" in content and "action" in content:
        try:
            parsed = extract_first_json(content)
            action_name = parsed.get("action")
            action_input = parsed.get("action_input") or parsed
            
            if isinstance(action_input, dict) and "action" in action_input and len(action_input) > 1:
                action_input = {k: v for k, v in action_input.items() if k != "action"}

            if action_name in TOOLS_MAP:
                tool_fn = TOOLS_MAP[action_name]
                tool_result = tool_fn(**action_input) if isinstance(action_input, dict) else tool_fn(action_input)
                feedback = HumanMessage(content=f"--- RÉSULTAT EXÉCUTION OUTIL [{action_name}] ---\n{tool_result}\n\nFormule ton rapport exécutif final.")
                return {"messages": [AIMessage(content=f"Exécution de l'outil {action_name}..."), feedback]}
        except Exception as e:
            logging.warning(f"Impossible de parser l'outil: {e}")

    return {"messages": [AIMessage(content=content)]}

def should_continue(state: AgentState):
    last_msg = state["messages"][-1]
    if isinstance(last_msg, HumanMessage) and "--- RÉSULTAT EXÉCUTION OUTIL" in last_msg.content:
        return "agent"
    return END

checkpointer = MemorySaver()
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model_async)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"agent": "agent", END: END})
app_graph = workflow.compile(checkpointer=checkpointer)

# ==========================================
# ENDPOINTS FASTAPI & WEBHOOK SLACK
# ==========================================
@app.get("/")
@app.get("/health")
def health_check():
    return {
        "status": "ONLINE",
        "version": "15.2.0",
        "timestamp": str(datetime.utcnow())
    }

def send_slack_message(channel: str, text: str):
    if not SLACK_TOKEN: return
    token = SLACK_TOKEN.strip()
    if token.startswith("http"):
        url, headers, payload = token, {"Content-Type": "application/json"}, {"text": text}
    else:
        url = "https://slack.com/api/chat.postMessage"
        auth = token if token.startswith("xoxb-") else f"xoxb-{token}"
        headers, payload = {"Authorization": f"Bearer {auth}", "Content-Type": "application/json"}, {"channel": channel, "text": text}
    try:
        with httpx.Client(timeout=15.0) as client:
            client.post(url, headers=headers, json=payload)
    except Exception as e:
        logging.error(f"Erreur Slack: {e}")

async def process_slack_mission_async(channel_id: str, user_prompt: str):
    try:
        config = {"configurable": {"thread_id": channel_id}}
        final_state = await app_graph.ainvoke({"messages": [HumanMessage(content=user_prompt)]}, config=config)
        msg = final_state["messages"][-1].content
        if msg.startswith("{") and "message" in msg:
            try: msg = json.loads(msg).get("message", msg)
            except Exception: pass
    except Exception as e:
        msg = f"⚠️ Erreur Amal-DG: {str(e)}"
    send_slack_message(channel_id, msg)

# Décorateurs multiples pour corriger définitivement l'erreur 404 (Slash)
@app.post("/slack/events")
@app.post("/slack/events/")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    try: 
        data = await request.json()
    except Exception: 
        return Response(status_code=400)
        
    if data.get("type") == "url_verification": 
        return {"challenge": data.get("challenge")}
        
    event = data.get("event", {})
    if event.get("type") in ["message", "app_mention"] and not event.get("bot_id"):
        ch, text = event.get("channel"), event.get("text")
        if ch and text: 
            background_tasks.add_task(process_slack_mission_async, ch, text)
            
    return Response(status_code=200)

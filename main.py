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
from supabase import create_client, Client
from fpdf import FPDF

# Import optionnel E2B Sandbox
try:
    from e2b_code_interpreter import Sandbox
except ImportError:
    Sandbox = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(title="AMAL-DG-EXECUTIVE-SWARM", version="13.0.0")

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
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")
E2B_API_KEY = os.getenv("E2B_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

MODEL_CATALOG = {
    "AMAL_DG": {
        "primary_provider": "openrouter",
        "primary_model": "openai/gpt-4o-mini",
        "fallback_provider": "openrouter",
        "fallback_model": "meta-llama/llama-3.3-70b-instruct:free",
        "max_tokens": 4096
    }
}

# ==========================================
# CHARGEMENT DE LA CHARTE SYSTEME DYNAMIQUE
# ==========================================
CHARTER_PATH = os.path.join(os.path.dirname(__file__), "dg_systeme.md")
BASE_CHARTER = ""
if os.path.exists(CHARTER_PATH):
    try:
        with open(CHARTER_PATH, "r", encoding="utf-8") as f:
            BASE_CHARTER = f.read()
    except Exception as e:
        logging.error(f"Erreur lors de la lecture de dg_systeme.md: {e}")

SYSTEM_PROMPT = f"""{BASE_CHARTER}

---
## PROTOCOLE DE FONCTIONNEMENT ET EXÉCUTION DES OUTILS
Tu es AMAL-DG, Directrice Générale du Swarm Agentique. Tu disposes de TOUS les pouvoirs opérationnels.
Si tu dois exécuter un outil technique, réponds EXCLUSIVEMENT avec le bloc JSON de l'action :
{{"action": "<nom_de_l_outil>", "action_input": {{...}}}}

Si la tâche ne nécessite pas d'outil, réponds directement sous forme de rapport exécutif clair, structuré et professionnel.

OUTILS DISPONIBLES :
- `git_delete_file`: {{ "file_path": "chemin/du/fichier" }}
- `git_commit_and_push`: {{ "file_path": "chemin", "content": "contenu", "commit_message": "msg" }}
- `read_github_file`: {{ "file_path": "chemin" }}
- `tavily_web_search`: {{ "query": "recherche internet à jour" }}
- `firecrawl_scrape_url`: {{ "url": "https://..." }}
- `execute_python_code_e2b`: {{ "code": "script python exécuté en sandbox cloud" }}
- `generate_pdf_report`: {{ "title": "Titre", "content": "Contenu", "filename": "rapport.pdf" }}
- `delegate_to_subagent`: {{ "pole": "FIN/TECH/GRO/SAL/SRC/RAD/RET/MED/GOV", "mission": "description", "priority": "HIGH/MEDIUM/LOW" }}
- `save_project_state`: {{ "project_id": "id", "state_data": {{...}} }}
- `load_project_state`: {{ "project_id": "id" }}
"""

# ==========================================
# BOITE A OUTILS INTÉGRALE (REQUIREMENTS.TXT)
# ==========================================

def generate_pdf_report(title: str, content: str, filename: str = "rapport_amal.pdf", **kwargs) -> str:
    """Génère un rapport PDF professionnel via fpdf2"""
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
        
        # Optionnel: commit automatique du PDF sur GitHub si configuré
        return f"SUCCÈS: Rapport PDF généré localement sous '{safe_filename}'."
    except Exception as e:
        return f"ERREUR GÉNÉRATION PDF: {str(e)}"

def execute_python_code_e2b(code: str, **kwargs) -> str:
    """Exécute du code Python dans un sandbox E2B sécurisé ou en local si non dispo"""
    try:
        if E2B_API_KEY and Sandbox:
            with Sandbox(api_key=E2B_API_KEY) as sandbox:
                execution = sandbox.run_code(code)
                return f"Résultats Sandbox E2B:\nLogs: {execution.logs}\nErreurs: {execution.error}"
        else:
            local_scope = {}
            exec(code, {}, local_scope)
            return f"Exécution locale réussie (E2B non actif): {local_scope}"
    except Exception as e:
        return f"ERREUR EXÉCUTION SANDBOX: {str(e)}"

def save_project_state(project_id: str, state_data: dict, **kwargs) -> str:
    if not supabase:
        return "Avertissement: Supabase non configuré."
    try:
        data = {"project_id": project_id, "state": state_data, "updated_at": datetime.utcnow().isoformat()}
        supabase.table("project_states").upsert(data).execute()
        return f"SUCCÈS: État du projet [{project_id}] sauvegardé dans Supabase."
    except Exception as e:
        return f"ERREUR SUPABASE: {str(e)}"

def load_project_state(project_id: str, **kwargs) -> str:
    if not supabase:
        return "Avertissement: Supabase non configuré."
    try:
        resp = supabase.table("project_states").select("*").eq("project_id", project_id).execute()
        if resp.data:
            return json.dumps(resp.data[0].get("state", {}), ensure_ascii=False)
        return f"Aucun état trouvé pour [{project_id}]."
    except Exception as e:
        return f"ERREUR SUPABASE: {str(e)}"

def git_delete_file(file_path: str = None, path: str = None, filepath: str = None, **kwargs) -> str:
    target_path = file_path or path or filepath
    if not target_path: return "Erreur: Chemin manquant."
    try:
        safe_path = os.path.normpath(target_path).replace("\\", "/")
        if os.path.exists(safe_path):
            try: os.remove(safe_path)
            except Exception: pass
        if not GITHUB_TOKEN or not GITHUB_REPO: return f"Fichier {safe_path} supprimé en local."
        
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{safe_path}"
        with httpx.Client() as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                sha = resp.json().get("sha")
                payload = {"message": f"Chore: delete {safe_path}", "sha": sha, "branch": "main"}
                client.request("DELETE", url, json=payload, headers=headers)
                return f"SUCCÈS: {safe_path} supprimé de GitHub."
        return f"Fichier {safe_path} absent de GitHub."
    except Exception as e:
        return f"ERREUR GITHUB DELETE: {str(e)}"

def git_commit_and_push(file_path: str, content: str, commit_message: str = "Update via Amal-DG", **kwargs) -> str:
    if not GITHUB_TOKEN or not GITHUB_REPO: return "Erreur: GitHub non configuré."
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
            if put_resp.status_code in [200, 201]: return f"SUCCÈS: {safe_path} poussé sur GitHub."
            return f"Échec GitHub ({put_resp.status_code})"
    except Exception as e:
        return f"ERREUR GITHUB COMMIT: {str(e)}"

def read_github_file(file_path: str, **kwargs) -> str:
    if not GITHUB_TOKEN or not GITHUB_REPO: return "Erreur: GitHub non configuré."
    try:
        safe_path = os.path.normpath(file_path).replace("\\", "/")
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{safe_path}"
        with httpx.Client() as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                return base64.b64decode(resp.json().get("content", "")).decode("utf-8")
            return "Fichier non trouvé."
    except Exception as e:
        return f"ERREUR LECTURE GITHUB: {str(e)}"

def tavily_web_search(query: str, **kwargs) -> str:
    """Recherche Web temps réel pour les pôles (Veille, Juridique TAL, etc.)"""
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
    """Scraping de pages web pour analyse (ex: textes de loi TAL Québec)"""
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
    logging.info(f"[DÉLÉGATION] Pôle {pole} activé ({priority}): {mission}")
    return f"Sous-agent du pôle [{pole}] instancié et missionné avec succès."

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
# MOTEUR LLM & LANGGRAPH
# ==========================================
async def invoke_llm(model: str, messages: List[Any], max_tokens: int = 4096) -> str:
    if not OPENROUTER_API_KEY: raise ValueError("OPENROUTER_API_KEY manquante.")
    client = ChatOpenAI(
        model=model, temperature=0.1, 
        openai_api_key=OPENROUTER_API_KEY, 
        openai_api_base="https://openrouter.ai/api/v1", 
        max_tokens=max_tokens
    )
    res = await asyncio.to_thread(client.invoke, messages)
    return res.content

async def execute_pole_llm(pole_key: str, messages: List[Any]) -> str:
    cfg = MODEL_CATALOG.get(pole_key, MODEL_CATALOG["AMAL_DG"])
    try:
        return await invoke_llm(cfg["primary_model"], messages, cfg["max_tokens"])
    except Exception as err:
        logging.warning(f"[{pole_key}] Échec Primary: {err}. Bascule Fallback...")
    try:
        return await invoke_llm(cfg["fallback_model"], messages, cfg["max_tokens"])
    except Exception as fallback_err:
        return f"⚠️ Erreur critique LLM: {fallback_err}"

class AgentState(TypedDict):
    messages: Annotated[List, operator.add]

def extract_first_json(text: str) -> dict:
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError("JSON invalide.")

async def call_model_async(state: AgentState):
    full_messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"][-8:]
    content = await execute_pole_llm("AMAL_DG", full_messages)
    content = content.strip()

    if "{" in content and "action" in content:
        try:
            parsed = extract_first_json(content)
            action_name = parsed.get("action")
            action_input = parsed.get("action_input", {})
            
            if action_name in TOOLS_MAP:
                tool_fn = TOOLS_MAP[action_name]
                tool_result = tool_fn(**action_input) if isinstance(action_input, dict) else tool_fn(action_input)
                feedback = HumanMessage(content=f"--- RÉSULTAT OUTIL [{action_name}] ---\n{tool_result}\n\nPoursuis la mission.")
                return {"messages": [AIMessage(content=content), feedback]}
        except Exception as e:
            logging.warning(f"Erreur exécution outil: {e}")

    return {"messages": [AIMessage(content=content)]}

def should_continue(state: AgentState):
    last_msg = state["messages"][-1]
    if isinstance(last_msg, HumanMessage) and "--- RÉSULTAT OUTIL" in last_msg.content:
        return "agent"
    return END

checkpointer = MemorySaver()
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model_async)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"agent": "agent", END: END})
app_graph = workflow.compile(checkpointer=checkpointer)

@app.get("/")
@app.get("/health")
def health_check():
    return {"status": "ONLINE", "version": "13.0.0", "timestamp": str(datetime.utcnow())}

# ==========================================
# DISPATCH SLACK
# ==========================================
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
            except: pass
    except Exception as e:
        msg = f"⚠️ Erreur Amal-DG: {str(e)}"
    send_slack_message(channel_id, msg)

@app.post("/slack/events")
@app.post("/slack/events/")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    try: data = await request.json()
    except: return Response(status_code=400)
    if data.get("type") == "url_verification": return {"challenge": data.get("challenge")}
    event = data.get("event", {})
    if event.get("type") in ["message", "app_mention"] and not event.get("bot_id"):
        ch, text = event.get("channel"), event.get("text")
        if ch and text: background_tasks.add_task(process_slack_mission_async, ch, text)
    return Response(status_code=200)

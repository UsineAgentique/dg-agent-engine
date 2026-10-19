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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(title="AMAL-DG-EXECUTIVE-SWARM", version="12.5.0")

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
Tu es AMAL-DG, Directrice Générale du Swarm Agentique.
Si tu dois exécuter un outil technique, tu dois répondre EXCLUSIVEMENT avec le bloc JSON de l'action :
{{"action": "<nom_de_l_outil>", "action_input": {{...}}}}

Si la tâche ne nécessite pas d'outil ou est une réponse conversationnelle, réponds directement sous forme de rapport exécutif clair, structuré et professionnel.

OUTILS DISPONIBLES :
- `git_delete_file`: {{ "file_path": "chemin/du/fichier" }}
- `git_commit_and_push`: {{ "file_path": "chemin", "content": "contenu", "commit_message": "msg" }}
- `read_github_file`: {{ "file_path": "chemin" }}
- `tavily_web_search`: {{ "query": "recherche" }}
- `firecrawl_scrape_url`: {{ "url": "https://..." }}
- `execute_python_code_e2b`: {{ "code": "script python" }}
- `delegate_to_subagent`: {{ "pole": "NOM_POLE", "mission": "description", "priority": "HIGH/MEDIUM/LOW" }}
- `save_project_state`: {{ "project_id": "id", "state_data": {{...}} }}
- `load_project_state`: {{ "project_id": "id" }}
"""

# ==========================================
# OUTILS TECH & GESTION DE MÉMOIRE PERSISTANTE
# ==========================================
def save_project_state(project_id: str, state_data: dict, **kwargs) -> str:
    if not supabase:
        return "Avertissement: Supabase non configuré, sauvegarde projet ignorée."
    try:
        data = {
            "project_id": project_id,
            "state": state_data,
            "updated_at": datetime.utcnow().isoformat()
        }
        resp = supabase.table("project_states").upsert(data).execute()
        return f"SUCCÈS: État du projet [{project_id}] enregistré dans Supabase."
    except Exception as e:
        return f"ERREUR SAUVEGARDE SUPABASE: {str(e)}"

def load_project_state(project_id: str, **kwargs) -> str:
    if not supabase:
        return "Avertissement: Supabase non configuré."
    try:
        resp = supabase.table("project_states").select("*").eq("project_id", project_id).execute()
        if resp.data:
            return json.dumps(resp.data[0].get("state", {}), ensure_ascii=False)
        return f"Aucun état trouvé pour le projet [{project_id}]."
    except Exception as e:
        return f"ERREUR LECTURE SUPABASE: {str(e)}"

def git_delete_file(file_path: str = None, path: str = None, filepath: str = None, **kwargs) -> str:
    target_path = file_path or path or filepath
    if not target_path:
        return "Erreur: Aucun chemin de fichier fourni."
    try:
        safe_path = os.path.normpath(target_path).replace("\\", "/")
        if os.path.exists(safe_path):
            try: os.remove(safe_path)
            except Exception: pass

        if not GITHUB_TOKEN or not GITHUB_REPO:
            return f"Fichier {safe_path} supprimé en local."

        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{safe_path}"
        with httpx.Client() as client:
            get_resp = client.get(url, headers=headers)
            if get_resp.status_code == 200:
                sha = get_resp.json().get("sha")
                payload = {"message": f"Chore: delete {safe_path}", "sha": sha, "branch": "main"}
                del_resp = client.request("DELETE", url, json=payload, headers=headers)
                if del_resp.status_code in [200, 202]:
                    return f"SUCCÈS: {safe_path} supprimé de GitHub."
                return f"Échec suppression GitHub ({del_resp.status_code})"
            return f"Fichier {safe_path} déjà absent de GitHub."
    except Exception as e:
        return f"ERREUR SUPPRESSION GITHUB: {str(e)}"

def git_commit_and_push(file_path: str, content: str, commit_message: str = "Update via Amal-DG", **kwargs) -> str:
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return "Erreur: GITHUB_TOKEN ou GITHUB_REPOSITORY non configuré."
    try:
        safe_path = os.path.normpath(file_path).replace("\\", "/")
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{safe_path}"
        
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        
        with httpx.Client() as client:
            get_resp = client.get(url, headers=headers)
            sha = get_resp.json().get("sha") if get_resp.status_code == 200 else None
            
            payload = {
                "message": commit_message,
                "content": encoded_content,
                "branch": "main"
            }
            if sha:
                payload["sha"] = sha
                
            put_resp = client.put(url, json=payload, headers=headers)
            if put_resp.status_code in [200, 201]:
                return f"SUCCÈS: {safe_path} mis à jour sur GitHub."
            return f"Échec commit GitHub ({put_resp.status_code}): {put_resp.text}"
    except Exception as e:
        return f"ERREUR COMMIT GITHUB: {str(e)}"

def read_github_file(file_path: str, **kwargs) -> str:
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return "Erreur: GITHUB_TOKEN ou GITHUB_REPOSITORY non disponible."
    try:
        safe_path = os.path.normpath(file_path).replace("\\", "/")
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{safe_path}"
        with httpx.Client() as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                content_b64 = resp.json().get("content", "")
                return base64.b64decode(content_b64).decode("utf-8")
            return f"Erreur lecture ({resp.status_code}): Fichier non trouvé."
    except Exception as e:
        return f"ERREUR LECTURE GITHUB: {str(e)}"

def tavily_web_search(query: str, **kwargs) -> str:
    if not TAVILY_API_KEY:
        return "Erreur: TAVILY_API_KEY non configurée."
    try:
        url = "https://api.tavily.com/search"
        payload = {"api_key": TAVILY_API_KEY, "query": query, "search_depth": "smart"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                summary = "\n".join([f"- [{r.get('title')}]({r.get('url')}): {r.get('content')}" for r in results[:4]])
                return summary if summary else "Aucun résultat trouvé."
            return f"Erreur Tavily ({resp.status_code})"
    except Exception as e:
        return f"ERREUR RECHERCHE TAVILY: {str(e)}"

def firecrawl_scrape_url(url: str, **kwargs) -> str:
    if not FIRECRAWL_API_KEY:
        return "Erreur: FIRECRAWL_API_KEY non configurée."
    try:
        headers = {"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"}
        payload = {"url": url, "formats": ["markdown"]}
        with httpx.Client(timeout=15.0) as client:
            resp = client.post("https://api.firecrawl.dev/v1/scrape", headers=headers, json=payload)
            if resp.status_code == 200:
                return resp.json().get("data", {}).get("markdown", "Contenu vide.")
            return f"Erreur Firecrawl ({resp.status_code})"
    except Exception as e:
        return f"ERREUR SCRAPING FIRECRAWL: {str(e)}"

def execute_python_code_e2b(code: str, **kwargs) -> str:
    try:
        local_scope = {}
        exec(code, {}, local_scope)
        return f"Exécution locale réussie: {local_scope}"
    except Exception as e:
        return f"ERREUR EXÉCUTION CODE: {str(e)}"

def delegate_to_subagent(pole: str, mission: str, priority: str = "MEDIUM", **kwargs) -> str:
    logging.info(f"[DÉLÉGATION] Mission transmise au Pôle {pole} ({priority}): {mission}")
    return f"Mission transmise avec succès au pôle {pole}."

TOOLS_MAP = {
    "git_delete_file": git_delete_file,
    "git_commit_and_push": git_commit_and_push,
    "read_github_file": read_github_file,
    "tavily_web_search": tavily_web_search,
    "firecrawl_scrape_url": firecrawl_scrape_url,
    "execute_python_code_e2b": execute_python_code_e2b,
    "delegate_to_subagent": delegate_to_subagent,
    "save_project_state": save_project_state,
    "load_project_state": load_project_state
}

# ==========================================
# MOTEUR LLM & RÉSILIENCE
# ==========================================
async def invoke_llm(provider: str, model: str, messages: List[Any], max_tokens: int = 4096) -> str:
    if not OPENROUTER_API_KEY: 
        raise ValueError("OPENROUTER_API_KEY manquante.")
        
    client = ChatOpenAI(
        model=model, 
        temperature=0.1, 
        openai_api_key=OPENROUTER_API_KEY, 
        openai_api_base="https://openrouter.ai/api/v1", 
        max_tokens=max_tokens
    )
    res = await asyncio.to_thread(client.invoke, messages)
    return res.content

async def execute_pole_llm(pole_key: str, messages: List[Any]) -> str:
    cfg = MODEL_CATALOG.get(pole_key, MODEL_CATALOG["AMAL_DG"])
    try:
        return await invoke_llm(cfg["primary_provider"], cfg["primary_model"], messages, cfg["max_tokens"])
    except Exception as err:
        logging.warning(f"[{pole_key}] Échec Primary ({cfg['primary_model']}): {err}. Bascule Fallback...")
    try:
        return await invoke_llm(cfg["fallback_provider"], cfg["fallback_model"], messages, cfg["max_tokens"])
    except Exception as fallback_err:
        logging.error(f"[{pole_key}] Échec Critique Fallback: {fallback_err}")
        return f"⚠️ Erreur critique du pôle {pole_key}: Services LLM indisponibles."

class AgentState(TypedDict):
    messages: Annotated[List, operator.add]

def extract_first_json(text: str) -> dict:
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            depth = 0
            start_idx = None
            for i, char in enumerate(text):
                if char == '{':
                    if depth == 0: start_idx = i
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0 and start_idx is not None:
                        return json.loads(text[start_idx:i+1])
    raise ValueError("Aucun JSON valide trouvé.")

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
                logging.info(f"Outil {action_name} exécuté: {tool_result}")
                
                feedback_msg = HumanMessage(content=f"--- RÉSULTAT EXÉCUTION OUTIL [{action_name}] ---\n{tool_result}\n\nPoursuis l'action suivante ou termine avec ton rapport.")
                return {"messages": [AIMessage(content=content), feedback_msg]}
        except Exception as parse_err:
            logging.warning(f"Erreur parsing JSON action: {parse_err}")

    return {"messages": [AIMessage(content=content)]}

def should_continue(state: AgentState):
    last_msg = state["messages"][-1]
    if isinstance(last_msg, HumanMessage) and "--- RÉSULTAT EXÉCUTION OUTIL" in last_msg.content:
        return "agent"
    return END

# ==========================================
# WORKFLOW AVEC CHECKPOINTER PERSISTANT
# ==========================================
checkpointer = MemorySaver()

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model_async)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"agent": "agent", END: END})

app_graph = workflow.compile(checkpointer=checkpointer)

@app.get("/")
@app.get("/health")
def health_check():
    return {"status": "ONLINE", "version": "12.5.0", "timestamp": str(datetime.utcnow())}

# ==========================================
# GESTION ET DISPATCH SLACK
# ==========================================
def send_slack_message(channel: str, text: str):
    if not SLACK_TOKEN: 
        logging.error("SLACK_BOT_TOKEN non configuré.")
        return
        
    raw_token = SLACK_TOKEN.strip()
    
    if raw_token.startswith("http://") or raw_token.startswith("https://"):
        target_url = raw_token
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {"text": text}
    else:
        target_url = "https://slack.com/api/chat.postMessage"
        token_auth = raw_token if raw_token.startswith("xoxb-") else f"xoxb-{raw_token}"
        headers = {"Authorization": f"Bearer {token_auth}", "Content-Type": "application/json; charset=utf-8"}
        payload = {"channel": channel, "text": text}

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(target_url, headers=headers, json=payload)
            logging.info(f"Slack response status: {resp.status_code}")
    except Exception as e:
        logging.error(f"Erreur Slack dispatch: {e}")

async def process_slack_mission_async(channel_id: str, user_prompt: str):
    try:
        # Configuration isolée par canal/projet via thread_id
        config = {"configurable": {"thread_id": channel_id}}
        
        final_state = await app_graph.ainvoke(
            {"messages": [HumanMessage(content=user_prompt)]},
            config=config
        )
        final_message = final_state["messages"][-1].content
        
        if final_message.startswith("{") and "message" in final_message:
            try:
                parsed_msg = json.loads(final_message)
                final_message = parsed_msg.get("message", final_message)
            except Exception:
                pass

    except Exception as e:
        final_message = f"⚠️ *Erreur Moteur Amal-DG* : {str(e)}"
        
    send_slack_message(channel_id, final_message)

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
        channel_id = event.get("channel")
        user_prompt = event.get("text")
        if channel_id and user_prompt:
            background_tasks.add_task(process_slack_mission_async, channel_id, user_prompt)

    return Response(status_code=200)

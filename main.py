import os
import sys
import json
import base64
import logging
import asyncio
import operator
import subprocess
from typing import TypedDict, Annotated, List, Union, Dict, Any
from datetime import datetime

from fastapi import FastAPI, Request, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(title="AMAL-DG-EXECUTIVE-SWARM", version="11.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# ==========================================
# MODEL CATALOG (OPENROUTER STABLE ENDPOINTS)
# ==========================================
MODEL_CATALOG = {
    "AMAL_DG": {
        "primary_provider": "openrouter",
        "primary_model": "openai/gpt-4o-mini",
        "fallback_provider": "openrouter",
        "fallback_model": "meta-llama/llama-3.3-70b-instruct:free",
        "max_tokens": 4096
    },
    "TECH_CODE": {
        "primary_provider": "openrouter",
        "primary_model": "openai/gpt-4o-mini",
        "fallback_provider": "openrouter",
        "fallback_model": "qwen/qwen-2.5-coder-32b-instruct:free",
        "max_tokens": 4096
    },
    "LEGAL_TAL": {
        "primary_provider": "openrouter",
        "primary_model": "openai/gpt-4o-mini",
        "fallback_provider": "openrouter",
        "fallback_model": "meta-llama/llama-3.3-70b-instruct:free",
        "max_tokens": 4096
    }
}

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
        logging.warning(f"[{pole_key}] Échec Primary ({cfg['primary_model']}): {err}. Bascule sur Fallback...")
    try:
        return await invoke_llm(cfg["fallback_provider"], cfg["fallback_model"], messages, cfg["max_tokens"])
    except Exception as fallback_err:
        logging.error(f"[{pole_key}] Échec Critique Fallback: {fallback_err}")
        return f"⚠️ Erreur critique du pôle {pole_key}: Services LLM indisponibles."

# ==========================================
# OUTILS DE GESTION GITHUB & RECHERCHE
# ==========================================
def tavily_web_search(query: str) -> str:
    if not TAVILY_API_KEY: return "Erreur: TAVILY_API_KEY non configurée."
    try:
        with httpx.Client(timeout=15.0) as client:
            res = client.post("https://api.tavily.com/search", json={"api_key": TAVILY_API_KEY, "query": query, "search_depth": "advanced"})
            return str(res.json().get("results", []))[:2000]
    except Exception as e:
        return f"Erreur Tavily: {str(e)}"

def read_github_file(file_path: str) -> str:
    try:
        if not GITHUB_TOKEN or not GITHUB_REPO:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f: return f.read()
            return f"Fichier {file_path} introuvable."
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
        with httpx.Client() as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                return base64.b64decode(resp.json().get("content", "")).decode("utf-8")
            return f"Fichier introuvable sur GitHub ({resp.status_code})."
    except Exception as e:
        return f"Erreur GitHub Read: {str(e)}"

def git_commit_and_push(file_path: str, commit_message: str, content: str) -> str:
    try:
        safe_path = os.path.normpath(file_path).replace("\\", "/")
        os.makedirs(os.path.dirname(safe_path) or ".", exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f: f.write(content)
        
        if not GITHUB_TOKEN or not GITHUB_REPO:
            return f"Fichier {file_path} sauvegardé en local."

        content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{safe_path}"
        with httpx.Client() as client:
            get_resp = client.get(url, headers=headers)
            payload = {"message": commit_message, "content": content_b64, "branch": "main"}
            if get_resp.status_code == 200:
                payload["sha"] = get_resp.json().get("sha")
            res = client.put(url, json=payload, headers=headers)
            if res.status_code in [200, 201]:
                return f"SUCCÈS: {file_path} commité et poussé sur GitHub."
            return f"Échec GitHub Commit ({res.status_code}): {res.text}"
    except Exception as e:
        return f"ERREUR GIT PUSH: {str(e)}"

def git_delete_file(file_path: str) -> str:
    try:
        safe_path = os.path.normpath(file_path).replace("\\", "/")
        if os.path.exists(safe_path):
            try: os.remove(safe_path)
            except Exception: pass

        if not GITHUB_TOKEN or not GITHUB_REPO:
            return f"Fichier {file_path} supprimé en local."

        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{safe_path}"
        with httpx.Client() as client:
            get_resp = client.get(url, headers=headers)
            if get_resp.status_code == 200:
                sha = get_resp.json().get("sha")
                payload = {"message": f"Chore: delete {safe_path}", "sha": sha, "branch": "main"}
                del_resp = client.request("DELETE", url, json=payload, headers=headers)
                if del_resp.status_code in [200, 202]:
                    return f"SUCCÈS: {file_path} supprimé de GitHub."
                return f"Échec suppression GitHub ({del_resp.status_code})"
            return f"Fichier {file_path} déjà absent de GitHub."
    except Exception as e:
        return f"ERREUR SUPPRESSION GITHUB: {str(e)}"

def delegate_to_subagent(team: str, task_description: str, search_query: str = "") -> str:
    pole_key = "TECH_CODE" if "tech" in team.lower() else "LEGAL_TAL" if "legal" in team.lower() else "AMAL_DG"
    live_data = tavily_web_search(search_query) if search_query else ""
    prompt_msgs = [
        SystemMessage(content=f"Tu es l'agent expert du pôle {team}. Sois rigoureux, technique et direct. Contexte web: {live_data}"),
        HumanMessage(content=task_description)
    ]
    try:
        loop = asyncio.get_running_loop()
        future = asyncio.run_coroutine_threadsafe(execute_pole_llm(pole_key, prompt_msgs), loop)
        return future.result(timeout=30.0)
    except Exception as e:
        return f"Erreur sous-agent {team}: {str(e)}"

TOOLS_MAP = {
    "tavily_web_search": tavily_web_search,
    "read_github_file": read_github_file,
    "git_commit_and_push": git_commit_and_push,
    "git_delete_file": git_delete_file,
    "delegate_to_subagent": delegate_to_subagent
}

SYSTEM_PROMPT = """Tu es AMAL-DG, Directrice Générale et Orchestratrice Suprême du Swarm Agentique.
Tu disposes d'une autonomie totale sur le dépôt GitHub et les outils d'exécution.

PROTOCOLE D'EXÉCUTION :
1. Avant d'exécuter une action de suppression ou modification, évalue si l'opération est valide.
2. Si un outil renvoie une erreur, analyse-la, ajuste l'action et réessaie de manière autonome.
3. Réponds EXCLUSIVEMENT sous la forme d'un objet JSON d'action valide :
{"action": "nom_outil", "action_input": {"param1": "valeur1"}}
OU si l'exécution est terminée :
{"message": "Ton compte-rendu ici"}
"""

class AgentState(TypedDict):
    messages: Annotated[List, operator.add]

async def call_model_async(state: AgentState):
    full_messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"][-8:]
    content = await execute_pole_llm("AMAL_DG", full_messages)
    content = content.strip()

    if content.startswith("```"):
        lines = content.splitlines()
        if lines[0].startswith("```"): lines = lines[1:]
        if lines and lines[-1].startswith("```"): lines = lines[:-1]
        content = "\n".join(lines).strip()

    if content.startswith("{") and "action" in content:
        try:
            parsed = json.loads(content)
            action_name = parsed.get("action")
            action_input = parsed.get("action_input", {})
            
            if action_name in TOOLS_MAP:
                tool_fn = TOOLS_MAP[action_name]
                tool_result = tool_fn(**action_input) if isinstance(action_input, dict) else tool_fn(action_input)
                logging.info(f"Outil {action_name} exécuté: {tool_result}")
                
                feedback_msg = HumanMessage(content=f"--- RÉSULTAT EXÉCUTION OUTIL [{action_name}] ---\n{tool_result}\n\nVérifie l'état final.")
                return {"messages": [AIMessage(content=content), feedback_msg]}
        except Exception as parse_err:
            logging.warning(f"Erreur parsing JSON action: {parse_err}")

    return {"messages": [AIMessage(content=content)]}

def should_continue(state: AgentState):
    last_msg = state["messages"][-1]
    if isinstance(last_msg, HumanMessage) and "--- RÉSULTAT EXÉCUTION OUTIL" in last_msg.content:
        return "agent"
    return END

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model_async)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"agent": "agent", END: END})

app_graph = workflow.compile()

@app.get("/")
@app.get("/health")
def health_check():
    return {"status": "ONLINE", "version": "11.3.0", "timestamp": str(datetime.utcnow())}

def send_slack_message(channel: str, text: str):
    if not SLACK_TOKEN: 
        logging.error("SLACK_BOT_TOKEN manquant")
        return
    token = SLACK_TOKEN.strip()
    url = "[https://slack.com/api/chat.postMessage](https://slack.com/api/chat.postMessage)"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
                json={"channel": channel, "text": text}
            )
            logging.info(f"Slack response status: {resp.status_code}")
    except Exception as e:
        logging.error(f"Erreur Slack dispatch: {e}")

async def process_slack_mission_async(channel_id: str, user_prompt: str):
    try:
        final_state = await app_graph.ainvoke({"messages": [HumanMessage(content=user_prompt)]})
        final_message = final_state["messages"][-1].content
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

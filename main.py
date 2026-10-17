import os
import sys
import json
import base64
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(title="AMAL-DG-ENGINE", version="10.7.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment Variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")

# ==========================================
# ROUTES SANITÉ & SLACK (DÉCLARÉES UPFRONT)
# ==========================================
@app.get("/")
@app.get("/health")
def health_check():
    return {"status": "ONLINE", "version": "10.7.0", "timestamp": str(datetime.utcnow())}

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

# ==========================================
# MOTEUR MULTI-PROVIDERS (GROQ / OPENROUTER)
# ==========================================
MODEL_CATALOG = {
    "AMAL_DG": {
        "primary_provider": "groq",
        "primary_model": "llama-3.1-8b-instant",
        "fallback_provider": "openrouter",
        "fallback_model": "google/gemma-2-9b-it:free",
        "max_tokens": 4096
    }
}

async def invoke_llm_provider(provider: str, model_name: str, messages: List[Any], max_tokens: int = 4096) -> str:
    if provider == "groq":
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY manquante.")
        client = ChatGroq(model=model_name, temperature=0.1, groq_api_key=GROQ_API_KEY, max_tokens=max_tokens)
        res = await asyncio.to_thread(client.invoke, messages)
        return res.content

    elif provider == "openrouter":
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY manquante.")
        client = ChatOpenAI(
            model=model_name,
            temperature=0.1,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            max_tokens=max_tokens
        )
        res = await asyncio.to_thread(client.invoke, messages)
        return res.content

    raise ValueError(f"Fournisseur inconnu: {provider}")

async def execute_llm(messages: List[Any]) -> str:
    cfg = MODEL_CATALOG["AMAL_DG"]
    try:
        return await invoke_llm_provider(cfg['primary_provider'], cfg['primary_model'], messages, cfg['max_tokens'])
    except Exception as err:
        logging.warning(f"Fallback déclenché: {err}")
        return await invoke_llm_provider(cfg['fallback_provider'], cfg['fallback_model'], messages, cfg['max_tokens'])

# ==========================================
# SYSTEM PROMPT & TOOLS
# ==========================================
SYSTEM_PROMPT = """Tu es AMAL-DG, Directrice Générale du Swarm.
Réponds sous forme de JSON d'action :
{"action": "git_delete_file", "action_input": {"file_path": "chemin/fichier.md"}}
Ou répond directement si c'est une discussion textuelle."""

def git_delete_file(file_path: str) -> str:
    try:
        safe_path = os.path.normpath(file_path).replace("\\", "/")
        if not GITHUB_TOKEN or not GITHUB_REPO:
            return f"Simulifation suppression local: {file_path}"

        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{safe_path}"

        with httpx.Client() as client:
            get_resp = client.get(api_url, headers=headers)
            if get_resp.status_code == 200:
                sha = get_resp.json().get("sha")
                payload = {"message": f"Chore: delete {safe_path}", "sha": sha, "branch": "main"}
                del_resp = client.request("DELETE", api_url, json=payload, headers=headers)
                if del_resp.status_code in [200, 202]:
                    return f"SUCCÈS: {file_path} supprimé de GitHub."
                return f"Échec suppression GitHub: {del_resp.status_code}"
            return f"Fichier {file_path} non trouvé."
    except Exception as e:
        return f"Erreur: {str(e)}"

TOOLS = {"git_delete_file": git_delete_file}

# ==========================================
# CORE SLACK PROCESSOR
# ==========================================
def send_slack_message(channel: str, text: str):
    if not SLACK_TOKEN:
        return
    token = SLACK_TOKEN.strip()
    url = "https://slack.com/api/chat.postMessage"
    try:
        with httpx.Client(timeout=15.0) as client:
            client.post(
                url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
                json={"channel": channel, "text": text}
            )
    except Exception as e:
        logging.error(f"Slack error: {e}")

async def process_slack_mission_async(channel_id: str, user_prompt: str):
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
    try:
        response_text = await execute_llm(messages)
        if "action" in response_text and "git_delete_file" in response_text:
            try:
                data = json.loads(response_text)
                fn_input = data.get("action_input", {})
                res = git_delete_file(**fn_input)
                final_msg = f" Action exécutée : {res}"
            except Exception:
                final_msg = response_text
        else:
            final_msg = response_text
    except Exception as e:
        final_msg = f"⚠️ Erreur: {str(e)}"

    send_slack_message(channel_id, final_msg)

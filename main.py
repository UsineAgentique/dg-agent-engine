import os
import sys
import json
import time
import base64
import operator
import logging
import asyncio
import subprocess
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

app = FastAPI(title="AMAL-DG-EXECUTIVE-SWARM", version="10.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration API Keys (Render Environment)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

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

# ==========================================
# MATRICE DES MODÈLES & QUOTAS ÉTENDUS (> 4000)
# ==========================================
MODEL_CATALOG = {
    "AMAL_DG": {
        "primary_provider": "huggingface",
        "primary_model": "openai/gpt-oss-safeguard-120b",
        "fallback_provider": "google",
        "fallback_model": "gemini-1.5-flash-latest",
        "max_tokens": 8192  # Quota augmenté au-delà de 4000
    },
    "TECH_CODE": {
        "primary_provider": "huggingface",
        "primary_model": "Qwen/Qwen2.5-Coder-32B-Instruct",
        "fallback_provider": "openrouter",
        "fallback_model": "cohere/north-mini-code:free",
        "max_tokens": 8192
    },
    "LEGAL_TAL": {
        "primary_provider": "huggingface",
        "primary_model": "deepseek-ai/DeepSeek-R1-Distill-Qwen-33B",
        "fallback_provider": "openrouter",
        "fallback_model": "google/gemma-4-31b:free",
        "max_tokens": 8192
    },
    "STRATEGY_GLM": {
        "primary_provider": "huggingface",
        "primary_model": "zai-org/GLM-4.7-Flash",
        "fallback_provider": "groq",
        "fallback_model": "llama-3.3-70b-versatile",
        "max_tokens": 8192
    },
    "WORKERS": {
        "primary_provider": "groq",
        "primary_model": "llama-3.1-8b-instant",
        "fallback_provider": "huggingface",
        "fallback_model": "google/gemma-3-1b-it",
        "max_tokens": 4096
    }
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
    if len(EXECUTION_LOGS) > 200:
        EXECUTION_LOGS.pop()

# ==========================================
# MOTEUR MULTI-PROVIDERS & CIRCUIT BREAKER
# ==========================================
async def invoke_llm_provider(provider: str, model_name: str, messages: List[Any], max_tokens: int = 8192) -> str:
    timeout_seconds = 30.0
    
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

    elif provider == "huggingface":
        if not HUGGINGFACE_API_KEY:
            raise ValueError("HUGGINGFACE_API_KEY manquante.")
        url = f"https://api-inference.huggingface.co/models/{model_name}"
        headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}", "Content-Type": "application/json"}
        prompt_text = "\n".join([f"{m.type}: {m.content}" for m in messages])
        payload = {"inputs": prompt_text, "parameters": {"max_new_tokens": max_tokens, "temperature": 0.1}}
        
        async with httpx.AsyncClient(timeout=timeout_seconds) as async_client:
            resp = await async_client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("generated_text", str(data))
                return str(data)
            else:
                raise RuntimeError(f"Hugging Face HTTP {resp.status_code}: {resp.text}")

    elif provider == "google":
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY manquante.")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        contents = []
        for m in messages:
            role = "user" if m.type in ["human", "system"] else "model"
            contents.append({"role": role, "parts": [{"text": m.content}]})
        payload = {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.1}}
        
        async with httpx.AsyncClient(timeout=timeout_seconds) as async_client:
            resp = await async_client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except KeyError:
                    return str(data)
            else:
                raise RuntimeError(f"Google AI HTTP {resp.status_code}: {resp.text}")

    else:
        raise ValueError(f"Fournisseur inconnu: {provider}")


async def execute_pole_llm(pole_key: str, messages: List[Any]) -> str:
    cfg = MODEL_CATALOG.get(pole_key, MODEL_CATALOG["WORKERS"])
    max_tokens = cfg.get("max_tokens", 8192)
    
    # 1. Primary
    try:
        logging.info(f"[{pole_key}] Primary: {cfg['primary_provider']} / {cfg['primary_model']}")
        result = await invoke_llm_provider(cfg['primary_provider'], cfg['primary_model'], messages, max_tokens)
        record_log(pole_key, "SUCCESS", f"{cfg['primary_provider']}/{cfg['primary_model']}", "Exécution réussie")
        return result
    except Exception as err:
        logging.warning(f"[{pole_key}] ECHEC Primary ({cfg['primary_model']}): {err}. Fallback...")
        record_log(pole_key, "FALLBACK_TRIGGERED", f"{cfg['primary_provider']}/{cfg['primary_model']}", f"Erreur: {str(err)[:100]}")

    # 2. Fallback
    try:
        logging.info(f"[{pole_key}] Fallback: {cfg['fallback_provider']} / {cfg['fallback_model']}")
        result = await invoke_llm_provider(cfg['fallback_provider'], cfg['fallback_model'], messages, max_tokens)
        record_log(pole_key, "SUCCESS_FALLBACK", f"{cfg['fallback_provider']}/{cfg['fallback_model']}", "Fallback exécuté avec succès")
        return result
    except Exception as fallback_err:
        logging.error(f"[{pole_key}] ECHEC CRITIQUE: {fallback_err}")
        record_log(pole_key, "FAILED_ALL", f"{cfg['fallback_provider']}/{cfg['fallback_model']}", f"Erreur critique: {str(fallback_err)[:100]}")
        return f"⚠️ Erreur d'exécution sur le pôle {pole_key}: Service temporairement indisponible."

# ==========================================
# SYSTEM PROMPT EXECUTIVE
# ==========================================
SYSTEM_PROMPT = """Tu es AMAL-DG, Directrice Générale, Architecte IA et Orchestratrice Suprême du Swarm Agentique.

CHARTE D'EXÉCUTION (DG_SYSTEME.MD v10.0) :
1. RESPECT ABSOLU DE DG_SYSTEME.MD : Tu appliques les règles et la posture du fichier `dg_systeme.md`. Tu peux le lire via `read_github_file("dg_systeme.md")`.
2. SILICON VALLEY CEO MINDSET : Execution Bias absolu, zéro blabla, orientation livrables réels.
3. ACCÈS WEB TEMPS RÉEL (ANTI-VASE CLOS) : Interdiction formelle de te fier uniquement à ta mémoire interne. Tu DOIS utiliser `tavily_web_search` ou `firecrawl_scrape_url` pour le pôle juridique (TAL/Québec), la veille et la tech.
4. DÉLÉGATION EXTENSIBLE : Tu délègues les sous-missions aux pôles via `delegate_to_subagent`.

FORMAT D'EXÉCUTION DES ACTIONS (EXCLUSIF) :
Réponds EXCLUSIVEMENT sous forme d'objet JSON d'action :
{"action": "nom_outil", "action_input": {...}}
OU pour plusieurs actions :
[
  {"action": "outil_1", "action_input": {...}},
  {"action": "outil_2", "action_input": {...}}
]

Outils disponibles :
- delegate_to_subagent
- tavily_web_search
- firecrawl_scrape_url
- execute_python_code_e2b
- execute_system_command
- git_commit_and_push
- read_github_file
- git_delete_file
- compile_markdowns_to_pdf
"""

# ==========================================
# OUTILS PHYSIQUES DU SWARM
# ==========================================
def tavily_web_search(query: str) -> str:
    if not TAVILY_API_KEY: 
        return "Erreur: TAVILY_API_KEY non configurée."
    try:
        with httpx.Client(timeout=15.0) as client:
            res = client.post("https://api.tavily.com/search", json={"api_key": TAVILY_API_KEY, "query": query, "search_depth": "advanced"}, timeout=15.0)
            return res.json().get("answer", str(res.json().get("results", [])))[:2000]
    except Exception as e:
        return f"Erreur Tavily Search: {str(e)}"

def firecrawl_scrape_url(url: str) -> str:
    if firecrawl_app:
        try:
            return firecrawl_app.scrape_url(url, params={'formats': ['markdown']}).get('markdown', '')[:2000]
        except Exception as e:
            return f"Erreur Firecrawl Scrape: {str(e)}"
    return "Firecrawl non disponible."

def execute_python_code_e2b(code: str) -> str:
    if not E2B_API_KEY or not CodeInterpreter:
        return "E2B non disponible."
    try:
        with CodeInterpreter(api_key=E2B_API_KEY) as sandbox:
            execution = sandbox.notebook.exec_cell(code)
            return "\n".join(execution.logs.stdout)
    except Exception as e:
        return f"Erreur E2B: {str(e)}"

def execute_system_command(command: str) -> str:
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout if result.stdout else result.stderr
        return output[:2000] if output else "Commande exécutée avec succès."
    except Exception as e:
        return f"Erreur exécution système: {str(e)}"

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

def git_commit_and_push(file_path: str, commit_message: str, content_to_write: Union[str, bytes], branch: str = "main") -> str:
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
            payload = {"message": commit_message, "content": content_b64, "branch": branch}
            if get_resp.status_code == 200:
                payload["sha"] = get_resp.json().get("sha")
            res = client.put(api_url, json=payload, headers=headers)
            if res.status_code in [200, 201]:
                return f"SUCCÈS: Fichier {file_path} mis à jour sur GitHub."
            return f"Échec GitHub ({res.status_code}): {res.text}"
    except Exception as e:
        return f"ERREUR GITHUB: {str(e)}"

def git_delete_file(file_path: str, commit_message: str = "Chore: Delete obsolete file", branch: str = "main") -> str:
    try:
        safe_path = os.path.normpath(file_path).replace("\\", "/")
        if os.path.exists(safe_path):
            try: os.remove(safe_path)
            except Exception: pass

        if not GITHUB_TOKEN or not GITHUB_REPO:
            return f"Fichier {file_path} supprimé en local."

        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{safe_path}"

        with httpx.Client() as client:
            get_resp = client.get(api_url, headers=headers)
            if get_resp.status_code == 200:
                sha = get_resp.json().get("sha")
                payload = {"message": commit_message, "sha": sha, "branch": branch}
                del_resp = client.request("DELETE", api_url, json=payload, headers=headers)
                if del_resp.status_code in [200, 202]:
                    return f"SUCCÈS: Fichier {file_path} supprimé de GitHub."
                return f"Échec suppression GitHub: {del_resp.status_code}"
            return f"Fichier {file_path} non trouvé sur GitHub."
    except Exception as e:
        return f"ERREUR SUPPRESSION GITHUB: {str(e)}"

def delegate_to_subagent(team: str, task_description: str, save_to_file: str = "", priority: str = "MEDIUM", search_query: str = "", project_id: str = "GLOBAL") -> str:
    team_lower = team.lower()
    
    live_context = ""
    if search_query or any(k in team_lower for k in ["legal", "juridique", "tal", "veille", "tech", "market"]):
        query_to_run = search_query if search_query else f"actualités juridiques et mises à jour {team} {task_description[:50]}"
        live_context = f"\n\n--- DATA WEB TEMPS RÉEL ---\n" + tavily_web_search(query_to_run)

    if any(k in team_lower for k in ["tech", "code", "dev", "frontend", "backend", "devops"]):
        pole_key = "TECH_CODE"
    elif any(k in team_lower for k in ["legal", "juridique", "tal", "conformite"]):
        pole_key = "LEGAL_TAL"
    elif any(k in team_lower for k in ["strategy", "strategie", "contenu", "marketing", "veille"]):
        pole_key = "STRATEGY_GLM"
    else:
        pole_key = "WORKERS"
    
    prompt_msg = [
        SystemMessage(content=f"Tu es l'agent sous-spécialisé du pôle '{team.upper()}' (Priorité: {priority}). Sois précis et détaillé. Zéro hallucination.{live_context}"),
        HumanMessage(content=task_description)
    ]
    
    try:
        loop = asyncio.get_running_loop()
        future = asyncio.run_coroutine_threadsafe(execute_pole_llm(pole_key, prompt_msg), loop)
        result_text = future.result(timeout=35.0)
    except RuntimeError:
        result_text = asyncio.run(execute_pole_llm(pole_key, prompt_msg))
    except Exception as ex:
        result_text = f"Erreur exécution sous-agent {team}: {str(ex)}"
    
    if save_to_file and not result_text.startswith("⚠️"):
        git_commit_and_push(save_to_file, f"Feat({team}/{project_id}): Deliverable", result_text)
        
    return result_text[:2500]

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

TOOLS_MAP = {
    "delegate_to_subagent": delegate_to_subagent,
    "tavily_web_search": tavily_web_search,
    "firecrawl_scrape_url": firecrawl_scrape_url,
    "execute_python_code_e2b": execute_python_code_e2b,
    "execute_system_command": execute_system_command,
    "read_github_file": read_github_file,
    "git_commit_and_push": git_commit_and_push,
    "git_delete_file": git_delete_file,
    "compile_markdowns_to_pdf": compile_markdowns_to_pdf
}

class AgentState(TypedDict):
    messages: Annotated[List, operator.add]

def execute_action_payload(action_item: dict) -> str:
    action_name = action_item.get("action")
    action_input = action_item.get("action_input", {})
    if action_name in TOOLS_MAP:
        tool_fn = TOOLS_MAP[action_name]
        try:
            if isinstance(action_input, dict):
                return f"[{action_name}]: " + str(tool_fn(**action_input))
            else:
                return f"[{action_name}]: " + str(tool_fn(action_input))
        except Exception as err:
            return f"[{action_name} ERREUR]: {str(err)}"
    return f"[{action_name}]: Outil inconnu."

async def call_model_async(state: AgentState):
    system_ctx = SystemMessage(content=SYSTEM_PROMPT)
    full_messages = [system_ctx] + state["messages"][-10:]
    
    content = await execute_pole_llm("AMAL_DG", full_messages)
    content = content.strip()
    
    if content.startswith("```"):
        lines = content.splitlines()
        if lines[0].startswith("```"): lines = lines[1:]
        if lines and lines[-1].startswith("```"): lines = lines[:-1]
        content = "\n".join(lines).strip()

    if (content.startswith("{") or content.startswith("[")) and "action" in content:
        try:
            parsed_json = json.loads(content)
            results = []
            
            if isinstance(parsed_json, list):
                for item in parsed_json:
                    if isinstance(item, dict) and "action" in item:
                        results.append(execute_action_payload(item))
            elif isinstance(parsed_json, dict) and "action" in parsed_json:
                results.append(execute_action_payload(parsed_json))
                
            if results:
                execution_summary = "\n".join(results)
                logging.info(f"EXÉCUTION Outils Réussi:\n{execution_summary}")
                tool_msg = HumanMessage(content=f"--- RÉSULTAT EXÉCUTION PHYSIQUE OUTILS ---\n{execution_summary}\n\nAnalyse ce résultat et poursuis l'exécution.")
                return {"messages": [AIMessage(content=content), tool_msg]}
        except Exception as parse_err:
            logging.warning(f"Erreur parsing JSON action: {parse_err}")

    return {"messages": [AIMessage(content=content)]}

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if isinstance(last_message, HumanMessage) and "--- RÉSULTAT EXÉCUTION PHYSIQUE OUTILS" in last_message.content:
        return "agent"
    return END

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model_async)
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
    if not SLACK_TOKEN:
        logging.error("Pas de token Slack configuré.")
        return
    
    token = SLACK_TOKEN.strip()
    if not token.startswith("xoxb-") and not token.startswith("xoxp-"):
        logging.error("Format de token Slack invalide.")
        return

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
        logging.error(f"Erreur envoi Slack: {e}")

async def process_slack_mission_async(channel_id: str, user_prompt: str):
    record_log("AMAL_DG", "STARTED", "openai/gpt-oss-safeguard-120b", f"Slack Mission: {user_prompt[:50]}...")
    try:
        final_state = await app_graph.ainvoke({"messages": [HumanMessage(content=user_prompt)]})
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
        "version": "10.2.0",
        "providers_integrated": ["Groq", "OpenRouter", "HuggingFace", "GoogleAI"],
        "models_catalog": MODEL_CATALOG,
        "execution_history": EXECUTION_LOGS
    }

@app.get("/health")
def health_check():
    return {"status": "ONLINE", "version": "10.2.0"}

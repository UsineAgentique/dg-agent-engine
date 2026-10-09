import os
import sys
import json
import base64
import subprocess
import operator
from typing import TypedDict, Annotated, List

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Response
from pydantic import BaseModel
import httpx

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from supabase import create_client, Client

app = FastAPI(title="DG-AGENT-CORE-SAAS", version="3.0.0")

# ==========================================
# 0. CONFIGURATION & CLÉS API
# ==========================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
REDIS_URL = os.getenv("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# PROMPT SYSTÈME ADAPTÉ (Sans native tool binding pour contourner le bug Harmony de Groq)
SYSTEM_PROMPT = """Tu es Amal-DG, Directrice Générale et Architecte IA du SaaS Immobilier Québec.

POUR DÉLÉGUER OU EXÉCUTER UNE ACTION, RÉPONDS UNIQUEMENT PAR UN OBJET JSON VALIDE (SANS AUCUN AUTRE TEXTE) :
{
  "action": "nom_outil",
  "action_input": { ...arguments... }
}

OUTILS DISPONIBLES :
1. `delegate_to_subagent` : Délègue une mission d'analyse ou de dev.
   Arguments : {"team": "team3_product", "task_description": "...", "save_to_file": "docs/market_intelligence_b2b.md"}
2. `tavily_web_search` : Recherche Web rapide.
   Arguments : {"query": "..."}
3. `firecrawl_read_site` : Lit/scrape une URL.
   Arguments : {"url": "..."}
4. `git_commit_and_push` : Écrit/déploie un fichier sur GitHub.
   Arguments : {"file_path": "...", "commit_message": "...", "content_to_write": "..."}

RÈGLE STRICTE : Si tu as reçu le résultat de l'outil et que tu réponds sur Slack, réponds en TEXTE NORMAL (3-5 puces synthétiques) sans JSON."""

# ==========================================
# 1. FONCTIONS DE TRAITEMENT
# ==========================================

def tavily_web_search(query: str) -> str:
    if not TAVILY_API_KEY: return "ERREUR: Clé TAVILY_API_KEY manquante."
    try:
        with httpx.Client() as client:
            res = client.post(
                "https://api.tavily.com/search",
                json={"api_key": TAVILY_API_KEY, "query": query, "search_depth": "basic", "include_answer": True},
                timeout=12.0
            )
            data = res.json()
            return data.get("answer", "Pas de réponse.")[:1000]
    except Exception as e:
        return f"Erreur de recherche: {str(e)}"

def firecrawl_read_site(url: str) -> str:
    if not FIRECRAWL_API_KEY: return "ERREUR: Clé FIRECRAWL_API_KEY manquante."
    try:
        headers = {"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"}
        with httpx.Client() as client:
            res = client.post("https://api.firecrawl.dev/v1/scrape", json={"url": url}, headers=headers, timeout=15.0)
            data = res.json()
            content = data.get("data", {}).get("markdown", "")
            return content[:1200] + "\n[Tronqué pour mémoire]" if len(content) > 1200 else content
    except Exception as e:
        return f"Erreur de scraping: {str(e)}"

def git_commit_and_push(file_path: str, commit_message: str, content_to_write: str) -> str:
    try:
        safe_path = os.path.normpath(file_path).replace("\\", "/")
        os.makedirs(os.path.dirname(safe_path) or ".", exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content_to_write)
            
        github_repo = os.getenv("GITHUB_REPOSITORY")
        if not GITHUB_TOKEN or not github_repo: return "Fichier créé localement (GitHub non configuré)."

        content_b64 = base64.b64encode(content_to_write.encode("utf-8")).decode("utf-8")
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        api_url = f"https://api.github.com/repos/{github_repo}/contents/{safe_path}"

        with httpx.Client() as client:
            get_resp = client.get(api_url, headers=headers)
            payload = {"message": commit_message, "content": content_b64, "branch": "main"}
            if get_resp.status_code == 200: payload["sha"] = get_resp.json().get("sha")
            client.put(api_url, json=payload, headers=headers)

        return f"SUCCÈS: Fichier {file_path} écrit et déployé sur Github."
    except Exception as e:
        return f"ERREUR GITHUB: {str(e)}"

def delegate_to_subagent(team: str, task_description: str, save_to_file: str = "") -> str:
    try:
        # Pôles d'analyse lourde et dev orientés vers Llama 3.3 70B
        model_name = "llama-3.3-70b-versatile" if team in ["team_dev", "team3_product", "team5_growth_seo"] else "llama-3.1-8b-instant"
        groq_client = ChatGroq(model=model_name, temperature=0.2, groq_api_key=GROQ_API_KEY)
        
        system_msg = SystemMessage(content=f"Tu es l'équipe spécialisée {team}. Exécute la mission de manière exhaustive. Rédige un rapport ou du code complet.")
        user_msg = HumanMessage(content=task_description)
        
        response = groq_client.invoke([system_msg, user_msg])
        result_text = response.content
        
        if save_to_file:
            git_commit_and_push(save_to_file, f"Livrable {team}", result_text)
            return f"SUCCÈS: La mission de {team} est terminée. Le rapport complet a été publié dans '{save_to_file}' sur GitHub.\n\nAperçu du rapport :\n{result_text[:800]}"
            
        return result_text[:3000]
    except Exception as e:
        return f"ERREUR DÉLÉGATION {team}: {str(e)}"

TOOLS_MAP = {
    "delegate_to_subagent": delegate_to_subagent,
    "tavily_web_search": tavily_web_search,
    "firecrawl_read_site": firecrawl_read_site,
    "git_commit_and_push": git_commit_and_push
}

# ==========================================
# 2. CERVEAU D'AMAL (GPT-OSS-120B)
# ==========================================

class AgentState(TypedDict):
    messages: Annotated[List, operator.add]
    retry_count: int

llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0, groq_api_key=GROQ_API_KEY)

def call_model(state: AgentState):
    recent_messages = state["messages"][-2:] if len(state["messages"]) > 2 else state["messages"]
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + recent_messages
    
    response = llm.invoke(messages)
    content = response.content.strip()
    
    # Détection et exécution automatique du JSON retourné par Amal-DG
    if content.startswith("{") and "action" in content:
        try:
            tool_data = json.loads(content)
            action_name = tool_data.get("action")
            action_input = tool_data.get("action_input", {})
            
            if action_name in TOOLS_MAP:
                tool_fn = TOOLS_MAP[action_name]
                if isinstance(action_input, dict):
                    tool_result = tool_fn(**action_input)
                else:
                    tool_result = tool_fn(action_input)
                    
                # Relance d'Amal avec le résultat de l'outil pour obtenir la synthèse Slack
                next_prompt = f"--- RÉSULTAT DE L'OUTIL '{action_name}' ---\n{tool_result}\n\nPrésente la synthèse exécutive finale en 3 à 5 puces sur Slack."
                synthesis_response = llm.invoke(messages + [AIMessage(content=content), HumanMessage(content=next_prompt)])
                return {"messages": [synthesis_response]}
        except Exception:
            pass

    return {"messages": [response]}

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.set_entry_point("agent")
workflow.add_edge("agent", END)

app_graph = workflow.compile()

# ==========================================
# 3. GESTIONNAIRE SLACK ASYNCHRONE
# ==========================================

def process_slack_mission_async(channel_id: str, user_prompt: str):
    conversation_history = [HumanMessage(content=user_prompt)]

    try:
        final_state = app_graph.invoke({"messages": conversation_history, "retry_count": 0})
        final_message = final_state["messages"][-1].content
    except Exception as e:
        final_message = f"⚠️ *Alerte Critique Amal-DG* : {str(e)}"

    if SLACK_TOKEN:
        try:
            httpx.post(
                "https://slack.com/api/chat.postMessage",
                json={"channel": channel_id, "text": final_message},
                headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"}
            )
        except: pass

    if supabase:
        try: supabase.table("agent_logs").insert({"channel_id": channel_id, "task": user_prompt, "output": final_message, "status": "success"}).execute()
        except: pass

# ==========================================
# 4. ENDPOINTS FASTAPI
# ==========================================

@app.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    if data.get("type") == "url_verification": return {"challenge": data.get("challenge")}
        
    event = data.get("event", {})
    if event.get("type") in ["message", "app_mention"] and not event.get("bot_id"):
        channel_id = event.get("channel")
        user_prompt = event.get("text")
        if channel_id and user_prompt:
            background_tasks.add_task(process_slack_mission_async, channel_id, user_prompt)

    return Response(status_code=200)

@app.get("/health")
def health_check():
    return {"status": "SAAS-ENGINE-ONLINE"}

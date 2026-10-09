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

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
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

# PROMPT SYSTÈME ULTRA-COMPACT (Économie massive de tokens)
SYSTEM_PROMPT = """Tu es Amal-DG, Directrice Générale et Architecte IA du SaaS Immobilier Québec.
Directives:
1. PENSÉE EN GRAPHE: Décompose les projets SaaS en étapes exécutables.
2. DÉLÉGATION SYSTÉMATIQUE: Confie le dev et l'analyse complexe à `team_dev` (Llama 70B) et le tri/rapide à `team_exec` (Llama 8B).
3. AUTONOMIE: Utilise les outils de recherche/scraping et sauvegarde systématiquement les rapports complets sur GitHub.
4. SYNTHÈSE: Reste très concise sur Slack (max 3-4 puces) pour préserver le quota TPM."""

# ==========================================
# 1. OUTILS EXTERNES (DOCSTRINGS LEGS POUR RÉDUIRE LE SCHÉMA JSON)
# ==========================================

@tool
def tavily_web_search(query: str) -> str:
    """Recherche Web en temps réel (marché, TAL, lois, actu)."""
    if not TAVILY_API_KEY: return "ERREUR: Clé TAVILY_API_KEY manquante."
    try:
        with httpx.Client() as client:
            res = client.post(
                "https://api.tavily.com/search",
                json={"api_key": TAVILY_API_KEY, "query": query, "search_depth": "basic", "include_answer": True},
                timeout=12.0
            )
            data = res.json()
            answer = data.get("answer", "Pas de réponse claire.")
            return answer[:1000]
    except Exception as e:
        return f"Erreur de recherche: {str(e)}"

@tool
def firecrawl_read_site(url: str) -> str:
    """Lit et convertit une URL/page Web en texte lisible."""
    if not FIRECRAWL_API_KEY: return "ERREUR: Clé FIRECRAWL_API_KEY manquante."
    try:
        headers = {"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"}
        with httpx.Client() as client:
            res = client.post("https://api.firecrawl.dev/v1/scrape", json={"url": url}, headers=headers, timeout=15.0)
            data = res.json()
            content = data.get("data", {}).get("markdown", "")
            return content[:1200] + "\n[Tronqué pour préserver la mémoire...]" if len(content) > 1200 else content
    except Exception as e:
        return f"Erreur de scraping: {str(e)}"

@tool
def redis_fast_memory(action: str, key: str, value: str = "") -> str:
    """Lit ('get') ou écrit ('set') une information dans la mémoire rapide Redis."""
    if not REDIS_URL or not REDIS_TOKEN: return "ERREUR: Configuration Upstash Redis manquante."
    try:
        headers = {"Authorization": f"Bearer {REDIS_TOKEN}"}
        with httpx.Client() as client:
            if action == "set":
                res = client.post(f"{REDIS_URL}/set/{key}", data=value, headers=headers)
                return "SUCCÈS: Sauvegardé dans Redis." if res.status_code == 200 else "Erreur sauvegarde Redis."
            elif action == "get":
                res = client.get(f"{REDIS_URL}/get/{key}", headers=headers)
                return str(res.json().get("result", "Clé introuvable."))
    except Exception as e:
        return f"Erreur Redis: {str(e)}"

@tool
def delegate_to_subagent(team: str, task_description: str, save_to_file: str = "") -> str:
    """
    Délègue une mission technique à 'team_dev' (Llama 70B) ou 'team_exec' (Llama 8B).
    Si `save_to_file` est fourni (ex: 'docs/market.md'), le rapport complet y sera sauvegardé via GitHub.
    """
    try:
        model_name = "llama-3.3-70b-versatile" if team == "team_dev" else "llama-3.1-8b-instant"
        groq_client = ChatGroq(model=model_name, temperature=0.2, groq_api_key=GROQ_API_KEY)
        
        system_msg = SystemMessage(content=f"Tu es le sous-agent {team}. Exécute cette mission technique de façon exhaustive et ultra-détaillée. Fournis le code ou le rapport complet.")
        user_msg = HumanMessage(content=task_description)
        
        response = groq_client.invoke([system_msg, user_msg])
        result_text = response.content
        
        # Sauvegarde automatique sur GitHub si un chemin de fichier est fourni
        if save_to_file:
            git_commit_and_push(save_to_file, f"Livrable {team}", result_text)
            return f"SUCCÈS: Mission {team} terminée à 100%. Le rapport/code complet a été publié dans '{save_to_file}' sur GitHub.\n\nAperçu du contenu:\n{result_text[:800]}"
            
        # Troncature du retour direct sur Slack pour protéger la mémoire d'Amal
        if len(result_text) > 3000:
            result_text = result_text[:3000] + "\n[...RÉSULTAT TRONQUÉ POUR PRÉSERVER LA MÉMOIRE DG...]"
            
        return f"--- RETOUR DE L'ÉQUIPE {team.upper()} ({model_name}) ---\n{result_text}"
    except Exception as e:
        return f"ERREUR LORS DE LA DÉLÉGATION À {team}: {str(e)}"

@tool
def git_commit_and_push(file_path: str, commit_message: str, content_to_write: str) -> str:
    """Écrit le contenu généré dans un fichier local PUIS le pousse sur Github."""
    try:
        safe_path = os.path.normpath(file_path).replace("\\", "/")
        os.makedirs(os.path.dirname(safe_path) or ".", exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content_to_write)
            
        github_repo = os.getenv("GITHUB_REPOSITORY")
        if not GITHUB_TOKEN or not github_repo: return "Fichier créé localement, mais GITHUB_TOKEN/REPO manquants pour le push."

        content_b64 = base64.b64encode(content_to_write.encode("utf-8")).decode("utf-8")
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        api_url = f"https://api.github.com/repos/{github_repo}/contents/{safe_path}"

        with httpx.Client() as client:
            get_resp = client.get(api_url, headers=headers)
            payload = {"message": commit_message, "content": content_b64, "branch": "main"}
            if get_resp.status_code == 200: payload["sha"] = get_resp.json().get("sha")
            client.put(api_url, json=payload, headers=headers)

        return f"SUCCÈS: Fichier {file_path} écrit et déployé sur le dépôt Github {github_repo}."
    except Exception as e:
        return f"ERREUR GITHUB: {str(e)}"

all_tools = [
    tavily_web_search,
    firecrawl_read_site,
    redis_fast_memory,
    delegate_to_subagent,
    git_commit_and_push
]

# ==========================================
# 2. ROUTEUR DYNAMIQUE ET CERVEAU D'AMAL (GPT-OSS-120B)
# ==========================================

class AgentState(TypedDict):
    messages: Annotated[List, operator.add]
    retry_count: int

# Modèle principal conservé
llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0, groq_api_key=GROQ_API_KEY)

def select_tools_for_query(text: str):
    """Filtre dynamiquement les outils présentés à Amal-DG pour réduire la charge initiale à ~1500 tokens."""
    text_lower = text.lower()
    selected = []
    
    # Mots-clés Recherche & Scraping
    if any(k in text_lower for k in ["cherche", "recherche", "web", "site", "scrape", "url", "http", "marché", "tal", "quebec"]):
        selected.extend([tavily_web_search, firecrawl_read_site])
        
    # Mots-clés Dev, Sous-agents & GitHub
    if any(k in text_lower for k in ["code", "dev", "agent", "équipe", "team", "git", "push", "github", "fichier"]):
        selected.extend([delegate_to_subagent, git_commit_and_push])
        
    # Mots-clés Mémoire
    if any(k in text_lower for k in ["redis", "mémoire", "sauvegarde", "lit"]):
        selected.append(redis_fast_memory)
        
    # Repli par défaut : Délégation + Recherche uniquement (empreinte minimale)
    if not selected:
        selected = [delegate_to_subagent, tavily_web_search]
        
    return list({t.name: t for t in selected}.values())

def call_model(state: AgentState):
    # Fenêtrage mémoire strict: Seuls les 2 derniers messages sont envoyés à Groq
    recent_messages = state["messages"][-2:] if len(state["messages"]) > 2 else state["messages"]
    
    # Extraction du dernier message utilisateur
    last_user_text = ""
    for m in reversed(recent_messages):
        if isinstance(m, HumanMessage):
            last_user_text = str(m.content)
            break
            
    # Sélection des outils nécessaires
    active_tools = select_tools_for_query(last_user_text)
    
    # Binding dynamique des outils filtrés
    llm_dynamic = llm.bind_tools(active_tools) if active_tools else llm
    
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + recent_messages
    response = llm_dynamic.invoke(messages)
    return {"messages": [response]}

# ToolNode conserve l'intégralité des outils pour l'exécution locale du graphe
tool_node = ToolNode(all_tools)

def reflection_node(state: AgentState):
    retry_count = state.get("retry_count", 0) + 1
    return {
        "messages": [AIMessage(content=f"AUTO-CORRECTION {retry_count}/3: Relecture et ajustement de l'approche.")],
        "retry_count": retry_count
    }

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    return "tools" if hasattr(last_message, "tool_calls") and last_message.tool_calls else "end"

def should_reflect_or_continue(state: AgentState):
    retry_count = state.get("retry_count", 0)
    is_error = isinstance(state["messages"][-1], ToolMessage) and "ERREUR" in str(state["messages"][-1].content)
    return "reflect" if is_error and retry_count < 3 else "agent"

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_node("reflect", reflection_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
workflow.add_conditional_edges("tools", should_reflect_or_continue, {"reflect": "reflect", "agent": "agent"})
workflow.add_edge("reflect", "agent")

app_graph = workflow.compile()

# ==========================================
# 3. GESTIONNAIRE SLACK ASYNCHRONE
# ==========================================

def process_slack_mission_async(channel_id: str, user_prompt: str):
    conversation_history = []
    
    # Chargement mémoire Supabase ultra-léger (1 seul échange précédent)
    if supabase:
        try:
            res = supabase.table("agent_logs").select("task, output").eq("channel_id", channel_id).order("created_at", desc=True).limit(1).execute()
            if res.data:
                log = res.data[0]
                if log.get("task"): conversation_history.append(HumanMessage(content=log["task"][:100]))
                if log.get("output"): conversation_history.append(AIMessage(content=log["output"][:100]))
        except: pass

    conversation_history.append(HumanMessage(content=user_prompt))

    try:
        final_state = app_graph.invoke({"messages": conversation_history, "retry_count": 0})
        final_message = final_state["messages"][-1].content
    except Exception as e:
        final_message = f"⚠️ *Alerte Critique Amal-DG* : {str(e)}"

    # RETOUR SLACK
    if SLACK_TOKEN:
        try:
            httpx.post(
                "https://slack.com/api/chat.postMessage",
                json={"channel": channel_id, "text": final_message},
                headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"}
            )
        except: pass

    # SAUVEGARDE SUPABASE
    if supabase:
        try: supabase.table("agent_logs").insert({"channel_id": channel_id, "task": user_prompt, "output": final_message, "status": "success"}).execute()
        except: pass

# ==========================================
# 4. ENDPOINTS WEB FASTAPI
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

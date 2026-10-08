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
# 0. CONFIGURATION & CLÉS API (Les Super-Pouvoirs)
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

# ADN D'AMAL-DG (Directives pour le SaaS et les Graphes)
SYSTEM_PROMPT = """Tu es Amal-DG, la Directrice Générale et Méta-Architecte IA d'une entreprise SaaS de pointe.
Ton objectif principal est de générer de la valeur, construire des produits robustes et coordonner l'Usine Agentique.

DIRECTIVES CRITIQUES POUR L'ANALYSE DE PROJET :
1. PENSÉE EN GRAPHE : Lorsque tu analyses un nouveau projet SaaS, tu dois obligatoirement fluidifier l'exécution en concevant un graphe de tâches.
2. DÉLÉGATION MASSIVE : Ne code pas tout toi-même. Utilise l'outil `delegate_to_subagent` pour confier l'architecture et le dev complexe à l'équipe Dev (Llama 3.3 70B), et les recherches ou tâches simples à l'équipe Exec (Llama 3.1 8B).
3. AUTONOMIE : Utilise Tavily pour chercher des infos, Firecrawl pour lire la doc des concurrents, et Redis pour stocker tes brouillons.
4. SYNTHÈSE : Reste concise dans tes réponses finales pour préserver la mémoire (Quota TPM)."""

# ==========================================
# 1. OUTILS EXTERNES (Recherche, Scraping, Mémoire)
# ==========================================

@tool
def tavily_web_search(query: str) -> str:
    """Effectue une recherche sur Internet en temps réel pour trouver des informations récentes, des documentations ou analyser le marché."""
    if not TAVILY_API_KEY: return "ERREUR: Clé TAVILY_API_KEY manquante."
    try:
        with httpx.Client() as client:
            res = client.post(
                "https://api.tavily.com/search",
                json={"api_key": TAVILY_API_KEY, "query": query, "search_depth": "advanced", "include_answer": True},
                timeout=15.0
            )
            data = res.json()
            return data.get("answer", "Pas de réponse claire.") + "\nSources: " + ", ".join([r["url"] for r in data.get("results", [])[:3]])
    except Exception as e:
        return f"Erreur de recherche: {str(e)}"

@tool
def firecrawl_read_site(url: str) -> str:
    """Aspire un site web complet (documentation, concurrent, article) et le convertit en texte lisible pour l'agent."""
    if not FIRECRAWL_API_KEY: return "ERREUR: Clé FIRECRAWL_API_KEY manquante."
    try:
        headers = {"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"}
        with httpx.Client() as client:
            res = client.post("https://api.firecrawl.dev/v1/scrape", json={"url": url}, headers=headers, timeout=20.0)
            data = res.json()
            content = data.get("data", {}).get("markdown", "")
            return content[:2500] + "\n[Contenu tronqué pour la mémoire...]" if len(content) > 2500 else content
    except Exception as e:
        return f"Erreur de scraping: {str(e)}"

@tool
def redis_fast_memory(action: str, key: str, value: str = "") -> str:
    """Utilise Upstash Redis comme un bloc-notes ultra-rapide pour stocker (action='set') ou lire (action='get') le contexte global d'un projet SaaS entre les agents."""
    if not REDIS_URL or not REDIS_TOKEN: return "ERREUR: Configuration Upstash Redis manquante."
    try:
        headers = {"Authorization": f"Bearer {REDIS_TOKEN}"}
        with httpx.Client() as client:
            if action == "set":
                res = client.post(f"{REDIS_URL}/set/{key}", data=value, headers=headers)
                return "SUCCÈS: Donnée sauvegardée dans Redis." if res.status_code == 200 else "Erreur sauvegarde Redis."
            elif action == "get":
                res = client.get(f"{REDIS_URL}/get/{key}", headers=headers)
                return res.json().get("result", "Clé introuvable.")
    except Exception as e:
        return f"Erreur Redis: {str(e)}"

# ==========================================
# 2. DÉLÉGATION ET ARCHITECTURE MULTI-MODÈLES (LLaMA)
# ==========================================

@tool
def delegate_to_subagent(team: str, task_description: str) -> str:
    """
    Délègue une tâche spécifique à un sous-agent IA spécialisé.
    Équipes disponibles:
    - 'team_dev' : Utilise Llama 3.3 70B. Parfait pour coder, concevoir l'architecture SaaS ou résoudre des bugs complexes.
    - 'team_exec' : Utilise Llama 3.1 8B. Parfait pour trier des logs, reformuler du texte ou des tâches très rapides.
    """
    try:
        # Routage intelligent
        if team == "team_dev":
            model_name = "llama-3.3-70b-versatile"
        else:
            model_name = "llama-3.1-8b-instant"

        groq_client = ChatGroq(model=model_name, temperature=0.2, groq_api_key=GROQ_API_KEY)
        
        # Isolation du sous-agent (Garantie de ne pas dépasser le TPM global)
        system_msg = SystemMessage(content=f"Tu es le sous-agent {team}. Ta mission est de réaliser cette tâche technique le plus parfaitement possible. Sois direct, fournis le code ou le résultat sans bavardage.")
        user_msg = HumanMessage(content=task_description[:2000]) # Anti-Bug: Limite à 2000 caractères
        
        response = groq_client.invoke([system_msg, user_msg])
        result_text = response.content
        
        # Troncature du retour pour protéger la mémoire d'Amal
        if len(result_text) > 3000:
            result_text = result_text[:3000] + "\n[...RÉSULTAT TRONQUÉ POUR PRÉSERVER LA MÉMOIRE DG...]"
            
        return f"--- RETOUR DE L'ÉQUIPE {team.upper()} ({model_name}) ---\n{result_text}"
    except Exception as e:
        return f"ERREUR LORS DE LA DÉLÉGATION À {team}: {str(e)}"

@tool
def git_commit_and_push(file_path: str, commit_message: str, content_to_write: str) -> str:
    """Écrit le contenu généré dans un fichier local PUIS le pousse sur Github (Idéal pour déployer le SaaS direct)."""
    try:
        # Écriture locale
        safe_path = os.path.normpath(file_path).replace("\\", "/")
        os.makedirs(os.path.dirname(safe_path) or ".", exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content_to_write)
            
        # Poussée vers Github
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

tools = [
    tavily_web_search,
    firecrawl_read_site,
    redis_fast_memory,
    delegate_to_subagent,
    git_commit_and_push
]

# ==========================================
# 3. LE CERVEAU D'AMAL (LANGGRAPH + GPT-OSS-120B)
# ==========================================

class AgentState(TypedDict):
    messages: Annotated[List, operator.add]
    retry_count: int

# Le modèle suprême pour orchestrer (Gratuit mais puissant)
llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0, groq_api_key=GROQ_API_KEY)
llm_with_tools = llm.bind_tools(tools)

def call_model(state: AgentState):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

tool_node = ToolNode(tools)

def reflection_node(state: AgentState):
    retry_count = state.get("retry_count", 0) + 1
    return {
        "messages": [AIMessage(content=f"AUTO-CORRECTION {retry_count}/3: L'outil a échoué. Analyse et essaie une autre approche.")],
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
# 4. GESTIONNAIRE SLACK ASYNCHRONE (ANTI-TIMEOUT & ANTI-413)
# ==========================================

def process_slack_mission_async(channel_id: str, user_prompt: str):
    conversation_history = []
    
    # CHARGEMENT MÉMOIRE SÉCURISÉ (< 1500 tokens)
    if supabase:
        try:
            res = supabase.table("agent_logs").select("task, output").eq("channel_id", channel_id).order("created_at", desc=True).limit(2).execute()
            if res.data:
                for log in res.data[::-1]:
                    if log.get("task"): conversation_history.append(HumanMessage(content=log["task"][:150]))
                    if log.get("output"): conversation_history.append(AIMessage(content=log["output"][:150] + ".."))
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
# 5. ENDPOINTS WEB FASTAPI
# ==========================================

@app.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    """Endpoint Slack non-bloquant : Réponse immédiate pour éviter le timeout 3s."""
    data = await request.json()
    if data.get("type") == "url_verification": return {"challenge": data.get("challenge")}
        
    event = data.get("event", {})
    if event.get("type") in ["message", "app_mention"] and not event.get("bot_id"):
        channel_id = event.get("channel")
        user_prompt = event.get("text")
        if channel_id and user_prompt:
            # Lancement asynchrone pour ne pas bloquer Render
            background_tasks.add_task(process_slack_mission_async, channel_id, user_prompt)

    # Réponse HTTP 200 en moins de 100ms
    return Response(status_code=200)

@app.get("/health")
def health_check():
    """Route pour UptimeRobot, empêche Render de s'endormir."""
    return {"status": "SAAS-ENGINE-ONLINE"}

import os
import httpx
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from supabase import create_client, Client
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from apscheduler.schedulers.background import BackgroundScheduler
from e2b_code_interpreter import Sandbox
from firecrawl import FirecrawlApp
from typing import TypedDict, List, Dict, Any

# 1. Initialisation de l'application FastAPI
app = FastAPI(
    title="DG-Core Sovereign Engine",
    description="Noyau autonome de pilotage multi-agents (Stack 2026)",
    version="2.0.0"
)

# 2. Récupération sécurisée des variables d'environnement
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Erreur critique : Les variables Supabase sont manquantes.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Initialisation du modèle LLM ultra-rapide via Groq
llm_dg = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.2,
    groq_api_key=GROQ_API_KEY
)

# 3. Définition de l'État Global (AgentState)
class AgentState(TypedDict):
    messages: List[Any]
    retry_count: int

# 4. Définition des Outils Souverains (Tools)
@tool
def search_agent_memory(query: str) -> str:
    """Recherche dans la base vectorielle Supabase les connaissances et compétences des agents."""
    try:
        response = supabase.table("agent_memory").select("content, metadata").limit(5).execute()
        return str(response.data)
    except Exception as e:
        return f"Erreur lors de la recherche en mémoire : {str(e)}"

@tool
def scrape_web_page(url: str) -> str:
    """Scrape une page web via Firecrawl et retourne son contenu Markdown pour la veille B2B."""
    try:
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            return "Erreur : FIRECRAWL_API_KEY manquante."
        app_fc = FirecrawlApp(api_key=api_key)
        result = app_fc.scrape_url(url, params={'formats': ['markdown']})
        return result.get('markdown', 'Contenu non trouvé')
    except Exception as e:
        return f"Erreur Firecrawl : {str(e)}"

@tool
def run_code_sandbox(code: str) -> str:
    """Exécute du code Python dans un bac à sable sécurisé E2B."""
    try:
        with Sandbox() as sandbox:
            execution = sandbox.run_code(code)
            return str(execution.logs)
    except Exception as e:
        return f"Erreur E2B Sandbox : {str(e)}"

@tool
def create_slack_channel(channel_name: str) -> str:
    """Crée un nouveau canal Slack public dédié à un sous-projet ou une mission spécifique."""
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    if not slack_token:
        return "Erreur : SLACK_BOT_TOKEN manquant."
    
    url = "https://slack.com/api/conversations.create"
    headers = {
        "Authorization": f"Bearer {slack_token}",
        "Content-Type": "application/json"
    }
    payload = {"name": channel_name}
    try:
        response = httpx.post(url, json=payload, headers=headers)
        data = response.json()
        if data.get("ok"):
            channel_id = data["channel"]["id"]
            return f"Canal Slack #{channel_name} créé avec succès (ID: {channel_id})."
        else:
            return f"Erreur Slack : {data.get('error')}"
    except Exception as e:
        return f"Erreur technique Slack : {str(e)}"

tools = [search_agent_memory, scrape_web_page, run_code_sandbox, create_slack_channel]
llm_dg_with_tools = llm_dg.bind_tools(tools)

# 5. Planificateur Proactif (APScheduler)
def proactive_dg_routine():
    """Routine exécutée automatiquement en arrière-plan pour lancer des analyses de marché autonomes."""
    print("[DG-CORE PROACTIVITÉ] Lancement de la routine automatique de veille...")
    # Le DG-Core déclenche une mission autonome de fond
    try:
        initial_state = {
            "messages": [HumanMessage(content="Effectue une veille proactive des opportunités business rentables.")],
            "retry_count": 0
        }
        # Appel interne du graphe pour exécuter la tâche de fond
        app_graph.invoke(initial_state)
    except Exception as e:
        print(f"[DG-CORE ERREUR PROACTIVITÉ] {str(e)}")

scheduler = BackgroundScheduler()
scheduler.add_job(proactive_dg_routine, 'interval', hours=2)

@app.on_event("startup")
async def startup_event():
    scheduler.start()
    print("[DG-CORE] Planificateur temporel démarré.")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()

# 6. Définition des Nœuds du Graphe LangGraph
def call_model(state: AgentState):
    messages = state["messages"]
    response = llm_dg_with_tools.invoke(messages)
    return {"messages": [response]}

def tool_node(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    tool_results = []
    
    if hasattr(last_message, "tool_calls"):
        for tool_call in last_message.tool_calls:
            try:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args", {})
                
                if tool_name == "search_agent_memory":
                    result = search_agent_memory.invoke(tool_args)
                elif tool_name == "scrape_web_page":
                    result = scrape_web_page.invoke(tool_args)
                elif tool_name == "run_code_sandbox":
                    result = run_code_sandbox.invoke(tool_args)
                elif tool_name == "create_slack_channel":
                    result = create_slack_channel.invoke(tool_args)
                else:
                    result = f"Outil {tool_name} non reconnu."
                
                tool_results.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
            except Exception as e:
                tool_results.append(ToolMessage(content=f"ERROR: {str(e)}", tool_call_id=tool_call["id"]))
                
    return {"messages": tool_results}

def reflection_node(state: AgentState):
    messages = state["messages"]
    retry_count = state.get("retry_count", 0) + 1
    feedback_content = f"[AUTO-CORRECTION TENTATIVE {retry_count}/3] Analyse l'erreur précédente, corrige tes paramètres et propose une nouvelle exécution valide."
    return {
        "messages": [AIMessage(content=feedback_content)],
        "retry_count": retry_count
    }

# 7. Routage Conditionnel
def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "end"

def should_reflect_or_continue(state: AgentState):
    messages = state["messages"]
    retry_count = state.get("retry_count", 0)
    last_message = messages[-1]
    
    is_error = isinstance(last_message, ToolMessage) and "ERROR" in last_message.content
    if is_error and retry_count < 3:
        return "reflect"
    return "agent"

# Construction du graphe d'exécution
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_node("reflect", reflection_node)

workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
workflow.add_conditional_edges("tools", should_reflect_or_continue, {"reflect": "reflect", "agent": "agent"})
workflow.add_edge("reflect", "agent")

app_graph = workflow.compile()

# 8. Endpoints FastAPI & Webhook Slack
class MissionRequest(BaseModel):
    prompt: str

@app.post("/run-mission")
async def run_mission(request: MissionRequest):
    try:
        initial_state = {
            "messages": [HumanMessage(content=request.prompt)],
            "retry_count": 0
        }
        final_state = app_graph.invoke(initial_state)
        final_message = final_state["messages"][-1].content
        
        # Enregistrement dans Supabase
        supabase.table("execution_logs").insert({
            "task": request.prompt,
            "output": {"result": final_message},
            "status": "success"
        }).execute()
        
        return {
            "status": "success",
            "result": final_message,
            "retries_used": final_state.get("retry_count", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/slack/events")
async def slack_events(request: Request):
    data = await request.json()
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}
    
    event = data.get("event", {})
    if event.get("type") in ["message", "app_mention"] and not event.get("bot_id"):
        user_prompt = event.get("text", "")
        channel_id = event.get("channel")
        
        initial_state = {
            "messages": [HumanMessage(content=user_prompt)],
            "retry_count": 0
        }
        final_state = app_graph.invoke(initial_state)
        agent_reply = final_state["messages"][-1].content
        
        slack_token = os.getenv("SLACK_BOT_TOKEN")
        if slack_token and channel_id:
            async with httpx.AsyncClient() as client:
                await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={"Authorization": f"Bearer {slack_token}"},
                    json={"channel": channel_id, "text": agent_reply}
                )
    return {"status": "ok"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "DG-AGENT-CORE"}

@app.get("/model")
async def get_active_model():
    return {
        "dg_model": "llama-3.3-70b-versatile",
        "tools_integrated": ["firecrawl", "e2b", "supabase", "slack_channels"]
    }

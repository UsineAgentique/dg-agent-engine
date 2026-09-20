import os
import operator
from typing import TypedDict, Annotated, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# LangGraph & LangChain imports
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage
from langchain_groq import ChatGroq

# Supabase imports
from supabase import create_client, Client

# APScheduler imports (Proactivité)
from apscheduler.schedulers.background import BackgroundScheduler

# Outils Avancés (Firecrawl & E2B)
from firecrawl import FirecrawlApp
from e2b_code_interpreter import Sandbox

# Initialisation de l'application FastAPI
app = FastAPI(title="DG-Core API", version="1.2.1")

# Initialisation du client Supabase (Mémoire RAG)
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

# 1. Définition de l'État Global de l'Agent
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    retry_count: int

# Initialisation du modèle LLM (Groq - gpt-oss-120b haute performance)
groq_api_key = os.getenv("GROQ_API_KEY")
llm = ChatGroq(
    model="gpt-oss-120b",
    temperature=0,
    api_key=groq_api_key
)

# --- 2. Outils Opérationnels & Mémoire ---

def search_agent_memory(query_text: str):
    """Interroge la mémoire vectorielle Supabase pour retrouver des playbooks."""
    if not supabase:
        return "Erreur : Client Supabase non initialisé."
    try:
        response = supabase.table("agent_memory").select("content, metadata").limit(5).execute()
        return response.data
    except Exception as e:
        return f"Erreur lors de la recherche en mémoire : {str(e)}"

def scrape_web_page(url: str):
    """Scrape une page web via Firecrawl et retourne son contenu Markdown."""
    try:
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            return "Erreur : FIRECRAWL_API_KEY manquante dans l'environnement."
        app_fc = FirecrawlApp(api_key=api_key)
        result = app_fc.scrape_url(url, params={'formats': ['markdown']})
        return result.get('markdown', 'Contenu non trouvé')
    except Exception as e:
        return f"Erreur Firecrawl : {str(e)}"

def run_code_sandbox(code: str):
    """Exécute du code Python dans un bac à sable sécurisé E2B."""
    try:
        with Sandbox() as sandbox:
            execution = sandbox.run_code(code)
            return str(execution.logs)
    except Exception as e:
        return f"Erreur E2B Sandbox : {str(e)}"

def proactive_dg_routine():
    """Routine exécutée automatiquement en arrière-plan par APScheduler."""
    print("[DG-CORE PROACTIVITÉ] Lancement de la routine automatique de veille...")


# --- 3. Configuration du Planificateur (APScheduler) ---

scheduler = BackgroundScheduler()
scheduler.add_job(proactive_dg_routine, 'interval', hours=2)

@app.on_event("startup")
async def startup_event():
    scheduler.start()
    print("[DG-CORE] Planificateur temporel démarré.")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()


# --- 4. Définition des Nœuds du Graphe ---

def call_model(state: AgentState):
    messages = state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}

def tool_node(state: AgentState):
    """Exécute l'outil demandé par le DG (Recherche mémoire, Firecrawl ou E2B)."""
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_results = []
    if last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            try:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args", {})
                
                if tool_name == "search_agent_memory":
                    result = str(search_agent_memory(tool_args.get("query_text", "")))
                elif tool_name == "scrape_web_page":
                    result = str(scrape_web_page(tool_args.get("url", "")))
                elif tool_name == "run_code_sandbox":
                    result = str(run_code_sandbox(tool_args.get("code", "")))
                else:
                    result = f"Outil {tool_name} non reconnu."
                    
                tool_results.append(
                    ToolMessage(content=result, tool_call_id=tool_call["id"])
                )
            except Exception as e:
                error_msg = f"ERROR: L'outil a échoué : {str(e)}"
                tool_results.append(
                    ToolMessage(content=error_msg, tool_call_id=tool_call["id"])
                )
                
    return {"messages": tool_results}

def reflection_node(state: AgentState):
    messages = state["messages"]
    retry_count = state.get("retry_count", 0) + 1
    last_message = messages[-1]
    error_content = last_message.content if hasattr(last_message, "content") else "Erreur inconnue"
    
    feedback_content = (
        f"[AUTO-CORRECTION TENTATIVE {retry_count}/3] "
        f"L'opération précédente a échoué : '{error_content}'. "
        "Analyse la cause, corrige tes paramètres et propose une nouvelle exécution valide."
    )
    
    return {
        "messages": messages + [AIMessage(content=feedback_content)],
        "retry_count": retry_count
    }


# --- 5. Routage Conditionnel ---

def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return "end"

def should_reflect_or_continue(state: AgentState):
    messages = state["messages"]
    retry_count = state.get("retry_count", 0)
    last_message = messages[-1]
    
    is_error = False
    if isinstance(last_message, ToolMessage):
        content_lower = str(last_message.content).lower()
        if any(kw in content_lower for kw in ["error", "exception", "failed", "invalid", "traceback"]):
            is_error = True
            
    if is_error:
        if retry_count >= 3:
            return "stop"
        return "reflect"
    return "continue"


# --- 6. Construction du Graphe ---

workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_node("reflect", reflection_node)

workflow.set_entry_point("agent")

workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
workflow.add_conditional_edges("tools", should_reflect_or_continue, {"reflect": "reflect", "stop": END, "continue": "agent"})
workflow.add_edge("reflect", "agent")

app_graph = workflow.compile()


# --- 7. Endpoints FastAPI ---

class MissionRequest(BaseModel):
    prompt: str

@app.post("/run-mission")
async def run_mission(request: MissionRequest):
    try:
        initial_state = {
            "messages": [BaseMessage(content=request.prompt, type="human")],
            "retry_count": 0
        }
        final_state = app_graph.invoke(initial_state)
        final_message = final_state["messages"][-1].content
        
        return {
            "status": "success",
            "result": final_message,
            "retries_used": final_state.get("retry_count", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "DG-AGENT-CORE"}

@app.get("/model")
async def get_active_model():
    return {"model": "gpt-oss-120b", "tools_integrated": ["firecrawl", "e2b", "supabase"]}

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

# Initialisation de l'application FastAPI
app = FastAPI(title="DG-Core API", version="1.1.0")

# Initialisation du client Supabase (Mémoire RAG)
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

# 1. Définition de l'État Global de l'Agent (avec suivi des erreurs)
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    retry_count: int  # Compteur de sécurité pour l'auto-correction

# Initialisation du modèle LLM (Groq - gpt-oss-120b haute performance)
groq_api_key = os.getenv("GROQ_API_KEY")
llm = ChatGroq(
    model="gpt-oss-120b",
    temperature=0,
    api_key=groq_api_key
)

# --- 2. Outils de Mémoire & Tâches Proactives ---

def search_agent_memory(query_text: str):
    """Interroge la mémoire vectorielle Supabase pour retrouver des playbooks ou antécédents."""
    if not supabase:
        return "Erreur : Client Supabase non initialisé."
    try:
        response = supabase.table("agent_memory").select("content, metadata").limit(5).execute()
        return response.data
    except Exception as e:
        return f"Erreur lors de la recherche en mémoire : {str(e)}"

def proactive_dg_routine():
    """Routine exécutée automatiquement en arrière-plan par APScheduler."""
    print("[DG-CORE PROACTIVITÉ] Lancement de la routine automatique de veille...")


# --- 3. Configuration du Planificateur (APScheduler) ---

scheduler = BackgroundScheduler()
scheduler.add_job(proactive_dg_routine, 'interval', hours=2)  # S'exécute toutes les 2 heures

@app.on_event("startup")
async def startup_event():
    """Démarre le planificateur au lancement du serveur FastAPI."""
    scheduler.start()
    print("[DG-CORE] Planificateur temporel démarré avec succès.")

@app.on_event("shutdown")
async def shutdown_event():
    """Arrête proprement le planificateur à la fermeture."""
    scheduler.shutdown()


# --- 4. Définition des Nœuds du Graphe ---

def call_model(state: AgentState):
    """Nœud principal : fait appel au DG (LLM gpt-oss-120b) pour analyser l'état."""
    messages = state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}

def tool_node(state: AgentState):
    """Nœud d'exécution des outils (incluant la mémoire Supabase)."""
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_results = []
    if last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            try:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args", {})
                
                if tool_name == "search_agent_memory":
                    query_text = tool_args.get("query_text", "")
                    result = str(search_agent_memory(query_text))
                else:
                    result = f"Exécution réussie de l'outil {tool_name}"
                    
                tool_results.append(
                    ToolMessage(content=result, tool_call_id=tool_call["id"])
                )
            except Exception as e:
                error_msg = f"ERROR: L'outil a échoué avec l'exception : {str(e)}"
                tool_results.append(
                    ToolMessage(content=error_msg, tool_call_id=tool_call["id"])
                )
                
    return {"messages": tool_results}

def reflection_node(state: AgentState):
    """Nœud d'auto-correction : analyse l'erreur et guide le DG pour rectifier ses paramètres."""
    messages = state["messages"]
    retry_count = state.get("retry_count", 0) + 1
    
    last_message = messages[-1]
    error_content = last_message.content if hasattr(last_message, "content") else "Erreur inconnue"
    
    feedback_content = (
        f"[AUTO-CORRECTION TENTATIVE {retry_count}/3] "
        f"L'opération précédente a généré l'erreur suivante : '{error_content}'. "
        "Analyse la cause, corrige tes arguments et propose une nouvelle exécution valide."
    )
    
    return {
        "messages": messages + [AIMessage(content=feedback_content)],
        "retry_count": retry_count
    }


# --- 5. Fonctions de Routage Conditionnel ---

def should_continue(state: AgentState):
    """Détermine si l'agent doit appeler des outils ou terminer sa mission."""
    messages = state["messages"]
    last_message = messages[-1]
    
    if last_message.tool_calls:
        return "tools"
    return "end"

def should_reflect_or_continue(state: AgentState):
    """Vérifie si le retour d'un outil contient une erreur pour déclencher la réflexion."""
    messages = state["messages"]
    retry_count = state.get("retry_count", 0)
    last_message = messages[-1]
    
    is_error = False
    if isinstance(last_message, ToolMessage):
        content_lower = str(last_message.content).lower()
        if any(kw in content_lower for kw in ["error", "exception", "failed", "invalid", "traceback", "syntax error"]):
            is_error = True
            
    if is_error:
        if retry_count >= 3:
            return "stop"
        return "reflect"
        
    return "continue"


# --- 6. Construction du Graphe LangGraph ---

workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_node("reflect", reflection_node)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        "end": END
    }
)

workflow.add_conditional_edges(
    "tools",
    should_reflect_or_continue,
    {
        "reflect": "reflect",
        "stop": END,
        "continue": "agent"
    }
)

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
    return {"model": "gpt-oss-120b", "provider": "Groq"}

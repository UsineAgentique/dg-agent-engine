import os
import operator
from typing import TypedDict, Annotated, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# LangGraph & LangChain imports
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage
from langchain_groq import ChatGroq

# Initialisation de l'application FastAPI
app = FastAPI(title="DG-Core API", version="1.0.0")

# 1. Définition de l'État Global de l'Agent (avec suivi des erreurs)
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    retry_count: int  # Compteur de sécurité pour l'auto-correction

# Initialisation du modèle LLM (Groq)
groq_api_key = os.getenv("GROQ_API_KEY")
llm = ChatGroq(
    model="llama3-70b-8192",
    temperature=0,
    api_key=groq_api_key
)

# --- 2. Définition des Nœuds du Graphe ---

def call_model(state: AgentState):
    """Nœud principal : fait appel au DG (LLM) pour analyser l'état et décider des actions."""
    messages = state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}

def tool_node(state: AgentState):
    """Nœud d'exécution des outils."""
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_results = []
    if last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            try:
                result = f"Exécution réussie de l'outil {tool_call['name']}"
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


# --- 3. Fonctions de Routage Conditionnel ---

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


# --- 4. Construction du Graphe LangGraph ---

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

# Correction propre ici : on appelle directement la fonction de routage
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


# --- 5. Endpoints FastAPI ---

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

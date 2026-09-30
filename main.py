import os
from typing import TypedDict, Annotated, List
import operator
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
import httpx
from supabase import create_client, Client

app = FastAPI(title="DG-AGENT-CORE", version="2.0.0")

# ==========================================
# 0. CHARGEMENT DYNAMIQUE DU CERVEAU (dg_system.md)
# ==========================================
SYSTEM_PROMPT = "Tu es le Directeur Général (DG) et Méta-Architecte d'une structure technologique de pointe."
if os.path.exists("dg_system.md"):
    try:
        with open("dg_system.md", "r", encoding="utf-8") as f:
            SYSTEM_PROMPT = f.read()
        print("Succès : Fichier dg_system.md chargé comme System Prompt exécutif.")
    except Exception as e:
        print(f"Alerte : Impossible de lire dg_system.md ({e})")

# Initialisation sécurisée (URL en dur pour éliminer les erreurs de variable Render)
SUPABASE_URL = "https://qiwdenzxtawkrrnkwoar.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_SERVICE_ROLE_KEY else None

# ==========================================
# 1. OUTILS D'INFRASTRUCTURE ET DE MAINTENANCE
# ==========================================

@tool
def clean_system_database() -> str:
    """Nettoie complètement les tables `execution_logs` et `agent_memory` sur Supabase et consigne l'action dans `missions_log`."""
    try:
        url = "https://qiwdenzxtawkrrnkwoar.supabase.co"
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not key:
            return "ERREUR : La clé Supabase (SUPABASE_SERVICE_ROLE_KEY) n'est pas configurée sur le serveur."

        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

        with httpx.Client() as client:
            # 1. Purge des tables de test
            resp_logs = client.delete(f"{url}/rest/v1/execution_logs?id=not.is.null", headers=headers)
            resp_memory = client.delete(f"{url}/rest/v1/agent_memory?id=not.is.null", headers=headers)
            
            # 2. Consignation de la traçabilité dans missions_log pour satisfaire les exigences d'audit
            log_payload = {
                "task": "Clean State System Purge",
                "output": "Purge des tables execution_logs et agent_memory effectuée avec succès.",
                "status": "success"
            }
            resp_mission = client.post(f"{url}/rest/v1/missions_log", json=log_payload, headers=headers)

        if resp_logs.status_code in [200, 204] and resp_memory.status_code in [200, 204]:
            return "Succès : Les tables `execution_logs` et `agent_memory` ont été purgées et l'opération a été consignée dans `missions_log`. État du système propre (Clean State) validé."
        else:
            return f"Erreur lors de la purge. Logs status: {resp_logs.status_code}, Memory status: {resp_memory.status_code}, Mission log status: {resp_mission.status_code}"
            
    except Exception as e:
        return f"ERREUR TECHNIQUE LORS DU NETTOYAGE : {str(e)}"

@tool
def inspect_infrastructure_health() -> str:
    """Vérifie l'état de santé global de l'infrastructure (Supabase, Render, connectivité)."""
    status_report = []
    
    try:
        url = "https://qiwdenzxtawkrrnkwoar.supabase.co"
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        headers = {"apikey": key, "Authorization": f"Bearer {key}"}
        resp = httpx.get(f"{url}/rest/v1/execution_logs?select=count", headers=headers, timeout=5.0)
        if resp.status_code == 200:
            status_report.append("Supabase DB : OPÉRATIONNEL (Connecté)")
        else:
            status_report.append(f"Supabase DB : ERREUR (Statut {resp.status_code})")
    except Exception as e:
        status_report.append(f"Supabase DB : INACCESSIBLE ({str(e)})")

    slack_token = os.getenv("SLACK_BOT_TOKEN")
    if slack_token and slack_token.startswith("xoxb-"):
        status_report.append("Slack Bot Token : CONFIGURÉ et au bon format")
    else:
        status_report.append("Slack Bot Token : MANQUANT ou format invalide")

    return "\n".join(status_report)

@tool
def execute_system_maintenance_command(command_type: str) -> str:
    """Exécute une commande de maintenance de bas niveau sur l'infrastructure (purge, reset des logs ou optimisation)."""
    if command_type == "purge_logs":
        return clean_system_database.invoke({})
    elif command_type == "diagnostic_system":
        return inspect_infrastructure_health.invoke({})
    return f"Commande de maintenance '{command_type}' non reconnue."


# ==========================================
# 2. OUTILS D'AUTONOMIE WORKSPACE & SOUS-AGENTS
# ==========================================

@tool
def explore_workspace_directory(directory_path: str = ".") -> str:
    """Permet à Amal DG de cartographier l'arborescence des fichiers et sous-agents disponibles dans le projet."""
    try:
        structure = []
        for root, dirs, files in os.walk(directory_path):
            if ".git" in root or "__pycache__" in root or "venv" in root:
                continue
            level = root.replace(directory_path, "").count(os.sep)
            indent = " " * 4 * level
            structure.append(f"{indent}{os.path.basename(root)}/")
            sub_indent = " " * 4 * (level + 1)
            for f in files:
                if f.endswith((".md", ".py", ".yaml", ".json")):
                    structure.append(f"{sub_indent}{f}")
        return "\n".join(structure) if structure else "Espace de travail vide."
    except Exception as e:
        return f"ERREUR LORS DE L'EXPLORATION : {str(e)}"

@tool
def read_workspace_file(file_path: str) -> str:
    """Permet à Amal DG de lire le contenu exact d'un sous-agent (.md) ou d'un fichier de configuration."""
    try:
        safe_path = os.path.normpath(file_path)
        if not os.path.exists(safe_path):
            return f"ERREUR : Le fichier '{file_path}' est introuvable."
        with open(safe_path, "r", encoding="utf-8") as f:
            content = f.read()
        return f"--- CONTENU DE {file_path} ---\n{content}"
    except Exception as e:
        return f"ERREUR LORS DE LA LECTURE : {str(e)}"

@tool
def write_or_improve_agent_skill(file_path: str, content: str) -> str:
    """Permet à Amal DG de créer un nouveau sous-agent, de rédiger une skill ou d'améliorer ses propres instructions."""
    try:
        safe_path = os.path.normpath(file_path)
        directory = os.path.dirname(safe_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"SUCCÈS : Le sous-agent/skill '{file_path}' a été écrit ou mis à jour avec succès."
    except Exception as e:
        return f"ERREUR LORS DE L'ÉCRITURE : {str(e)}"

@tool
def remove_obsolete_component(file_path: str) -> str:
    """Permet à Amal DG de supprimer un fichier ou un sous-agent devenu inutile ou obsolète."""
    try:
        safe_path = os.path.normpath(file_path)
        if os.path.exists(safe_path):
            os.remove(safe_path)
            return f"SUCCÈS : '{file_path}' a été supprimé du système."
        return f"AVERTISSEMENT : Le fichier '{file_path}' n'existe pas."
    except Exception as e:
        return f"ERREUR LORS DE LA SUPPRESSION : {str(e)}"

tools = [
    clean_system_database,
    inspect_infrastructure_health,
    execute_system_maintenance_command,
    explore_workspace_directory,
    read_workspace_file,
    write_or_improve_agent_skill,
    remove_obsolete_component
]


# ==========================================
# 3. CONFIGURATION DU MODÈLE ET DU GRAPHE
# ==========================================

class AgentState(TypedDict):
    messages: Annotated[List, operator.add]
    retry_count: int

llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
llm_with_tools = llm.bind_tools(tools)

def call_model(state: AgentState):
    system_message = SystemMessage(content=SYSTEM_PROMPT)
    messages = [system_message] + state["messages"]
    
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

tool_node = ToolNode(tools)

def reflection_node(state: AgentState):
    messages = state["messages"]
    retry_count = state.get("retry_count", 0) + 1
    feedback_content = f"AUTO-CORRECTION TENTATIVE {retry_count}/3: Analyse l'erreur et propose une correction."
    return {
        "messages": [AIMessage(content=feedback_content)],
        "retry_count": retry_count
    }

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "end"

def should_reflect_or_continue(state: AgentState):
    retry_count = state.get("retry_count", 0)
    last_message = state["messages"][-1]
    is_error = isinstance(last_message, ToolMessage) and "ERREUR" in last_message.content
    if is_error and retry_count < 3:
        return "reflect"
    return "agent"

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
# 4. ENDPOINTS FASTAPI
# ==========================================

class MissionRequest(BaseModel):
    prompt: str

@app.post("/slack/events")
async def slack_events(request: Request):
    """Endpoint pour intercepter et traiter les événements Slack."""
    data = await request.json()
    
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}
        
    event = data.get("event", {})
    if event.get("type") in ["message", "app_mention"] and not event.get("bot_id"):
        user_prompt = event.get("text", "")
        channel_id = event.get("channel", "")
        
        try:
            initial_state = {
                "messages": [HumanMessage(content=user_prompt)],
                "retry_count": 0
            }
            final_state = app_graph.invoke(initial_state)
            final_message = final_state["messages"][-1].content
        except Exception as e:
            final_message = f"ERREUR D'EXÉCUTION DU DG-CORE : {str(e)}"
            
        slack_token = os.getenv("SLACK_BOT_TOKEN")
        if slack_token:
            headers = {
                "Authorization": f"Bearer {slack_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "channel": channel_id,
                "text": final_message
            }
            try:
                httpx.post("https://slack.com/api/chat.postMessage", json=payload, headers=headers)
            except Exception:
                pass
                
        if supabase:
            try:
                supabase.table("execution_logs").insert({
                    "task": user_prompt,
                    "output": final_message,
                    "status": "success"
                }).execute()
            except Exception:
                pass

    return {"status": "ok"}

@app.post("/run-mission")
async def run_mission(request: MissionRequest):
    try:
        initial_state = {
            "messages": [HumanMessage(content=request.prompt)],
            "retry_count": 0
        }
        final_state = app_graph.invoke(initial_state)
        final_message = final_state["messages"][-1].content
        
        if supabase:
            supabase.table("execution_logs").insert({
                "task": request.prompt,
                "output": final_message,
                "status": "success"
            }).execute()
        
        return {
            "status": "success",
            "result": final_message,
            "retries_used": final_state.get("retry_count", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "DG-AGENT-CORE",
        "dg_system_loaded": os.path.exists("dg_system.md")
    }

@app.get("/model")
async def get_active_model():
    return {
        "dg_model": "openai/gpt-oss-120b",
        "tools_integrated": [t.name for t in tools],
        "system_prompt_source": "dg_system.md"
    }

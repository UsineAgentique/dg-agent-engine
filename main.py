import os
import sys
import json
import subprocess
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

app = FastAPI(title="DG-AGENT-CORE", version="2.5.0")

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

# Initialisation Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://qiwqenzxtawkrnknkoar.supabase.co")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_SERVICE_ROLE_KEY else None

# ==========================================
# 1. OUTILS D'INFRASTRUCTURE ET DE MAINTENANCE
# ==========================================

@tool
def clean_system_database() -> str:
    """Nettoie complètement les tables `agent_logs` et `agent_memory` sur Supabase et consigne l'action dans `missions_log`."""
    try:
        url = SUPABASE_URL
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
            resp_logs = client.delete(f"{url}/rest/v1/agent_logs?id=not.is.null", headers=headers)
            resp_memory = client.delete(f"{url}/rest/v1/agent_memory?id=not.is.null", headers=headers)
            
            log_payload = {
                "task": "Clean State System Purge",
                "output": "Purge des tables agent_logs et agent_memory effectuée avec succès.",
                "status": "success"
            }
            resp_mission = client.post(f"{url}/rest/v1/missions_log", json=log_payload, headers=headers)

        if resp_logs.status_code in [200, 204] and resp_memory.status_code in [200, 204]:
            return "Succès : Purge validée et consignée dans `missions_log`. État du système propre (Clean State) validé."
        else:
            return f"Erreur lors de la purge. Logs status: {resp_logs.status_code}, Memory status: {resp_memory.status_code}"
            
    except Exception as e:
        return f"ERREUR TECHNIQUE LORS DU NETTOYAGE : {str(e)}"

@tool
def inspect_infrastructure_health() -> str:
    """Vérifie l'état de santé global de l'infrastructure (Supabase, Slack, Clés API)."""
    status_report = []
    
    try:
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        headers = {"apikey": key, "Authorization": f"Bearer {key}"}
        resp = httpx.get(f"{SUPABASE_URL}/rest/v1/agent_logs?select=count", headers=headers, timeout=5.0)
        if resp.status_code == 200:
            status_report.append("Supabase DB : OPÉRATIONNEL (Connecté)")
        else:
            status_report.append(f"Supabase DB : ERREUR (Statut {resp.status_code})")
    except Exception as e:
        status_report.append(f"Supabase DB : INACCESSIBLE ({str(e)})")

    slack_token = os.getenv("SLACK_BOT_TOKEN")
    if slack_token and slack_token.startswith("xoxb-"):
        status_report.append("Slack Bot Token : CONFIGURÉ et valide")
    else:
        status_report.append("Slack Bot Token : MANQUANT ou format invalide")

    return "\n".join(status_report)

@tool
def execute_system_maintenance_command(command_type: str) -> str:
    """Exécute une commande de maintenance de bas niveau sur l'infrastructure."""
    if command_type == "purge_logs":
        return clean_system_database.invoke({})
    elif command_type == "diagnostic_system":
        return inspect_infrastructure_health.invoke({})
    return f"Commande de maintenance '{command_type}' non reconnue."


# ==========================================
# 2. OUTILS WORKSPACE, GIT & EXÉCUTION ISOLÉE
# ==========================================

@tool
def git_commit_and_push(file_path: str, commit_message: str) -> str:
    """Effectue un commit et un push direct d'un fichier vers le dépôt GitHub distant en utilisant GITHUB_TOKEN."""
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        return "ERREUR : GITHUB_TOKEN est absent des variables d'environnement Render."

    try:
        safe_path = os.path.normpath(file_path)
        if not os.path.exists(safe_path):
            return f"ERREUR : Le fichier '{file_path}' n'existe pas localement."

        # Config temporaire Git
        subprocess.run(["git", "config", "user.email", "bot@amal-dg.local"], check=True)
        subprocess.run(["git", "config", "user.name", "Amal-DG Bot"], check=True)

        # Stage + Commit
        subprocess.run(["git", "add", safe_path], check=True)
        commit_proc = subprocess.run(["git", "commit", "-m", commit_message], capture_output=True, text=True)

        # Obtenir URL remote
        remote_proc = subprocess.run(["git", "config", "--get", "remote.origin.url"], capture_output=True, text=True)
        remote_url = remote_proc.stdout.strip()

        if "github.com" in remote_url:
            clean_url = remote_url.split("github.com/")[-1]
            auth_url = f"https://x-access-token:{github_token}@github.com/{clean_url}"
            push_proc = subprocess.run(["git", "push", auth_url, "HEAD"], capture_output=True, text=True)
        else:
            push_proc = subprocess.run(["git", "push"], capture_output=True, text=True)

        if push_proc.returncode == 0:
            return f"SUCCÈS : Le fichier '{file_path}' a été commité ('{commit_message}') et pushé avec succès sur GitHub."
        else:
            return f"ERREUR PUSH GIT : {push_proc.stderr}"

    except Exception as e:
        return f"ERREUR EXÉCUTION GIT : {str(e)}"

@tool
def explore_workspace_directory(directory_path: str = ".") -> str:
    """Permet à Amal DG de cartographier l'arborescence des fichiers et sous-agents disponibles."""
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
    """Permet à Amal DG de lire le contenu exact d'un sous-agent (.py, .md) ou d'un fichier de configuration."""
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
    """Permet à Amal DG de créer un nouveau sous-agent Python ou d'améliorer des instructions."""
    try:
        safe_path = os.path.normpath(file_path)
        directory = os.path.dirname(safe_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"SUCCÈS : Le composant '{file_path}' a été écrit ou mis à jour avec succès."
    except Exception as e:
        return f"ERREUR LORS DE L'ÉCRITURE : {str(e)}"

@tool
def remove_obsolete_component(file_path: str) -> str:
    """Permet à Amal DG de supprimer un fichier ou sous-agent devenu obsolète."""
    try:
        safe_path = os.path.normpath(file_path)
        if os.path.exists(safe_path):
            os.remove(safe_path)
            return f"SUCCÈS : '{file_path}' a été supprimé du système."
        return f"AVERTISSEMENT : Le fichier '{file_path}' n'existe pas."
    except Exception as e:
        return f"ERREUR LORS DE LA SUPPRESSION : {str(e)}"

@tool
def execute_subagent(agent_name: str, mission: str) -> str:
    """Exécute un sous-agent autonome situé dans 'agents/' de manière totalement isolée (Subprocess)."""
    try:
        os.makedirs("agents", exist_ok=True)
        clean_name = os.path.basename(agent_name).replace(".py", "").strip()
        file_path = os.path.join("agents", f"{clean_name}.py")

        if not os.path.exists(file_path):
            return f"ERREUR : Le sous-agent '{clean_name}' n'existe pas dans 'agents/'. Crée-le d'abord avec 'write_or_improve_agent_skill'."

        runner_code = f"""
import sys
import json
import importlib.util

try:
    spec = importlib.util.spec_from_file_location("subagent", {json.dumps(file_path)})
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    if hasattr(module, "run_mission"):
        res = module.run_mission({json.dumps(mission)})
        print(json.dumps({{"status": "success", "result": res}}))
    else:
        print(json.dumps({{"status": "error", "error": "La fonction run_mission(mission) est introuvable dans le module."}}))
except Exception as e:
    print(json.dumps({{"status": "error", "error": str(e)}}))
"""

        process = subprocess.run(
            [sys.executable, "-c", runner_code],
            capture_output=True,
            text=True,
            timeout=90
        )

        if process.returncode != 0:
            return f"ERREUR CRITIQUE SUBPROCESS (Code {process.returncode}) :\n{process.stderr}"

        output_data = json.loads(process.stdout.strip())
        if output_data.get("status") == "success":
            return f"--- RÉSULTAT EXÉCUTÉ PAR LE SOUS-AGENT ({clean_name}) ---\n{output_data.get('result')}"
        else:
            return f"ERREUR DU SOUS-AGENT : {output_data.get('error')}"

    except subprocess.TimeoutExpired:
        return f"ALERTE TIMEOUT : Le sous-agent '{clean_name}' a été interrompu car son exécution a dépassé 90 secondes."
    except Exception as e:
        return f"ERREUR DE PILOTAGE SYSTEME : {str(e)}"

tools = [
    clean_system_database,
    inspect_infrastructure_health,
    execute_system_maintenance_command,
    git_commit_and_push,
    explore_workspace_directory,
    read_workspace_file,
    write_or_improve_agent_skill,
    remove_obsolete_component,
    execute_subagent
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
    retry_count = state.get("retry_count", 0) + 1
    feedback_content = f"AUTO-CORRECTION TENTATIVE {retry_count}/3: Analyse l'erreur technique rencontrée et corrige ta stratégie."
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
    is_error = isinstance(last_message, ToolMessage) and "ERREUR" in str(last_message.content)
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
    """Endpoint Slack avec mémoire isolée par canal (channel_id)."""
    data = await request.json()
    
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}
        
    event = data.get("event", {})
    if event.get("type") in ["message", "app_mention"] and not event.get("bot_id"):
        user_prompt = event.get("text", "")
        channel_id = event.get("channel", "")
        
        # --- MÉMOIRE ISOLÉE PAR CANAL SLACK ---
        conversation_history = []
        if supabase and channel_id:
            try:
                res = supabase.table("agent_logs") \
                    .select("task, output") \
                    .eq("channel_id", channel_id) \
                    .order("created_at", desc=True) \
                    .limit(5) \
                    .execute()
                
                if res.data:
                    logs = res.data[::-1]
                    for log in logs:
                        if log.get("task"):
                            conversation_history.append(HumanMessage(content=log["task"]))
                        if log.get("output"):
                            conversation_history.append(AIMessage(content=log["output"]))
            except Exception as e:
                print(f"Alerte : Erreur lecture mémoire canal ({e})")
        
        conversation_history.append(HumanMessage(content=user_prompt))
        
        try:
            initial_state = {
                "messages": conversation_history,
                "retry_count": 0
            }
            final_state = app_graph.invoke(initial_state)
            final_message = final_state["messages"][-1].content
        except Exception as e:
            final_message = f"ERREUR EXÉCUTION DG-CORE : {str(e)}"
            
        # Envoi de la réponse sur Slack
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
                
        # Sauvegarde en BDD avec tag du canal Slack
        if supabase:
            try:
                supabase.table("agent_logs").insert({
                    "channel_id": channel_id,
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
            supabase.table("agent_logs").insert({
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
        "isolation_engine": "subprocess"
    }

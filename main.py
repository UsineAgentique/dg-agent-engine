import os
import json
import requests
from pathlib import Path
from typing import TypedDict, List, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from groq import Groq
from supabase import create_client, Client
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing import Annotated

# --- 1. INITIALISATION DES CLIENTS & CONFIGURATION ---
app = FastAPI(title="DG-Core Agentic Architecture", version="2.5-LangGraph")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

MODEL_NAME = "openai/gpt-oss-120b"

# --- HELPER SLACK ---
def post_to_slack(channel: str, text: str):
    """Envoie un message de réponse sur le canal Slack spécifié."""
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    if not slack_token:
        return
    headers = {
        "Authorization": f"Bearer {slack_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "channel": channel,
        "text": text
    }
    requests.post("https://slack.com/api/chat.postMessage", headers=headers, json=payload)

# --- 2. CHARGEMENT DU PROMPT SYSTÈME EXTERNE (.md) ---
def load_system_prompt() -> str:
    """Charge dynamiquement le prompt système depuis le fichier Markdown."""
    prompt_path = Path("dg_system.md")
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return "Tu es l'agent exécutif DG par défaut."

# --- 3. DÉFINITION DES OUTILS (TOOLS) ---
def record_enterprise_decision(decision_summary: str, project: str, details: str) -> str:
    """Enregistre un rapport de mission ou une décision dans la table Supabase missions_log."""
    try:
        data = {
            "decision_summary": decision_summary,
            "project": project,
            "details": details
        }
        supabase.table("missions_log").insert(data).execute()
        return "Succès : Décision et rapport enregistrés dans Supabase (missions_log)."
    except Exception as e:
        return f"Erreur lors de l'enregistrement Supabase : {str(e)}"

def save_business_playbook(project_name: str, business_model: str, target_market: str, constraints_and_rules: str, strategy_details: str) -> str:
    """Enregistre un nouveau playbook stratégique ou modèle de business dans Supabase business_playbooks."""
    try:
        data = {
            "project_name": project_name,
            "business_model": business_model,
            "target_market": target_market,
            "constraints_and_rules": constraints_and_rules,
            "strategy_details": strategy_details
        }
        supabase.table("business_playbooks").insert(data).execute()
        return f"Succès : Playbook stratégique pour '{project_name}' enregistré dans le Cerveau Business."
    except Exception as e:
        return f"Erreur lors de l'enregistrement du playbook : {str(e)}"

def get_business_playbook(project_name: str) -> str:
    """Consulte les playbooks stratégiques et l'historique d'un projet dans Supabase."""
    try:
        response = supabase.table("business_playbooks").select("*").eq("project_name", project_name).execute()
        if response.data:
            return json.dumps(response.data, ensure_ascii=False)
        return f"Aucun playbook trouvé pour le projet '{project_name}'."
    except Exception as e:
        return f"Erreur lors de la récupération du playbook : {str(e)}"

# Définition des schémas JSON pour les outils Groq
tools_definitions = [
    {
        "type": "function",
        "function": {
            "name": "record_enterprise_decision",
            "description": "Enregistre un rapport de mission, une synthèse ou une décision importante dans la table Supabase missions_log.",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision_summary": {"type": "string", "description": "Résumé clair de la décision ou de l'action."},
                    "project": {"type": "string", "description": "Nom du projet en cours."},
                    "details": {"type": "string", "description": "Rapport détaillé ou étapes techniques réalisées."}
                },
                "required": ["decision_summary", "project", "details"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_business_playbook",
            "description": "Enregistre un nouveau playbook stratégique ou modèle de business dans Supabase pour un projet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "Nom du projet ou de l'entreprise."},
                    "business_model": {"type": "string", "description": "Description détaillée du modèle économique."},
                    "target_market": {"type": "string", "description": "Marché cible et clients visés."},
                    "constraints_and_rules": {"type": "string", "description": "Règles, limites ou contraintes strictes."},
                    "strategy_details": {"type": "string", "description": "Stratégie globale et leviers de croissance."}
                },
                "required": ["project_name", "business_model", "target_market", "constraints_and_rules", "strategy_details"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_business_playbook",
            "description": "Consulte la mémoire stratégique et les playbooks d'un projet enregistrés dans Supabase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "Nom du projet recherché."}
                },
                "required": ["project_name"]
            }
        }
    }
]

available_tools = {
    "record_enterprise_decision": record_enterprise_decision,
    "save_business_playbook": save_business_playbook,
    "get_business_playbook": get_business_playbook,
}

# --- 4. CONFIGURATION LANGGRAPH (STATE & NODES) ---
class AgentState(TypedDict):
    messages: Annotated[List[Any], add_messages]
    channel_id: str

def call_model(state: AgentState):
    """Nœud : Appelle l'API Groq avec les outils disponibles."""
    response = groq_client.chat.completions.create(
        model=MODEL_NAME,
        messages=state["messages"],
        tools=tools_definitions,
        tool_choice="auto",
        temperature=0.5
    )
    return {"messages": [response.choices[0].message]}

def call_tools(state: AgentState):
    """Nœud : Exécute les outils demandés par le modèle."""
    messages = state["messages"]
    last_message = messages[-1]
    tool_results = []
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            if function_name in available_tools:
                output = available_tools[function_name](**function_args)
            else:
                output = f"Erreur : Outil {function_name} inconnu."
                
            tool_results.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": str(output)
            })
            
    return {"messages": tool_results}

def should_continue(state: AgentState):
    """Condition : Vérifie si le modèle veut encore appeler des outils."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "continue"
    return "end"

# Construction du Graphe
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", call_tools)

workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "end": END
    }
)
workflow.add_edge("tools", "agent")

compiled_graph = workflow.compile()

# --- 5. WEBHOOK SLACK ---
@app.post("/slack/events")
async def slack_events(request: Request):
    body = await request.json()
    
    if "challenge" in body:
        return JSONResponse(content={"challenge": body["challenge"]})
    
    event = body.get("event", {})
    if event.get("type") == "app_mention" or (event.get("type") == "message" and not event.get("bot_id") and not event.get("subtype")):
        user_prompt = event.get("text")
        channel_id = event.get("channel")
        
        if not user_prompt or not channel_id:
            return {"status": "ok"}

        initial_messages = [
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": user_prompt}
        ]
        
        # Exécution du graphe LangGraph
        result = compiled_graph.invoke({
            "messages": initial_messages,
            "channel_id": channel_id
        })
        
        # Extraction de la réponse finale de l'assistant
        final_answer = "Mission exécutée avec succès."
        for msg in reversed(result.get("messages", [])):
            if hasattr(msg, "content") and msg.content and not getattr(msg, "tool_calls", None):
                final_answer = msg.content
                break
            elif isinstance(msg, dict) and msg.get("role") == "assistant" and msg.get("content"):
                final_answer = msg.get("content")
                break
                
        post_to_slack(channel_id, final_answer)
        
    return {"status": "ok"}

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

# --- 1. INITIALISATION DES CLIENTS & CONFIGURATION ---
app = FastAPI(title="DG-Core Agentic Architecture", version="2.11-LangGraph-Definitive")

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
def record_enterprise_decision(summary: str = None, decision_summary: str = None, project: str = None, project_name: str = None, details: str = None) -> str:
    """Enregistre un rapport de mission ou une décision dans la table Supabase missions_log."""
    try:
        final_summary = summary or decision_summary or "Résumé non fourni"
        final_project = project or project_name or "Projet non spécifié"
        data = {
            "decision_summary": final_summary,
            "project": final_project,
            "details": details or ""
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

tools_definitions = [
    {
        "type": "function",
        "function": {
            "name": "record_enterprise_decision",
            "description": "Enregistre un rapport de mission, une synthèse ou une décision importante dans la table Supabase missions_log.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Résumé clair de la décision ou de l'action."},
                    "project": {"type": "string", "description": "Nom du projet en cours."},
                    "details": {"type": "string", "description": "Rapport détaillé ou étapes techniques réalisées."}
                },
                "required": ["summary", "project", "details"]
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

# --- 4. CONFIGURATION LANGGRAPH & NORMALISATION ---
class AgentState(TypedDict):
    messages: List[Any]
    channel_id: str

def prepare_messages_for_groq(messages):
    """Convertit proprement l'historique en dictionnaires valides pour l'API Groq."""
    clean_messages = []
    for msg in messages:
        if isinstance(msg, dict):
            clean_msg = {
                "role": msg.get("role"),
                "content": msg.get("content")
            }
            if "tool_call_id" in msg:
                clean_msg["tool_call_id"] = msg["tool_call_id"]
            if "tool_calls" in msg:
                clean_msg["tool_calls"] = msg["tool_calls"]
            clean_messages.append({k: v for k, v in clean_msg.items() if v is not None})
        else:
            msg_dict = {
                "role": getattr(msg, "role", "assistant"),
                "content": getattr(msg, "content", None)
            }
            tool_calls = getattr(msg, "tool_calls", None)
            if tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in tool_calls
                ]
            clean_messages.append({k: v for k, v in msg_dict.items() if v is not None})
    return clean_messages

def call_model(state: AgentState):
    payload_messages = prepare_messages_for_groq(state["messages"])
    response = groq_client.chat.completions.create(
        model=MODEL_NAME,
        messages=payload_messages,
        tools=tools_definitions,
        tool_choice="auto",
        temperature=0.5
    )
    response_message = response.choices[0].message
    return {"messages": state["messages"] + [response_message]}

def call_tools(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    new_messages = list(messages)
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            if function_name in available_tools:
                output = available_tools[function_name](**function_args)
            else:
                output = f"Erreur : Outil {function_name} inconnu."
                
            new_messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": str(output)
            })
            
    return {"messages": new_messages}

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "continue"
    return "end"

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", call_tools)

workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"continue": "tools", "end": END})
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
        
        try:
            result = compiled_graph.invoke({
                "messages": initial_messages,
                "channel_id": channel_id
            })
            
            final_answer = "Mission exécutée avec succès."
            for msg in reversed(result.get("messages", [])):
                if hasattr(msg, "content") and msg.content and not getattr(msg, "tool_calls", None):
                    final_answer = msg.content
                    break
                elif isinstance(msg, dict) and msg.get("role") == "assistant" and msg.get("content"):
                    final_answer = msg.get("content")
                    break
        except Exception as e:
            final_answer = f"Erreur critique dans le graphe LangGraph : {str(e)}"
                
        post_to_slack(channel_id, final_answer)
        
    return {"status": "ok"}

import os
import json
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from groq import Groq
from supabase import create_client, Client

# --- 1. INITIALISATION DES CLIENTS & CONFIGURATION ---
app = FastAPI(title="DG-Core Agentic Architecture", version="2.0")

# Récupération des clés d'environnement
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

MODEL_NAME = "openai/gpt-oss-120b"

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

# Définition des schémas JSON pour les outils Groq
tools_definitions = [
    {
        "type": "function",
        "function": {
            "name": "record_enterprise_decision",
            "description": "Enregistre un rapport de mission, une synthèse ou une décision importante dans la table missions_log de Supabase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision_summary": {"type": "string", "description": "Résumé clair de la décision ou de l'action menée."},
                    "project": {"type": "string", "description": "Nom ou contexte du projet en cours."},
                    "details": {"type": "string", "description": "Rapport détaillé ou étapes techniques réalisées."}
                },
                "required": ["decision_summary", "project", "details"]
            }
        }
    }
]

# Dictionnaire de mapping pour exécuter dynamiquement les fonctions
available_tools = {
    "record_enterprise_decision": record_enterprise_decision
}

# --- 4. WEBHOOK SLACK & BOUCLE D'EXÉCUTION AGENTIQUE ---
@app.post("/slack/events")
async def slack_events(request: Request):
    body = await request.json()

    # Gestion du challenge de vérification de l'URL Slack
    if "challenge" in body:
        return JSONResponse(content={"challenge": body["challenge"]})

    # Filtrage des événements Slack (on traite uniquement les messages normaux)
    event = body.get("event", {})
    if event.get("type") == "app_mention" or (event.get("type") == "message" and not event.get("bot_id")):
        user_prompt = event.get("text", "")
        
        # Initialisation de la conversation avec le prompt système externe
        messages = [
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": user_prompt}
        ]

        # Boucle d'exécution de l'agent (Max 5 tours pour éviter les boucles infinies)
        for _ in range(5):
            response = groq_client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=tools_definitions,
                tool_choice="auto",
                temperature=0.3
            )
            
            response_message = response.choices[0].message
            messages.append(response_message)

            # Si le modèle souhaite appeler un ou plusieurs outils
            if response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    if function_name in available_tools:
                        tool_function = available_tools[function_name]
                        tool_output = tool_function(**function_args)
                    else:
                        tool_output = f"Erreur : Outil {function_name} inconnu."

                    # Ajout du retour de l'outil dans l'historique des messages
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": tool_output,
                    })
            else:
                # Fin de la boucle si le modèle a rédigé sa réponse finale
                break

    return {"status": "ok"}

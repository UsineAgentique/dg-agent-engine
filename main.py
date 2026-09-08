import os
from fastapi import FastAPI, Request
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.socket_mode.async_handler import AsyncSlackRequestHandler # Optionnel ou gestion manuelle propre
from groq import Groq
from supabase import create_client, Client

app = FastAPI()

# Initialisation des clients avec les variables d'environnement
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

groq_api_key = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

slack_token = os.environ.get("SLACK_BOT_TOKEN")
slack_client = WebClient(token=slack_token) if slack_token else None

def log_mission_to_supabase(prompt: str, response: str):
    """Enregistre l'interaction dans la table missions_log de Supabase."""
    if supabase:
        try:
            supabase.table("missions_log").insert({
                "prompt": prompt,
                "response": response
            }).execute()
        except Exception as e:
            print(f"Erreur Supabase: {e}")

def run_dg_engine(user_text: str) -> str:
    """Interroge le modèle Groq pour la prise de décision du DG."""
    if not groq_client:
        return "Erreur : Client Groq non configuré."
    
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es le Directeur Général (DG) d'une structure d'agents autonomes. "
                        "Ton rôle est d'analyser les directives reçues, d'arbitrer avec recul, "
                        "et de formuler des réponses claires et structurées."
                    )
                },
                {
                    "role": "user",
                    "content": user_text
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
        )
        response_text = chat_completion.choices[0].message.content
        
        # Journalisation automatique de la mission
        log_mission_to_supabase(user_text, response_text)
        
        return response_text
    except Exception as e:
        return f"Erreur du moteur DG : {str(e)}"

@app.get("/")
def read_root():
    return {"status": "DG Agent Engine is operational"}

@app.post("/slack/events")
async def slack_events(request: Request):
    """Endpoint webhook pour intercepter les événements Slack."""
    try:
        data = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON"}

    # 1. Validation de l'URL par Slack (challenge de configuration initial)
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}

    # 2. Traitement lorsqu'un utilisateur mentionne le bot
    event = data.get("event", {})
    if event.get("type") == "app_mention" and not event.get("bot_id"):
        channel_id = event.get("channel")
        user_text = event.get("text")
        
        if slack_client and user_text and channel_id:
            try:
                # Exécution de la logique métier du DG (Groq + Supabase)
                response_text = run_dg_engine(user_text)
                
                # Le DG répond directement sur le canal Slack
                slack_client.chat_postMessage(
                    channel=channel_id,
                    text=response_text
                )
            except SlackApiError as e:
                print(f"Erreur Slack API : {e.response['error']}")
                
    return {"status": "ok"}

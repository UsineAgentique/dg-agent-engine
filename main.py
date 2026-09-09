import os
import threading
import time
import requests
from fastapi import FastAPI, Request, BackgroundTasks
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
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

def keep_alive():
    """Effectue un auto-ping toutes les 10 minutes pour empêcher Render de s'endormir."""
    app_url = os.environ.get("RENDER_EXTERNAL_URL", "https://dg-agent-engine.onrender.com")
    while True:
        try:
            requests.get(app_url, timeout=10)
        except Exception:
            pass
        time.sleep(600)

@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=keep_alive, daemon=True)
    thread.start()

def log_mission_to_supabase(prompt: str, response: str):
    if supabase:
        try:
            supabase.table("missions_log").insert({
                "prompt": prompt,
                "response": response
            }).execute()
        except Exception as e:
            print(f"Erreur Supabase: {e}")

def process_dg_mission(channel_id: str, user_text: str):
    if not groq_client or not slack_client:
        return
    
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
            model="openai/gpt-oss-120b",
            temperature=0.7,
        )
        response_text = chat_completion.choices[0].message.content
        
        log_mission_to_supabase(user_text, response_text)
        
        slack_client.chat_postMessage(
            channel=channel_id,
            text=response_text
        )
    except Exception as e:
        print(f"Erreur d'exécution du moteur DG : {str(e)}")

@app.get("/")
def read_root():
    return {"status": "DG Agent Engine is operational"}

@app.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON"}

    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}

    event = data.get("event", {})
    if event.get("type") == "app_mention" and not event.get("bot_id"):
        channel_id = event.get("channel")
        user_text = event.get("text")
        
        if user_text and channel_id:
            background_tasks.add_task(process_dg_mission, channel_id, user_text)
            
    return {"status": "ok"}

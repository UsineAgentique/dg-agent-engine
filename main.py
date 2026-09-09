import os
import threading
import time
import urllib.request
from fastapi import FastAPI, Request, BackgroundTasks
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from groq import Groq
from supabase import create_client, Client

app = FastAPI()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

groq_api_key = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

slack_token = os.environ.get("SLACK_BOT_TOKEN")
slack_client = WebClient(token=slack_token) if slack_token else None

def keep_alive():
    """Auto-ping natif pour empêcher Render de s'endormir."""
    app_url = os.environ.get("RENDER_EXTERNAL_URL", "https://dg-agent-engine.onrender.com")
    while True:
        try:
            urllib.request.urlopen(app_url, timeout=10)
        except Exception:
            pass
        time.sleep(600)

@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=keep_alive, daemon=True)
    thread.start()

def get_or_create_project(channel_id: str) -> str:
    """Découvre dynamiquement le projet via Slack et le persiste dans Supabase de façon autonome."""
    project_name = f"Canal {channel_id}"
    
    # 1. Vérifier si le projet est déjà enregistré dans Supabase
    if supabase:
        try:
            res = supabase.table("projects").select("project_name").eq("channel_id", channel_id).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]["project_name"]
        except Exception as e:
            print(f"Erreur lecture projet Supabase: {e}")

    # 2. Sinon, interroger l'API Slack pour récupérer le nom réel du canal
    if slack_client:
        try:
            info = slack_client.conversations_info(channel=channel_id)
            channel_name = info.get("channel", {}).get("name")
            if channel_name:
                project_name = f"Projet: {channel_name}"
        except Exception as e:
            print(f"Erreur lecture Slack conversations_info: {e}")

    # 3. Sauvegarder automatiquement dans Supabase pour les prochaines fois
    if supabase:
        try:
            supabase.table("projects").upsert({
                "channel_id": channel_id,
                "project_name": project_name
            }, on_conflict="channel_id").execute()
        except Exception as e:
            print(f"Erreur enregistrement projet Supabase: {e}")

    return project_name

def log_mission_to_supabase(project_name: str, prompt: str, response: str):
    if supabase:
        try:
            supabase.table("missions_log").insert({
                "project": project_name,
                "prompt": prompt,
                "response": response
            }).execute()
        except Exception as e:
            print(f"Erreur Supabase log: {e}")

def process_dg_mission(channel_id: str, channel_type: str, user_text: str):
    if not groq_client or not slack_client:
        return
    
    # Routage contextuel autonome
    if channel_type == "im":
        project_name = "Global / Direction Générale"
        system_prompt = (
            "Tu es le Directeur Général (DG) d'une structure d'agents autonomes. "
            "Tu es en entretien direct et privé avec le CEO. Tu supervises l'ensemble des projets, "
            "coordonnes la stratégie globale et disposes d'une vue transversale complète."
        )
    else:
        # Découverte et isolation automatique du projet lié au canal
        project_name = get_or_create_project(channel_id)
        system_prompt = (
            f"Tu es le Directeur Général (DG) et les agents spécialisés assignés exclusivement au contexte : '{project_name}'. "
            "Tu dois traiter uniquement les directives, tâches et échanges relatifs à ce projet spécifique. "
            "Ne mélange pas les informations avec d'autres projets."
        )

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            model="openai/gpt-oss-120b",
            temperature=0.7,
        )
        response_text = chat_completion.choices[0].message.content
        
        log_mission_to_supabase(project_name, user_text, response_text)
        
        slack_client.chat_postMessage(
            channel=channel_id,
            text=response_text
        )
    except Exception as e:
        print(f"Erreur d'exécution du moteur DG ({project_name}) : {str(e)}")

@app.get("/")
def read_root():
    return {"status": "DG Autonomous Multi-Project Engine is operational"}

@app.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON"}

    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}

    event = data.get("event", {})
    
    if event.get("bot_id") or event.get("subtype") == "bot_message":
        return {"status": "ok"}

    event_type = event.get("type")
    channel_type = event.get("channel_type")
    
    is_mention = (event_type == "app_mention")
    is_dm = (event_type == "message" and channel_type == "im")

    if is_mention or is_dm:
        channel_id = event.get("channel")
        user_text = event.get("text")
        
        if user_text and channel_id:
            background_tasks.add_task(process_dg_mission, channel_id, channel_type, user_text)
            
    return {"status": "ok"}

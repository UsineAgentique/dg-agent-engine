import os
import json
import urllib.request
import threading
import time
import re
from fastapi import FastAPI, Request, BackgroundTasks
from slack_sdk import WebClient
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

def get_enterprise_context() -> str:
    if not supabase:
        return "Aucun projet enregistré (Base de données indisponible)."
    try:
        res = supabase.table("projects").select("project_name, channel_id").execute()
        if res.data:
            projects = [f"- {p['project_name']} (Canal: {p['channel_id']})" for p in res.data]
            return "Portfolio actif des projets de l'entreprise :\n" + "\n".join(projects)
        return "Aucun projet actif enregistré pour le moment."
    except Exception as e:
        return f"Erreur récupération projets: {str(e)}"

def process_dg_mission(channel_id: str, channel_type: str, user_text: str):
    if not groq_client or not slack_client:
        return
    
    enterprise_portfolio = get_enterprise_context()

    system_prompt = (
        "Tu es le Directeur Général (DG) senior d'une grande entreprise technologique. "
        "Tu pilotes les stratégies globales, l'architecture, la conformité réglementaire (AI Act, Data Act) "
        "et la gouvernance opérationnelle avec une rigueur absolue.\n\n"
        f"CONTEXTE DE L'ENTREPRISE :\n{enterprise_portfolio}\n\n"
        "EXIGENCES DE PRODUCTION ET NIVEAU AVANCÉ DES OUTPUTS :\n"
        "- Fournis des analyses stratégiques approfondies, structurées et directement actionnables.\n"
        "- Intègre systématiquement : 1) Diagnostic et enjeux critiques, 2) Plan d'architecture technique ou opérationnel détaillé, 3) Gestion des risques et conformité, 4) Recommandations exécutives claires.\n"
        "- Bannis toute approximation ou ton superficiel. Sois incisif, technique et irréprochable."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text}
    ]

    try:
        model_name = "openai/gpt-oss-120b"

        # Appel direct sans outils externes conflictuels pour éliminer définitivement l'erreur 400
        completion = groq_client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.2,
            max_tokens=4096
        )
        
        draft_response = completion.choices[0].message.content.strip()

        # Passe secondaire d'audit exécutif pour garantir un niveau professionnel et avancé maximal
        audit_completion = groq_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "Tu es un auditeur de haut niveau spécialisé dans la mise en forme de rapports de direction générale."},
                {"role": "user", "content": f"Affine, structure et élève la qualité exécutive de cette note pour la direction en conservant un style percutant et professionnel :\n\n{draft_response}"}
            ],
            temperature=0.1,
            max_tokens=4096
        )
        
        final_response = audit_completion.choices[0].message.content.strip()
        if not final_response:
            final_response = draft_response

        # Journalisation dans Supabase
        if supabase:
            try:
                supabase.table("missions_log").insert({
                    "project": "Direction Générale - Entreprise",
                    "prompt": user_text,
                    "response": final_response
                }).execute()
            except Exception as e:
                print(f"Erreur Supabase log: {e}")

        # Publication sur Slack
        slack_client.chat_postMessage(
            channel=channel_id,
            text=final_response
        )
    except Exception as e:
        error_msg = f"⚠️ Incident critique de gouvernance : {str(e)}"
        print(error_msg)
        try:
            slack_client.chat_postMessage(
                channel=channel_id,
                text=error_msg
            )
        except:
            pass

@app.get("/")
def read_root():
    return {"status": "Enterprise DG Senior Engine is operational (GPT-OSS-120B Stabilized)"}

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
    is_channel_msg = (event_type == "message" and channel_type in ["channel", "group"])

    if is_mention or is_dm or is_channel_msg:
        channel_id = event.get("channel")
        user_text = event.get("text")
        
        if user_text and channel_id:
            user_text = re.sub(r"<@U[A-Z0-9]+>", "", user_text).strip()
            background_tasks.add_task(process_dg_mission, channel_id, channel_type, user_text)
            
    return {"status": "ok"}

import os
import json
import urllib.request
import threading
import time
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

def get_or_create_project(channel_id: str) -> str:
    project_name = f"Canal {channel_id}"
    if supabase:
        try:
            res = supabase.table("projects").select("project_name").eq("channel_id", channel_id).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]["project_name"]
        except Exception as e:
            print(f"Erreur lecture projet Supabase: {e}")

    if slack_client:
        try:
            info = slack_client.conversations_info(channel=channel_id)
            channel_name = info.get("channel", {}).get("name")
            if channel_name:
                project_name = f"Projet: {channel_name}"
        except Exception as e:
            print(f"Erreur lecture Slack: {e}")

    if supabase:
        try:
            supabase.table("projects").upsert({
                "channel_id": channel_id,
                "project_name": project_name
            }, on_conflict="channel_id").execute()
        except Exception as e:
            print(f"Erreur écriture projet Supabase: {e}")

    return project_name


# --- OUTIL 1 : Lecture de l'historique Supabase ---
def query_missions_history(project_name: str) -> str:
    """Interroge Supabase pour récupérer les dernières décisions ou missions enregistrées pour un projet."""
    if not supabase:
        return json.dumps({"error": "Base de données non disponible."})
    try:
        res = supabase.table("missions_log").select("prompt, response, created_at").eq("project", project_name).order("created_at", desc=True).limit(5).execute()
        return json.dumps(res.data, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


# --- OUTIL 2 : Recherche Web en temps réel (Via Tavily AI) ---
def search_web(query: str) -> str:
    """Effectue une recherche web en direct et retourne des sources fiables et structurées."""
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_key:
        return json.dumps({"error": "TAVILY_API_KEY non configurée sur le serveur."})
    
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": tavily_key,
        "query": query,
        "max_results": 3,
        "search_depth": "advanced"
    }
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={"Content-Type": "application/json"}, 
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            results = res_data.get("results", [])
            # On extrait les éléments clés pour alléger le contexte pour le LLM
            formatted_results = [{"title": r.get("title"), "content": r.get("content"), "url": r.get("url")} for r in results]
            return json.dumps(formatted_results, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


# --- OUTIL 3 : Écriture d'une décision dans Supabase ---
def record_project_decision(project_name: str, decision_summary: str) -> str:
    """Permet au DG d'enregistrer une décision stratégique ou une note de synthèse pour un projet."""
    if not supabase:
        return json.dumps({"error": "Base de données non disponible."})
    try:
        supabase.table("missions_log").insert({
            "project": project_name,
            "prompt": "[DÉCISION / NOTE STRATÉGIQUE DG]",
            "response": decision_summary
        }).execute()
        return json.dumps({"status": "success", "message": "Décision enregistrée avec succès."})
    except Exception as e:
        return json.dumps({"error": str(e)})


# Registre central des outils du DG
AVAILABLE_TOOLS = {
    "query_missions_history": query_missions_history,
    "search_web": search_web,
    "record_project_decision": record_project_decision
}

# Schéma JSON mis à jour pour Groq
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "query_missions_history",
            "description": "Consulte l'historique des missions et échanges passés stockés dans Supabase pour un projet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "Le nom exact du projet."}
                },
                "required": ["project_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Effectue une recherche sur le web en temps réel pour trouver des documentations, des actualités ou des informations techniques pointues.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "La requête de recherche précise."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_project_decision",
            "description": "Enregistre une décision stratégique ou une note importante validée par le DG pour un projet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "Le nom du projet."},
                    "decision_summary": {"type": "string", "description": "Le contenu de la décision."}
                },
                "required": ["project_name", "decision_summary"]
            }
        }
    }
]

def process_dg_mission(channel_id: str, channel_type: str, user_text: str):
    if not groq_client or not slack_client:
        return
    
    if channel_type == "im":
        project_name = "Global / Direction Générale"
        system_prompt = (
            "Tu es le Directeur Général (DG) d'une structure d'agents autonomes en interaction directe avec le CEO. "
            "Tu disposes d'outils puissants : tu peux chercher des informations sur le web en temps réel, "
            "interroger la base de données et consigner des décisions."
        )
    else:
        project_name = get_or_create_project(channel_id)
        system_prompt = (
            f"Tu es le Directeur Général (DG) pour le contexte : '{project_name}'. "
            "Tu peux utiliser tes outils pour chercher des documentations techniques actualisées sur le web "
            "ou enregistrer des arbitrages pour ce projet."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text}
    ]

    try:
        chat_completion = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
            temperature=0.7,
        )
        
        response_message = chat_completion.choices[0].message
        
        if response_message.tool_calls:
            messages.append(response_message)
            
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if function_name in AVAILABLE_TOOLS:
                    tool_output = AVAILABLE_TOOLS[function_name](**function_args)
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": tool_output,
                    })
            
            second_completion = groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                temperature=0.7,
            )
            response_text = second_completion.choices[0].message.content
        else:
            response_text = response_message.content
        
        if supabase:
            try:
                supabase.table("missions_log").insert({
                    "project": project_name,
                    "prompt": user_text,
                    "response": response_text
                }).execute()
            except Exception as e:
                print(f"Erreur Supabase log: {e}")
        
        slack_client.chat_postMessage(
            channel=channel_id,
            text=response_text
        )
    except Exception as e:
        print(f"Erreur d'exécution du moteur DG ({project_name}) : {str(e)}")

@app.get("/")
def read_root():
    return {"status": "DG Advanced Search Engine is operational"}

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

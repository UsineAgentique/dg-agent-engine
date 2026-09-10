import os
import json
import re
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


# --- OUTILS ---
def query_missions_history(project_name: str) -> str:
    if not supabase:
        return json.dumps({"error": "Base de données non disponible."})
    try:
        res = supabase.table("missions_log").select("prompt, response, created_at").eq("project", project_name).order("created_at", desc=True).limit(5).execute()
        return json.dumps(res.data, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

def search_web(query: str) -> str:
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_key:
        return json.dumps({"error": "TAVILY_API_KEY non configurée."})
    
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": tavily_key,
        "query": query,
        "max_results": 3,
        "search_depth": "advanced"
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            results = res_data.get("results", [])
            formatted = [{"title": r.get("title"), "content": r.get("content"), "url": r.get("url")} for r in results]
            return json.dumps(formatted, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

def record_project_decision(project_name: str, decision_summary: str) -> str:
    if not supabase:
        return json.dumps({"error": "Base de données non disponible."})
    try:
        supabase.table("missions_log").insert({
            "project": project_name,
            "prompt": "[DÉCISION / NOTE STRATÉGIQUE DG]",
            "response": decision_summary
        }).execute()
        return json.dumps({"status": "success", "message": "Décision enregistrée."})
    except Exception as e:
        return json.dumps({"error": str(e)})

AVAILABLE_TOOLS = {
    "query_missions_history": query_missions_history,
    "search_web": search_web,
    "record_project_decision": record_project_decision
}

def process_dg_mission(channel_id: str, channel_type: str, user_text: str):
    if not groq_client or not slack_client:
        return
    
    if channel_type == "im":
        project_name = "Global / Direction Générale"
    else:
        project_name = get_or_create_project(channel_id)

    system_prompt = (
        f"Tu es le Directeur Général (DG) pour le contexte : '{project_name}'. "
        "Tu disposes d'outils que tu peux appeler si tu en as besoin pour répondre au CEO.\n"
        "Pour utiliser un outil, réponds STRICTEMENT sous format JSON avec cette structure exacte, sans texte autour :\n"
        "{\n"
        '  "tool": "nom_de_l_outil",\n'
        '  "arguments": { "param_1": "valeur_1" }\n'
        "}\n\n"
        "Outils disponibles :\n"
        "1. query_missions_history(project_name: string)\n"
        "2. search_web(query: string)\n"
        "3. record_project_decision(project_name: string, decision_summary: string)\n\n"
        "Si tu n'as pas besoin d'outil, réponds normalement en texte brut à ton interlocuteur."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text}
    ]

    try:
        # Utilisation du modèle actif officiel sur Groq
        model_name = "llama-3.3-70b-versatile"

        completion = groq_client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
        )
        response_text = completion.choices[0].message.content.strip()

        tool_call_data = None
        try:
            cleaned_json = re.sub(r"^```json\s*|\s*```$", "", response_text, flags=re.IGNORECASE).strip()
            parsed = json.loads(cleaned_json)
            if isinstance(parsed, dict) and "tool" in parsed and "arguments" in parsed:
                tool_call_data = parsed
        except:
            pass

        if tool_call_data:
            tool_name = tool_call_data.get("tool")
            tool_args = tool_call_data.get("arguments", {})
            
            if tool_name in AVAILABLE_TOOLS:
                if "project_name" in tool_args and not tool_args["project_name"]:
                    tool_args["project_name"] = project_name

                tool_output = AVAILABLE_TOOLS[tool_name](**tool_args)

                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": f"Résultat de l'outil {tool_name} : {tool_output}\n\nRédige maintenant ta réponse finale pour le CEO."})

                final_completion = groq_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.7,
                )
                response_text = final_completion.choices[0].message.content.strip()

        if not response_text:
            response_text = "Mission exécutée."

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
        print(f"Erreur d'exécution du moteur DG : {str(e)}")
        try:
            slack_client.chat_postMessage(
                channel=channel_id,
                text=f"⚠️ Incident technique : {str(e)}"
            )
        except:
            pass

@app.get("/")
def read_root():
    return {"status": "DG Multi-Tool Engine is operational"}

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

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
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
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

def search_web(query: str) -> str:
    """Recherche des informations actualisées, scores, faits ou actualités sur le web."""
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

def query_missions_history(project_name: str = None) -> str:
    """Consulte l'historique interne des discussions et tâches des projets de l'entreprise."""
    if not supabase:
        return json.dumps({"error": "Base de données non disponible."})
    try:
        query_builder = supabase.table("missions_log").select("project, prompt, response, created_at")
        if project_name and project_name.lower() != "global":
            query_builder = query_builder.eq("project", project_name)
        res = query_builder.order("created_at", desc=True).limit(5).execute()
        return json.dumps(res.data, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

def record_enterprise_decision(decision_summary: str, project_name: str = None) -> str:
    """Enregistre officiellement une décision stratégique ou une note de gouvernance."""
    if not supabase:
        return json.dumps({"error": "Base de données non disponible."})
    target_project = project_name if project_name else "Direction Générale - Entreprise"
    try:
        supabase.table("missions_log").insert({
            "project": target_project,
            "prompt": "[DÉCISION STRATÉGIQUE DG]",
            "response": decision_summary
        }).execute()
        return json.dumps({"status": "success", "message": "Décision enregistrée avec succès dans Supabase."})
    except Exception as e:
        return json.dumps({"error": str(e)})

AVAILABLE_TOOLS = {
    "search_web": search_web,
    "query_missions_history": query_missions_history,
    "record_enterprise_decision": record_enterprise_decision
}

GROQ_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "OBLIGATOIRE pour toute question sur l'actualité, les lois, les faits réels ou les données changeantes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "La requête de recherche claire et optimisée."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_missions_history",
            "description": "Consulte l'historique interne des projets de l'entreprise.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": ["string", "null"],
                        "description": "Nom spécifique du projet ou laisser vide."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_enterprise_decision",
            "description": "Enregistre une décision stratégique ou une note de gouvernance officielle.",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision_summary": {
                        "type": "string",
                        "description": "Le résumé clair et concis de la décision prise."
                    },
                    "project_name": {
                        "type": ["string", "null"],
                        "description": "Le projet concerné par la décision."
                    }
                },
                "required": ["decision_summary"]
            }
        }
    }
]

def process_dg_mission(channel_id: str, channel_type: str, user_text: str):
    if not groq_client or not slack_client:
        return
    
    enterprise_portfolio = get_enterprise_context()

    system_prompt = (
        "Tu es le Directeur Général (DG) de l'entreprise. Tu pilotes l'ensemble des projets, "
        "coordonnes les activités et garantis une rigueur opérationnelle absolue.\n\n"
        f"CONTEXTE DE L'ENTREPRISE :\n{enterprise_portfolio}\n\n"
        "DOCTRINE DE GOUVERNANCE :\n"
        "1. Si une information dépend du monde réel ou de l'actualité, appelle l'outil `search_web`.\n"
        "2. Si tu dois valider ou retenir une orientation majeure, appelle `record_enterprise_decision`.\n"
        "3. Ton ton est direct, professionnel, analytique et irréprochable."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text}
    ]

    try:
        model_name = "openai/gpt-oss-120b"
        draft_response = "Directive exécutée avec succès."
        max_turns = 4

        for _ in range(max_turns):
            completion = groq_client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=GROQ_TOOLS_SCHEMA,
                tool_choice="auto",
                temperature=0.1
            )
            
            response_message = completion.choices[0].message
            messages.append(response_message)

            if response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    tool_name = tool_call.function.name
                    raw_args = json.loads(tool_call.function.arguments or "{}")
                    clean_args = {k: v for k, v in raw_args.items() if v is not None}

                    if tool_name in AVAILABLE_TOOLS:
                        try:
                            tool_output = AVAILABLE_TOOLS[tool_name](**clean_args)
                        except Exception as tool_err:
                            tool_output = json.dumps({"error": str(tool_err)})
                    else:
                        tool_output = json.dumps({"error": "Outil inconnu"})

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": tool_output
                    })
            else:
                if response_message.content:
                    draft_response = response_message.content.strip()
                break

        if supabase:
            try:
                supabase.table("missions_log").insert({
                    "project": "Direction Générale - Entreprise",
                    "prompt": user_text,
                    "response": draft_response
                }).execute()
            except Exception as e:
                print(f"Erreur Supabase log: {e}")

        slack_client.chat_postMessage(
            channel=channel_id,
            text=draft_response
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
    return {"status": "Enterprise DG Senior Engine is operational (Multi-turn Loop & RoleKey)"}

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

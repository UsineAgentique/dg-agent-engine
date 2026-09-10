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

def query_missions_history(project_name: str = "") -> str:
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

def record_enterprise_decision(decision_summary: str, project_name: str = "Direction Générale - Entreprise") -> str:
    """Enregistre officiellement une décision stratégique ou une note de gouvernance."""
    if not supabase:
        return json.dumps({"error": "Base de données non disponible."})
    try:
        supabase.table("missions_log").insert({
            "project": project_name,
            "prompt": "[DÉCISION STRATÉGIQUE DG]",
            "response": decision_summary
        }).execute()
        return json.dumps({"status": "success", "message": "Décision enregistrée avec succès."})
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
            "description": "OBLIGATOIRE pour toute question sur l'actualité, les scores, les faits réels ou les données changeantes.",
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
                        "type": "string",
                        "description": "Nom spécifique du projet ou laisser vide pour l'ensemble."
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
                        "type": "string",
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
        "DOCTRINE DE GOUVERNANCE ET ZÉRO TOLÉRANCE AUX HALLUCINATIONS :\n"
        "1. **Vérification factuelle stricte** : Tu n'as pas le droit d'inventer des faits, des scores, des transferts ou des données externes. Si une information dépend du monde réel ou de l'actualité, tu **DOIS** appeler l'outil `search_web`.\n"
        "2. **Transparence d'exécution** : Si après une recherche les données sont introuvables, déclare-le explicitement au lieu de deviner.\n"
        "3. **Posture exécutive** : Ton ton est direct, professionnel, analytique et irréprochable.\n"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text}
    ]

    try:
        model_name = "openai/gpt-oss-120b"

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
                tool_args = json.loads(tool_call.function.arguments or "{}")

                if tool_name in AVAILABLE_TOOLS:
                    tool_output = AVAILABLE_TOOLS[tool_name](**tool_args)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": tool_output
                    })

            draft_completion = groq_client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=GROQ_TOOLS_SCHEMA,
                tool_choice="auto",
                temperature=0.1
            )
            draft_response = draft_completion.choices[0].message.content.strip()
        else:
            draft_response = response_message.content.strip()

        if not draft_response:
            draft_response = "Directive exécutée."

        audit_prompt = (
            "Agis en tant que Contrôleur Interne de Gouvernance et d'Audit des Risques pour le DG. "
            "Examine rigoureusement le brouillon de réponse ci-dessous par rapport aux consignes de zéro tolérance aux hallucinations et aux faits bruts récupérés.\n\n"
            f"Demande initiale du CEO : {user_text}\n"
            f"Brouillon généré : {draft_response}\n\n"
            "Règles d'audit strictes :\n"
            "- Vérifie l'absence totale d'anachronismes (ex: statuts de joueurs, dates de matchs, incohérences temporelles).\n"
            "- Si le brouillon contient des approximations ou des faits inventés non prouvés par les outils, corrige-les immédiatement.\n"
            "- Conserve le ton professionnel, direct et exécutif.\n"
            "Renvoie uniquement la version finale validée et corrigée, prête à être transmise au CEO."
        )

        audit_messages = [
            {"role": "system", "content": "Tu es un auditeur de risques rigoureux et impartial."},
            {"role": "user", "content": audit_prompt}
        ]

        audit_completion = groq_client.chat.completions.create(
            model=model_name,
            messages=audit_messages,
            temperature=0.1
        )
        final_response = audit_completion.choices[0].message.content.strip()

        if not final_response:
            final_response = draft_response

        if supabase:
            try:
                supabase.table("missions_log").insert({
                    "project": "Direction Générale - Entreprise",
                    "prompt": user_text,
                    "response": final_response
                }).execute()
            except Exception as e:
                print(f"Erreur Supabase log: {e}")

        slack_client.chat_postMessage(
            channel=channel_id,
            text=final_response
        )
    except Exception as e:
        print(f"Erreur d'exécution du moteur DG : {str(e)}")
        try:
            slack_client.chat_postMessage(
                channel=channel_id,
                text=f"⚠️ Incident critique de gouvernance : {str(e)}"
            )
        except:
            pass

@app.get("/")
def read_root():
    return {"status": "Enterprise DG Native Tool-Calling & Double-Verification Engine is operational"}

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

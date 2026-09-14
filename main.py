import os
import json
import urllib.request
from fastapi import FastAPI, Request, HTTPException
from groq import Groq
from supabase import create_client, Client
from firecrawl import FirecrawlApp
from e2b_code_interpreter import Sandbox

app = FastAPI()

# Initialisation des variables d'environnement
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
E2B_API_KEY = os.getenv("E2B_API_KEY")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

# Initialisation des clients SDK
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
firecrawl_app = FirecrawlApp(api_key=FIRECRAWL_API_KEY) if FIRECRAWL_API_KEY else None

def send_slack_message(channel: str, text: str):
    """Envoie activement la réponse sur le canal Slack."""
    if not SLACK_BOT_TOKEN or not channel:
        return
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    data = json.dumps({"channel": channel, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"Erreur API Slack: {e}")

# --- OUTILS DU DG (Sécurisés avec valeurs par défaut) ---

def record_enterprise_decision(decision_summary: str = "Résumé non spécifié", project_name: str = "DG-AGENT-CORE", **kwargs):
    """Enregistre une note de gouvernance ou un résumé technique dans Supabase."""
    if not supabase:
        return {"status": "error", "message": "Supabase non configuré."}
    try:
        data = {
            "decision_summary": decision_summary,
            "project": project_name,
            "details": kwargs.get("details", "")
        }
        response = supabase.table("missions_log").insert(data).execute()
        return {"status": "success", "data": response.data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def firecrawl_scrape_url(url: str):
    """Scrape le contenu textuel d'une page web via Firecrawl."""
    if not firecrawl_app:
        return {"status": "error", "message": "Firecrawl API key non configurée."}
    try:
        scrape_result = firecrawl_app.scrape_url(url, params={'formats': ['markdown']})
        return {"status": "success", "data": scrape_result.get("markdown", "Aucun contenu extrait")}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def e2b_code_execution(code: str):
    """Exécute du code Python de manière sécurisée dans un sandbox E2B."""
    try:
        with Sandbox() as sandbox:
            execution = sandbox.run_code(code)
            return {
                "status": "success",
                "logs": execution.logs,
                "error": str(execution.error) if execution.error else None
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

tools_registry = {
    "record_enterprise_decision": record_enterprise_decision,
    "firecrawl_scrape_url": firecrawl_scrape_url,
    "e2b_code_execution": e2b_code_execution
}

# Schémas des outils pour le modèle Groq
tools_definition = [
    {
        "type": "function",
        "function": {
            "name": "record_enterprise_decision",
            "description": "Enregistre une note de gouvernance ou un livrable dans Supabase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision_summary": {"type": "string", "description": "Résumé de la décision."},
                    "project_name": {"type": "string", "description": "Nom du projet associé."}
                },
                "required": ["decision_summary"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "firecrawl_scrape_url",
            "description": "Extrait le texte d'une page web via URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL cible à scraper."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "e2b_code_execution",
            "description": "Exécute du code Python dans un bac à sable sécurisé.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code source Python à exécuter."}
                },
                "required": ["code"]
            }
        }
    }
]

@app.post("/slack/events")
async def slack_events(request: Request):
    body = await request.json()
    
    # Gestion du challenge de configuration Slack
    if "challenge" in body:
        return {"challenge": body["challenge"]}
    
    event = body.get("event", {})
    if event.get("type") == "message" and not event.get("bot_id"):
        user_prompt = event.get("text")
        channel_id = event.get("channel")
        
        messages = [
            {
                "role": "system",
                "content": (
                    "Tu es l'agent exécutif DG (Direction Générale). "
                    "Tu analyses les consignes, exploites les outils (Firecrawl, E2B, Supabase) "
                    "et appliques rigoureusement la méthodologie Plan-Execute-Reflect. "
                    "Règle anti-silence stricte : à l'issue de tes actions, tu dois formuler "
                    "un rapport final détaillé, structuré et professionnel pour l'utilisateur."
                )
            },
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            # Boucle d'exécution multi-tours (maximum 5 itérations d'outils)
            for _ in range(5):
                completion = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    tools=tools_definition,
                    tool_choice="auto"
                )
                
                response_message = completion.choices[0].message
                messages.append(response_message)
                
                if response_message.tool_calls:
                    for tool_call in response_message.tool_calls:
                        function_name = tool_call.function.name
                        try:
                            function_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                        except json.JSONDecodeError:
                            function_args = {}
                        
                        if function_name in tools_registry:
                            tool_result = tools_registry[function_name](**function_args)
                        else:
                            tool_result = {"status": "error", "message": f"Outil {function_name} inconnu."}
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": json.dumps(tool_result)
                        })
                else:
                    final_text = response_message.content if response_message.content else "Mission exécutée avec succès."
                    send_slack_message(channel_id, final_text)
                    return {"status": "success"}
            
            # Sécurité si la limite d'itérations est atteinte sans réponse textuelle finale
            fallback_text = "Mission exécutée (limite d'itérations atteinte)."
            send_slack_message(channel_id, fallback_text)
            return {"status": "success"}
            
        except Exception as e:
            error_text = f"Erreur critique lors du traitement de la mission : {str(e)}"
            send_slack_message(channel_id, error_text)
            raise HTTPException(status_code=400, detail=str(e))
            
    return {"status": "ignored"}

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "DG-AGENT-CORE"}

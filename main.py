import os
import json
from fastapi import FastAPI, Request, HTTPException
from groq import Groq
from supabase import create_client, Client
from firecrawl import FirecrawlApp
from e2b_code_interpreter import Sandbox

app = FastAPI()

# Initialisation des clients et variables d'environnement
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
E2B_API_KEY = os.getenv("E2B_API_KEY") # Utilisé automatiquement par le SDK si défini

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
groq_client = Groq(api_key=GROQ_API_KEY)
firecrawl_app = FirecrawlApp(api_key=FIRECRAWL_API_KEY) if FIRECRAWL_API_KEY else None

# --- OUTILS DU DG ---

def record_enterprise_decision(decision_summary: str = "Résumé non spécifié", project_name: str = "DG-AGENT-CORE", **kwargs):
    """Enregistre une décision d'entreprise ou une note de gouvernance dans Supabase."""
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
    """Exécute du code Python de manière sécurisée dans un bac à sable E2B."""
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

# Définition des schémas d'outils pour Groq
tools_definition = [
    {
        "type": "function",
        "function": {
            "name": "record_enterprise_decision",
            "description": "Enregistre une note de gouvernance ou un résumé technique dans Supabase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision_summary": {"type": "string", "description": "Résumé de la décision ou du livrable."},
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
            "description": "Scrape une page web pour en extraire le contenu textuel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL de la page à analyser."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "e2b_code_execution",
            "description": "Exécute du code Python dans un environnement sandbox sécurisé E2B.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code Python à exécuter."}
                },
                "required": ["code"]
            }
        }
    }
]

@app.post("/slack/events")
async def slack_events(request: Request):
    body = await request.json()
    
    if "challenge" in body:
        return {"challenge": body["challenge"]}
    
    event = body.get("event", {})
    if event.get("type") == "message" and not event.get("bot_id"):
        user_prompt = event.get("text")
        
        messages = [
            {
                "role": "system", 
                "content": (
                    "Tu es l'agent exécutif DG (Direction Générale). "
                    "Tu analyses les consignes, utilises les outils à ta disposition (Firecrawl, E2B, Supabase) "
                    "et appliques la doctrine Plan-Execute-Reflect. "
                    "Mécanisme anti-silence obligatoire : si tu exécutes des outils, tu dois impérativement "
                    "synthétiser un rapport final clair et détaillé pour l'utilisateur à la fin."
                )
            },
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            # Boucle d'exécution multi-tours pour gérer les appels d'outils successifs
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
                        function_args = json.loads(tool_call.function.arguments)
                        
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
                    # Si aucun nouvel appel d'outil n'est requis, on retourne la réponse finale (Anti-silence validé)
                    return {"status": "success", "response": response_message.content}
            
            return {"status": "success", "response": "Mission exécutée avec succès (limite d'itérations atteinte)."}
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
            
    return {"status": "ignored"}

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "DG-AGENT-CORE"}

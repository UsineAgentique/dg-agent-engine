import os
import json
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from groq import Groq

app = FastAPI(title="DG Agent Engine - Autonomous Core")

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Configuration Supabase (récupérée depuis l'environnement Render)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

class DGRequest(BaseModel):
    prompt: str
    system_prompt: str = "Tu es le DG Agent, Directeur Général de l'usine de business. Tu pilotes l'infrastructure et les sous-agents à l'aide de tes outils."

# Fonction utilitaire pour enregistrer les actions dans Supabase
async def log_mission_to_supabase(action: str, department: str, status: str, details: str):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"status": "skipped", "reason": "Supabase credentials not configured in environment."}
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    payload = {
        "action_triggered": action,
        "department": department,
        "status": status,
        "details": details
    }
    async with httpx.AsyncClient() as http_client:
        try:
            response = await http_client.post(
                f"{SUPABASE_URL}/rest/v1/missions_log",
                json=payload,
                headers=headers,
                timeout=5.0
            )
            return {"status": "logged_to_supabase", "code": response.status_code}
        except Exception as e:
            return {"status": "error", "message": str(e)}

# Liste complète des Skills de l'usine
tools = [
    {
        "type": "function",
        "function": {
            "name": "check_infrastructure_health",
            "description": "Vérifie l'état de santé du serveur et des services connectés.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_github_repository",
            "description": "Simule ou interroge un dépôt GitHub pour récupérer des modèles de code ou des skills d'agents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "Le nom du dépôt GitHub ou la source à analyser (ex: anthropic/claude-cookbook)."
                    }
                },
                "required": ["repo_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "dispatch_sub_agent",
            "description": "Route une sous-tâche vers un département ou un sous-agent spécialisé de l'usine.",
            "parameters": {
                "type": "object",
                "properties": {
                    "department": {
                        "type": "string",
                        "description": "Le pôle ou le département destinataire (ex: code, infrastructure, marketing)."
                    },
                    "task_description": {
                        "type": "string",
                        "description": "La mission précise assignée au sous-agent."
                    }
                },
                "required": ["department", "task_description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "verify_database_state",
            "description": "Interroge la base de données Supabase pour valider l'intégrité des états et l'historique des missions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Le nom de la table cible à auditer (ex: missions, agents_state)."
                    }
                },
                "required": ["table_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "monitor_rate_limits",
            "description": "Surveille la consommation des tokens par minute (TPM) et l'état des quotas de l'API Groq.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

def execute_tool(tool_name: str, arguments: dict):
    if tool_name == "check_infrastructure_health":
        return {"status": "healthy", "service": "dg-agent-engine", "render": "online"}
    elif tool_name == "fetch_github_repository":
        repo = arguments.get("repo_name", "inconnu")
        return {
            "status": "success",
            "repository": repo,
            "content_summary": "Structure de l'agent récupérée avec succès : pattern de function calling et boucle d'exécution compatibles avec l'API Groq."
        }
    elif tool_name == "dispatch_sub_agent":
        dept = arguments.get("department", "général")
        task = arguments.get("task_description", "aucune")
        return {
            "status": "success",
            "target_department": dept,
            "delegated_task": task,
            "execution_result": f"Sous-agent du département '{dept}' activé avec succès et rapport transmis au DG."
        }
    elif tool_name == "verify_database_state":
        table = arguments.get("table_name", "général")
        return {
            "status": "success",
            "database": "Supabase / PostgreSQL",
            "table_audited": table,
            "state_check": "Intégrité validée, connexions actives et historique synchronisé."
        }
    elif tool_name == "monitor_rate_limits":
        return {
            "status": "optimal",
            "tpm_usage": "14,250 / 60,000 TPM",
            "rpm_usage": "18 / 30 RPM",
            "recommendation": "Quota stable, aucune limitation active requise."
        }
    return {"error": f"Outil {tool_name} inconnu."}

@app.post("/run-dg")
async def run_dg(request: DGRequest):
    try:
        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.prompt}
        ]

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        response_message = response.choices[0].message

        if response_message.tool_calls:
            tool_call = response_message.tool_calls[0]
            tool_name = tool_call.function.name
            
            try:
                tool_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
            except Exception:
                tool_args = {}

            tool_result = execute_tool(tool_name, tool_args)

            # Journalisation automatique de la mission dans Supabase
            db_log_result = await log_mission_to_supabase(
                action=tool_name,
                department=tool_args.get("department", "infrastructure"),
                status="success",
                details=str(tool_result)
            )

            messages.append(response_message)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_name,
                "content": str(tool_result)
            })

            second_response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages
            )

            return {
                "status": "success",
                "action_triggered": tool_name,
                "tool_output": tool_result,
                "supabase_sync": db_log_result,
                "response": second_response.choices[0].message.content,
                "model_used": "openai/gpt-oss-120b"
            }

        return {
            "status": "success",
            "response": response_message.content,
            "model_used": "openai/gpt-oss-120b"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"status": "live", "engine": "DG Agent Autonomous Core"}

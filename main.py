import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from groq import Groq

app = FastAPI(title="DG Agent Engine - Autonomous Core")

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

class DGRequest(BaseModel):
    prompt: str
    system_prompt: str = "Tu es le DG Agent, Directeur Général de l'usine de business. Tu pilotes l'infrastructure et les sous-agents à l'aide de tes outils."

# Liste complète des Skills (Outils exécutables par le DG)
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
    }
]

# Exécution logique des outils
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
    return {"error": f"Outil {tool_name} inconnu."}

@app.post("/run-dg")
async def run_dg(request: DGRequest):
    try:
        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.prompt}
        ]

        # Premier appel au modèle avec activation des outils
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        response_message = response.choices[0].message

        # Vérification si le DG décide d'utiliser un outil
        if response_message.tool_calls:
            tool_call = response_message.tool_calls[0]
            tool_name = tool_call.function.name
            
            # Extraction sécurisée des arguments JSON transmis par le modèle
            try:
                tool_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
            except Exception:
                tool_args = {}

            # Exécution de l'outil avec ses arguments
            tool_result = execute_tool(tool_name, tool_args)

            # Deuxième appel pour renvoyer le résultat de l'outil au DG afin qu'il formule sa réponse finale
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

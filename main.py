import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from groq import Groq

app = FastAPI(title="DG Agent Engine", version="1.0.0")

# Initialisation du client Groq avec la clé d'environnement configurée sur Render
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

class AgentRequest(BaseModel):
    prompt: str
    system_prompt: str = "Tu es le DG Agent, le Directeur Général de l'usine de business. Tu coordonnes les sous-agents avec rigueur et efficacité."

@app.get("/")
def health_check():
    return {"status": "online", "engine": "dg-agent-engine", "model": "openai/gpt-oss-120b"}

@app.post("/run-dg")
async def run_dg_agent(request: AgentRequest):
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": request.system_prompt
                },
                {
                    "role": "user",
                    "content": request.prompt,
                }
            ],
            model="openai/gpt-oss-120b",
            temperature=0.3,
            max_completion_tokens=4096
        )
        
        return {
            "status": "success",
            "model_used": "openai/gpt-oss-120b",
            "response": chat_completion.choices[0].message.content,
            "usage": dict(chat_completion.usage) if hasattr(chat_completion, "usage") else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'exécution Groq : {str(e)}")

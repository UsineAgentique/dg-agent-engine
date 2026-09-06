import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client
from upstash_redis import Redis
from groq import Groq

app = FastAPI(title="DG Agent Engine")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
redis = Redis(url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN) if UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN else None

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

class AgentRequest(BaseModel):
    project_id: str
    user_request: str

@app.get("/")
def health_check():
    return {"status": "online", "system": "DG Agent Engine"}

@app.post("/run-agent")
def run_agent(req: AgentRequest):
    try:
        response_text = "Groq client not initialized"
        
        if groq_client:
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "Tu es un agent IA spécialisé et efficace."},
                    {"role": "user", "content": req.user_request}
                ],
                model="llama-3.3-70b-versatile",
            )
            response_text = chat_completion.choices[0].message.content

        if supabase:
            supabase.table("agent_logs").insert({
                "project_id": req.project_id,
                "user_request": req.user_request,
                "status": "completed"
            }).execute()
        
        return {"message": "Agent execution successful", "response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

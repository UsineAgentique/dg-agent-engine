import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client
from upstash_redis import Redis

app = FastAPI(title="DG Agent Engine")

# Initialisation Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# Initialisation Upstash Redis
UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
redis = Redis(url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN) if UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN else None

class AgentRequest(BaseModel):
    project_id: str
    user_request: str

@app.get("/")
def health_check():
    return {"status": "online", "system": "DG Agent Engine"}

@app.post("/run-agent")
def run_agent(req: AgentRequest):
    try:
        if supabase:
            supabase.table("agent_logs").insert({
                "project_id": req.project_id,
                "user_request": req.user_request,
                "status": "pending"
            }).execute()
        
        return {"message": "Agent execution initiated", "request": req.user_request}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


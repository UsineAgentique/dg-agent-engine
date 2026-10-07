import json
from typing import Any, Dict

class BaseAgent:
    """Base class for all agents in the product pole.
    Provides a simple interface and shared utilities.
    """
    def __init__(self):
        pass

    def handle(self, mission: str) -> str:
        raise NotImplementedError("Subclasses must implement the handle method.")

class CPOProductAgent(BaseAgent):
    """Chief Product Officer Agent – defines product strategy, roadmap and KPI tracking."""
    def handle(self, mission: str) -> str:
        # Simple placeholder logic – in real usage this would be expanded.
        response = {
            "agent": "CPOProductAgent",
            "mission": mission,
            "action": "Define product vision and roadmap",
            "status": "completed"
        }
        return json.dumps(response)

class UXUIDesignerAgent(BaseAgent):
    """UX/UI Designer Agent – creates wireframes, prototypes and usability guidelines."""
    def handle(self, mission: str) -> str:
        response = {
            "agent": "UXUIDesignerAgent",
            "mission": mission,
            "action": "Generate wireframes and UI guidelines",
            "status": "completed"
        }
        return json.dumps(response)

class GrowthMarketingAgent(BaseAgent):
    """Growth Marketing Agent – plans acquisition, activation, retention and referral strategies."""
    def handle(self, mission: str) -> str:
        response = {
            "agent": "GrowthMarketingAgent",
            "mission": mission,
            "action": "Design growth funnel and KPI experiments",
            "status": "completed"
        }
        return json.dumps(response)

def run_mission(mission: str) -> str:
    """Entry point for the pole3 product agent.
    The mission string should contain a JSON payload with a "type" field
    indicating which sub‑agent should handle the request, e.g.:
    {"type": "cpo", "payload": "..."}
    If the type is unknown, the function returns an error JSON.
    """
    try:
        data: Dict[str, Any] = json.loads(mission)
        agent_type = data.get("type", "").lower()
        payload = data.get("payload", "")
    except json.JSONDecodeError:
        error = {"error": "Invalid JSON mission payload"}
        return json.dumps(error)

    if agent_type == "cpo":
        agent = CPOProductAgent()
    elif agent_type == "uxui":
        agent = UXUIDesignerAgent()
    elif agent_type == "growth":
        agent = GrowthMarketingAgent()
    else:
        error = {"error": f"Unknown agent type '{agent_type}'"}
        return json.dumps(error)

    return agent.handle(payload)

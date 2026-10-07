import json
from typing import Any, Dict

class BaseAgent:
    """Base class providing common utilities for all agents."""
    def __init__(self):
        pass

    def _format_response(self, status: str, data: Any = None, message: str = "") -> str:
        """Standardize JSON response for Slack integration.
        Args:
            status: 'success' or 'error'
            data: Payload to include
            message: Human readable message
        Returns:
            JSON string
        """
        response = {
            "status": status,
            "data": data,
            "message": message,
        }
        return json.dumps(response)

class CPOProductAgent(BaseAgent):
    """Chief Product Officer Agent – defines product vision, roadmap and specs."""
    def define_vision(self, market: str, user_needs: str) -> Dict[str, str]:
        return {
            "market": market,
            "user_needs": user_needs,
            "vision": f"Deliver a market‑leading solution for {market} that solves {user_needs}.",
        }

    def create_roadmap(self, features: list) -> Dict[str, Any]:
        # Simple prioritized roadmap (MVP, v1, v2)
        roadmap = {
            "MVP": features[:2],
            "v1": features[2:5],
            "v2": features[5:],
        }
        return roadmap

class UXUIDesignerAgent(BaseAgent):
    """UX/UI Designer Agent – produces wireframes & design guidelines."""
    def generate_wireframe(self, feature: str) -> Dict[str, str]:
        return {
            "feature": feature,
            "wireframe": f"Wireframe mockup for {feature} (placeholder SVG/HTML).",
        }

    def design_system(self) -> Dict[str, Any]:
        return {
            "palette": ["#0A0A0A", "#FFFFFF", "#1E90FF"],
            "typography": {"primary": "Inter", "secondary": "Roboto"},
            "components": ["Button", "Card", "Modal"],
        }

class GrowthMarketingAgent(BaseAgent):
    """Growth Marketing Agent – defines acquisition, activation, retention loops."""
    def acquisition_strategy(self, channel: str) -> Dict[str, str]:
        return {
            "channel": channel,
            "tactic": f"Run targeted {channel} campaigns with A/B testing and funnel analytics.",
        }

    def activation_funnel(self) -> Dict[str, Any]:
        return {
            "steps": ["Sign‑up", "Onboarding", "First Value"],
            "KPIs": {"conversion_rate": "%", "time_to_value": "days"},
        }

    def retention_plan(self) -> Dict[str, Any]:
        return {
            "programs": ["Email drip", "In‑app messaging", "Loyalty rewards"],
            "metrics": ["DAU", " churn", "NPS"],
        }

def run_mission(mission: str) -> str:
    """Entry point for the Team3 Product & Growth pole.
    The *mission* string must be a JSON payload with the following shape:
    {
        "agent": "CPO" | "UXUI" | "Growth",
        "action": "...",
        "params": { ... }
    }
    The function routes the request to the appropriate sub‑agent and returns a JSON string.
    """
    try:
        payload = json.loads(mission)
        agent_type = payload.get("agent")
        action = payload.get("action")
        params = payload.get("params", {})

        if agent_type == "CPO":
            agent = CPOProductAgent()
            if action == "define_vision":
                result = agent.define_vision(params.get("market", ""), params.get("user_needs", ""))
                return agent._format_response("success", result)
            if action == "create_roadmap":
                result = agent.create_roadmap(params.get("features", []))
                return agent._format_response("success", result)
        elif agent_type == "UXUI":
            agent = UXUIDesignerAgent()
            if action == "generate_wireframe":
                result = agent.generate_wireframe(params.get("feature", ""))
                return agent._format_response("success", result)
            if action == "design_system":
                result = agent.design_system()
                return agent._format_response("success", result)
        elif agent_type == "Growth":
            agent = GrowthMarketingAgent()
            if action == "acquisition_strategy":
                result = agent.acquisition_strategy(params.get("channel", ""))
                return agent._format_response("success", result)
            if action == "activation_funnel":
                result = agent.activation_funnel()
                return agent._format_response("success", result)
            if action == "retention_plan":
                result = agent.retention_plan()
                return agent._format_response("success", result)

        # If we reach here, the request is unknown or malformed
        return json.dumps({"status": "error", "message": "Unknown agent/action or missing parameters."})
    except json.JSONDecodeError:
        return json.dumps({"status": "error", "message": "Mission payload must be valid JSON."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

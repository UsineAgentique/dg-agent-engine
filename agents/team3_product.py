import json
from typing import Any, Dict

class BaseAgent:
    """Base class providing common utilities for all agents."""
    def __init__(self):
        pass

    def _format_response(self, status: str, data: Any = None, message: str = "") -> str:
        """Standardize JSON response for the run_mission interface.
        Args:
            status: 'success' or 'error'
            data: payload to include
            message: optional human‑readable message
        Returns:
            JSON string
        """
        response: Dict[str, Any] = {
            "status": status,
            "data": data,
            "message": message,
        }
        return json.dumps(response, ensure_ascii=False)

class CPOProductAgent(BaseAgent):
    """Chief Product Officer – defines product vision, roadmap and KPI tracking."""
    def define_vision(self, market_context: str) -> str:
        # Placeholder logic – to be enriched by real market analysis
        return f"Product vision aligned with market: {market_context}"

    def create_roadmap(self, features: list) -> str:
        roadmap = [{"quarter": i + 1, "features": f} for i, f in enumerate(features)]
        return json.dumps(roadmap, ensure_ascii=False, indent=2)

    def set_kpis(self, targets: dict) -> str:
        return json.dumps(targets, ensure_ascii=False, indent=2)

class UXUIDesignerAgent(BaseAgent):
    """UX/UI Designer – crafts user flows, wireframes and design system components."""
    def generate_user_flow(self, steps: list) -> str:
        flow = {"flow": steps}
        return json.dumps(flow, ensure_ascii=False, indent=2)

    def create_wireframe(self, page_name: str) -> str:
        # In a real implementation this would output a design spec or SVG.
        return f"Wireframe placeholder for {page_name}"

    def define_design_system(self, palette: dict, typography: dict) -> str:
        ds = {"palette": palette, "typography": typography}
        return json.dumps(ds, ensure_ascii=False, indent=2)

class GrowthMarketingAgent(BaseAgent):
    """Growth Marketing – plans acquisition, activation, retention and referral loops."""
    def build_funnel(self, stages: list) -> str:
        funnel = {"funnel": stages}
        return json.dumps(funnel, ensure_ascii=False, indent=2)

    def propose_experiments(self, hypothesis: str) -> str:
        return f"Experiment proposal based on hypothesis: {hypothesis}"

    def calculate_ltv(self, arpu: float, churn_rate: float) -> float:
        if churn_rate <= 0:
            return float('inf')
        return arpu / churn_rate

def run_mission(mission: str) -> str:
    """Entry point for the Team3 Product pole.
    The *mission* string must be a JSON payload with the following schema:
    {
        "agent": "cpo" | "designer" | "growth",
        "action": "<action_name>",
        "params": { ... }
    }
    The function routes the request to the appropriate sub‑agent and returns a
    standardized JSON response.
    """
    try:
        payload = json.loads(mission)
        agent_type = payload.get("agent")
        action = payload.get("action")
        params = payload.get("params", {})

        if agent_type == "cpo":
            agent = CPOProductAgent()
            if action == "define_vision":
                result = agent.define_vision(params.get("market_context", ""))
            elif action == "create_roadmap":
                result = agent.create_roadmap(params.get("features", []))
            elif action == "set_kpis":
                result = agent.set_kpis(params.get("targets", {}))
            else:
                return BaseAgent()._format_response(
                    "error", None, f"Unsupported CPO action: {action}"
                )
        elif agent_type == "designer":
            agent = UXUIDesignerAgent()
            if action == "generate_user_flow":
                result = agent.generate_user_flow(params.get("steps", []))
            elif action == "create_wireframe":
                result = agent.create_wireframe(params.get("page_name", ""))
            elif action == "define_design_system":
                result = agent.define_design_system(
                    params.get("palette", {}), params.get("typography", {})
                )
            else:
                return BaseAgent()._format_response(
                    "error", None, f"Unsupported Designer action: {action}"
                )
        elif agent_type == "growth":
            agent = GrowthMarketingAgent()
            if action == "build_funnel":
                result = agent.build_funnel(params.get("stages", []))
            elif action == "propose_experiments":
                result = agent.propose_experiments(params.get("hypothesis", ""))
            elif action == "calculate_ltv":
                arpu = float(params.get("arpu", 0))
                churn = float(params.get("churn_rate", 0))
                result = agent.calculate_ltv(arpu, churn)
            else:
                return BaseAgent()._format_response(
                    "error", None, f"Unsupported Growth action: {action}"
                )
        else:
            return BaseAgent()._format_response(
                "error", None, f"Unknown agent type: {agent_type}"
            )

        return BaseAgent()._format_response("success", result, "Mission executed")
    except json.JSONDecodeError:
        return BaseAgent()._format_response(
            "error", None, "Mission payload must be valid JSON"
        )
    except Exception as e:
        return BaseAgent()._format_response(
            "error", None, f"Unexpected error: {str(e)}"
        )

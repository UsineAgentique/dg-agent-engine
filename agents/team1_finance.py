import json

class CFOFinOpsAgent:
    """Agent responsible for monitoring burn rate and API quota costs."""
    def __init__(self):
        self.quota_usage = {}
        self.burn_rate = 0.0

    def update_quota(self, service: str, used: float, limit: float):
        self.quota_usage[service] = {
            "used": used,
            "limit": limit,
            "percentage": (used / limit) * 100 if limit else 0,
        }
        return self.quota_usage[service]

    def set_burn_rate(self, amount: float):
        self.burn_rate = amount
        return self.burn_rate

    def report(self):
        return {
            "burn_rate": self.burn_rate,
            "quota_usage": self.quota_usage,
        }

class LegalComplianceAgent:
    """Agent handling open‑source license audit and data privacy compliance."""
    def __init__(self):
        self.license_issues = []
        self.privacy_issues = []

    def audit_license(self, repo_name: str, license_type: str):
        # Simple rule: permissive licenses are ok, copyleft requires review
        if license_type.lower() in ["mit", "apache-2.0", "bsd-3-clause"]:
            status = "compliant"
        else:
            status = "requires review"
            self.license_issues.append({"repo": repo_name, "license": license_type})
        return {"repo": repo_name, "license": license_type, "status": status}

    def audit_privacy(self, data_category: str, encrypted: bool):
        if encrypted:
            status = "compliant"
        else:
            status = "non‑compliant"
            self.privacy_issues.append({"category": data_category, "encrypted": encrypted})
        return {"category": data_category, "encrypted": encrypted, "status": status}

    def report(self):
        return {
            "license_issues": self.license_issues,
            "privacy_issues": self.privacy_issues,
        }

class RiskManagerAgent:
    """Agent that identifies single points of failure and proposes mitigation plans."""
    def __init__(self):
        self.spoof_components = []
        self.mitigation_plans = {}

    def register_component(self, name: str, is_spof: bool):
        if is_spof:
            self.spoof_components.append(name)
        return {"component": name, "spof": is_spof}

    def add_mitigation(self, component: str, plan: str):
        self.mitigation_plans[component] = plan
        return {"component": component, "plan": plan}

    def report(self):
        return {
            "spof_components": self.spoof_components,
            "mitigation_plans": self.mitigation_plans,
        }

def run_mission(mission: str) -> str:
    """Entry point for the Finance/Juridique/Risques pole.

    The *mission* string is expected to be a JSON payload with the following keys:
    - "agent": one of "cfo", "legal", "risk"
    - "action": the method to invoke on the selected agent
    - "params": dictionary of parameters for the action

    Example::
        {
            "agent": "cfo",
            "action": "set_burn_rate",
            "params": {"amount": 1200.5}
        }
    """
    try:
        payload = json.loads(mission)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"})

    agent_name = payload.get("agent")
    action = payload.get("action")
    params = payload.get("params", {})

    # Instantiate agents lazily – they keep no state between calls.
    agents = {
        "cfo": CFOFinOpsAgent(),
        "legal": LegalComplianceAgent(),
        "risk": RiskManagerAgent(),
    }

    agent = agents.get(agent_name)
    if not agent:
        return json.dumps({"error": f"Unknown agent '{agent_name}'"})

    # Resolve method safely
    if not hasattr(agent, action):
        return json.dumps({"error": f"Agent '{agent_name}' has no action '{action}'"})

    method = getattr(agent, action)
    try:
        result = method(**params)
    except TypeError as e:
        return json.dumps({"error": f"Parameter mismatch: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"Execution error: {str(e)}"})

    return json.dumps({"agent": agent_name, "action": action, "result": result})

import json

class CFOFinOpsAgent:
    """Agent responsible for monitoring burn rate and API quota usage."""
    def __init__(self):
        self.quota_limits = {
            "groq": 1000000,  # example request quota per month
            "render": 5000,   # example service units
            "supabase": 2000000,
        }
        self.current_usage = {
            "groq": 0,
            "render": 0,
            "supabase": 0,
        }
        self.burn_rate = 0.0

    def update_usage(self, service: str, amount: int):
        if service in self.current_usage:
            self.current_usage[service] += amount
        else:
            raise ValueError(f"Unknown service {service}")

    def check_quota(self):
        alerts = []
        for svc, limit in self.quota_limits.items():
            usage = self.current_usage.get(svc, 0)
            if usage > limit:
                alerts.append(f"{svc} quota exceeded: {usage}/{limit}")
        return alerts

    def compute_burn_rate(self, period_days: int = 30):
        # Placeholder: in real world would pull cost data
        self.burn_rate = sum(self.current_usage.values()) / period_days
        return self.burn_rate

    def run(self, mission: str) -> str:
        if mission == "status":
            alerts = self.check_quota()
            burn = self.compute_burn_rate()
            status = {
                "usage": self.current_usage,
                "alerts": alerts,
                "burn_rate_per_day": burn,
            }
            return json.dumps(status)
        return f"CFOFinOpsAgent: unknown mission '{mission}'"

class LegalComplianceAgent:
    """Agent for open‑source licence audit and data privacy compliance."""
    def __init__(self):
        self.license_registry = {}
        self.privacy_issues = []

    def register_dependency(self, name: str, license_type: str):
        self.license_registry[name] = license_type

    def audit_licenses(self):
        non_compliant = []
        for dep, lic in self.license_registry.items():
            if lic not in ["MIT", "Apache-2.0", "BSD-3-Clause"]:
                non_compliant.append({"dependency": dep, "license": lic})
        return non_compliant

    def report_privacy(self):
        return self.privacy_issues

    def run(self, mission: str) -> str:
        if mission == "audit":
            issues = self.audit_licenses()
            return json.dumps({"license_issues": issues})
        elif mission == "privacy":
            return json.dumps({"privacy_issues": self.privacy_issues})
        return f"LegalComplianceAgent: unknown mission '{mission}'"

class RiskManagerAgent:
    """Agent for SPOF detection and automated mitigation planning."""
    def __init__(self):
        self.components = {}
        self.spo_factors = []

    def register_component(self, name: str, redundancy: bool):
        self.components[name] = {"redundancy": redundancy}

    def detect_spof(self):
        self.spo_factors = [name for name, info in self.components.items() if not info["redundancy"]]
        return self.spo_factors

    def generate_mitigation_plan(self):
        plan = {}
        for comp in self.spo_factors:
            plan[comp] = f"Add redundancy for {comp} (e.g., secondary instance, failover)"
        return plan

    def run(self, mission: str) -> str:
        if mission == "spof":
            spofs = self.detect_spof()
            plan = self.generate_mitigation_plan()
            return json.dumps({"spof": spofs, "mitigation": plan})
        return f"RiskManagerAgent: unknown mission '{mission}'"

def run_mission(mission: str) -> str:
    """Entry point for the Finance, Legal & Risk pole.
    Expected mission format: "<agent_name>:<sub_mission>"
    Example: "cfo:status" or "legal:audit" or "risk:spof"
    """
    try:
        agent_key, sub_mission = mission.split(":", 1)
    except ValueError:
        return "Invalid mission format. Use '<agent>:<sub_mission>'."

    agents = {
        "cfo": CFOFinOpsAgent(),
        "legal": LegalComplianceAgent(),
        "risk": RiskManagerAgent(),
    }

    agent = agents.get(agent_key.lower())
    if not agent:
        return f"Unknown agent '{agent_key}'. Available agents: cfo, legal, risk."
    return agent.run(sub_mission)

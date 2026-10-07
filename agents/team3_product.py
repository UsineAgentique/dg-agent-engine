import json


def _cpo_manager(mission: str) -> str:
    """Handle CPO & Product Manager related missions.
    Supported sub‑missions:
    - "roadmap": returns a template roadmap.
    - "features": returns a prioritized feature list.
    """
    mission = mission.lower()
    if "roadmap" in mission:
        roadmap = {
            "Q1": ["Discovery & research", "MVP definition"],
            "Q2": ["MVP launch", "User feedback loop"],
            "Q3": ["Feature expansion", "Scalability improvements"],
            "Q4": ["Growth hacking", "Internationalisation"]
        }
        return json.dumps({"role": "CPO/Product Manager", "roadmap": roadmap}, indent=2)
    if "feature" in mission:
        features = [
            {"name": "User onboarding", "priority": "high"},
            {"name": "Analytics dashboard", "priority": "medium"},
            {"name": "In‑app messaging", "priority": "low"}
        ]
        return json.dumps({"role": "CPO/Product Manager", "features": features}, indent=2)
    return "CPO/Product Manager: mission not recognized. Available: roadmap, features."


def _ux_ui_designer(mission: str) -> str:
    """Handle UX/UI Designer Agent missions.
    Supported sub‑missions:
    - "design system": returns a minimal design‑system skeleton.
    - "interface guidelines": returns UI/UX best‑practice rules.
    """
    mission = mission.lower()
    if "design system" in mission:
        ds = {
            "colors": {"primary": "#0066FF", "secondary": "#FF6600", "background": "#FFFFFF"},
            "typography": {"fontFamily": "Inter, sans-serif", "baseSize": "16px"},
            "components": ["Button", "Card", "Modal", "Input"]
        }
        return json.dumps({"role": "UX/UI Designer", "design_system": ds}, indent=2)
    if "interface" in mission or "guideline" in mission:
        guidelines = [
            "Maintain a 8‑pixel grid.",
            "Use accessible color contrast (>4.5:1).",
            "Provide clear feedback on user actions.",
            "Design for mobile‑first."]
        return json.dumps({"role": "UX/UI Designer", "interface_guidelines": guidelines}, indent=2)
    return "UX/UI Designer: mission not recognized. Available: design system, interface guidelines."


def _growth_marketing(mission: str) -> str:
    """Handle Growth & Marketing Specialist missions.
    Supported sub‑missions:
    - "acquisition": returns a high‑level acquisition funnel.
    - "metrics": returns key engagement metrics to monitor.
    """
    mission = mission.lower()
    if "acquisition" in mission:
        funnel = {
            "awareness": ["SEO", "Paid Ads", "Social Media"],
            "interest": ["Content Marketing", "Webinars"],
            "conversion": ["Landing Pages", "A/B Testing"],
            "retention": ["Email Nurture", "Push Notifications"]
        }
        return json.dumps({"role": "Growth & Marketing", "acquisition_funnel": funnel}, indent=2)
    if "metric" in mission:
        metrics = ["DAU/MAU ratio", "Customer Acquisition Cost (CAC)", "Lifetime Value (LTV)", "Churn rate"]
        return json.dumps({"role": "Growth & Marketing", "key_metrics": metrics}, indent=2)
    return "Growth & Marketing: mission not recognized. Available: acquisition, metrics."


def run_mission(mission: str) -> str:
    """Entry point for the Team3 Product pole.
    The *mission* string should contain a keyword that maps to one of the three sub‑agents.
    Example missions:
    - "roadmap for Q2"
    - "design system skeleton"
    - "acquisition funnel overview"
    """
    if not mission:
        return "Error: empty mission string."
    lowered = mission.lower()
    if any(k in lowered for k in ["roadmap", "feature"]):
        return _cpo_manager(mission)
    if any(k in lowered for k in ["design system", "interface", "guideline"]):
        return _ux_ui_designer(mission)
    if any(k in lowered for k in ["acquisition", "metric", "growth"]):
        return _growth_marketing(mission)
    return "Mission not routed: please include keywords like 'roadmap', 'design system', or 'acquisition'."

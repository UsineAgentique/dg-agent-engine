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
    - "interface rules": returns UI/UX best‑practice rules.
    """
    mission = mission.lower()
    if "design system" in mission:
        ds = {
            "colors": {"primary": "#0066FF", "secondary": "#FF6600", "background": "#FFFFFF"},
            "typography": {"fontFamily": "Inter, sans-serif", "baseSize": "16px"},
            "spacing": "8px"
        }
        return json.dumps({"role": "UX/UI Designer", "design_system": ds}, indent=2)
    if "interface" in mission or "rule" in mission:
        rules = [
            "Consistent navigation hierarchy",
            "Accessible contrast ratios (WCAG AA)",
            "Responsive layout (mobile‑first)",
            "Feedback on every user action"
        ]
        return json.dumps({"role": "UX/UI Designer", "interface_rules": rules}, indent=2)
    return "UX/UI Designer: mission not recognized. Available: design system, interface rules."


def _growth_marketing(mission: str) -> str:
    """Handle Growth & Marketing Specialist missions.
    Supported sub‑missions:
    - "acquisition": returns a high‑level acquisition funnel.
    - "metrics": returns key engagement metrics.
    """
    mission = mission.lower()
    if "acquisition" in mission:
        funnel = {
            "awareness": ["SEO", "Paid ads", "Social media"],
            "interest": ["Content marketing", "Webinars"],
            "conversion": ["Landing pages", "A/B testing"],
            "retention": ["Email drip", "Push notifications"]
        }
        return json.dumps({"role": "Growth & Marketing", "acquisition_funnel": funnel}, indent=2)
    if "metric" in mission or "engagement" in mission:
        metrics = {
            "DAU": "Daily Active Users",
            "MAU": "Monthly Active Users",
            "CAC": "Customer Acquisition Cost",
            "LTV": "Lifetime Value",
            "CR": "Conversion Rate"
        }
        return json.dumps({"role": "Growth & Marketing", "key_metrics": metrics}, indent=2)
    return "Growth & Marketing: mission not recognized. Available: acquisition, metrics."


def run_mission(mission: str) -> str:
    """Entry point for the Team3 Product pole.
    The mission string should contain a keyword indicating the target role:
    - "cpo" or "product" → CPO/Product Manager
    - "designer" or "ui" → UX/UI Designer
    - "growth" or "marketing" → Growth & Marketing
    The remainder of the string is forwarded to the role‑specific handler.
    """
    lowered = mission.lower()
    if "cpo" in lowered or "product" in lowered:
        return _cpo_manager(mission)
    if "designer" in lowered or "ui" in lowered:
        return _ux_ui_designer(mission)
    if "growth" in lowered or "marketing" in lowered:
        return _growth_marketing(mission)
    return "Team3 Product pole: unable to route mission. Include one of [cpo, product, designer, ui, growth, marketing] in the description."

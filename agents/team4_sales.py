import json

class SalesAgent:
    """Agent responsable du closing, prospection et génération de devis."""
    def __init__(self):
        pass

    def prospect(self, lead_info: dict) -> str:
        return f"Prospecting lead: {lead_info.get('name', 'unknown')}"

    def close_deal(self, deal_info: dict) -> str:
        return f"Closing deal with value {deal_info.get('amount', 0)}"

    def generate_quote(self, request: dict) -> str:
        return f"Quote generated for {request.get('client', 'unknown')}"

class ContentMarketerAgent:
    """Agent chargé de la rédaction, SEO et gestion des réseaux sociaux."""
    def __init__(self):
        pass

    def write_content(self, topic: str) -> str:
        return f"Article draft on {topic}"

    def optimize_seo(self, content: str) -> str:
        return f"SEO-optimized content: {content[:60]}..."

    def schedule_social(self, platform: str, content: str) -> str:
        return f"Scheduled post on {platform}: {content[:30]}..."

class CustomerSuccessAgent:
    """Agent dédié au support client et à la fidélisation."""
    def __init__(self):
        pass

    def handle_ticket(self, ticket_id: str) -> str:
        return f"Ticket {ticket_id} resolved"

    def nurture_account(self, account_id: str) -> str:
        return f"Nurturing account {account_id} for upsell"

def run_mission(mission: str) -> str:
    """Entrypoint unique du pôle 4.
    Le paramètre `mission` doit être un JSON string contenant:
    {
        "agent": "sales|content|success",
        "action": "...",
        "payload": { ... }
    }
    """
    try:
        data = json.loads(mission)
    except json.JSONDecodeError:
        return "[ERROR] Mission must be a valid JSON string"

    agent_type = data.get("agent")
    action = data.get("action")
    payload = data.get("payload", {})

    if agent_type == "sales":
        agent = SalesAgent()
        if action == "prospect":
            return agent.prospect(payload)
        if action == "close":
            return agent.close_deal(payload)
        if action == "quote":
            return agent.generate_quote(payload)
        return f"[ERROR] Unknown sales action: {action}"

    if agent_type == "content":
        agent = ContentMarketerAgent()
        if action == "write":
            return agent.write_content(payload.get("topic", ""))
        if action == "seo":
            return agent.optimize_seo(payload.get("content", ""))
        if action == "schedule":
            return agent.schedule_social(payload.get("platform", ""), payload.get("content", ""))
        return f"[ERROR] Unknown content action: {action}"

    if agent_type == "success":
        agent = CustomerSuccessAgent()
        if action == "ticket":
            return agent.handle_ticket(payload.get("ticket_id", ""))
        if action == "nurture":
            return agent.nurture_account(payload.get("account_id", ""))
        return f"[ERROR] Unknown success action: {action}"

    return f"[ERROR] Unknown agent type: {agent_type}"

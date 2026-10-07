class OutreachAgent:
    def handle(self, data):
        return f"Outreach performed on {data}"

class CloserAgent:
    def handle(self, data):
        return f"Closing actions taken for {data}"

class ProposalAgent:
    def handle(self, data):
        return f"Proposal generated for {data}"

def run_mission(mission: str) -> str:
    parts = mission.split(":", 1)
    if len(parts) != 2:
        return "Invalid mission format. Use 'type:payload'"
    typ, payload = parts[0].strip().lower(), parts[1].strip()
    if typ == "outreach":
        return OutreachAgent().handle(payload)
    if typ == "close":
        return CloserAgent().handle(payload)
    if typ == "proposal":
        return ProposalAgent().handle(payload)
    return "Unknown mission type"

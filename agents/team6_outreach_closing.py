class OutreachAgent:
    def prospect(self, lead):
        return f"Prospecting lead {lead}"
    def qualify(self, lead):
        return f"Qualifying lead {lead}"

class CloserAgent:
    def handle_objection(self, objection):
        return f"Handling objection: {objection}"
    def negotiate(self, terms):
        return f"Negotiating terms: {terms}"

class ProposalAgent:
    def generate(self, client, details):
        return f"Proposal for {client}: {details}"

def run_mission(mission: str) -> str:
    if mission.startswith("prospect"):
        lead = mission.split(" ",1)[1] if " " in mission else "unknown"
        return OutreachAgent().prospect(lead)
    elif mission.startswith("qualify"):
        lead = mission.split(" ",1)[1] if " " in mission else "unknown"
        return OutreachAgent().qualify(lead)
    elif mission.startswith("objection"):
        obj = mission.split(" ",1)[1] if " " in mission else "unknown"
        return CloserAgent().handle_objection(obj)
    elif mission.startswith("negotiate"):
        terms = mission.split(" ",1)[1] if " " in mission else "unknown"
        return CloserAgent().negotiate(terms)
    elif mission.startswith("proposal"):
        parts = mission.split(" ",2)
        client = parts[1] if len(parts)>1 else "unknown"
        details = parts[2] if len(parts)>2 else ""
        return ProposalAgent().generate(client, details)
    else:
        return "Mission not recognized"

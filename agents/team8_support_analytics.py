class SupportAgent:
    def __init__(self):
        self.tickets = []
        self.faq = {}
        self.satisfaction_scores = []

    def create_ticket(self, user_id, issue):
        ticket = {'id': len(self.tickets) + 1, 'user_id': user_id, 'issue': issue, 'status': 'open'}
        self.tickets.append(ticket)
        return f"Ticket {ticket['id']} created."

    def resolve_ticket(self, ticket_id, resolution):
        for t in self.tickets:
            if t['id'] == ticket_id:
                t['status'] = 'closed'
                t['resolution'] = resolution
                return f"Ticket {ticket_id} resolved."
        return f"Ticket {ticket_id} not found."

    def add_faq(self, question, answer):
        self.faq[question] = answer
        return "FAQ entry added."

    def get_faq(self, question):
        return self.faq.get(question, "No answer available.")

    def record_satisfaction(self, score):
        self.satisfaction_scores.append(score)
        return "Satisfaction score recorded."

    def average_satisfaction(self):
        if not self.satisfaction_scores:
            return 0
        return sum(self.satisfaction_scores) / len(self.satisfaction_scores)

class AnalyticsAgent:
    def __init__(self):
        self.usage_metrics = []
        self.retention_data = []

    def log_usage(self, user_id, event):
        self.usage_metrics.append({'user_id': user_id, 'event': event})
        return "Usage event logged."

    def compute_retention(self, period_days):
        # Simple placeholder: count unique users in last period
        recent_users = {m['user_id'] for m in self.usage_metrics if m.get('days_ago', 0) <= period_days}
        return len(recent_users)

    def compute_churn(self, period_days):
        # Placeholder churn: users not seen in period
        all_users = {m['user_id'] for m in self.usage_metrics}
        recent_users = {m['user_id'] for m in self.usage_metrics if m.get('days_ago', 0) <= period_days}
        churned = all_users - recent_users
        return len(churned)

class PivotAgent:
    def __init__(self):
        self.recommendations = []

    def analyze(self, support_agent: SupportAgent, analytics_agent: AnalyticsAgent):
        sat = support_agent.average_satisfaction()
        retention = analytics_agent.compute_retention(30)
        churn = analytics_agent.compute_churn(30)
        rec = []
        if sat < 3:
            rec.append('Improve FAQ coverage and response times.')
        if churn > retention * 0.2:
            rec.append('Launch re-engagement campaign.')
        self.recommendations = rec
        return rec

def run_mission(mission: str) -> str:
    # Simple dispatcher based on keywords
    support = SupportAgent()
    analytics = AnalyticsAgent()
    pivot = PivotAgent()
    if mission.startswith('ticket:'):
        _, user_id, issue = mission.split(':', 2)
        return support.create_ticket(user_id, issue)
    if mission.startswith('resolve:'):
        _, ticket_id, resolution = mission.split(':', 2)
        return support.resolve_ticket(int(ticket_id), resolution)
    if mission.startswith('faq:add:'):
        _, question, answer = mission.split(':', 2)
        return support.add_faq(question, answer)
    if mission.startswith('faq:get:'):
        _, question = mission.split(':', 1)
        return support.get_faq(question)
    if mission.startswith('satisfaction:'):
        _, score = mission.split(':', 1)
        return support.record_satisfaction(float(score))
    if mission.startswith('usage:'):
        _, user_id, event = mission.split(':', 2)
        return analytics.log_usage(user_id, event)
    if mission == 'pivot':
        recs = pivot.analyze(support, analytics)
        return ' | '.join(recs) if recs else 'No recommendations.'
    return 'Mission not recognized.'

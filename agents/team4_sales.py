import re

class SalesAgent:
    """Agent dédié aux activités de vente : prospection, closing, génération de devis."""
    def prospect(self, target: str) -> str:
        return f"Prospection initiée pour le segment '{target}'."

    def close_deal(self, deal_id: str) -> str:
        return f"Deal {deal_id} clôturé avec succès."

    def generate_quote(self, client: str, amount: float) -> str:
        return f"Devis généré pour {client} d'un montant de {amount:.2f} €."

class ContentMarketerAgent:
    """Agent dédié au marketing de contenu : rédaction, SEO, gestion des réseaux sociaux."""
    def write_article(self, topic: str) -> str:
        return f"Article rédigé sur le sujet '{topic}'."

    def optimize_seo(self, page_url: str) -> str:
        return f"SEO optimisé pour la page {page_url}."

    def schedule_social(self, platform: str, content: str) -> str:
        return f"Publication programmée sur {platform}: '{content}'."

class CustomerSuccessAgent:
    """Agent dédié à la réussite client : support, fidélisation, upsell."""
    def handle_ticket(self, ticket_id: str) -> str:
        return f"Ticket {ticket_id} traité et résolu."

    def nurture_account(self, account_id: str) -> str:
        return f"Programme de fidélisation lancé pour le compte {account_id}."

    def propose_upsell(self, account_id: str) -> str:
        return f"Proposition d'upsell envoyée au compte {account_id}."

def run_mission(mission: str) -> str:
    """Entrée unique du pôle 4.
    Le paramètre `mission` doit contenir un mot‑clé indiquant le sous‑agent à invoquer.
    Exemple : "prospect: SMB" ou "write_article: IA et marketing".
    """
    # Normaliser la chaîne
    mission = mission.strip()
    if not mission:
        return "Aucune mission fournie."

    # Découper le type et le payload
    match = re.match(r"(?P<action>[^:]+):?\s*(?P<payload>.*)", mission)
    if not match:
        return f"Format de mission invalide: '{mission}'."

    action = match.group('action').lower()
    payload = match.group('payload')

    # Instancier les agents
    sales = SalesAgent()
    marketer = ContentMarketerAgent()
    cs = CustomerSuccessAgent()

    # Routage simple basé sur le préfixe de l'action
    if action in {"prospect", "prospection"}:
        return sales.prospect(payload or "général")
    if action in {"close", "close_deal", "closing"}:
        return sales.close_deal(payload or "unknown")
    if action in {"quote", "devis", "generate_quote"}:
        # Attendre "client,amount"
        parts = [p.strip() for p in payload.split(',')]
        if len(parts) != 2:
            return "Payload pour devis doit être 'client,amount'."
        client, amount_str = parts
        try:
            amount = float(amount_str)
        except ValueError:
            return f"Montant invalide: {amount_str}."
        return sales.generate_quote(client, amount)
    if action in {"write_article", "article", "rédaction"}:
        return marketer.write_article(payload or "sans titre")
    if action in {"seo", "optimize_seo"}:
        return marketer.optimize_seo(payload or "URL inconnue")
    if action in {"schedule_social", "social", "post"}:
        # Attendre "platform|content"
        parts = [p.strip() for p in payload.split('|', 1)]
        if len(parts) != 2:
            return "Payload pour post social doit être 'platform|content'."
        platform, content = parts
        return marketer.schedule_social(platform, content)
    if action in {"ticket", "handle_ticket", "support"}:
        return cs.handle_ticket(payload or "unknown")
    if action in {"nurture", "fidelisation", "nurture_account"}:
        return cs.nurture_account(payload or "unknown")
    if action in {"upsell", "propose_upsell"}:
        return cs.propose_upsell(payload or "unknown")

    return f"Action inconnue: '{action}'."

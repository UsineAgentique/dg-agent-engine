import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SalesAgent:
    """Agent responsable du closing, de la prospection et de la génération de devis."""
    def __init__(self):
        self.pipeline = []

    def prospect(self, lead: dict) -> str:
        """Simule la prospection d'un lead et l'ajoute au pipeline."""
        self.pipeline.append(lead)
        logger.info(f"Prospection du lead: {lead.get('name')}")
        return f"Lead {lead.get('name')} ajouté au pipeline."

    def generate_quote(self, lead_name: str, amount: float) -> str:
        """Génère un devis simple pour le lead spécifié."""
        quote = {
            "lead": lead_name,
            "amount": amount,
            "currency": "EUR",
            "status": "draft"
        }
        logger.info(f"Devis généré pour {lead_name}: {amount} EUR")
        return f"Devis pour {lead_name}: {amount} EUR (statut: draft)."

    def close_deal(self, lead_name: str) -> str:
        """Marque le lead comme gagné dans le pipeline."""
        for lead in self.pipeline:
            if lead.get('name') == lead_name:
                lead['status'] = 'won'
                logger.info(f"Deal clos pour {lead_name}")
                return f"Deal clos pour {lead_name}."
        logger.warning(f"Lead {lead_name} non trouvé dans le pipeline.")
        return f"Lead {lead_name} non trouvé."

class ContentMarketerAgent:
    """Agent dédié à la création de contenu, SEO et gestion des réseaux sociaux."""
    def __init__(self):
        self.articles = []
        self.social_posts = []

    def write_article(self, title: str, keywords: list) -> str:
        article = {
            "title": title,
            "keywords": keywords,
            "content": f"Article sur {title} avec mots-clés {', '.join(keywords)}."
        }
        self.articles.append(article)
        logger.info(f"Article rédigé: {title}")
        return f"Article '{title}' créé."

    def seo_audit(self, url: str) -> str:
        # Placeholder audit
        logger.info(f"Audit SEO réalisé pour {url}")
        return f"Audit SEO basique pour {url}: score 75/100."

    def schedule_social_post(self, platform: str, content: str, schedule_time: str) -> str:
        post = {
            "platform": platform,
            "content": content,
            "schedule_time": schedule_time
        }
        self.social_posts.append(post)
        logger.info(f"Post programmé sur {platform} à {schedule_time}")
        return f"Post programmé sur {platform} à {schedule_time}."

class CustomerSuccessAgent:
    """Agent chargé du support client et de la fidélisation."""
    def __init__(self):
        self.tickets = []
        self.nps_scores = []

    def create_ticket(self, client: str, issue: str) -> str:
        ticket = {
            "client": client,
            "issue": issue,
            "status": "open"
        }
        self.tickets.append(ticket)
        logger.info(f"Ticket créé pour {client}: {issue}")
        return f"Ticket ouvert pour {client}."

    def resolve_ticket(self, client: str) -> str:
        for ticket in self.tickets:
            if ticket["client"] == client and ticket["status"] == "open":
                ticket["status"] = "closed"
                logger.info(f"Ticket résolu pour {client}")
                return f"Ticket résolu pour {client}."
        logger.warning(f"Aucun ticket ouvert trouvé pour {client}")
        return f"Aucun ticket ouvert pour {client}."

    def record_nps(self, client: str, score: int) -> str:
        self.nps_scores.append({"client": client, "score": score})
        logger.info(f"NPS enregistré pour {client}: {score}")
        return f"NPS de {score} enregistré pour {client}."

def run_mission(mission: str) -> str:
    """Entrypoint générique du pôle 4.
    Le paramètre `mission` détermine l'action à exécuter.
    Exemple de missions supportées :
      - "prospect:{'name':'Acme Corp','industry':'Tech'}"
      - "quote:{'lead':'Acme Corp','amount':5000}"
      - "article:{'title':'Guide SEO 2024','keywords':['seo','2024','guide']}"
    Toute mission non reconnue renvoie un message d'erreur.
    """
    try:
        # Simple parsing based on prefix
        if mission.startswith("prospect:"):
            import ast
            lead = ast.literal_eval(mission.split(":", 1)[1])
            agent = SalesAgent()
            return agent.prospect(lead)
        elif mission.startswith("quote:"):
            import ast
            data = ast.literal_eval(mission.split(":", 1)[1])
            agent = SalesAgent()
            return agent.generate_quote(data["lead"], data["amount"])
        elif mission.startswith("close:"):
            lead_name = mission.split(":", 1)[1]
            agent = SalesAgent()
            return agent.close_deal(lead_name)
        elif mission.startswith("article:"):
            import ast
            data = ast.literal_eval(mission.split(":", 1)[1])
            agent = ContentMarketerAgent()
            return agent.write_article(data["title"], data["keywords"])
        elif mission.startswith("seo:"):
            url = mission.split(":", 1)[1]
            agent = ContentMarketerAgent()
            return agent.seo_audit(url)
        elif mission.startswith("social:"):
            import ast
            data = ast.literal_eval(mission.split(":", 1)[1])
            agent = ContentMarketerAgent()
            return agent.schedule_social_post(data["platform"], data["content"], data["schedule_time"])
        elif mission.startswith("ticket:"):
            import ast
            data = ast.literal_eval(mission.split(":", 1)[1])
            agent = CustomerSuccessAgent()
            return agent.create_ticket(data["client"], data["issue"])
        elif mission.startswith("resolve:"):
            client = mission.split(":", 1)[1]
            agent = CustomerSuccessAgent()
            return agent.resolve_ticket(client)
        elif mission.startswith("nps:"):
            import ast
            data = ast.literal_eval(mission.split(":", 1)[1])
            agent = CustomerSuccessAgent()
            return agent.record_nps(data["client"], data["score"])
        else:
            return f"Mission non reconnue: {mission}"
    except Exception as e:
        logger.exception("Erreur lors de l'exécution de la mission")
        return f"Erreur: {str(e)}"

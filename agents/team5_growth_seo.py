import re
import json
from typing import List, Dict

class SEOAgent:
    """Agent dédié à l'optimisation SEO.
    - génération de mots‑clés pertinents
    - audit technique simplifié
    - recommandations on‑page
    """

    def __init__(self):
        self.keywords: List[str] = []
        self.audit_report: Dict[str, str] = {}
        self.optimizations: List[str] = []

    def generate_keywords(self, topic: str, max_keywords: int = 10) -> List[str]:
        """Génère une liste de mots‑clés à partir d'un sujet.
        Implémentation très basique : découpage du texte, suppression des stop‑words
        et sélection des termes les plus fréquents.
        """
        stop_words = {"le", "la", "les", "de", "des", "du", "un", "une", "et", "en", "à", "pour", "dans", "sur", "avec", "par", "ou", "mais", "si", "au", "aux"}
        words = re.findall(r"[a-zA-ZÀ-ÿ']+", topic.lower())
        freq: Dict[str, int] = {}
        for w in words:
            if w not in stop_words and len(w) > 2:
                freq[w] = freq.get(w, 0) + 1
        # tri par fréquence puis alphabetique
        sorted_words = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
        self.keywords = [w for w, _ in sorted_words[:max_keywords]]
        return self.keywords

    def technical_audit(self, url: str) -> Dict[str, str]:
        """Audit technique très simplifié (placeholder).
        Retourne un rapport factice contenant les points classiques à vérifier.
        """
        # Dans un vrai contexte, on appellerait des APIs comme Google PageSpeed, Lighthouse, etc.
        self.audit_report = {
            "url": url,
            "mobile_friendly": "OK",
            "page_speed_score": "85/100",
            "structured_data": "Présent",
            "broken_links": "0",
            "meta_description_length": "150 caractères",
        }
        return self.audit_report

    def on_page_optimizations(self, content: str) -> List[str]:
        """Analyse le contenu et propose des actions d'optimisation on‑page.
        Retourne une liste d'actions (ex: ajouter H1, densité mots‑clés, etc.).
        """
        suggestions = []
        # Vérification H1
        if not re.search(r"<h1[^>]*>.*?</h1>", content, re.IGNORECASE):
            suggestions.append("Ajouter une balise H1 descriptive.")
        # Densité mots‑clés (exemple très basique)
        if self.keywords:
            total_words = len(re.findall(r"\w+", content))
            for kw in self.keywords:
                count = len(re.findall(rf"\b{re.escape(kw)}\b", content, re.IGNORECASE))
                density = (count / total_words) * 100 if total_words else 0
                if density < 0.5:
                    suggestions.append(f"Augmenter la densité du mot‑clé '{kw}'.")
        self.optimizations = suggestions
        return suggestions

class GrowthHackerAgent:
    """Agent dédié aux stratégies de croissance virale et aux funnels AARRR.
    """

    def __init__(self):
        self.funnels: List[Dict[str, str]] = []
        self.campaigns: List[Dict[str, str]] = []

    def design_funnel(self, name: str, stages: List[str]) -> Dict[str, str]:
        """Crée une description de funnel AARRR.
        stages doit contenir les étapes dans l'ordre (Acquisition, Activation, Retention, Referral, Revenue).
        """
        funnel = {"name": name, "stages": " -> ".join(stages)}
        self.funnels.append(funnel)
        return funnel

    def suggest_viral_mechanic(self, product_desc: str) -> str:
        """Propose une mécanique virale simple basée sur le texte fourni.
        Cette implémentation est factice : elle recherche des mots‑clés comme "invite", "share", "reward".
        """
        if any(word in product_desc.lower() for word in ["invite", "share", "reward", "referral"]):
            return "Implémenter un programme de parrainage avec récompense à chaque partage.")
        return "Créer un challenge social avec un tableau de classement public."

    def automate_acquisition(self, channel: str, budget: float) -> Dict[str, str]:
        """Retourne un plan d'automatisation d'acquisition (placeholder).
        """
        plan = {
            "channel": channel,
            "budget": f"${budget:.2f}",
            "action": "Déployer campagne CPC + retargeting automatisé",
            "tool": "Google Ads + Facebook Ads API",
        }
        self.campaigns.append(plan)
        return plan

class CopywriterAgent:
    """Agent de rédaction optimisée SEO & marketing.
    """

    def __init__(self):
        self.articles: List[Dict[str, str]] = []

    def write_blog_post(self, title: str, keywords: List[str], length: int = 500) -> str:
        """Génère un texte de blog très basique en insérant les mots‑clés.
        Le texte n'est pas destiné à être publié tel quel ; il sert de squelette.
        """
        intro = f"{title}\n" + "=" * len(title) + "\n\n"
        body = f"Cet article explore les concepts clés autour de {', '.join(keywords)}. "
        # répéter le corps pour atteindre la longueur approximative
        while len(body) < length:
            body += "Nous approfondissons chaque point avec des exemples concrets et des bonnes pratiques. "
        content = intro + body.strip()
        self.articles.append({"title": title, "content": content})
        return content

    def craft_newsletter(self, subject: str, highlights: List[str]) -> str:
        """Compose un texte de newsletter simple.
        """
        header = f"Subject: {subject}\n\n"
        body = "\n- ".join(["", *highlights])
        return header + body

    def social_post(self, platform: str, message: str, hashtags: List[str]) -> str:
        """Formate un post pour un réseau social donné.
        """
        tag_str = " ".join(f"#{tag}" for tag in hashtags)
        return f"[{platform.upper()}] {message} {tag_str}".strip()

def run_mission(mission: str) -> str:
    """Entrypoint unique du sous‑agent.
    Le paramètre *mission* doit être un JSON string contenant:
    {
        "agent": "seo|growth|copywriter",
        "action": "...",
        "params": { ... }
    }
    La fonction retourne un JSON string avec le résultat ou une erreur.
    """
    try:
        payload = json.loads(mission)
        agent_type = payload.get("agent")
        action = payload.get("action")
        params = payload.get("params", {})
        if agent_type == "seo":
            agent = SEOAgent()
            if action == "generate_keywords":
                topic = params.get("topic", "")
                max_k = int(params.get("max", 10))
                result = agent.generate_keywords(topic, max_k)
            elif action == "technical_audit":
                url = params.get("url", "")
                result = agent.technical_audit(url)
            elif action == "on_page":
                content = params.get("content", "")
                result = agent.on_page_optimizations(content)
            else:
                raise ValueError(f"Action SEO inconnue: {action}")
        elif agent_type == "growth":
            agent = GrowthHackerAgent()
            if action == "design_funnel":
                name = params.get("name", "Unnamed Funnel")
                stages = params.get("stages", ["Acquisition", "Activation", "Retention", "Referral", "Revenue"])
                result = agent.design_funnel(name, stages)
            elif action == "viral_mechanic":
                desc = params.get("description", "")
                result = agent.suggest_viral_mechanic(desc)
            elif action == "automate_acquisition":
                channel = params.get("channel", "online")
                budget = float(params.get("budget", 0))
                result = agent.automate_acquisition(channel, budget)
            else:
                raise ValueError(f"Action Growth inconnue: {action}")
        elif agent_type == "copywriter":
            agent = CopywriterAgent()
            if action == "write_blog":
                title = params.get("title", "Untitled")
                keywords = params.get("keywords", [])
                length = int(params.get("length", 500))
                result = agent.write_blog_post(title, keywords, length)
            elif action == "newsletter":
                subject = params.get("subject", "Newsletter")
                highlights = params.get("highlights", [])
                result = agent.craft_newsletter(subject, highlights)
            elif action == "social":
                platform = params.get("platform", "twitter")
                message = params.get("message", "")
                hashtags = params.get("hashtags", [])
                result = agent.social_post(platform, message, hashtags)
            else:
                raise ValueError(f"Action Copywriter inconnue: {action}")
        else:
            raise ValueError(f"Agent inconnu: {agent_type}")
        return json.dumps({"status": "success", "result": result})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

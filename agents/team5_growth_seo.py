import re
from typing import List, Dict

class SEOAgent:
    """Agent responsible for SEO related tasks.
    - keyword research
    - technical SEO audit
    - on-page optimization
    """

    def __init__(self):
        self.keywords: List[str] = []
        self.audit_report: Dict[str, str] = {}
        self.optimizations: List[str] = []

    def research_keywords(self, topic: str, top_n: int = 10) -> List[str]:
        """Simple placeholder keyword generator based on the topic.
        In a real scenario this would call an external API or use a corpus.
        """
        base = re.sub(r"[^a-zA-Z0-9]", " ", topic).lower().split()
        self.keywords = [f"{word} {suffix}" for word in base for suffix in ["tips", "guide", "2024", "best practices"]][:top_n]
        return self.keywords

    def technical_audit(self, url: str) -> Dict[str, str]:
        """Placeholder technical audit – returns dummy findings.
        """
        self.audit_report = {
            "url": url,
            "status": "OK",
            "issues": "None detected",
            "recommendation": "Maintain current performance"
        }
        return self.audit_report

    def optimize_on_page(self, content: str, target_keyword: str) -> str:
        """Very naive on‑page optimization: injects the target keyword in the first paragraph.
        """
        paragraphs = content.split('\n\n')
        if not paragraphs:
            return content
        paragraphs[0] = f"{target_keyword}: {paragraphs[0]}"
        optimized = "\n\n".join(paragraphs)
        self.optimizations.append(f"Injected keyword '{target_keyword}' in first paragraph")
        return optimized

class GrowthHackerAgent:
    """Agent handling growth hacking tactics.
    - viral acquisition ideas
    - AARRR funnel mapping
    - automation suggestions
    """

    def __init__(self):
        self.funnel_steps = ["Acquisition", "Activation", "Retention", "Referral", "Revenue"]
        self.ideas: List[str] = []
        self.automations: List[str] = []

    def generate_viral_ideas(self, product: str, max_ideas: int = 5) -> List[str]:
        base = product.title()
        self.ideas = [
            f"Launch a referral contest for {base} users",
            f"Create shareable infographic about {base} benefits",
            f"Offer limited‑time discount for social shares of {base}",
            f"Integrate {base} with popular meme templates",
            f"Host a live AMA featuring {base} power users"
        ][:max_ideas]
        return self.ideas

    def map_aarrr_funnel(self, product: str) -> Dict[str, str]:
        mapping = {step: f"Define {step.lower()} strategy for {product}" for step in self.funnel_steps}
        return mapping

    def suggest_automation(self, task: str) -> str:
        suggestion = f"Use Zapier/Make to automate '{task}' with email triggers and Slack notifications."
        self.automations.append(suggestion)
        return suggestion

class CopywriterAgent:
    """Agent for copy creation.
    - SEO‑friendly articles
    - newsletters
    - social media posts
    """

    def __init__(self):
        self.last_output: str = ""

    def write_article(self, title: str, keywords: List[str], length: int = 500) -> str:
        kw_str = ", ".join(keywords)
        article = f"# {title}\n\n" \
                  f"This article covers {kw_str}.\n\n" \
                  f"" + "Lorem ipsum " * (length // 11)
        self.last_output = article
        return article

    def write_newsletter(self, subject: str, highlights: List[str]) -> str:
        body = f"Subject: {subject}\n\nDear subscriber,\n\nHere are this week’s highlights:\n"
        for i, h in enumerate(highlights, 1):
            body += f"{i}. {h}\n"
        body += "\nBest regards,\nYour Growth Team"
        self.last_output = body
        return body

    def write_social_post(self, platform: str, message: str, hashtags: List[str]) -> str:
        tag_str = " ".join(f"#{tag}" for tag in hashtags)
        post = f"[{platform.upper()}] {message} {tag_str}"
        self.last_output = post
        return post

def run_mission(mission: str) -> str:
    """Entry point for the Growth & SEO pole.
    The mission string should be a simple command in the form:
    `agent:action:param1,param2,...`
    Example: `seo:research_keywords:Artificial Intelligence`
    """
    try:
        agent_part, action_part, *params = mission.split(":")
        params = params[0].split(",") if params else []
        if agent_part.lower() == "seo":
            agent = SEOAgent()
            if action_part == "research_keywords":
                return ", ".join(agent.research_keywords(params[0] if params else ""))
            if action_part == "technical_audit":
                return str(agent.technical_audit(params[0] if params else ""))
            if action_part == "optimize_on_page":
                content = params[0] if len(params) > 0 else ""
                keyword = params[1] if len(params) > 1 else ""
                return agent.optimize_on_page(content, keyword)
        elif agent_part.lower() == "growth":
            agent = GrowthHackerAgent()
            if action_part == "viral_ideas":
                return ", ".join(agent.generate_viral_ideas(params[0] if params else ""))
            if action_part == "map_funnel":
                return str(agent.map_aarrr_funnel(params[0] if params else ""))
            if action_part == "automation":
                return agent.suggest_automation(params[0] if params else "")
        elif agent_part.lower() == "copy":
            agent = CopywriterAgent()
            if action_part == "article":
                title = params[0] if params else "Untitled"
                keywords = params[1].split("|") if len(params) > 1 else []
                return agent.write_article(title, keywords)
            if action_part == "newsletter":
                subject = params[0] if params else "Newsletter"
                highlights = params[1].split("|") if len(params) > 1 else []
                return agent.write_newsletter(subject, highlights)
            if action_part == "social":
                platform = params[0] if params else "Twitter"
                message = params[1] if len(params) > 1 else ""
                hashtags = params[2].split("|") if len(params) > 2 else []
                return agent.write_social_post(platform, message, hashtags)
        return f"[ERROR] Unknown agent or action: {mission}"
    except Exception as e:
        return f"[EXCEPTION] {str(e)}"

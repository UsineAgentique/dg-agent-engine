import json

class CTOLeadArchitect:
    """Design des systèmes et scalabilité."""
    def handle(self, mission: str) -> str:
        # Placeholder implementation – real logic to be added later
        return f"[CTO] Mission reçue: {mission} – conception en cours."

class DevOpsCICDSpecialist:
    """Monitoring Render, Supabase et santé des pipelines."""
    def handle(self, mission: str) -> str:
        # Placeholder implementation – real logic to be added later
        return f"[DevOps] Mission reçue: {mission} – monitoring en cours."

class DataSecurityEngineer:
    """Intégrité des données Supabase et sécurité."""
    def handle(self, mission: str) -> str:
        # Placeholder implementation – real logic to be added later
        return f"[DataSec] Mission reçue: {mission} – audit en cours."

# Mapping des rôles aux classes
ROLE_MAP = {
    "cto": CTOLeadArchitect(),
    "devops": DevOpsCICDSpecialist(),
    "data_security": DataSecurityEngineer(),
}

def run_mission(mission: str) -> str:
    """Entrée unique du pôle technique.

    Le format attendu du paramètre `mission` est un JSON string contenant:
    {
        "role": "cto" | "devops" | "data_security",
        "task": "description de la tâche"
    }
    La fonction délègue la tâche au sous‑agent correspondant et renvoie sa réponse.
    """
    try:
        payload = json.loads(mission)
        role = payload.get("role")
        task = payload.get("task", "")
        if role not in ROLE_MAP:
            return f"[Erreur] Rôle inconnu: {role}. Rôles disponibles: {list(ROLE_MAP.keys())}"
        handler = ROLE_MAP[role]
        return handler.handle(task)
    except json.JSONDecodeError:
        return "[Erreur] Mission doit être un JSON valide avec les clés 'role' et 'task'."
    except Exception as e:
        return f"[Erreur] Exception inattendue: {str(e)}"

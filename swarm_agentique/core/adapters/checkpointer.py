"""Module de gestion de la persistance des checkpoints (mémoire à long terme)."""

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pathlib import Path

# Chemin absolu vers le fichier de base de données SQLite
DB_PATH = Path(__file__).resolve().parents[3] / "checkpoints.db"


def get_checkpointer() -> AsyncSqliteSaver:
    """
    Retourne une instance configurée de AsyncSqliteSaver connectée à swarm_agentique/checkpoints.db.
    
    Returns:
        AsyncSqliteSaver: Instance prête à l'emploi pour la persistance des états LangGraph.
    """
    # ensure directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return AsyncSqliteSaver.from_conn_string(str(DB_PATH))


# Instance singleton pour une utilisation directe si nécessaire
checkpointer = get_checkpointer()

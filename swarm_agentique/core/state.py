from typing import TypedDict, List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ArtifactType(str, Enum):
    """Types d'artifacts produits par les agents."""
    DOCUMENT = "document"
    CODE = "code"
    ANALYSIS = "analysis"
    REPORT = "report"
    DATA = "data"
    PLAN = "plan"
    DECISION = "decision"
    OTHER = "other"


class ArtifactRef(BaseModel):
    """Référence à un artifact produit par un agent."""
    id: str = Field(..., description="Identifiant unique de l'artifact")
    type: ArtifactType = Field(..., description="Type de l'artifact")
    title: str = Field(..., description="Titre descriptif")
    description: str = Field(default="", description="Description détaillée")
    content: Optional[str] = Field(default=None, description="Contenu textuel de l'artifact")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées additionnelles")
    created_by: str = Field(..., description="Agent créateur")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp de création")
    version: int = Field(default=1, description="Numéro de version")
    tags: List[str] = Field(default_factory=list, description="Tags pour recherche/filtrage")
    parent_id: Optional[str] = Field(default=None, description="ID de l'artifact parent si dérivé")

    class Config:
        use_enum_values = True


def merge_artifacts(existing: List[ArtifactRef], new: List[ArtifactRef]) -> List[ArtifactRef]:
    """
    Fusionne deux listes d'artifacts en dédupliquant par ID.
    Les nouveaux artifacts remplacent les existants s'ils ont le même ID.
    """
    artifact_map: Dict[str, ArtifactRef] = {}
    
    # Ajouter les artifacts existants
    for artifact in existing:
        artifact_map[artifact.id] = artifact
    
    # Remplacer/ajouter les nouveaux artifacts
    for artifact in new:
        artifact_map[artifact.id] = artifact
    
    return list(artifact_map.values())


class SwarmState(TypedDict):
    """État global partagé par tous les agents du swarm."""
    # Identité de la mission
    mission_id: str
    mission_objective: str
    mission_context: Dict[str, Any]
    
    # État d'exécution
    current_phase: str
    completed_phases: List[str]
    active_agents: List[str]
    
    # Artifacts produits
    artifacts: List[ArtifactRef]
    
    # Décisions et validations
    decisions: List[Dict[str, Any]]
    validations: List[Dict[str, Any]]
    
    # Métriques et monitoring
    metrics: Dict[str, Any]
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    
    # Configuration dynamique
    config: Dict[str, Any]
    
    # Historique d'exécution
    execution_log: List[Dict[str, Any]]
    
    # Timestamps
    created_at: str
    updated_at: str

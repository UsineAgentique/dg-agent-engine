"""
Contrats de base (Ports) pour l'architecture hexagonale du Swarm Agentique.

Définition des interfaces (Protocols/ABC) pour :
- LLMProvider : Abstraction multi-fournisseurs (OpenAI, Anthropic, Gemini, etc.)
- SecretProvider : Gestion étanche des clés API par rôle/agent
- ArtifactStore : Stockage d'artefacts (LocalFS, S3, GCS, etc.)
- Checkpointer : Persistance d'état (AsyncSqlite, Postgres, etc.)
- EventBus : Communication inter-nœuds asynchrone
"""
from __future__ import annotations

import abc
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Generic, Protocol, TypeVar, runtime_checkable
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")
R = TypeVar("R")


class Role(str, Enum):
    """Rôles canoniques du Swarm."""
    GOV = "GOV"
    FIN = "FIN"
    TECH = "TECH"
    SRC = "SRC"
    GRO = "GRO"
    SAL = "SAL"
    RAD = "RAD"
    RET = "RET"
    MED = "MED"
    DEV = "DEV"  # Agent développeur secondaire
    DG = "DG"    # Directrice Générale (Amal)


class ModelProvider(str, Enum):
    """Fournisseurs LLM supportés."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    MISTRAL = "mistral"
    OLLAMA = "ollama"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """Configuration immuable d'un modèle LLM."""
    provider: ModelProvider
    model_name: str
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.2
    max_tokens: int | None = 4096
    timeout_seconds: float = 60.0
    extra_params: dict[str, Any] = field(default_factory=dict)


class LLMMessage(BaseModel):
    """Message standardisé pour l'API LLM."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    role: str  # system, user, assistant, tool
    content: str | list[dict[str, Any]]
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class LLMResponse(BaseModel):
    """Réponse standardisée d'un LLM."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    usage: dict[str, int] | None = None
    model: str
    finish_reason: str | None = None


@runtime_checkable
class LLMProvider(Protocol):
    """Port : Fournisseur LLM unifié (multi-vendor).
    
    L'Agent Dev utilise son propre provider (ex: Anthropic/Claude),
    Amal-DG utilise le sien (ex: OpenAI/Gemini).
    L'injection se fait via SecretProvider.
    """
    
    @property
    def config(self) -> ModelConfig: ...
    
    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse: ...
    
    async def stream_complete(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]: ...
    
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


@runtime_checkable
class SecretProvider(Protocol):
    """Port : Fournisseur de secrets étanche par rôle.
    
    Garantit l'isolation budgétaire et sécuritaire :
    - Agent Dev ne voit que ses clés (ex: ANTHROPIC_API_KEY)
    - Amal-DG ne voit que les siennes (ex: OPENAI_API_KEY, GEMINI_API_KEY)
    - Rotation, audit, expiration automatiques.
    """
    
    async def get_llm_config(self, role: Role) -> ModelConfig: ...
    
    async def get_secret(self, key: str, role: Role) -> str | None: ...
    
    async def set_secret(self, key: str, value: str, role: Role, ttl_seconds: int | None = None) -> None: ...
    
    async def list_keys(self, role: Role) -> list[str]: ...
    
    async def revoke(self, key: str, role: Role) -> bool: ...


class ArtifactRef(BaseModel):
    """Référence immuable vers un artefact stocké."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    artifact_id: UUID = Field(default_factory=uuid4)
    name: str
    mime_type: str
    size_bytes: int
    storage_path: str  # Chemin relatif dans le store
    checksum_sha256: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: set[str] = Field(default_factory=set)


@runtime_checkable
class ArtifactStore(Protocol):
    """Port : Stockage d'artefacts (fichiers, binaires, datasets).
    
    Implémentations : LocalFSArtifactStore, S3ArtifactStore, GCSArtifactStore.
    """
    
    async def put(
        self,
        content: bytes,
        name: str,
        mime_type: str,
        metadata: dict[str, Any] | None = None,
        tags: set[str] | None = None,
    ) -> ArtifactRef: ...
    
    async def get(self, artifact_id: UUID) -> bytes: ...
    
    async def get_ref(self, artifact_id: UUID) -> ArtifactRef: ...
    
    async def delete(self, artifact_id: UUID) -> bool: ...
    
    async def list(
        self,
        prefix: str = "",
        tags: set[str] | None = None,
        limit: int = 100,
    ) -> list[ArtifactRef]: ...
    
    async def exists(self, artifact_id: UUID) -> bool: ...


class Checkpoint(BaseModel, Generic[T]):
    """Point de contrôle d'exécution (state + metadata)."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    checkpoint_id: UUID = Field(default_factory=uuid4)
    thread_id: str
    state: T
    step: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
    parent_checkpoint_id: UUID | None = None


@runtime_checkable
class Checkpointer(Protocol, Generic[T]):
    """Port : Persistance d'état (checkpointing) pour reprise/crash-recovery.
    
    Implémentations : AsyncSqliteCheckpointer, PostgresCheckpointer.
    """
    
    async def put(self, checkpoint: Checkpoint[T]) -> None: ...
    
    async def get(self, thread_id: str, checkpoint_id: UUID | None = None) -> Checkpoint[T] | None: ...
    
    async def list(self, thread_id: str, limit: int = 10) -> list[Checkpoint[T]]: ...
    
    async def delete_thread(self, thread_id: str) -> int: ...


class Event(BaseModel, Generic[T]):
    """Événement du bus de messages inter-nœuds."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    source_role: Role
    target_roles: set[Role] = Field(default_factory=set)  # Vide = broadcast
    payload: T
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: UUID | None = None
    reply_to: UUID | None = None


@runtime_checkable
class EventBus(Protocol):
    """Port : Bus d'événements asynchrone (pub/sub).
    
    Permet la communication découplée entre nœuds du graphe.
    """
    
    async def publish(self, event: Event[Any]) -> None: ...
    
    async def subscribe(self, event_type: str, role: Role) -> AsyncIterator[Event[Any]]: ...
    
    async def request_response(
        self,
        event: Event[T],
        timeout: float = 30.0,
    ) -> Event[R] | None: ...


class ToolSpec(BaseModel):
    """Spécification d'un outil (function calling)."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    required: list[str] = Field(default_factory=list)
    returns: dict[str, Any] | None = None
    is_async: bool = True
    timeout_seconds: float = 30.0
    idempotent: bool = False


@runtime_checkable
class ToolRegistry(Protocol):
    """Port : Registre d'outils dynamiques par pôle."""
    
    def register(self, spec: ToolSpec, handler: callable) -> None: ...
    
    def unregister(self, name: str) -> bool: ...
    
    def get(self, name: str) -> tuple[ToolSpec, callable] | None: ...
    
    def list_for_role(self, role: Role) -> list[ToolSpec]: ...
    
    async def execute(self, name: str, args: dict[str, Any], context: dict[str, Any] | None = None) -> Any: ...


# Export public
__all__ = [
    "Role",
    "ModelProvider",
    "ModelConfig",
    "LLMMessage",
    "LLMResponse",
    "LLMProvider",
    "SecretProvider",
    "ArtifactRef",
    "ArtifactStore",
    "Checkpoint",
    "Checkpointer",
    "Event",
    "EventBus",
    "ToolSpec",
    "ToolRegistry",
]
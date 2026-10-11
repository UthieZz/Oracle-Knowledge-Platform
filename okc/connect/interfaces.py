"""Minimal OKP Connect contract.

One contract covering: auth, initial sync, incremental updates, deletion,
permissions, retries, health. Implementations live outside the core.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol


class HealthStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass
class SyncEvent:
    """Durable, idempotent event for the sync engine."""
    event_id: str
    source: str
    kind: str  # create, update, delete, permission_change
    cursor: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    occurred_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    tenant_id: str = ""
    silo_id: str = ""


class Connector(ABC):
    """Replaceable integration. Must not mutate Knowledge Core directly."""

    name: str
    version: str = "1.0.0"

    @abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Establish or refresh auth. Returns True on success."""
        ...

    @abstractmethod
    def initial_sync(self, tenant_id: str, silo_id: str) -> List[SyncEvent]:
        """Full initial pull. Must be resumable via cursor."""
        ...

    @abstractmethod
    def incremental_sync(self, cursor: str, tenant_id: str, silo_id: str) -> List[SyncEvent]:
        """Delta since cursor. Idempotent."""
        ...

    @abstractmethod
    def handle_deletion(self, object_id: str, tenant_id: str, silo_id: str) -> SyncEvent:
        """Propagate source deletion."""
        ...

    @abstractmethod
    def permissions(self, object_id: str) -> Dict[str, Any]:
        """Current permission snapshot for the object."""
        ...

    @abstractmethod
    def health(self) -> HealthStatus:
        """Connection health for admin panel."""
        ...

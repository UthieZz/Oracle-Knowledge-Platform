"""Minimal stub connector for proving the OKP Connect lifecycle.

In-memory documents only. Emits SyncEvents; never writes KnowledgePackage.
"""
from __future__ import annotations

from typing import Any, Dict, List

from okc.connect.interfaces import Connector, HealthStatus, SyncEvent


class StubConnector(Connector):
    """Replaceable stub that yields create events from an in-memory list."""

    name = "stub"
    version = "0.1.0"

    def __init__(self, documents: List[Dict[str, str]]) -> None:
        self.documents = documents  # [{"id": "...", "text": "..."}]
        self._authenticated = False

    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        self._authenticated = True
        return True

    def initial_sync(self, tenant_id: str, silo_id: str) -> List[SyncEvent]:
        if not self._authenticated:
            raise RuntimeError("not authenticated")
        events: List[SyncEvent] = []
        for i, doc in enumerate(self.documents):
            events.append(
                SyncEvent(
                    event_id=f"stub-{doc['id']}",
                    source=self.name,
                    kind="create",
                    cursor=str(i + 1),
                    payload={"text": doc["text"], "object_id": doc["id"]},
                    tenant_id=tenant_id,
                    silo_id=silo_id,
                )
            )
        return events

    def incremental_sync(self, cursor: str, tenant_id: str, silo_id: str) -> List[SyncEvent]:
        # Stub has no deltas after initial.
        return []

    def handle_deletion(self, object_id: str, tenant_id: str, silo_id: str) -> SyncEvent:
        return SyncEvent(
            event_id=f"stub-del-{object_id}",
            source=self.name,
            kind="delete",
            payload={"object_id": object_id},
            tenant_id=tenant_id,
            silo_id=silo_id,
        )

    def permissions(self, object_id: str) -> Dict[str, Any]:
        return {"read": True, "object_id": object_id}

    def health(self) -> HealthStatus:
        return HealthStatus.OK if self._authenticated else HealthStatus.DEGRADED

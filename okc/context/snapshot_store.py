"""Immutable Evidence Snapshot Store.

Locked contracts: design/context-aware-reasoning/
I-10: Evidence retrieval creates a new evidence snapshot.
Snapshots are immutable. Store never mutates existing snapshots.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class EvidenceSnapshot(BaseModel):
    """Immutable evidence snapshot for a query context revision.

    Content is a frozen reference set. New retrieval produces a new snapshot.
    """

    snapshot_id: str
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    parent_snapshot_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = {"frozen": True}


class EvidenceSnapshotStore:
    """Owns immutable evidence snapshots.

    create_snapshot always produces a new object. get returns the original.
    No update or delete methods.
    """

    def __init__(self) -> None:
        self._snapshots: Dict[str, EvidenceSnapshot] = {}

    def create_snapshot(
        self,
        snapshot_id: str,
        evidence_refs: Optional[List[str]] = None,
        parent_snapshot_id: Optional[str] = None,
    ) -> EvidenceSnapshot:
        if snapshot_id in self._snapshots:
            raise ValueError(f"Snapshot {snapshot_id} already exists; snapshots are immutable")
        snap = EvidenceSnapshot(
            snapshot_id=snapshot_id,
            evidence_refs=tuple(evidence_refs or []),
            parent_snapshot_id=parent_snapshot_id,
        )
        self._snapshots[snapshot_id] = snap
        return snap

    def get(self, snapshot_id: str) -> Optional[EvidenceSnapshot]:
        return self._snapshots.get(snapshot_id)

    def exists(self, snapshot_id: str) -> bool:
        return snapshot_id in self._snapshots

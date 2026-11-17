"""Query Context Engine — envelope revision management.

Locked contracts: design/context-aware-reasoning/
Assumptions never auto-promote. New revisions preserve lineage.
Orchestrator must not contain domain logic; this engine owns envelope state transitions.
Evidence retrieval (I-10) creates a new immutable snapshot when a store is attached.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from okc.context.models import (
    ParameterStatus,
    QueryContextEnvelope,
    QueryParameter,
)
from okc.context.snapshot_store import EvidenceSnapshotStore


class QueryContextEngine:
    """Manages QueryContextEnvelope lifecycle: creation, revision, assumption application.

    Does not promote assumptions to resolved status. Promotion requires explicit
    user confirmation (source=\"user\") or new evidence supplied by caller.
    When an EvidenceSnapshotStore is provided, promote_with_evidence always
    creates a fresh immutable snapshot (I-10).
    """

    def __init__(self, snapshot_store: Optional[EvidenceSnapshotStore] = None) -> None:
        self._snapshot_store = snapshot_store

    def create_envelope(
        self,
        envelope_id: str,
        query_id: str,
        package_ref: str,
        parameters: Optional[Dict[str, QueryParameter]] = None,
    ) -> QueryContextEnvelope:
        return QueryContextEnvelope(
            envelope_id=envelope_id,
            revision=1,
            parent_revision=None,
            query_id=query_id,
            package_ref=package_ref,
            parameters=parameters or {},
        )

    def create_revision(
        self,
        parent: QueryContextEnvelope,
        updated_parameters: Optional[Dict[str, QueryParameter]] = None,
        evidence_set_ref: Optional[str] = None,
    ) -> QueryContextEnvelope:
        """Create immutable child revision. Parent lineage preserved.

        Parameters are copied; caller supplies any deliberate updates.
        No automatic status changes.
        """
        new_params = dict(parent.parameters)
        if updated_parameters:
            new_params.update(updated_parameters)
        return QueryContextEnvelope(
            envelope_id=parent.envelope_id,
            revision=parent.revision + 1,
            parent_revision=parent.revision,
            query_id=parent.query_id,
            package_ref=parent.package_ref,
            parameters=new_params,
            evidence_set_ref=evidence_set_ref or parent.evidence_set_ref,
        )

    def apply_assumption(
        self,
        envelope: QueryContextEnvelope,
        dimension_id: str,
        assumed_value: Any,
    ) -> QueryContextEnvelope:
        """Apply a disclosed assumption without promoting status to RESOLVED.

        Returns a new revision. Original assumption remains visible.
        Status stays MISSING or PARTIALLY_RESOLVED unless already higher.
        """
        current = envelope.parameters.get(dimension_id)
        if current is None:
            new_param = QueryParameter(
                dimension_id=dimension_id,
                status=ParameterStatus.MISSING,
                assumption=assumed_value,
                source="assumption",
            )
        else:
            # Preserve existing status; never auto-upgrade from assumption alone
            new_status = current.status
            if new_status == ParameterStatus.RESOLVED:
                # Already resolved; assumption does not override
                new_status = ParameterStatus.RESOLVED
            new_param = QueryParameter(
                dimension_id=dimension_id,
                status=new_status,
                value=current.value,
                assumption=assumed_value,
                source="assumption",
            )
        updated = {dimension_id: new_param}
        return self.create_revision(envelope, updated)

    def promote_with_user_confirmation(
        self,
        envelope: QueryContextEnvelope,
        dimension_id: str,
        confirmed_value: Any,
    ) -> QueryContextEnvelope:
        """Explicit user confirmation promotes to RESOLVED. New revision."""
        new_param = QueryParameter(
            dimension_id=dimension_id,
            status=ParameterStatus.RESOLVED,
            value=confirmed_value,
            source="user",
        )
        return self.create_revision(envelope, {dimension_id: new_param})

    def promote_with_evidence(
        self,
        envelope: QueryContextEnvelope,
        dimension_id: str,
        evidence_value: Any,
        evidence_set_ref: Optional[str] = None,
        evidence_refs: Optional[list[str]] = None,
    ) -> QueryContextEnvelope:
        """New evidence promotes to RESOLVED.

        If a snapshot store is attached, always creates a new immutable snapshot
        (I-10) and uses its id as evidence_set_ref. Caller-supplied evidence_set_ref
        is treated as a preferred snapshot id only when the store accepts it.
        Without a store, the supplied evidence_set_ref is used as-is (backward compatible).
        """
        new_param = QueryParameter(
            dimension_id=dimension_id,
            status=ParameterStatus.RESOLVED,
            value=evidence_value,
            source="evidence",
        )

        snapshot_id: Optional[str] = evidence_set_ref
        if self._snapshot_store is not None:
            # Always create a fresh snapshot on retrieval/evidence application
            preferred_id = evidence_set_ref or f"snap-{envelope.envelope_id}-{envelope.revision + 1}"
            # If preferred id already exists, append a suffix to guarantee new snapshot
            candidate = preferred_id
            suffix = 0
            while self._snapshot_store.exists(candidate):
                suffix += 1
                candidate = f"{preferred_id}-{suffix}"
            snap = self._snapshot_store.create_snapshot(
                snapshot_id=candidate,
                evidence_refs=evidence_refs or [],
                parent_snapshot_id=envelope.evidence_set_ref,
            )
            snapshot_id = snap.snapshot_id

        return self.create_revision(
            envelope, {dimension_id: new_param}, evidence_set_ref=snapshot_id
        )

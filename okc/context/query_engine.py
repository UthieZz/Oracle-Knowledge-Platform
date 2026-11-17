"""Query Context Engine — envelope revision management.

Locked contracts: design/context-aware-reasoning/
Assumptions never auto-promote. New revisions preserve lineage.
Orchestrator must not contain domain logic; this engine owns envelope state transitions.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from okc.context.models import (
    ParameterStatus,
    QueryContextEnvelope,
    QueryParameter,
)


class QueryContextEngine:
    """Manages QueryContextEnvelope lifecycle: creation, revision, assumption application.

    Does not promote assumptions to resolved status. Promotion requires explicit
    user confirmation (source=\"user\") or new evidence supplied by caller.
    """

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
        evidence_set_ref: str,
    ) -> QueryContextEnvelope:
        """New evidence promotes to RESOLVED. Creates new snapshot ref and revision."""
        new_param = QueryParameter(
            dimension_id=dimension_id,
            status=ParameterStatus.RESOLVED,
            value=evidence_value,
            source="evidence",
        )
        return self.create_revision(
            envelope, {dimension_id: new_param}, evidence_set_ref=evidence_set_ref
        )

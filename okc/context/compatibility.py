"""Evidence Compatibility Engine.

Classification is per-dimension, never global.
Affordance eligibility produced only here.
Orchestrator contains no domain business logic.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from okc.context.models import (
    AffordanceAvailability,
    CompatibilityState,
    ExpansionAffordance,
    ParameterStatus,
    QueryContextEnvelope,
)
from okc.context.registry import ContextRegistry


class EvidenceSpanConstraint(BaseModel):
    """Grounded context_constraints on an evidence span."""

    span_id: str
    constraints: Dict[str, Any] = Field(default_factory=dict)


class EvidenceCompatibilityEngine:
    def __init__(self, registry: ContextRegistry) -> None:
        self.registry = registry

    def classify(
        self,
        span_constraints: Dict[str, Any],
        dimension_id: str,
        target_value: Any,
    ) -> CompatibilityState:
        """Per-dimension classification. B1-B5."""
        if dimension_id not in span_constraints:
            return CompatibilityState.UNCONSTRAINED
        constraint = span_constraints[dimension_id]
        if constraint is None:
            return CompatibilityState.UNCONSTRAINED
        if constraint == target_value:
            return CompatibilityState.FULLY_COMPATIBLE
        if isinstance(constraint, list) and target_value in constraint:
            return CompatibilityState.PARTIALLY_COMPATIBLE
        return CompatibilityState.INCOMPATIBLE

    def generate_affordances(
        self,
        envelope: QueryContextEnvelope,
        evidence_spans: List[Dict[str, Any]],
        retrieval_paths: Optional[Dict[str, str]] = None,
    ) -> List[ExpansionAffordance]:
        """D1-D5. Only available/retrievable emitted."""
        affordances: List[ExpansionAffordance] = []
        retrieval_paths = retrieval_paths or {}
        for dim_id, param in envelope.parameters.items():
            if param.status == ParameterStatus.RESOLVED:
                continue
            candidate = param.value if param.value is not None else "candidate"
            supporting = [
                s
                for s in evidence_spans
                if self.classify(s.get("constraints", {}), dim_id, candidate)
                == CompatibilityState.FULLY_COMPATIBLE
            ]
            if supporting:
                affordances.append(
                    ExpansionAffordance(
                        affordance_id=f"aff-{envelope.envelope_id}-{dim_id}-reuse",
                        dimension_id=dim_id,
                        target_value=candidate,
                        availability=AffordanceAvailability.AVAILABLE,
                        effect="add_evidence",
                        source_envelope_id=envelope.envelope_id,
                        source_revision=envelope.revision,
                        evidence_set_ref=envelope.evidence_set_ref,
                    )
                )
            elif dim_id in retrieval_paths:
                affordances.append(
                    ExpansionAffordance(
                        affordance_id=f"aff-{envelope.envelope_id}-{dim_id}-retrieve",
                        dimension_id=dim_id,
                        target_value=candidate,
                        availability=AffordanceAvailability.RETRIEVABLE,
                        effect="add_evidence",
                        source_envelope_id=envelope.envelope_id,
                        source_revision=envelope.revision,
                        cost="defined_path",
                    )
                )
            # unsupported never emitted
        return affordances

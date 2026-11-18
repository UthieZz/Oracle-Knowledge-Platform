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
        """D1-D5. Only available/retrievable emitted.

        For unresolved dimensions, emit one AVAILABLE affordance per distinct
        fully-specified constrained value observed in the evidence spans.
        This makes both (or all) well-supported alternatives eligible when a
        conflict exists and no domain rule has resolved it (C4). No majority
        or provenance override is applied (C3).
        """
        affordances: List[ExpansionAffordance] = []
        retrieval_paths = retrieval_paths or {}
        # Pre-collect distinct constrained values per dimension
        observed: Dict[str, set] = {}
        for span in evidence_spans:
            constraints = span.get("constraints") or {}
            for dim_id, value in constraints.items():
                if value is None or isinstance(value, list):
                    continue
                observed.setdefault(dim_id, set()).add(value)

        for dim_id, param in envelope.parameters.items():
            if param.status == ParameterStatus.RESOLVED:
                continue
            # C4: when multiple distinct constrained values exist (conflict, no rule applied),
            # emit one AVAILABLE affordance for each. No silent selection (C3).
            # Otherwise preserve original single-candidate / retrieval path (D1/D2).
            candidates = sorted(observed.get(dim_id, set()))
            emitted_any = False
            if len(candidates) > 1:
                for candidate in candidates:
                    supporting = [
                        s
                        for s in evidence_spans
                        if self.classify(s.get("constraints", {}), dim_id, candidate)
                        == CompatibilityState.FULLY_COMPATIBLE
                    ]
                    if supporting:
                        affordances.append(
                            ExpansionAffordance(
                                affordance_id=f"aff-{envelope.envelope_id}-{dim_id}-{candidate}",
                                dimension_id=dim_id,
                                target_value=candidate,
                                availability=AffordanceAvailability.AVAILABLE,
                                effect="add_evidence",
                                source_envelope_id=envelope.envelope_id,
                                source_revision=envelope.revision,
                                evidence_set_ref=envelope.evidence_set_ref,
                            )
                        )
                        emitted_any = True
            # Fallback single candidate path (no conflict, or no multi-values)
            if not emitted_any:
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

    def detect_simple_conflicts(
        self,
        evidence_spans: List[Dict[str, Any]],
        dimension_ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Detect dimensions with multiple distinct constrained values across spans.

        Returns dimension_ids that have conflicting fully-specified constraints.
        No domain rules applied; no silent winner. Unconstrained spans ignored.
        Caller (orchestrator) may pass result to Answer Stage for disclosure.
        """
        if not evidence_spans:
            return []
        observed: Dict[str, set] = {}
        for span in evidence_spans:
            constraints = span.get("constraints") or {}
            for dim_id, value in constraints.items():
                if dimension_ids is not None and dim_id not in dimension_ids:
                    continue
                if value is None:
                    continue
                # Treat list constraints as potential partial; collect only scalar for conflict
                if isinstance(value, list):
                    continue
                observed.setdefault(dim_id, set()).add(value)
        return sorted(dim for dim, vals in observed.items() if len(vals) > 1)

    def apply_simple_domain_rules(
        self,
        conflicts: List[str],
        evidence_spans: List[Dict[str, Any]],
        domain_rules: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """Apply optional domain rules to simple conflicts (C2).

        domain_rules: {dimension_id: {"preferred_value": Any, "rationale": str}}
        Only applies when preferred_value is among the observed conflicting values.
        Returns {dim_id: {"resolved_value": ..., "rationale": ..., "preserved_values": set}}
        Does not invent values; preserves all conflicting evidence. No silent override.
        """
        if not conflicts or not domain_rules:
            return {}
        observed: Dict[str, set] = {}
        for span in evidence_spans:
            constraints = span.get("constraints") or {}
            for dim_id, value in constraints.items():
                if dim_id not in conflicts or value is None or isinstance(value, list):
                    continue
                observed.setdefault(dim_id, set()).add(value)

        resolutions: Dict[str, Dict[str, Any]] = {}
        for dim_id in conflicts:
            rule = domain_rules.get(dim_id)
            if not rule:
                continue
            preferred = rule.get("preferred_value")
            rationale = rule.get("rationale", "domain rule applied")
            vals = observed.get(dim_id, set())
            if preferred in vals:
                resolutions[dim_id] = {
                    "resolved_value": preferred,
                    "rationale": rationale,
                    "preserved_values": vals,
                }
        return resolutions


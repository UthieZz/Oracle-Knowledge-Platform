"""Minimal Answer Stage.

Converts resolved query context + compatible evidence into structured grounded answer.
Does not redefine dimensions, change envelope statuses, invent evidence/provenance,
resolve conflicts independently, generate unsupported expansions, or mutate packages/snapshots.

Locked: design/context-aware-reasoning/03-answer-stage-contract.md
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from okc.context.models import (
    ExpansionAffordance,
    ParameterStatus,
    QueryContextEnvelope,
    Sensitivity,
)
from okc.context.registry import ContextRegistry


class Claim(BaseModel):
    text: str
    support_status: str  # supported | partial | background | conflicted | assumption
    evidence_refs: List[str] = Field(default_factory=list)


class AnswerContent(BaseModel):
    content: str
    scope: str = "query-scoped"
    qualifications: List[str] = Field(default_factory=list)
    claims: List[Claim] = Field(default_factory=list)


class AnswerContext(BaseModel):
    envelope_id: str
    revision: int
    applied_assumptions: List[Dict[str, Any]] = Field(default_factory=list)
    unresolved_dimensions: List[str] = Field(default_factory=list)
    conflicted_dimensions: List[str] = Field(default_factory=list)
    unavailable_dimensions: List[str] = Field(default_factory=list)


class AnswerEvidence(BaseModel):
    supporting_refs: List[str] = Field(default_factory=list)
    background_refs: List[str] = Field(default_factory=list)
    partial_support_refs: List[str] = Field(default_factory=list)
    conflicting_refs: List[str] = Field(default_factory=list)


class Completion(BaseModel):
    answer_delivered: bool
    contextually_complete: bool
    reason: Optional[str] = None


class AnswerResult(BaseModel):
    answer_id: str
    query_id: str
    answer: AnswerContent
    context: AnswerContext
    evidence: AnswerEvidence
    expansion_affordances: List[ExpansionAffordance]
    completion: Completion


class AnswerStage:
    """Minimal deterministic Answer Stage."""

    def __init__(self, registry: ContextRegistry) -> None:
        self.registry = registry

    def produce(
        self,
        envelope: QueryContextEnvelope,
        affordances: List[ExpansionAffordance],
        evidence_summary: Optional[Dict[str, List[str]]] = None,
        conflicts: Optional[List[str]] = None,
        rule_resolutions: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> AnswerResult:
        evidence_summary = evidence_summary or {}
        conflicts = conflicts or []
        rule_resolutions = rule_resolutions or {}

        # Context disclosure
        applied = []
        unresolved = []
        for dim_id, param in envelope.parameters.items():
            if param.assumption is not None:
                applied.append({
                    "dimension_id": dim_id,
                    "assumption": param.assumption,
                    "source": param.source or "assumption",
                })
            dim = self.registry.get(dim_id)
            if dim and dim.sensitivity == Sensitivity.HIGH:
                if param.status in (ParameterStatus.MISSING, ParameterStatus.PARTIALLY_RESOLVED):
                    unresolved.append(dim_id)

        contextually_complete = len(unresolved) == 0 and len(conflicts) == 0

        # Minimal useful answer when any evidence or assumption exists
        has_material = (
            bool(evidence_summary.get("supporting"))
            or bool(evidence_summary.get("partial"))
            or bool(applied)
            or any(p.status == ParameterStatus.RESOLVED for p in envelope.parameters.values())
        )
        answer_delivered = has_material

        claims = []
        content_parts = []
        if applied:
            for a in applied:
                claims.append(
                    Claim(
                        text=f"Assuming {a['dimension_id']}={a['assumption']} (assumption)",
                        support_status="assumption",
                    )
                )
                content_parts.append(f"Under assumption {a['dimension_id']}={a['assumption']}")
        if evidence_summary.get("supporting"):
            claims.append(
                Claim(
                    text="Primary findings supported by compatible evidence",
                    support_status="supported",
                    evidence_refs=evidence_summary["supporting"],
                )
            )
            content_parts.append("Supported findings available.")
        if evidence_summary.get("partial"):
            claims.append(
                Claim(
                    text="Partial support from partially-compatible evidence (qualification required)",
                    support_status="partial",
                    evidence_refs=evidence_summary["partial"],
                )
            )
            content_parts.append("Partial findings available with qualification.")
        if evidence_summary.get("background"):
            claims.append(
                Claim(
                    text="Background context from unconstrained evidence (not used to establish dimensions)",
                    support_status="background",
                    evidence_refs=evidence_summary["background"],
                )
            )
        # Disclose domain-rule resolutions (C2) while preserving that conflict existed
        for dim_id, res in rule_resolutions.items():
            claims.append(
                Claim(
                    text=f"Resolved {dim_id}={res['resolved_value']} via domain rule: {res['rationale']} (conflicting values retained: {res['preserved_values']})",
                    support_status="supported",
                )
            )
            content_parts.append(f"Domain rule applied to {dim_id}")
        if not content_parts:
            content_parts.append("No material evidence or assumptions for a useful answer.")

        qualifications = []
        if unresolved:
            qualifications.append(f"Unresolved high-sensitivity dimensions: {', '.join(unresolved)}")
        if conflicts:
            qualifications.append(f"Conflicts retained: {', '.join(conflicts)}")
        if evidence_summary.get("partial"):
            qualifications.append("Partial compatibility disclosed; not full substantiation.")
        if rule_resolutions:
            quals = [f"{d}: {r['rationale']}" for d, r in rule_resolutions.items()]
            qualifications.append(f"Domain rules applied: {'; '.join(quals)}")

        reason = None
        if not answer_delivered:
            reason = "insufficient_evidence"
        elif not contextually_complete:
            if unresolved:
                reason = "unresolved_high_sensitivity"
            elif conflicts:
                reason = "conflicts_retained"
            else:
                reason = "context_incomplete"

        return AnswerResult(
            answer_id=f"ans-{envelope.envelope_id}-r{envelope.revision}",
            query_id=envelope.query_id,
            answer=AnswerContent(
                content="; ".join(content_parts),
                qualifications=qualifications,
                claims=claims,
            ),
            context=AnswerContext(
                envelope_id=envelope.envelope_id,
                revision=envelope.revision,
                applied_assumptions=applied,
                unresolved_dimensions=unresolved,
                conflicted_dimensions=conflicts,
            ),
            evidence=AnswerEvidence(
                supporting_refs=evidence_summary.get("supporting", []),
                background_refs=evidence_summary.get("background", []),
                partial_support_refs=evidence_summary.get("partial", []),
                conflicting_refs=evidence_summary.get("conflicting", []),
            ),
            expansion_affordances=affordances,  # pre-authorized only; no mutation
            completion=Completion(
                answer_delivered=answer_delivered,
                contextually_complete=contextually_complete,
                reason=reason,
            ),
        )

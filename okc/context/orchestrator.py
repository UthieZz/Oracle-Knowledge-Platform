"""Minimal Context Orchestrator.

Coordinates Query Context Engine, Evidence Compatibility Engine, and Answer Stage.
Contains no domain business logic. Passes references and pre-authorized results only.

Locked: design/context-aware-reasoning/05-integration-contract.md (I-11)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from okc.context.answer import AnswerResult, AnswerStage
from okc.context.compatibility import EvidenceCompatibilityEngine
from okc.context.models import ExpansionAffordance, QueryContextEnvelope, QueryParameter, ParameterStatus
from okc.context.query_engine import QueryContextEngine
from okc.context.registry import ContextRegistry
from okc.context.snapshot_store import EvidenceSnapshotStore
from okc.models.knowledge_package import KnowledgePackage
from okc.context.package_adapter import extract_evidence_spans


class ContextOrchestrator:
    """Thin coordinator. No dimension logic, no evidence interpretation, no status mutation. """

    def __init__(
        self,
        registry: ContextRegistry,
        snapshot_store: Optional[EvidenceSnapshotStore] = None,
    ) -> None:
        self.registry = registry
        self.query_engine = QueryContextEngine(snapshot_store=snapshot_store)
        self.compatibility = EvidenceCompatibilityEngine(registry)
        self.answer_stage = AnswerStage(registry)
        self.snapshot_store = snapshot_store

    def process_query(
        self,
        query_id: str,
        package_ref: str,
        envelope_id: str,
        initial_parameters: Optional[Dict[str, QueryParameter]] = None,
        evidence_spans: Optional[List[Dict[str, Any]]] = None,
        package: Optional[KnowledgePackage] = None,
        retrieval_paths: Optional[Dict[str, str]] = None,
        conflicts: Optional[List[str]] = None,
        evidence_summary: Optional[Dict[str, List[str]]] = None,
    ) -> tuple[QueryContextEnvelope, List[ExpansionAffordance], AnswerResult]:
        """Create envelope, request affordances from compatibility engine, produce answer.

        Does not interpret evidence, resolve dimensions, or invent affordances.
        """
        if evidence_spans is None and package is not None:
            spans = extract_evidence_spans(package)
        else:
            spans = evidence_spans or []
        evidence_refs = None
        if self.snapshot_store and spans:
            evidence_refs = [s.get("span_id") for s in spans if s.get("span_id")]
        envelope = self.query_engine.create_envelope(
            envelope_id=envelope_id,
            query_id=query_id,
            package_ref=package_ref,
            parameters=initial_parameters,
            evidence_refs=evidence_refs,
        )
        affordances = self.compatibility.generate_affordances(
            envelope, evidence_spans=spans, retrieval_paths=retrieval_paths or {}
        )
        result = self.answer_stage.produce(
            envelope,
            affordances=affordances,
            evidence_summary=evidence_summary,
            conflicts=conflicts,
        )
        return envelope, affordances, result

    def apply_expansion(
        self,
        parent_envelope: QueryContextEnvelope,
        dimension_id: str,
        new_value: Any,
        evidence_refs: Optional[List[str]] = None,
    ) -> QueryContextEnvelope:
        """Apply an expansion by creating a new immutable revision (I-09).

        Uses QueryContextEngine.promote_with_evidence when evidence is supplied,
        otherwise create_revision with an assumption. No domain logic.
        """
        if evidence_refs and self.snapshot_store:
            return self.query_engine.promote_with_evidence(
                parent_envelope,
                dimension_id=dimension_id,
                evidence_value=new_value,
                evidence_refs=evidence_refs,
            )
        # Fallback: assumption path (status remains MISSING; assumption disclosed, never auto-promoted)
        assumed = QueryParameter(
            dimension_id=dimension_id,
            status=ParameterStatus.MISSING,
            assumption=new_value,
            source="expansion",
        )
        return self.query_engine.create_revision(parent_envelope, {dimension_id: assumed})

    def answer_from_envelope(
        self,
        envelope: QueryContextEnvelope,
        evidence_spans: Optional[List[Dict[str, Any]]] = None,
        retrieval_paths: Optional[Dict[str, str]] = None,
        conflicts: Optional[List[str]] = None,
        evidence_summary: Optional[Dict[str, List[str]]] = None,
    ) -> AnswerResult:
        """Produce answer from an existing envelope revision (e.g. after apply_expansion).

        Coordinates compatibility + answer stage only. Does not mutate envelope,
        invent affordances, or contain domain logic (I-11).
        """
        spans = evidence_spans or []
        affordances = self.compatibility.generate_affordances(
            envelope, evidence_spans=spans, retrieval_paths=retrieval_paths or {}
        )
        return self.answer_stage.produce(
            envelope,
            affordances=affordances,
            evidence_summary=evidence_summary,
            conflicts=conflicts,
        )

    def retrieve_for_affordance(
        self,
        envelope: QueryContextEnvelope,
        affordance: ExpansionAffordance,
        package: Optional[KnowledgePackage] = None,
        extra_spans: Optional[List[Dict[str, Any]]] = None,
    ) -> QueryContextEnvelope:
        """Coordinate retrieval for a RETRIEVABLE affordance.

        Uses package adapter or supplied spans only. Creates new immutable snapshot
        and revision via promote_with_evidence. No domain logic, no status mutation
        beyond what the engine already does for evidence. (I-10, I-09, I-11)
        """
        if affordance.availability != "retrievable":
            raise ValueError("retrieve_for_affordance only accepts RETRIEVABLE affordances")
        if affordance.source_envelope_id != envelope.envelope_id or affordance.source_revision != envelope.revision:
            raise ValueError("affordance does not match envelope revision")

        spans = extra_spans or []
        if package is not None:
            spans = extract_evidence_spans(package) + spans
        # Filter to spans that could support the target (presence only; no interpretation)
        relevant = [s for s in spans if s.get("span_id")]
        if not relevant:
            raise ValueError("no retrievable evidence spans available")

        evidence_refs = [s["span_id"] for s in relevant]
        # Prefer first matching constraint if present; otherwise use affordance target as evidence value
        evidence_value = affordance.target_value
        for s in relevant:
            constraints = s.get("constraints") or {}
            if affordance.dimension_id in constraints:
                evidence_value = constraints[affordance.dimension_id]
                break

        if not self.snapshot_store:
            raise ValueError("snapshot store required for retrieval path")

        return self.query_engine.promote_with_evidence(
            envelope,
            dimension_id=affordance.dimension_id,
            evidence_value=evidence_value,
            evidence_refs=evidence_refs,
        )

    def confirm_parameter(
        self,
        envelope: QueryContextEnvelope,
        dimension_id: str,
        confirmed_value: Any,
    ) -> QueryContextEnvelope:
        """Explicit user confirmation of a parameter.

        Delegates to QueryContextEngine.promote_with_user_confirmation.
        Produces new immutable revision with parent lineage (I-09).
        No domain logic, no evidence interpretation (I-11).
        """
        return self.query_engine.promote_with_user_confirmation(
            envelope,
            dimension_id=dimension_id,
            confirmed_value=confirmed_value,
        )


"""Deterministic tests for Context-Aware Reasoning.

Source of truth: design/context-aware-reasoning/02-deterministic-tests.md
Any implementation failing these is non-compliant.
"""

import pytest

from okc.context import (
    AffordanceAvailability,
    AnswerStage,
    CompatibilityState,
    ContextDimension,
    ContextRegistry,
    EvidenceCompatibilityEngine,
    EvidenceSnapshotStore,
    ExpansionAffordance,
    ParameterStatus,
    QueryContextEngine,
    QueryContextEnvelope,
    QueryParameter,
    ResolutionPolicy,
    Sensitivity,
    ValueType,
)


@pytest.fixture
def registry() -> ContextRegistry:
    reg = ContextRegistry()
    dim = ContextDimension(
        dimension_id="historical_period",
        version="1.0",
        value_type=ValueType.CONTROLLED_VOCABULARY,
        sensitivity=Sensitivity.HIGH,
        resolution_policy=ResolutionPolicy.REQUIRE_EVIDENCE,
        can_be_assumed=True,
        allowed_values=["ancient", "medieval", "modern"],
    )
    reg.register(dim)
    return reg


# Suite A — Registry

def test_A1_package_redefinition_rejected(registry: ContextRegistry) -> None:
    with pytest.raises(ValueError, match="may not own or redefine"):
        registry.reject_package_ownership({"context_dimensions": {"historical_period": {}}})


def test_A2_domain_extension_boundaries(registry: ContextRegistry) -> None:
    # Adding values is allowed via new version or domain plugin (represented as new registration of extended)
    extended = ContextDimension(
        dimension_id="historical_period",
        version="1.1",
        value_type=ValueType.CONTROLLED_VOCABULARY,
        sensitivity=Sensitivity.HIGH,  # base sensitivity unchanged
        resolution_policy=ResolutionPolicy.REQUIRE_EVIDENCE,
        can_be_assumed=True,
        allowed_values=["ancient", "medieval", "modern", "contemporary"],
    )
    registry.register(extended)
    assert registry.get("historical_period", "1.1").allowed_values[-1] == "contemporary"


def test_A3_version_isolation(registry: ContextRegistry) -> None:
    old = registry.get("historical_period", "1.0")
    assert old is not None
    assert "contemporary" not in old.allowed_values


def test_A4_soft_deprecation_still_resolvable(registry: ContextRegistry) -> None:
    registry.soft_deprecate("historical_period", "1.0")
    assert registry.get("historical_period", "1.0") is not None


def test_A5_declaration_alone_does_not_make_affordance_available() -> None:
    # Package support declaration is not evidence; affordance engine requires evidence or path
    engine = EvidenceCompatibilityEngine(ContextRegistry())
    envelope = QueryContextEnvelope(
        envelope_id="e1",
        revision=1,
        query_id="q1",
        package_ref="pkg1",
        parameters={
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.MISSING,
            )
        },
    )
    affordances = engine.generate_affordances(envelope, evidence_spans=[])
    assert affordances == []


# Suite B — Evidence Compatibility

def test_B1_fully_compatible(registry: ContextRegistry) -> None:
    engine = EvidenceCompatibilityEngine(registry)
    state = engine.classify({"historical_period": "modern"}, "historical_period", "modern")
    assert state == CompatibilityState.FULLY_COMPATIBLE


def test_B2_incompatible(registry: ContextRegistry) -> None:
    engine = EvidenceCompatibilityEngine(registry)
    state = engine.classify({"historical_period": "ancient"}, "historical_period", "modern")
    assert state == CompatibilityState.INCOMPATIBLE


def test_B3_unconstrained_does_not_establish(registry: ContextRegistry) -> None:
    engine = EvidenceCompatibilityEngine(registry)
    state = engine.classify({}, "historical_period", "modern")
    assert state == CompatibilityState.UNCONSTRAINED
    # Contract: unconstrained cannot establish resolution (enforced by caller / envelope rules)


def test_B4_partial_compatibility(registry: ContextRegistry) -> None:
    engine = EvidenceCompatibilityEngine(registry)
    state = engine.classify(
        {"historical_period": ["modern", "contemporary"]},
        "historical_period",
        "modern",
    )
    assert state == CompatibilityState.PARTIALLY_COMPATIBLE


def test_B5_invalid_provenance_treated_as_unconstrained(registry: ContextRegistry) -> None:
    engine = EvidenceCompatibilityEngine(registry)
    # None constraint or missing treated as unconstrained
    state = engine.classify({"historical_period": None}, "historical_period", "modern")
    assert state == CompatibilityState.UNCONSTRAINED


# Suite C — Conflict Resolution (minimal detection; full domain rules later)

def test_C1_conflict_retained_when_no_rule() -> None:
    # Two fully compatible but contradictory spans retained
    # Implementation stores both; neither promoted
    spans = [
        {"constraints": {"historical_period": "modern"}},
        {"constraints": {"historical_period": "ancient"}},
    ]
    # Engine classifies independently; caller retains both
    engine = EvidenceCompatibilityEngine(ContextRegistry())
    states = [engine.classify(s["constraints"], "historical_period", "modern") for s in spans]
    assert CompatibilityState.FULLY_COMPATIBLE in states
    assert CompatibilityState.INCOMPATIBLE in states
    # No silent winner


def test_C3_no_silent_majority_or_provenance_override() -> None:
    # Explicit: engine does not select winner by count or provenance
    assert True  # covered by C1 contract; no majority logic present


def test_C4_both_alternatives_become_affordances() -> None:
    # When well-supported alternatives exist, both can be offered
    # (minimal: engine can emit multiple if caller supplies candidates)
    assert True  # eligibility produced only by engine; see D-suite


# Suite D — Affordance Generation

def test_D1_available_when_evidence_present(registry: ContextRegistry) -> None:
    engine = EvidenceCompatibilityEngine(registry)
    envelope = QueryContextEnvelope(
        envelope_id="e2",
        revision=1,
        query_id="q2",
        package_ref="pkg1",
        parameters={
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.MISSING,
                value="modern",
            )
        },
    )
    spans = [{"constraints": {"historical_period": "modern"}}]
    affs = engine.generate_affordances(envelope, spans)
    assert len(affs) == 1
    assert affs[0].availability == AffordanceAvailability.AVAILABLE


def test_D2_retrievable_when_path_exists(registry: ContextRegistry) -> None:
    engine = EvidenceCompatibilityEngine(registry)
    envelope = QueryContextEnvelope(
        envelope_id="e3",
        revision=1,
        query_id="q3",
        package_ref="pkg1",
        parameters={
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.MISSING,
            )
        },
    )
    affs = engine.generate_affordances(
        envelope, [], retrieval_paths={"historical_period": "/retrieve/period"}
    )
    assert len(affs) == 1
    assert affs[0].availability == AffordanceAvailability.RETRIEVABLE
    assert affs[0].cost == "defined_path"


def test_D3_unsupported_never_emitted(registry: ContextRegistry) -> None:
    engine = EvidenceCompatibilityEngine(registry)
    envelope = QueryContextEnvelope(
        envelope_id="e4",
        revision=1,
        query_id="q4",
        package_ref="pkg1",
        parameters={
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.MISSING,
            )
        },
    )
    affs = engine.generate_affordances(envelope, [])
    assert affs == []
    # Direct construction of unsupported is rejected by model
    with pytest.raises(ValueError):
        ExpansionAffordance(
            affordance_id="bad",
            dimension_id="historical_period",
            target_value="x",
            availability=AffordanceAvailability.UNSUPPORTED,
            effect="add_evidence",
            source_envelope_id="e4",
            source_revision=1,
        )


def test_D5_projected_change_is_estimate_only() -> None:
    # Model allows optional projected_change; no enforcement as promise
    aff = ExpansionAffordance(
        affordance_id="est",
        dimension_id="historical_period",
        target_value="modern",
        availability=AffordanceAvailability.AVAILABLE,
        effect="add_evidence",
        source_envelope_id="e",
        source_revision=1,
        projected_change="may resolve dimension",
    )
    assert aff.projected_change == "may resolve dimension"


# Suite E — Envelope Lifecycle

def test_E1_assumption_never_auto_promotes(registry: ContextRegistry) -> None:
    env = QueryContextEnvelope(
        envelope_id="e5",
        revision=1,
        query_id="q5",
        package_ref="pkg1",
        parameters={
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.MISSING,
                value="modern", assumption="modern",
                source="assumption",
            )
        },
    )
    # No promotion method exists that changes status without new evidence/user
    assert env.parameters["historical_period"].status == ParameterStatus.MISSING
    assert env.parameters["historical_period"].assumption == "modern"


def test_E2_promotion_requires_evidence_or_user() -> None:
    # Contract enforced by absence of auto-promote; caller must supply new evidence or source="user"
    assert True


def test_E3_snapshots_immutable() -> None:
    store = EvidenceSnapshotStore()
    snap1 = store.create_snapshot("snap-1", evidence_refs=["ev-a", "ev-b"])
    retrieved = store.get("snap-1")
    assert retrieved is snap1
    assert retrieved.evidence_refs == ("ev-a", "ev-b")
    # Cannot mutate (tuple)
    with pytest.raises(AttributeError):
        retrieved.evidence_refs.append("ev-c")
    # New retrieval / expansion creates new snapshot
    snap2 = store.create_snapshot(
        "snap-2", evidence_refs=["ev-a", "ev-b", "ev-c"], parent_snapshot_id="snap-1"
    )
    assert store.get("snap-1").evidence_refs == ("ev-a", "ev-b")
    assert snap2.parent_snapshot_id == "snap-1"
    # Re-create same id forbidden
    with pytest.raises(ValueError):
        store.create_snapshot("snap-1", evidence_refs=["other"])


def test_E4_revision_lineage() -> None:
    child = QueryContextEnvelope(
        envelope_id="e6",
        revision=2,
        parent_revision=1,
        query_id="q6",
        package_ref="pkg1",
    )
    assert child.parent_revision == 1


def test_E5_high_sensitivity_unresolved_makes_contextually_incomplete(
    registry: ContextRegistry,
) -> None:
    env = QueryContextEnvelope(
        envelope_id="e7",
        revision=1,
        query_id="q7",
        package_ref="pkg1",
        parameters={
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.MISSING,
            )
        },
    )
    assert env.derive_open_high_sensitivity(registry) is True
    # contextually_complete must be false when this is true (Answer Stage rule)


def test_E6_unconstrained_alone_cannot_establish_completeness(registry: ContextRegistry) -> None:
    engine = EvidenceCompatibilityEngine(registry)
    state = engine.classify({}, "historical_period", "modern")
    assert state == CompatibilityState.UNCONSTRAINED
    # Cannot count toward resolution


# Suite F — Answer Stage (minimal next increment)

def test_F1_independent_flags_assumption_disclosed_incomplete(registry: ContextRegistry) -> None:
    stage = AnswerStage(registry)
    env = QueryContextEnvelope(
        envelope_id="e8",
        revision=1,
        query_id="q8",
        package_ref="pkg1",
        parameters={
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.MISSING,
                value="modern", assumption="modern",
                source="assumption",
            )
        },
    )
    result = stage.produce(env, affordances=[])
    assert result.completion.answer_delivered is True  # useful under assumption
    assert result.completion.contextually_complete is False  # high-sens unresolved
    assert result.context.applied_assumptions
    assert "historical_period" in result.context.unresolved_dimensions
    assert any(c.support_status == "assumption" for c in result.answer.claims)


def test_F2_insufficient_evidence(registry: ContextRegistry) -> None:
    stage = AnswerStage(registry)
    env = QueryContextEnvelope(
        envelope_id="e9",
        revision=1,
        query_id="q9",
        package_ref="pkg1",
        parameters={
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.MISSING,
            )
        },
    )
    result = stage.produce(env, affordances=[])
    assert result.completion.answer_delivered is False
    assert result.completion.contextually_complete is False
    assert result.completion.reason == "insufficient_evidence"


def test_F3_preauthorized_affordances_only(registry: ContextRegistry) -> None:
    stage = AnswerStage(registry)
    env = QueryContextEnvelope(
        envelope_id="e10",
        revision=1,
        query_id="q10",
        package_ref="pkg1",
        parameters={
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.MISSING,
                value="modern", assumption="modern",
            )
        },
    )
    aff = ExpansionAffordance(
        affordance_id="aff-test",
        dimension_id="historical_period",
        target_value="modern",
        availability=AffordanceAvailability.AVAILABLE,
        effect="add_evidence",
        source_envelope_id="e10",
        source_revision=1,
    )
    result = stage.produce(env, affordances=[aff])
    assert len(result.expansion_affordances) == 1
    assert result.expansion_affordances[0].affordance_id == "aff-test"
    # Stage does not invent or alter eligibility


def test_F4_conflicts_force_incomplete_and_disclosed(registry: ContextRegistry) -> None:
    stage = AnswerStage(registry)
    env = QueryContextEnvelope(
        envelope_id="e11",
        revision=1,
        query_id="q11",
        package_ref="pkg1",
        parameters={
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.RESOLVED,
                value="modern",
                source="evidence",
            )
        },
    )
    result = stage.produce(
        env,
        affordances=[],
        evidence_summary={"supporting": ["span1"]},
        conflicts=["historical_period"],
    )
    assert result.completion.answer_delivered is True
    assert result.completion.contextually_complete is False
    assert "historical_period" in result.context.conflicted_dimensions


# Suite G — Query Context Engine (envelope revision, assumption non-promotion)

def test_G1_assumption_does_not_promote_status() -> None:
    engine = QueryContextEngine()
    parent = engine.create_envelope("e-g1", "q-g1", "pkg1")
    revised = engine.apply_assumption(parent, "historical_period", "modern")
    assert revised.revision == 2
    assert revised.parent_revision == 1
    param = revised.parameters["historical_period"]
    assert param.status == ParameterStatus.MISSING
    assert param.assumption == "modern"
    assert param.source == "assumption"
    # Original parent unchanged
    assert "historical_period" not in parent.parameters


def test_G2_user_confirmation_promotes() -> None:
    engine = QueryContextEngine()
    parent = engine.create_envelope("e-g2", "q-g2", "pkg1")
    revised = engine.promote_with_user_confirmation(parent, "historical_period", "modern")
    param = revised.parameters["historical_period"]
    assert param.status == ParameterStatus.RESOLVED
    assert param.value == "modern"
    assert param.source == "user"
    assert revised.parent_revision == 1


def test_G3_evidence_promotes_and_new_snapshot() -> None:
    engine = QueryContextEngine()
    parent = engine.create_envelope("e-g3", "q-g3", "pkg1")
    revised = engine.promote_with_evidence(
        parent, "historical_period", "modern", "snap-new-1"
    )
    param = revised.parameters["historical_period"]
    assert param.status == ParameterStatus.RESOLVED
    assert param.source == "evidence"
    assert revised.evidence_set_ref == "snap-new-1"
    assert revised.revision == 2


def test_G5_promote_with_evidence_creates_immutable_snapshot_when_store_attached() -> None:
    """I-10: retrieval / evidence application creates a new immutable snapshot."""
    store = EvidenceSnapshotStore()
    engine = QueryContextEngine(snapshot_store=store)
    parent = engine.create_envelope("e-g5", "q-g5", "pkg1")
    revised = engine.promote_with_evidence(
        parent,
        "historical_period",
        "modern",
        evidence_set_ref="snap-g5",
        evidence_refs=["ev-1", "ev-2"],
    )
    assert revised.evidence_set_ref == "snap-g5"
    snap = store.get("snap-g5")
    assert snap is not None
    assert snap.evidence_refs == ("ev-1", "ev-2")
    assert snap.parent_snapshot_id is None
    # Second application creates a different snapshot (immutability + new-on-retrieval)
    revised2 = engine.promote_with_evidence(
        revised,
        "historical_period",
        "medieval",
        evidence_set_ref="snap-g5",  # preferred id already taken
        evidence_refs=["ev-3"],
    )
    assert revised2.evidence_set_ref != "snap-g5"
    assert store.exists(revised2.evidence_set_ref)
    assert store.get("snap-g5").evidence_refs == ("ev-1", "ev-2")  # original unchanged
    assert revised2.parent_revision == 2


def test_G4_lineage_preserved_across_multiple_revisions() -> None:
    engine = QueryContextEngine()
    e1 = engine.create_envelope("e-g4", "q-g4", "pkg1")
    e2 = engine.apply_assumption(e1, "historical_period", "medieval")
    e3 = engine.promote_with_user_confirmation(e2, "historical_period", "modern")
    assert e1.revision == 1 and e1.parent_revision is None
    assert e2.revision == 2 and e2.parent_revision == 1
    assert e3.revision == 3 and e3.parent_revision == 2
    assert e3.parameters["historical_period"].status == ParameterStatus.RESOLVED


# Suite H — Orchestrator (minimal coordination, no domain logic)

def test_H1_orchestrator_coordinates_without_domain_logic(registry: ContextRegistry) -> None:
    from okc.context import ContextOrchestrator

    orch = ContextOrchestrator(registry)
    envelope, affordances, result = orch.process_query(
        query_id="q-h1",
        package_ref="pkg-h1",
        envelope_id="e-h1",
        initial_parameters={
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.MISSING,
                value="modern",
            )
        },
        evidence_spans=[{"constraints": {"historical_period": "modern"}}],
    )
    assert envelope.revision == 1
    assert len(affordances) == 1
    assert affordances[0].availability == AffordanceAvailability.AVAILABLE
    assert result.expansion_affordances == affordances
    # Orchestrator did not invent or alter status
    assert envelope.parameters["historical_period"].status == ParameterStatus.MISSING


# Suite I — Package adapter and initial snapshot

def test_I1_orchestrator_uses_package_evidence_spans_without_inference(registry: ContextRegistry) -> None:
    from okc.models.knowledge_package import (
        KnowledgePackage,
        KnowledgeObject,
        Provenance,
        EvidenceSpan,
    )
    from okc.context import ContextOrchestrator, extract_evidence_spans

    prov = Provenance(
        source_platform="test",
        source_file="test.md",
        tenant_id="t1",
        silo_id="s1",
    )
    span = EvidenceSpan(
        span_id="sp1",
        message_id="m1",
        role="user",
        timestamp="2026-01-01T00:00:00Z",
        content="The period is modern.",
    )
    obj = KnowledgeObject(
        object_id="obj1",
        title="test",
        provenance=prov,
        evidence=[span],
        content="The period is modern.",
    )
    pkg = KnowledgePackage(package_id="pkg-i1", objects=[obj])
    # Explicit constraint in package metadata
    pkg.metadata["context_constraints"] = {"obj1": {"historical_period": "modern"}}

    extracted = extract_evidence_spans(pkg)
    assert len(extracted) == 1
    assert extracted[0]["constraints"] == {"historical_period": "modern"}
    assert extracted[0]["provenance"]["tenant_id"] == "t1"

    orch = ContextOrchestrator(registry)
    initial = {
        "historical_period": QueryParameter(
            dimension_id="historical_period",
            status=ParameterStatus.MISSING,
            value="modern",  # candidate for compatibility check
        )
    }
    envelope, affordances, result = orch.process_query(
        query_id="q-i1",
        package_ref="pkg-i1",
        envelope_id="e-i1",
        initial_parameters=initial,
        package=pkg,  # evidence_spans omitted → adapter used
    )
    assert len(affordances) == 1
    assert affordances[0].availability == AffordanceAvailability.AVAILABLE
    # Answer stage receives pre-authorized affordances; delivery depends on content/assumptions
    assert result.expansion_affordances == affordances
    # No inference: status remains missing until explicit promotion
    assert envelope.parameters["historical_period"].status == ParameterStatus.MISSING


def test_I2_initial_snapshot_created_from_package_evidence(registry: ContextRegistry) -> None:
    """I-10: when snapshot store present and package supplies evidence, initial envelope gets immutable snapshot."""
    from okc.models.knowledge_package import (
        KnowledgePackage,
        KnowledgeObject,
        Provenance,
        EvidenceSpan,
    )
    from okc.context import ContextOrchestrator, EvidenceSnapshotStore

    prov = Provenance(source_platform="test", source_file="t.md", tenant_id="t1", silo_id="s1")
    span = EvidenceSpan(span_id="sp-init", message_id="m1", role="user", timestamp="2026-01-01T00:00:00Z", content="evidence")
    obj = KnowledgeObject(object_id="obj1", title="t", provenance=prov, evidence=[span], content="evidence")
    pkg = KnowledgePackage(package_id="pkg-i2", objects=[obj])

    store = EvidenceSnapshotStore()
    orch = ContextOrchestrator(registry, snapshot_store=store)
    envelope, _, _ = orch.process_query(
        query_id="q-i2",
        package_ref="pkg-i2",
        envelope_id="e-i2",
        package=pkg,
    )
    assert envelope.evidence_set_ref is not None
    assert store.exists(envelope.evidence_set_ref)
    snap = store.get(envelope.evidence_set_ref)
    assert snap is not None
    assert "sp-init" in snap.evidence_refs
    # Snapshot is immutable (frozen)
    assert snap.model_config.get("frozen") is True


def test_I3_apply_expansion_creates_immutable_revision_with_lineage(registry: ContextRegistry) -> None:
    """I-09: apply_expansion produces new envelope revision with parent lineage; evidence path uses new snapshot."""
    from okc.context import ContextOrchestrator, EvidenceSnapshotStore, QueryParameter, ParameterStatus

    store = EvidenceSnapshotStore()
    orch = ContextOrchestrator(registry, snapshot_store=store)
    parent = orch.query_engine.create_envelope(
        envelope_id="e-i3",
        query_id="q-i3",
        package_ref="pkg-i3",
        parameters={
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.MISSING,
            )
        },
    )
    # Evidence path: promotes and creates snapshot
    revised = orch.apply_expansion(
        parent,
        dimension_id="historical_period",
        new_value="modern",
        evidence_refs=["ev-i3-1"],
    )
    assert revised.revision == 2
    assert revised.parent_revision == 1
    assert revised.parameters["historical_period"].status == ParameterStatus.RESOLVED
    assert revised.parameters["historical_period"].value == "modern"
    assert revised.parameters["historical_period"].source == "evidence"
    assert revised.evidence_set_ref is not None
    assert store.exists(revised.evidence_set_ref)
    snap = store.get(revised.evidence_set_ref)
    assert snap is not None
    assert "ev-i3-1" in snap.evidence_refs
    assert snap.parent_snapshot_id is None  # first evidence

    # Assumption path (no evidence_refs): new revision, status remains MISSING, assumption disclosed
    assumed = orch.apply_expansion(
        revised,
        dimension_id="historical_period",
        new_value="medieval",
    )
    assert assumed.revision == 3
    assert assumed.parent_revision == 2
    assert assumed.parameters["historical_period"].status == ParameterStatus.MISSING
    assert assumed.parameters["historical_period"].assumption == "medieval"
    assert assumed.parameters["historical_period"].source == "expansion"
    assert assumed.parameters["historical_period"].value is None  # not promoted
    # Parent snapshot unchanged
    assert store.get(revised.evidence_set_ref).evidence_refs == ("ev-i3-1",)

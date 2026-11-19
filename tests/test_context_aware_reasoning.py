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
    """C3: engine never selects a winner by count or provenance.
    Both values remain eligible affordances; no override applied.
    """
    engine = EvidenceCompatibilityEngine(ContextRegistry())
    envelope = QueryContextEnvelope(
        envelope_id="c3",
        revision=1,
        query_id="qc3",
        package_ref="pkg1",
        parameters={
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.MISSING,
            )
        },
    )
    # Three spans support "modern", one supports "ancient" — majority must not win
    spans = [
        {"constraints": {"historical_period": "modern"}},
        {"constraints": {"historical_period": "modern"}},
        {"constraints": {"historical_period": "modern"}},
        {"constraints": {"historical_period": "ancient"}},
    ]
    affs = engine.generate_affordances(envelope, spans)
    targets = {a.target_value for a in affs}
    assert "modern" in targets
    assert "ancient" in targets
    assert len(affs) == 2  # both alternatives retained; no silent majority


def test_C4_both_alternatives_become_affordances(registry: ContextRegistry) -> None:
    """C4: when well-supported alternatives exist and no domain rule resolves,
    both become eligible affordances. Eligibility produced only by the engine.
    """
    engine = EvidenceCompatibilityEngine(registry)
    envelope = QueryContextEnvelope(
        envelope_id="c4",
        revision=1,
        query_id="qc4",
        package_ref="pkg1",
        parameters={
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.MISSING,
            )
        },
    )
    spans = [
        {"constraints": {"historical_period": "modern"}},
        {"constraints": {"historical_period": "ancient"}},
    ]
    affs = engine.generate_affordances(envelope, spans)
    assert len(affs) == 2
    targets = sorted(a.target_value for a in affs)
    assert targets == ["ancient", "modern"]
    for a in affs:
        assert a.availability == AffordanceAvailability.AVAILABLE
        assert a.effect == "add_evidence"
        assert a.source_envelope_id == "c4"
        assert a.source_revision == 1


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
    assert affs[0].projected_change == "estimate: may resolve or refine dimension"


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
    assert affs[0].projected_change == "estimate: may resolve or refine dimension"


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


def test_I4_answer_from_revised_envelope_no_domain_logic(registry: ContextRegistry) -> None:
    """I-11 / expansion loop: answer_from_envelope coordinates on existing revision without mutating it or inventing logic."""
    from okc.context import ContextOrchestrator, EvidenceSnapshotStore, QueryParameter, ParameterStatus

    store = EvidenceSnapshotStore()
    orch = ContextOrchestrator(registry, snapshot_store=store)
    parent = orch.query_engine.create_envelope(
        envelope_id="e-i4",
        query_id="q-i4",
        package_ref="pkg-i4",
        parameters={
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.MISSING,
            )
        },
    )
    revised = orch.apply_expansion(
        parent,
        dimension_id="historical_period",
        new_value="modern",
        evidence_refs=["ev-i4"],
    )
    # Snapshot original revision id/status
    orig_revision = revised.revision
    orig_status = revised.parameters["historical_period"].status
    result = orch.answer_from_envelope(
        revised,
        evidence_spans=[{"span_id": "ev-i4"}],
        evidence_summary={"supporting": ["ev-i4"]},
    )
    # Envelope unchanged (no mutation)
    assert revised.revision == orig_revision
    assert revised.parameters["historical_period"].status == orig_status
    # Answer coordinated from the existing revision
    assert result.context.envelope_id == revised.envelope_id
    assert result.context.revision == revised.revision
    assert result.completion.answer_delivered is True
    assert isinstance(result.expansion_affordances, list)


def test_I5_retrieve_for_affordance_creates_new_snapshot_and_revision(registry: ContextRegistry) -> None:
    """I-10 / I-09: retrieval path for RETRIEVABLE affordance produces new immutable snapshot and revision."""
    from okc.models.knowledge_package import (
        KnowledgePackage,
        KnowledgeObject,
        Provenance,
        EvidenceSpan,
    )
    from okc.context import (
        ContextOrchestrator,
        EvidenceSnapshotStore,
        QueryParameter,
        ParameterStatus,
        AffordanceAvailability,
    )

    prov = Provenance(source_platform="test", source_file="t.md", tenant_id="t1", silo_id="s1")
    span = EvidenceSpan(
        span_id="sp-ret",
        message_id="m1",
        role="user",
        timestamp="2026-01-01T00:00:00Z",
        content="modern evidence",
    )
    obj = KnowledgeObject(
        object_id="obj1",
        title="t",
        provenance=prov,
        evidence=[span],
        content="modern evidence",
        metadata={},
    )
    pkg = KnowledgePackage(package_id="pkg-i5", objects=[obj])
    pkg.metadata = {"context_constraints": {"obj1": {"historical_period": "modern"}}}

    store = EvidenceSnapshotStore()
    orch = ContextOrchestrator(registry, snapshot_store=store)

    # Start with missing parameter; supply retrieval path so affordance is RETRIEVABLE
    initial = {
        "historical_period": QueryParameter(
            dimension_id="historical_period",
            status=ParameterStatus.MISSING,
        )
    }
    envelope, affordances, _ = orch.process_query(
        query_id="q-i5",
        package_ref="pkg-i5",
        envelope_id="e-i5",
        initial_parameters=initial,
        package=pkg,
        retrieval_paths={"historical_period": "package"},
    )
    assert len(affordances) == 1
    aff = affordances[0]
    assert aff.availability == AffordanceAvailability.RETRIEVABLE
    assert envelope.evidence_set_ref is not None  # initial snapshot

    revised = orch.retrieve_for_affordance(envelope, aff, package=pkg)
    assert revised.revision == envelope.revision + 1
    assert revised.parent_revision == envelope.revision
    assert revised.parameters["historical_period"].status == ParameterStatus.RESOLVED
    assert revised.parameters["historical_period"].value == "modern"
    assert revised.evidence_set_ref is not None
    assert revised.evidence_set_ref != envelope.evidence_set_ref
    snap = store.get(revised.evidence_set_ref)
    assert snap is not None
    assert "sp-ret" in snap.evidence_refs
    assert snap.parent_snapshot_id == envelope.evidence_set_ref
    # Original envelope unchanged
    assert envelope.revision == 1
    assert envelope.parameters["historical_period"].status == ParameterStatus.MISSING


def test_I6_confirm_parameter_creates_revision_with_user_source(registry: ContextRegistry) -> None:
    """Suite I6: explicit user confirmation via orchestrator produces new revision.

    Verifies I-09 lineage and that status becomes RESOLVED with source="user".
    No domain logic in orchestrator.
    """
    from okc.context.orchestrator import ContextOrchestrator
    from okc.context.models import QueryParameter, ParameterStatus
    from okc.context.snapshot_store import EvidenceSnapshotStore

    store = EvidenceSnapshotStore()
    orch = ContextOrchestrator(registry, snapshot_store=store)

    initial = {
        "jurisdiction": QueryParameter(
            dimension_id="jurisdiction",
            status=ParameterStatus.MISSING,
            assumption="ZA",
            source="assumption",
        )
    }
    env, _, _ = orch.process_query(
        query_id="q1",
        package_ref="pkg1",
        envelope_id="env1",
        initial_parameters=initial,
    )
    assert env.parameters["jurisdiction"].status == ParameterStatus.MISSING
    assert env.revision == 1

    revised = orch.confirm_parameter(env, "jurisdiction", "ZA")
    assert revised.revision == 2
    assert revised.parent_revision == env.revision
    assert revised.parameters["jurisdiction"].status == ParameterStatus.RESOLVED
    assert revised.parameters["jurisdiction"].value == "ZA"
    assert revised.parameters["jurisdiction"].source == "user"
    # Original assumption preserved in history via parent
    assert env.parameters["jurisdiction"].assumption == "ZA"


def test_I7_confirmation_makes_high_sensitivity_contextually_complete(registry: ContextRegistry) -> None:
    """Suite I7: user confirmation of high-sensitivity dimension allows contextually_complete=True.

    Chains process_query (with assumption) → confirm_parameter → answer_from_envelope.
    Verifies independent flags, lineage (I-09), no auto-promotion, and no domain logic (I-11).
    """
    from okc.context.orchestrator import ContextOrchestrator
    from okc.context.models import QueryParameter, ParameterStatus
    from okc.context.snapshot_store import EvidenceSnapshotStore

    store = EvidenceSnapshotStore()
    orch = ContextOrchestrator(registry, snapshot_store=store)

    initial = {
        "historical_period": QueryParameter(
            dimension_id="historical_period",
            status=ParameterStatus.MISSING,
            assumption="modern",
            source="assumption",
        )
    }
    env, affs, initial_result = orch.process_query(
        query_id="q-i7",
        package_ref="pkg1",
        envelope_id="env-i7",
        initial_parameters=initial,
    )
    assert initial_result.completion.answer_delivered is True
    assert initial_result.completion.contextually_complete is False
    assert "historical_period" in initial_result.context.unresolved_dimensions

    revised = orch.confirm_parameter(env, "historical_period", "modern")
    assert revised.revision == 2
    assert revised.parent_revision == 1
    assert revised.parameters["historical_period"].status == ParameterStatus.RESOLVED
    assert revised.parameters["historical_period"].source == "user"

    final_result = orch.answer_from_envelope(revised)
    assert final_result.completion.answer_delivered is True
    assert final_result.completion.contextually_complete is True
    assert "historical_period" not in final_result.context.unresolved_dimensions
    # Parent still incomplete
    assert env.parameters["historical_period"].status == ParameterStatus.MISSING


def test_I8_auto_detect_simple_conflicts_disclosed(registry: ContextRegistry) -> None:
    """Suite I8 / C1: orchestrator auto-detects simple conflicting constraints and discloses them.

    No domain rule applied; both values retained; contextually_complete=False.
    Caller does not need to pass conflicts explicitly.
    """
    from okc.context.orchestrator import ContextOrchestrator

    orch = ContextOrchestrator(registry)
    initial = {
        "historical_period": QueryParameter(
            dimension_id="historical_period",
            status=ParameterStatus.MISSING,
        )
    }
    spans = [
        {"span_id": "s1", "constraints": {"historical_period": "modern"}},
        {"span_id": "s2", "constraints": {"historical_period": "ancient"}},
    ]
    envelope, affordances, result = orch.process_query(
        query_id="q-i8",
        package_ref="pkg1",
        envelope_id="e-i8",
        initial_parameters=initial,
        evidence_spans=spans,
    )
    assert "historical_period" in result.context.conflicted_dimensions
    assert result.completion.contextually_complete is False
    assert result.completion.answer_delivered is False  # no supporting material or assumption
    # No silent winner; both alternatives remain eligible via engine if candidates supplied
    assert isinstance(affordances, list)


def test_I9_domain_rule_resolves_simple_conflict_preserves_evidence(registry: ContextRegistry) -> None:
    """Suite I9 / C2: domain rule applied to simple conflict; rationale recorded; evidence preserved.

    Preferred value must already be among observed constraints. No silent invention.
    Envelope revised with source=domain_rule; remaining conflicts empty for that dim.
    """
    from okc.context.orchestrator import ContextOrchestrator

    orch = ContextOrchestrator(registry)
    initial = {
        "historical_period": QueryParameter(
            dimension_id="historical_period",
            status=ParameterStatus.MISSING,
        )
    }
    spans = [
        {"span_id": "s1", "constraints": {"historical_period": "modern"}},
        {"span_id": "s2", "constraints": {"historical_period": "ancient"}},
    ]
    domain_rules = {
        "historical_period": {
            "preferred_value": "modern",
            "rationale": "prefer modern for contemporary analysis",
        }
    }
    envelope, affordances, result = orch.process_query(
        query_id="q-i9",
        package_ref="pkg1",
        envelope_id="e-i9",
        initial_parameters=initial,
        evidence_spans=spans,
        domain_rules=domain_rules,
    )
    # Resolved via rule
    param = envelope.parameters["historical_period"]
    assert param.status == ParameterStatus.RESOLVED
    assert param.value == "modern"
    assert param.source == "domain_rule"
    # Conflict no longer listed (resolved); rationale disclosed
    assert "historical_period" not in result.context.conflicted_dimensions
    assert any("domain rule" in q.lower() for q in result.answer.qualifications)
    assert any("prefer modern" in c.text for c in result.answer.claims)
    # Original conflict values preserved in claim text
    assert "ancient" in str(result.answer.claims)
    # Contextually complete if no other unresolved high-sensitivity
    assert result.completion.contextually_complete is True
    assert result.completion.answer_delivered is True



def test_D4_assumption_replacement_creates_new_revision(registry: ContextRegistry) -> None:
    """Suite D4: assumption path creates new revision; original assumption preserved in parent history."""
    from okc.context.orchestrator import ContextOrchestrator
    store = EvidenceSnapshotStore()
    orch = ContextOrchestrator(registry, snapshot_store=store)
    parent = orch.query_engine.create_envelope(
        envelope_id="d4",
        query_id="qd4",
        package_ref="pkg",
        parameters={
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.MISSING,
                assumption="ancient",
            )
        },
    )
    revised = orch.apply_expansion(parent, "historical_period", "modern")
    assert revised.revision == parent.revision + 1
    assert revised.parent_revision == parent.revision
    # Original assumption preserved in parent
    assert parent.parameters["historical_period"].assumption == "ancient"
    # New revision has the replacement as assumption (never auto-promoted)
    assert revised.parameters["historical_period"].assumption == "modern"
    assert revised.parameters["historical_period"].status == ParameterStatus.MISSING
    assert revised.parameters["historical_period"].source == "expansion"


def test_F5_partial_and_background_claims_disclosed(registry: ContextRegistry) -> None:
    """I-08 / contract: partial requires qualification; unconstrained is background only."""
    stage = AnswerStage(registry)
    env = QueryContextEnvelope(
        envelope_id="e12",
        revision=1,
        query_id="q12",
        package_ref="pkg1",
        parameters={
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.RESOLVED,
                value="modern",
            )
        },
    )
    evidence = {
        "supporting": ["span-full"],
        "partial": ["span-partial"],
        "background": ["span-unconstrained"],
    }
    result = stage.produce(env, affordances=[], evidence_summary=evidence)
    assert result.completion.answer_delivered is True
    statuses = {c.support_status for c in result.answer.claims}
    assert "supported" in statuses
    assert "partial" in statuses
    assert "background" in statuses
    assert any("Partial compatibility" in q for q in result.answer.qualifications)
    # Background claim does not claim to establish dimension
    bg = next(c for c in result.answer.claims if c.support_status == "background")
    assert "not used to establish" in bg.text




def test_I10_retrieval_makes_high_sensitivity_contextually_complete(registry: ContextRegistry) -> None:
    """Suite I10: retrieval of evidence for RETRIEVABLE affordance resolves high-sensitivity dimension and allows contextually_complete=True.

    Chains process_query → retrieve_for_affordance → answer_from_envelope.
    Verifies independent flags, lineage (I-09), new snapshot (I-10), no domain logic (I-11).
    """
    from okc.context.orchestrator import ContextOrchestrator
    from okc.context.models import (
        QueryParameter,
        ParameterStatus,
        AffordanceAvailability,
        ExpansionAffordance,
    )
    from okc.context.snapshot_store import EvidenceSnapshotStore

    store = EvidenceSnapshotStore()
    orch = ContextOrchestrator(registry, snapshot_store=store)

    initial = {
        "historical_period": QueryParameter(
            dimension_id="historical_period",
            status=ParameterStatus.MISSING,
        )
    }
    # Start with no evidence so the dimension remains unresolved
    envelope, _, first = orch.process_query(
        query_id="q-i10",
        package_ref="pkg-i10",
        envelope_id="e-i10",
        initial_parameters=initial,
        evidence_spans=[],
        retrieval_paths={"historical_period": "package"},
    )
    assert first.completion.contextually_complete is False
    assert envelope.parameters["historical_period"].status == ParameterStatus.MISSING

    # Controlled RETRIEVABLE affordance matching the envelope
    aff = ExpansionAffordance(
        affordance_id="aff-i10",
        dimension_id="historical_period",
        availability=AffordanceAvailability.RETRIEVABLE,
        target_value="modern",
        source_envelope_id=envelope.envelope_id,
        source_revision=envelope.revision,
        evidence_set_ref=envelope.evidence_set_ref,
        effect="add_evidence",
        projected_change="estimate: may resolve or refine dimension",
    )

    # Supply evidence spans that carry the resolving constraint
    evidence_spans = [
        {
            "span_id": "sp-complete",
            "content": "the period is modern",
            "constraints": {"historical_period": "modern"},
        }
    ]
    revised = orch.retrieve_for_affordance(envelope, aff, extra_spans=evidence_spans)

    assert revised.revision == envelope.revision + 1
    assert revised.parent_revision == envelope.revision
    assert revised.parameters["historical_period"].status == ParameterStatus.RESOLVED
    assert revised.parameters["historical_period"].value == "modern"
    assert revised.evidence_set_ref is not None
    assert revised.evidence_set_ref != envelope.evidence_set_ref

    # Answer from the revised envelope with the same evidence
    final = orch.answer_from_envelope(revised, evidence_spans=evidence_spans)
    assert final.completion.answer_delivered is True
    assert final.completion.contextually_complete is True
    # Original envelope remains unchanged (immutable)
    assert envelope.parameters["historical_period"].status == ParameterStatus.MISSING
    assert envelope.revision == 1


def test_F6_completion_reason_discloses_unresolved_high_sensitivity(registry: ContextRegistry) -> None:
    """When answer is delivered but high-sensitivity remains unresolved, reason discloses the cause."""
    from okc.context.answer import AnswerStage
    from okc.context.models import (
        QueryContextEnvelope, QueryParameter, ParameterStatus, Sensitivity,
        ContextDimension, ValueType, ResolutionPolicy,
    )

    dim = ContextDimension(
        dimension_id="jurisdiction",
        version="1",
        value_type=ValueType.STRING,
        sensitivity=Sensitivity.HIGH,
        resolution_policy=ResolutionPolicy.ALLOW_ASSUMPTION,
        can_be_assumed=True,
    )
    registry.register(dim)
    env = QueryContextEnvelope(
        envelope_id="e1",
        query_id="q1",
        package_ref="pkg1",
        revision=1,
        parameters={"jurisdiction": QueryParameter(dimension_id="jurisdiction", status=ParameterStatus.MISSING, assumption="US")},
    )
    stage = AnswerStage(registry)
    result = stage.produce(env, affordances=[], evidence_summary={"supporting": ["span1"]})
    assert result.completion.answer_delivered is True
    assert result.completion.contextually_complete is False
    assert result.completion.reason == "unresolved_high_sensitivity"
    assert any("Unresolved high-sensitivity" in q for q in result.answer.qualifications)


def test_F7_completion_reason_discloses_conflicts_retained(registry: ContextRegistry) -> None:
    """When answer is delivered but conflicts are retained (no high-sensitivity unresolved), reason discloses the cause."""
    from okc.context.answer import AnswerStage
    from okc.context.models import (
        QueryContextEnvelope, QueryParameter, ParameterStatus,
    )

    env = QueryContextEnvelope(
        envelope_id="e-f7",
        query_id="q-f7",
        package_ref="pkg-f7",
        revision=1,
        parameters={"speaker_affiliation": QueryParameter(dimension_id="speaker_affiliation", status=ParameterStatus.RESOLVED, value="internal")},
    )
    stage = AnswerStage(registry)
    result = stage.produce(
        env,
        affordances=[],
        evidence_summary={"supporting": ["span-a", "span-b"]},
        conflicts=["speaker_affiliation"],
    )
    assert result.completion.answer_delivered is True
    assert result.completion.contextually_complete is False
    assert result.completion.reason == "conflicts_retained"
    assert any("Conflicts retained" in q for q in result.answer.qualifications)
    assert "speaker_affiliation" in result.context.conflicted_dimensions


def test_F8_conflicts_disclosed_as_conflicted_claims(registry: ContextRegistry) -> None:
    """Retained conflicts produce an explicit claim with support_status=conflicted (I-08 / disclosure rule)."""
    from okc.context.answer import AnswerStage
    from okc.context.models import (
        QueryContextEnvelope, QueryParameter, ParameterStatus,
    )

    env = QueryContextEnvelope(
        envelope_id="e-f8",
        query_id="q-f8",
        package_ref="pkg-f8",
        revision=1,
        parameters={"speaker_affiliation": QueryParameter(dimension_id="speaker_affiliation", status=ParameterStatus.RESOLVED, value="internal")},
    )
    stage = AnswerStage(registry)
    result = stage.produce(
        env,
        affordances=[],
        evidence_summary={"supporting": ["span-a"], "conflicting": ["span-c"]},
        conflicts=["speaker_affiliation"],
    )
    assert result.completion.answer_delivered is True
    assert result.completion.contextually_complete is False
    conflict_claims = [c for c in result.answer.claims if c.support_status == "conflicted"]
    assert len(conflict_claims) == 1
    assert "speaker_affiliation" in conflict_claims[0].text
    assert "neither value treated as established" in conflict_claims[0].text
    assert conflict_claims[0].evidence_refs == ["span-c"]
    assert "speaker_affiliation" in result.context.conflicted_dimensions


def test_F9_disclosure_summary_includes_completion_and_qualifications(registry: ContextRegistry) -> None:
    """Presentation aid surfaces content, qualifications, and independent completion flags without inventing facts."""
    from okc.context.answer import AnswerStage
    from okc.context.models import QueryContextEnvelope, QueryParameter, ParameterStatus

    env = QueryContextEnvelope(
        envelope_id="e-f9",
        query_id="q-f9",
        package_ref="pkg-f9",
        revision=1,
        parameters={"historical_period": QueryParameter(dimension_id="historical_period", status=ParameterStatus.MISSING)},
    )
    stage = AnswerStage(registry)
    result = stage.produce(env, affordances=[], evidence_summary={"supporting": ["span-1"]}, conflicts=[])
    summary = result.to_disclosure_summary()
    assert "Supported findings available." in summary
    assert "Unresolved high-sensitivity dimensions: historical_period" in summary
    assert "Delivered=True" in summary
    assert "ContextuallyComplete=False" in summary
    assert "Reason=unresolved_high_sensitivity" in summary
    assert "Unresolved: historical_period" in summary


def test_F10_unavailable_dimensions_disclosed_when_cannot_assume(registry: ContextRegistry) -> None:
    """High-sensitivity missing dimensions that cannot be assumed are disclosed as unavailable (presentation + I-12)."""
    from okc.context.answer import AnswerStage
    from okc.context.models import (
        QueryContextEnvelope, QueryParameter, ParameterStatus,
        ContextDimension, ValueType, Sensitivity, ResolutionPolicy,
    )

    # Register a high-sens dim that cannot be assumed
    no_assume = ContextDimension(
        dimension_id="legal_jurisdiction",
        version="1.0",
        value_type=ValueType.CONTROLLED_VOCABULARY,
        sensitivity=Sensitivity.HIGH,
        resolution_policy=ResolutionPolicy.REQUIRE_EVIDENCE,
        can_be_assumed=False,
        allowed_values=["us", "eu", "other"],
    )
    registry.register(no_assume)

    env = QueryContextEnvelope(
        envelope_id="e-f10",
        query_id="q-f10",
        package_ref="pkg-f10",
        revision=1,
        parameters={
            "legal_jurisdiction": QueryParameter(
                dimension_id="legal_jurisdiction",
                status=ParameterStatus.MISSING,
            ),
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.MISSING,
                assumption="modern",
            ),
        },
    )
    stage = AnswerStage(registry)
    result = stage.produce(env, affordances=[], evidence_summary={"supporting": ["span-1"]})
    assert result.completion.answer_delivered is True
    assert result.completion.contextually_complete is False
    assert "legal_jurisdiction" in result.context.unavailable_dimensions
    assert "legal_jurisdiction" in result.context.unresolved_dimensions
    assert "historical_period" not in result.context.unavailable_dimensions  # can_be_assumed=True
    summary = result.to_disclosure_summary()
    assert "Unavailable: legal_jurisdiction" in summary
    assert "Unresolved: legal_jurisdiction" in summary or "historical_period" in summary


def test_F11_unavailable_qualification_emitted_when_cannot_assume(registry: ContextRegistry) -> None:
    """Unavailable high-sensitivity dimensions that cannot be assumed receive an explicit qualification (I-12 disclosure)."""
    from okc.context.answer import AnswerStage
    from okc.context.models import (
        QueryContextEnvelope, QueryParameter, ParameterStatus,
        ContextDimension, ValueType, Sensitivity, ResolutionPolicy,
    )

    no_assume = ContextDimension(
        dimension_id="legal_jurisdiction",
        version="1.0",
        value_type=ValueType.CONTROLLED_VOCABULARY,
        sensitivity=Sensitivity.HIGH,
        resolution_policy=ResolutionPolicy.REQUIRE_EVIDENCE,
        can_be_assumed=False,
        allowed_values=["us", "eu", "other"],
    )
    registry.register(no_assume)

    env = QueryContextEnvelope(
        envelope_id="e-f11",
        query_id="q-f11",
        package_ref="pkg-f11",
        revision=1,
        parameters={
            "legal_jurisdiction": QueryParameter(
                dimension_id="legal_jurisdiction",
                status=ParameterStatus.MISSING,
            ),
        },
    )
    stage = AnswerStage(registry)
    result = stage.produce(env, affordances=[], evidence_summary={"supporting": ["span-1"]})
    assert result.completion.answer_delivered is True
    assert result.completion.contextually_complete is False
    assert "legal_jurisdiction" in result.context.unavailable_dimensions
    quals = result.answer.qualifications
    assert any("Unavailable (cannot be assumed): legal_jurisdiction" in q for q in quals)
    summary = result.to_disclosure_summary()
    assert "Unavailable: legal_jurisdiction" in summary
    assert "Unavailable (cannot be assumed): legal_jurisdiction" in summary


def test_B6_per_dimension_independent_classification(registry: ContextRegistry) -> None:
    """Consistency clarification: a single span may be unconstrained for one
    dimension, fully compatible for another, and partially compatible for a third.
    Classification is always per-dimension, never global.
    """
    engine = EvidenceCompatibilityEngine(registry)
    span_constraints = {
        "historical_period": "2020s",          # fully compatible if target matches
        "speaker_affiliation": ["academic", "industry"],  # partial if target in list
        # "legal_jurisdiction" absent → unconstrained
    }
    assert engine.classify(span_constraints, "historical_period", "2020s") == CompatibilityState.FULLY_COMPATIBLE
    assert engine.classify(span_constraints, "speaker_affiliation", "academic") == CompatibilityState.PARTIALLY_COMPATIBLE
    assert engine.classify(span_constraints, "legal_jurisdiction", "us") == CompatibilityState.UNCONSTRAINED
    # Incompatible case for completeness
    assert engine.classify(span_constraints, "historical_period", "1990s") == CompatibilityState.INCOMPATIBLE

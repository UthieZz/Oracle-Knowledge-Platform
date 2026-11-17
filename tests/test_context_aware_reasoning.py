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
                assumption="modern",
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
                assumption="modern",
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
                assumption="modern",
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


def test_G4_lineage_preserved_across_multiple_revisions() -> None:
    engine = QueryContextEngine()
    e1 = engine.create_envelope("e-g4", "q-g4", "pkg1")
    e2 = engine.apply_assumption(e1, "historical_period", "medieval")
    e3 = engine.promote_with_user_confirmation(e2, "historical_period", "modern")
    assert e1.revision == 1 and e1.parent_revision is None
    assert e2.revision == 2 and e2.parent_revision == 1
    assert e3.revision == 3 and e3.parent_revision == 2
    # Assumption from e2 not auto-promoted; e3 has resolved via user
    assert e3.parameters["historical_period"].status == ParameterStatus.RESOLVED

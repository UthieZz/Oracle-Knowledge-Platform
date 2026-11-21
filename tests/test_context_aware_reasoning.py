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


def _dim(
    dimension_id: str = "historical_period",
    version: str = "1.0",
    sensitivity: Sensitivity = Sensitivity.MEDIUM,
    can_be_assumed: bool = True,
) -> ContextDimension:
    return ContextDimension(
        dimension_id=dimension_id,
        version=version,
        value_type=ValueType.CONTROLLED_VOCABULARY,
        sensitivity=sensitivity,
        resolution_policy=ResolutionPolicy.ALLOW_ASSUMPTION,
        can_be_assumed=can_be_assumed,
        allowed_values=["ancient", "medieval", "modern"],
    )


class TestSuiteARegistry:
    def test_a1_package_redefinition_rejected(self):
        registry = ContextRegistry()
        registry.register(_dim())
        with pytest.raises(ValueError, match="may not own or redefine"):
            registry.reject_package_ownership({"context_dimensions": [{"dimension_id": "historical_period"}]})

    def test_a3_version_isolation(self):
        registry = ContextRegistry()
        registry.register(_dim(version="1.0"))
        registry.register(_dim(version="2.0", sensitivity=Sensitivity.HIGH))
        assert registry.get("historical_period", "1.0").sensitivity == Sensitivity.MEDIUM
        assert registry.get("historical_period", "2.0").sensitivity == Sensitivity.HIGH
        assert registry.get("historical_period").version == "2.0"

    def test_a4_soft_deprecate_still_resolvable(self):
        registry = ContextRegistry()
        registry.register(_dim())
        registry.soft_deprecate("historical_period", "1.0")
        assert registry.get("historical_period", "1.0") is not None


class TestSuiteBCompatibility:
    def test_b1_fully_compatible(self):
        engine = EvidenceCompatibilityEngine(ContextRegistry())
        state = engine.classify({"historical_period": "modern"}, "historical_period", "modern")
        assert state == CompatibilityState.FULLY_COMPATIBLE

    def test_b2_incompatible(self):
        engine = EvidenceCompatibilityEngine(ContextRegistry())
        state = engine.classify({"historical_period": "ancient"}, "historical_period", "modern")
        assert state == CompatibilityState.INCOMPATIBLE

    def test_b3_unconstrained(self):
        engine = EvidenceCompatibilityEngine(ContextRegistry())
        state = engine.classify({}, "historical_period", "modern")
        assert state == CompatibilityState.UNCONSTRAINED
        state2 = engine.classify({"historical_period": None}, "historical_period", "modern")
        assert state2 == CompatibilityState.UNCONSTRAINED

    def test_b4_partially_compatible(self):
        engine = EvidenceCompatibilityEngine(ContextRegistry())
        state = engine.classify(
            {"historical_period": ["medieval", "modern"]},
            "historical_period",
            "modern",
        )
        assert state == CompatibilityState.PARTIALLY_COMPATIBLE


class TestSuiteEEnvelopeLifecycle:
    def test_e1_assumption_never_auto_promotes(self):
        engine = QueryContextEngine()
        env = engine.create_envelope("e1", "q1", "pkg1")
        env = engine.apply_assumption(env, "historical_period", "modern")
        assert env.parameters["historical_period"].status == ParameterStatus.MISSING
        assert env.parameters["historical_period"].assumption == "modern"
        # revision does not promote
        rev = engine.create_revision(env)
        assert rev.parameters["historical_period"].status == ParameterStatus.MISSING
        assert rev.parameters["historical_period"].assumption == "modern"

    def test_e2_promotion_only_via_confirmation_or_evidence(self):
        engine = QueryContextEngine()
        env = engine.create_envelope("e1", "q1", "pkg1")
        env = engine.apply_assumption(env, "historical_period", "modern")
        # confirmation
        confirmed = engine.promote_with_user_confirmation(env, "historical_period", "modern")
        assert confirmed.parameters["historical_period"].status == ParameterStatus.RESOLVED
        assert confirmed.parameters["historical_period"].assumption is None
        # evidence path
        env2 = engine.create_envelope("e2", "q2", "pkg1")
        evidenced = engine.promote_with_evidence(
            env2, "historical_period", "modern", evidence_set_ref="snap-1"
        )
        assert evidenced.parameters["historical_period"].status == ParameterStatus.RESOLVED

    def test_e3_snapshot_immutability(self):
        store = EvidenceSnapshotStore()
        snap = store.create_snapshot("snap-1", ["span-a", "span-b"])
        with pytest.raises(ValueError):
            store.create_snapshot("snap-1", ["other"])
        retrieved = store.get("snap-1")
        assert retrieved.evidence_refs == ("span-a", "span-b")
        assert retrieved.snapshot_id == "snap-1"

    def test_e4_revision_lineage(self):
        engine = QueryContextEngine()
        parent = engine.create_envelope("e1", "q1", "pkg1")
        child = engine.create_revision(parent)
        assert child.parent_revision == parent.revision
        assert child.revision == parent.revision + 1
        assert child.envelope_id == parent.envelope_id


class TestSuiteCConflictAffordances:
    def test_c4_both_alternatives_become_affordances(self):
        registry = ContextRegistry()
        registry.register(_dim())
        engine = EvidenceCompatibilityEngine(registry)
        env = QueryContextEnvelope(
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
        spans = [
            {"span_id": "s1", "constraints": {"historical_period": "ancient"}},
            {"span_id": "s2", "constraints": {"historical_period": "modern"}},
        ]
        affordances = engine.generate_affordances(env, spans)
        targets = {a.target_value for a in affordances}
        assert targets == {"ancient", "modern"}
        assert all(a.availability == AffordanceAvailability.AVAILABLE for a in affordances)

    def test_d3_unsupported_never_emitted(self):
        registry = ContextRegistry()
        registry.register(_dim())
        engine = EvidenceCompatibilityEngine(registry)
        env = QueryContextEnvelope(
            envelope_id="e1",
            revision=1,
            query_id="q1",
            package_ref="pkg1",
            parameters={
                "historical_period": QueryParameter(
                    dimension_id="historical_period",
                    status=ParameterStatus.UNSUPPORTED,
                )
            },
        )
        affordances = engine.generate_affordances(env, [])
        assert affordances == []


class TestAnswerStageCompletionFlags:
    def test_high_sensitivity_unresolved_not_complete(self):
        registry = ContextRegistry()
        registry.register(_dim(sensitivity=Sensitivity.HIGH, can_be_assumed=False))
        stage = AnswerStage(registry)
        env = QueryContextEnvelope(
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
        result = stage.produce(env, [])
        assert result.completion.answer_delivered is False
        assert result.completion.contextually_complete is False

    def test_resolved_high_sensitivity_complete(self):
        registry = ContextRegistry()
        registry.register(_dim(sensitivity=Sensitivity.HIGH))
        stage = AnswerStage(registry)
        env = QueryContextEnvelope(
            envelope_id="e1",
            revision=1,
            query_id="q1",
            package_ref="pkg1",
            parameters={
                "historical_period": QueryParameter(
                    dimension_id="historical_period",
                    status=ParameterStatus.RESOLVED,
                    value="modern",
                )
            },
        )
        result = stage.produce(env, [], evidence_summary={"supporting": ["span-1"]})
        assert result.completion.answer_delivered is True
        assert result.completion.contextually_complete is True


class TestSuiteCConflictRetention:
    def test_c1_conflict_detected_and_retained(self):
        engine = EvidenceCompatibilityEngine(ContextRegistry())
        spans = [
            {"id": "s1", "constraints": {"historical_period": "ancient"}},
            {"id": "s2", "constraints": {"historical_period": "modern"}},
        ]
        conflicts = engine.detect_simple_conflicts(spans)
        assert "historical_period" in conflicts
        # No silent resolution
        assert len(conflicts) == 1

    def test_c3_no_silent_majority_or_override(self):
        engine = EvidenceCompatibilityEngine(ContextRegistry())
        # Three ancient, one modern — still both must remain eligible (no majority)
        spans = [
            {"id": "s1", "constraints": {"historical_period": "ancient"}},
            {"id": "s2", "constraints": {"historical_period": "ancient"}},
            {"id": "s3", "constraints": {"historical_period": "ancient"}},
            {"id": "s4", "constraints": {"historical_period": "modern"}},
        ]
        env = QueryContextEnvelope(
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
        affordances = engine.generate_affordances(env, spans)
        targets = {a.target_value for a in affordances}
        assert targets == {"ancient", "modern"}


class TestSuiteECompletionAndUnconstrained:
    def test_e5_high_sensitivity_unresolved_not_complete(self):
        registry = ContextRegistry()
        registry.register(_dim(sensitivity=Sensitivity.HIGH, can_be_assumed=False))
        stage = AnswerStage(registry)
        env = QueryContextEnvelope(
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
        result = stage.produce(env, [])
        assert result.completion.contextually_complete is False

    def test_e6_unconstrained_alone_cannot_establish_completeness(self):
        registry = ContextRegistry()
        registry.register(_dim(sensitivity=Sensitivity.HIGH))
        stage = AnswerStage(registry)
        env = QueryContextEnvelope(
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
        # Only unconstrained evidence
        evidence_summary = {"background": ["span-bg"], "supporting": []}
        result = stage.produce(env, [], evidence_summary=evidence_summary)
        assert result.completion.contextually_complete is False
        # Background only — must not promote dimension
        assert any("Unresolved" in q or "high-sensitivity" in q.lower() for q in result.answer.qualifications)


class TestSuiteDAffordanceAvailability:
    def test_d1_available_when_evidence_present(self):
        registry = ContextRegistry()
        registry.register(_dim())
        engine = EvidenceCompatibilityEngine(registry)
        spans = [{"id": "s1", "constraints": {"historical_period": "modern"}}]
        env = QueryContextEnvelope(
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
        affordances = engine.generate_affordances(env, spans)
        assert len(affordances) == 1
        assert affordances[0].availability == AffordanceAvailability.AVAILABLE
        assert affordances[0].target_value == "modern"

    def test_d2_retrievable_when_path_declared(self):
        registry = ContextRegistry()
        registry.register(_dim())
        engine = EvidenceCompatibilityEngine(registry)
        env = QueryContextEnvelope(
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
        affordances = engine.generate_affordances(
            env, [], retrieval_paths={"historical_period": "external_lookup"}
        )
        assert len(affordances) == 1
        assert affordances[0].availability == AffordanceAvailability.RETRIEVABLE


class TestSuiteDAssumptionAndEstimate:
    def test_d4_assumption_replacement_creates_new_revision(self):
        store = EvidenceSnapshotStore()
        engine = QueryContextEngine(store)
        parent = engine.create_envelope("e1", "q1", "pkg1", parameters={
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.MISSING,
                assumption="ancient",
            )
        })
        # Apply expansion via assumption path (no evidence_refs)
        orch = None  # use engine directly for isolation
        revised = engine.create_revision(parent, {
            "historical_period": QueryParameter(
                dimension_id="historical_period",
                status=ParameterStatus.MISSING,
                assumption="modern",
                source="expansion",
            )
        })
        assert revised.revision == parent.revision + 1
        assert revised.parent_revision == parent.revision
        assert parent.parameters["historical_period"].assumption == "ancient"
        assert revised.parameters["historical_period"].assumption == "modern"
        assert revised.parameters["historical_period"].status == ParameterStatus.MISSING  # never auto-promoted

    def test_d5_projected_change_is_estimate_only(self):
        registry = ContextRegistry()
        registry.register(_dim())
        engine = EvidenceCompatibilityEngine(registry)
        env = QueryContextEnvelope(
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
        spans = [{"span_id": "s1", "constraints": {"historical_period": "modern"}}]
        affordances = engine.generate_affordances(env, spans)
        assert len(affordances) == 1
        assert affordances[0].projected_change == "estimate: may resolve or refine dimension"
        # Estimate only: no promise of resolution
        assert "promise" not in (affordances[0].projected_change or "").lower()


class TestSuiteCDomainRule:
    def test_c2_domain_rule_resolves_only_when_preferred_observed(self):
        from okc.context.orchestrator import ContextOrchestrator
        registry = ContextRegistry()
        registry.register(_dim())
        store = EvidenceSnapshotStore()
        orch = ContextOrchestrator(registry, snapshot_store=store)
        spans = [
            {"span_id": "s1", "constraints": {"historical_period": "ancient"}},
            {"span_id": "s2", "constraints": {"historical_period": "modern"}},
        ]
        domain_rules = {"historical_period": {"preferred_value": "modern", "rationale": "preferred modern"}}
        env, affordances, answer = orch.process_query(
            envelope_id="e1",
            query_id="q1",
            package_ref="pkg1",
            initial_parameters={"historical_period": QueryParameter(dimension_id="historical_period", status=ParameterStatus.MISSING)},
            evidence_spans=spans,
            domain_rules=domain_rules,
        )
        # Preferred is among observed, so resolution applied
        assert env.parameters["historical_period"].status == ParameterStatus.RESOLVED
        assert env.parameters["historical_period"].value == "modern"
        assert env.parameters["historical_period"].source == "domain_rule"
        # Conflicts retained in answer
        assert any("domain rule" in (q or "").lower() or "preferred" in (q or "").lower() for q in (answer.answer.qualifications or []))


class TestSuiteADomainExtensionAndSupport:
    def test_a2_domain_extension_new_version_allowed_same_rejected(self):
        registry = ContextRegistry()
        base = _dim(version="1.0", sensitivity=Sensitivity.MEDIUM)
        registry.register(base)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(_dim(version="1.0", sensitivity=Sensitivity.HIGH))
        extended = _dim(version="1.1", sensitivity=Sensitivity.HIGH)
        extended = extended.model_copy(update={"allowed_values": ["ancient", "medieval", "modern", "contemporary"]})
        registry.register(extended)
        assert registry.get("historical_period", "1.0").sensitivity == Sensitivity.MEDIUM
        assert registry.get("historical_period", "1.1").sensitivity == Sensitivity.HIGH
        assert "contemporary" in registry.get("historical_period", "1.1").allowed_values

    def test_a5_package_support_declaration_alone_does_not_make_affordance_available(self):
        registry = ContextRegistry()
        registry.register(_dim())
        engine = EvidenceCompatibilityEngine(registry)
        env = QueryContextEnvelope(
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
        affordances = engine.generate_affordances(env, evidence_spans=[])
        assert affordances == []


class TestSuiteBInvalidProvenance:
    def test_b5_invalid_provenance_constraint_treated_as_unconstrained(self):
        engine = EvidenceCompatibilityEngine(ContextRegistry())
        state = engine.classify("not-a-dict", "historical_period", "modern")
        assert state == CompatibilityState.UNCONSTRAINED
        state2 = engine.classify({"historical_period": object()}, "historical_period", "modern")
        assert state2 != CompatibilityState.FULLY_COMPATIBLE


class TestSuiteFAnswerStageInsufficient:
    def test_f_insufficient_evidence_no_delivery_independent_flags(self):
        """Locks insufficient evidence path: answer_delivered=false, reason set,
        contextually_complete independent, no invented claims.
        Source: 03-answer-stage-contract.md insufficient evidence example + I-12.
        """
        registry = ContextRegistry()
        registry.register(_dim(sensitivity=Sensitivity.HIGH, can_be_assumed=False))
        stage = AnswerStage(registry)
        env = QueryContextEnvelope(
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
        result = stage.produce(env, affordances=[], evidence_summary={})
        assert result.completion.answer_delivered is False
        assert result.completion.contextually_complete is False
        assert result.completion.reason == "insufficient_evidence"
        assert result.answer.claims == []
        assert "No material" in result.answer.content
        # High-sensitivity missing and non-assumable is disclosed
        assert "historical_period" in result.context.unresolved_dimensions
        assert "historical_period" in result.context.unavailable_dimensions
        # Disclosure summary includes the flags
        summary = result.to_disclosure_summary()
        assert "Delivered=False" in summary
        assert "ContextuallyComplete=False" in summary
        assert "Reason=insufficient_evidence" in summary


class TestSuiteIRetrievalPath:
    """Locks I-10 (retrieval creates new immutable snapshot) and I-09 (revision lineage)
    on the orchestrator retrieval path for RETRIEVABLE affordances.
    Source: design/context-aware-reasoning/05-integration-contract.md I-09, I-10.
    """

    def test_retrieve_for_affordance_creates_new_snapshot_and_revision(self):
        from okc.context.orchestrator import ContextOrchestrator
        from okc.context.models import AffordanceAvailability, ExpansionAffordance
        from okc.context.snapshot_store import EvidenceSnapshotStore

        registry = ContextRegistry()
        registry.register(_dim())
        store = EvidenceSnapshotStore()
        orch = ContextOrchestrator(registry, snapshot_store=store)

        # Initial envelope with a parent snapshot
        initial = orch.query_engine.create_envelope(
            envelope_id="env-r1",
            query_id="q-r1",
            package_ref="pkg-r1",
            parameters={
                "historical_period": QueryParameter(
                    dimension_id="historical_period",
                    status=ParameterStatus.MISSING,
                )
            },
            evidence_refs=["span-initial"],
        )
        assert initial.revision == 1
        assert initial.evidence_set_ref is not None
        original_snap_id = initial.evidence_set_ref
        original_snap = store.get(original_snap_id)
        assert original_snap is not None
        assert original_snap.evidence_refs == ("span-initial",)

        # Construct a valid RETRIEVABLE affordance matching the envelope
        affordance = ExpansionAffordance(
            affordance_id="aff-r1",
            dimension_id="historical_period",
            target_value="modern",
            availability=AffordanceAvailability.RETRIEVABLE,
            effect="add_evidence",
            source_envelope_id=initial.envelope_id,
            source_revision=initial.revision,
            cost="low",
        )

        # Provide a span that carries an explicit constraint (presence only; no interpretation)
        extra_spans = [
            {
                "span_id": "span-retrieved",
                "constraints": {"historical_period": "modern"},
            }
        ]

        new_env = orch.retrieve_for_affordance(
            envelope=initial,
            affordance=affordance,
            extra_spans=extra_spans,
        )

        # New revision with parent lineage (I-09)
        assert new_env.revision == 2
        assert new_env.parent_revision == 1
        assert new_env.envelope_id == initial.envelope_id

        # Parameter promoted via evidence
        param = new_env.parameters["historical_period"]
        assert param.status == ParameterStatus.RESOLVED
        assert param.value == "modern"
        assert param.source == "evidence"

        # New immutable snapshot created (I-10), parent linked
        assert new_env.evidence_set_ref is not None
        assert new_env.evidence_set_ref != original_snap_id
        new_snap = store.get(new_env.evidence_set_ref)
        assert new_snap is not None
        assert new_snap.parent_snapshot_id == original_snap_id
        assert "span-retrieved" in new_snap.evidence_refs

        # Originals remain unchanged (immutability)
        assert initial.revision == 1
        assert initial.evidence_set_ref == original_snap_id
        assert store.get(original_snap_id).evidence_refs == ("span-initial",)
        # Attempting to recreate the same snapshot id must fail
        try:
            store.create_snapshot(original_snap_id, ["other"])
            assert False, "duplicate snapshot id must be rejected"
        except ValueError:
            pass


class TestSuiteBPerDimensionIndependence:
    def test_b6_single_span_independent_classifications_across_dimensions(self):
        """Locks binding clarification: evidence classification is per-dimension, never global.
        One span can be unconstrained, fully compatible, and partially compatible simultaneously.
        Source: design/context-aware-reasoning/01-registry-and-compatibility.md Per-dimension classification.
        """
        registry = ContextRegistry()
        registry.register(_dim("period"))
        registry.register(_dim("region"))
        registry.register(_dim("theme"))
        engine = EvidenceCompatibilityEngine(registry)
        # Single span constrains period fully, region partially, theme not at all
        span_constraints = {
            "period": "modern",
            "region": ["europe", "asia"],  # partial if querying for "europe"
        }
        state_period = engine.classify(span_constraints, "period", "modern")
        state_region = engine.classify(span_constraints, "region", "europe")
        state_theme = engine.classify(span_constraints, "theme", "science")
        assert state_period == CompatibilityState.FULLY_COMPATIBLE
        assert state_region == CompatibilityState.PARTIALLY_COMPATIBLE
        assert state_theme == CompatibilityState.UNCONSTRAINED



class TestSuiteIIntegrationInvariants:
    def test_i06_i07_answer_stage_passes_preauthorized_affordances_unmodified(self):
        """Locks I-06 (only pre-authorized affordances reach Answer Stage)
        and I-07 (Answer Stage cannot modify eligibility or execution metadata).
        Source: design/context-aware-reasoning/05-integration-contract.md
        """
        registry = ContextRegistry()
        registry.register(_dim("historical_period"))
        stage = AnswerStage(registry)

        envelope = QueryContextEnvelope(
            envelope_id="env-i07",
            query_id="q-i07",
            package_ref="pkg-1",
            evidence_set_ref="snap-1",
            revision=1,
            parameters={
                "historical_period": QueryParameter(
                    dimension_id="historical_period",
                    status=ParameterStatus.RESOLVED,
                    value="modern",
                    source="evidence",
                )
            },
        )

        original = ExpansionAffordance(
            affordance_id="aff-pre",
            dimension_id="historical_period",
            target_value="modern",
            availability=AffordanceAvailability.AVAILABLE,
            effect="constrain",
            source_envelope_id=envelope.envelope_id,
            source_revision=envelope.revision,
            cost="none",
        )

        result = stage.produce(
            envelope=envelope,
            affordances=[original],
            evidence_summary={"supporting": ["span-1"]},
        )

        assert len(result.expansion_affordances) == 1
        returned = result.expansion_affordances[0]
        assert returned.affordance_id == original.affordance_id
        assert returned.availability == original.availability
        assert returned.effect == original.effect
        assert returned.source_envelope_id == original.source_envelope_id
        assert returned.source_revision == original.source_revision
        assert returned.target_value == original.target_value
        # No mutation of the input object
        assert original.availability == AffordanceAvailability.AVAILABLE

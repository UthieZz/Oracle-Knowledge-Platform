
## 2026-11-18 — Context-Aware Reasoning both alternatives as affordances on conflict (C4 / C3)

- Problem: Suite C4 was a stub. When evidence contained conflicting fully-specified values for an unresolved dimension and no domain rule resolved it, only a single candidate affordance (or none) was emitted. Majority or silent selection risk existed.
- Change: EvidenceCompatibilityEngine.generate_affordances now emits one AVAILABLE affordance per distinct constrained value when a conflict is present (len(candidates) > 1). No majority/provenance override. Original single-candidate and RETRIEVABLE paths preserved for non-conflict cases. Suite C3 and C4 replaced with real assertions. 42 passed.
- Verification: pytest tests/test_context_aware_reasoning.py → 42 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances locked Context-Aware Reasoning by making both well-supported alternatives eligible affordances. No deviation from C3/C4 or I-11.

## 2026-11-18 — Context-Aware Reasoning domain-rule resolution for simple conflicts (C2 / I-11)

- Problem: No path to apply an optional versioned domain rule to a retained simple conflict while recording rationale and preserving all conflicting evidence.
- Change: EvidenceCompatibilityEngine.apply_simple_domain_rules accepts {dim: {preferred_value, rationale}} and returns resolutions only when preferred is among observed values. ContextOrchestrator.process_query accepts domain_rules; on match creates new immutable revision (source="domain_rule"), passes remaining conflicts + rule_resolutions to AnswerStage which discloses rationale and preserved values. Suite I9 added.
- Verification: pytest tests/test_context_aware_reasoning.py → 42 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances locked Context-Aware Reasoning by implementing C2 without embedding domain logic. No silent invention or majority override.

## 2026-11-18 — Context-Aware Reasoning simple conflict detection (C1 / I-11)

- Problem: Conflicts between evidence constraints had to be supplied by the caller; no automatic retention/disclosure path for simple multi-value cases.
- Change: EvidenceCompatibilityEngine.detect_simple_conflicts returns dimension_ids with multiple distinct scalar constraints. ContextOrchestrator.process_query and answer_from_envelope auto-detect when conflicts argument is None and spans present. No domain rules, no silent override. Suite I8 added.
- Verification: pytest tests/test_context_aware_reasoning.py → 41 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances locked Context-Aware Reasoning by ensuring simple conflicts are retained and disclosed. No deviation from C1 / I-11.

## 2026-11-18 — Context-Aware Reasoning confirmation completeness (I-09 / I-12)

- Problem: After explicit user confirmation of a high-sensitivity parameter, AnswerStage still reported answer_delivered=False (insufficient_evidence) even though context was complete.
- Change: AnswerStage.produce now treats any RESOLVED parameter as material for answer_delivered. Suite I7 chains process_query → confirm_parameter → answer_from_envelope and asserts independent flags + lineage.
- Verification: pytest tests/test_context_aware_reasoning.py → 40 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances locked Context-Aware Reasoning by ensuring confirmation can produce a contextually complete, deliverable answer. No deviation from I-09 / I-11 / I-12.

## 2026-11-17 — Context-Aware Reasoning explicit user confirmation path (I-09 / I-11)

- Problem: QueryContextEngine.promote_with_user_confirmation existed but orchestrator had no coordinated path for explicit user confirmation of a parameter.
- Change: Added ContextOrchestrator.confirm_parameter. Delegates only; produces new revision with parent lineage. Status RESOLVED, source="user". No domain logic. Suite I6 added.
- Verification: pytest tests/test_context_aware_reasoning.py → 39 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances locked Context-Aware Reasoning by exposing the user-confirmation promotion path through the orchestrator. No deviation from I-09 / I-11.

## 2026-11-17 — Context-Aware Reasoning retrieval path for RETRIEVABLE affordances (I-10 / I-09)

- Problem: RETRIEVABLE affordances had no coordinated path that produced a new immutable evidence snapshot and envelope revision.
- Change: Added ContextOrchestrator.retrieve_for_affordance. Uses package adapter or supplied spans only; delegates to promote_with_evidence for new snapshot + revision. No domain logic, no auto-promotion beyond existing engine rules. Suite I5 added.
- Verification: pytest tests/test_context_aware_reasoning.py → 38 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances locked Context-Aware Reasoning by closing the retrieval → snapshot → revision loop. No deviation from I-10 / I-09 / I-11.


## 2026-11-17 — Context-Aware Reasoning answer from revised envelope (I-11)

- Problem: After apply_expansion produced a new envelope revision, no orchestrator path existed to coordinate an answer from that existing revision without re-creating state.
- Change: Added ContextOrchestrator.answer_from_envelope. Coordinates compatibility + AnswerStage on a caller-supplied envelope; does not mutate envelope, invent affordances, or contain domain logic. Suite I4 added.
- Verification: pytest tests/test_context_aware_reasoning.py → 38 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances locked Context-Aware Reasoning by closing the expansion → answer coordination loop. No deviation from I-11.

## 2026-11-17 — Context-Aware Reasoning expansion creates immutable revision (I-09)

- Problem: Orchestrator had no path to apply an ExpansionAffordance and produce a new envelope revision with parent lineage.
- Change: Added ContextOrchestrator.apply_expansion. When evidence_refs and snapshot store present, delegates to promote_with_evidence (new snapshot). Otherwise creates revision with MISSING status + disclosed assumption (never auto-promoted). No domain logic. Suite I3 added.
- Verification: pytest tests/test_context_aware_reasoning.py → 36 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances locked Context-Aware Reasoning by demonstrating I-09 lineage on expansion. No deviation from I-09 / I-11.

## 2026-11-17 — Context-Aware Reasoning initial evidence snapshot on package path (I-10)

- Problem: process_query created envelope without attaching an immutable evidence snapshot even when snapshot store was present and package/adapter supplied spans.
- Change: QueryContextEngine.create_envelope accepts optional evidence_refs; when store attached, creates fresh immutable snapshot and sets evidence_set_ref (I-10). ContextOrchestrator passes span_ids extracted from package or supplied spans. Suite I2 added.
- Verification: pytest tests/test_context_aware_reasoning.py → 35 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances locked Context-Aware Reasoning by ensuring initial evidence path produces immutable snapshot. No deviation from I-10 / I-11.

[Full historical log continues from prior commits; see git history for complete prior entries.]

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

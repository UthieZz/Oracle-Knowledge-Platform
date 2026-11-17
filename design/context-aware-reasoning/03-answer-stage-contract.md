# Answer-Stage Input/Output Contract

**Version:** 1.0  
**Status:** Locked  
**Date:** 2026-11-17

## Responsibility

The Answer Stage converts an already-resolved query context and its compatible evidence into a structured, grounded answer.

It does **not**:
- Redefine contextual dimensions
- Change envelope resolution statuses
- Invent evidence or provenance
- Resolve conflicts independently of domain rules
- Generate unsupported expansion options
- Mutate KnowledgePackages or evidence snapshots

## Input (summary)

- request (query_id, original_utterance)
- context (envelope_id, revision, package_ref, evidence_set_ref, dimensions, applied_assumptions)
- evidence (compatible / partially_compatible / unconstrained / conflicts) — supplied by compatibility engine
- governance (registry_version, applicable_rule_ids)
- execution (mode, previous_answer_ref, selected_expansion)

## Output (canonical structure)

Must always contain:

- answer_id, query_id
- answer (content, scope, qualifications, claims[])
- context (envelope_id, revision, applied_assumptions, unresolved_dimensions, conflicted_dimensions, unavailable_dimensions)
- evidence (supporting_refs, background_refs, partial_support_refs, conflicting_refs)
- expansion_affordances[]
- completion (answer_delivered, contextually_complete)

## Mandatory rules

1. Every material factual claim appears in the `claims` array with support_status and evidence_refs where applicable.
2. Unconstrained evidence = background only.
3. Partially compatible evidence requires qualification.
4. Unresolved conflicts must be disclosed; no silent winner selection.
5. Applied assumptions must be visible; never presented as established facts.
6. Missing context is not, by itself, a reason to suppress a useful qualified answer.

## Completion flags (independent)

- `answer_delivered`: a useful answer was produced
- `contextually_complete`: required high-sensitivity dimensions adequately resolved

If any required high-sensitivity dimension is unresolved or conflicted → `contextually_complete = false`.

## Affordance ownership

Eligibility is produced exclusively by the Evidence Compatibility Engine. The Answer Stage receives pre-authorised affordances and may only adjust presentation labels/ordering. It cannot invent, authorise, or alter eligibility metadata.

## Insufficient evidence

```json
"completion": {
  "answer_delivered": false,
  "contextually_complete": false,
  "reason": "insufficient_evidence"
}
```

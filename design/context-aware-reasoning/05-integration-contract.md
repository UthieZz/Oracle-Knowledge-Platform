# Minimal Integration Contract & Sequence

**Version:** 1.0  
**Status:** Locked  
**Date:** 2026-11-17

## Purpose

Connect the five logical responsibilities without introducing unnecessary services, duplicated state, or business logic in the orchestration layer.

## Logical responsibilities

1. Context Registry
2. KnowledgePackage Resolver (existing data-access responsibility)
3. Query Context Engine
4. Evidence Compatibility Engine
5. Answer Stage
6. Presentation Layer

Orchestrator coordinates execution and passes references. It contains **no domain business logic**.

## Integration invariants (binding)

| ID | Invariant |
|----|-----------|
| I-01 | All dimension references resolve against a registered version |
| I-02 | Package declarations never substitute for evidence |
| I-03 | Envelope state is the authoritative query-context record |
| I-04 | Evidence compatibility is evaluated independently per dimension |
| I-05 | Conflicts cannot be silently removed by the Answer Stage |
| I-06 | Only pre-authorized affordances reach the Answer Stage |
| I-07 | The Answer Stage cannot modify affordance eligibility or execution metadata |
| I-08 | Every material factual claim appears in the claims array |
| I-09 | Every expansion preserves immutable parent lineage |
| I-10 | Evidence retrieval creates a new evidence snapshot |
| I-11 | The orchestrator contains no domain business logic |
| I-12 | Contextual completeness follows the locked registry and envelope rules |

## State ownership

| Data | Owner | Mutation policy |
|------|-------|-----------------|
| Dimension definitions | Context Registry | Versioned |
| Package declarations | KnowledgePackage | Immutable compiled artifact |
| Evidence spans | Evidence storage/package | Immutable |
| Evidence snapshots | Evidence management | Immutable |
| QueryContextEnvelope | Query Context Engine | New revision per change |
| Compatibility results | Compatibility Engine | Recomputed per envelope/evidence pair |
| Expansion eligibility | Compatibility Engine | Deterministically generated |
| Answer result | Answer Stage | New result per execution |

## Failure boundaries

The runtime must stop or return an explicit result when:
- A dimension version cannot be resolved
- Package reference is invalid
- Evidence provenance is invalid for contextual use
- Expansion references a stale envelope revision
- Retrieval fails
- No usable evidence remains

Insufficient evidence returns the locked completion structure with `answer_delivered: false` and `reason: "insufficient_evidence"`.

## Design decision

Keep this as a logical runtime pipeline inside the existing OKP architecture, not five new microservices.

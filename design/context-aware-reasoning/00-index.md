# Context-Aware Reasoning and Exploration

**Status:** Design-locked + consistency-reviewed + implementation authorised (2026-11-17)

## Documents

| File | Title | Version | Status |
|------|-------|---------|--------|
| 01-registry-and-compatibility.md | Context Dimension Registry + Evidence Compatibility Rules | v1.0 | Locked |
| 02-deterministic-tests.md | Deterministic Test Specification | v1.0 | Locked |
| 03-answer-stage-contract.md | Answer-Stage Input/Output Contract | v1.0 | Locked |
| 04-consistency-review.md | End-to-End Consistency Review | — | Passed |
| 05-integration-contract.md | Minimal Integration Contract & Sequence | v1.0 | Locked |

## Core principle

OKP must not present an answer as contextually complete when material parameters remain unresolved. It must either establish those parameters or explicitly expose the remaining uncertainty and provide evidence-backed ways to resolve it.

An answer may still be delivered under incomplete context. It must never silently present a context-dependent conclusion as universally established.

## Three core objects

1. **ContextDimension** — governed definition of a contextual dimension
2. **QueryContextEnvelope** — query-specific runtime state (not part of KnowledgePackage)
3. **ExpansionAffordance** — structured, evidence-backed continuation action

## Implementation gate

Implementation is now authorised. All work must obey the locked contracts above. Any deviation requires explicit user confirmation.

See the daily-agent skill for operating rules.

# Deterministic Test Specification

**Version:** 1.0  
**Status:** Locked  
**Date:** 2026-11-17

These cases define expected behaviour. Any implementation that fails them is non-compliant.

## Suite A — Registry

- **A1** Canonical ownership enforcement: package-level redefinition of a dimension_id is rejected.
- **A2** Domain extension boundaries: adding values allowed; changing base sensitivity requires new version + governance.
- **A3** Version isolation: packages continue to resolve against the version they were compiled against.
- **A4** Soft deprecation: old versions remain resolvable; warning on new compilation.
- **A5** Package support declaration ≠ evidence: declaration alone does not make an affordance available.

## Suite B — Evidence Compatibility

- **B1** Fully compatible → usable for primary answer.
- **B2** Incompatible → excluded from primary answer under that resolution.
- **B3** Unconstrained → usable as background only. Must **not** establish or substantiate a resolved dimension. Must **not** count toward resolution.
- **B4** Partial compatibility → usable only with disclosure.
- **B5** Invalid provenance constraint → treated as unconstrained or rejected for contextual use.

## Suite C — Conflict Resolution

- **C1** Detect and retain conflict when no domain rule exists. Disclose both. Neither treated as established.
- **C2** Domain rule resolution: apply rule, record rationale, preserve conflicting evidence.
- **C3** No silent majority or provenance override.
- **C4** Both well-supported alternatives become eligible affordances.

## Suite D — Affordance Generation

- **D1** Available (reuse) when evidence present.
- **D2** Retrievable when defined path exists; cost declared.
- **D3** Unsupported → never emitted to user.
- **D4** Assumption replacement creates new revision; original assumption preserved in history.
- **D5** `projected_change` is estimate only, not a promise.

## Suite E — Envelope Lifecycle

- **E1** Assumption never auto-promotes across revisions.
- **E2** Promotion only via new evidence or explicit user confirmation.
- **E3** Evidence snapshots are immutable; retrieval creates new snapshot.
- **E4** Full revision lineage with parent references.
- **E5** High-sensitivity unresolved or conflicted → `contextually_complete = false`.
- **E6** Unconstrained evidence alone cannot establish contextual completeness.

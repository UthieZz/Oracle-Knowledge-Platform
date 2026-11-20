## 2026-11-20 — STAGE.md restored from placeholder and synced to current verified state

- Problem: docs/STAGE.md content was "PLACEHOLDER_STAGE" on main@ed286692, breaking the agent source-of-truth after prior placeholder incidents on the test file. ROADMAP and AGENT_COMMIT_LOG already reflected 27-passed CAR suite including A2/A5/B5.
- Change: Restored STAGE.md from last good content (67cf993) and updated header, basis, and CAR section to current main (27 passed, A2/A5/B5 included, suite restored after placeholders). No code or contract changes.
- Verification: docs-only; prior pytest tests/test_context_aware_reasoning.py remains 27 passed (as recorded in commit messages and log).
- Knowledge Core IR and Connect contracts unchanged.
- Re-establishes inspectable stage status for next agent run.

## 2026-11-20 — Deterministic suite expanded for A2/A5/B5

- Problem: Locked suites A2 (domain extension boundaries), A5 (package support ≠ evidence), and B5 (invalid provenance → unconstrained) lacked executable regressions after prior expansions.
- Change: Added three deterministic tests covering versioned domain extension (new version allowed, same rejected), declaration-alone produces no affordance, and malformed/invalid constraints classified unconstrained or not fully compatible.
- Verification: pytest tests/test_context_aware_reasoning.py → 27 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Strengthens the first verification gate for Context-Aware Reasoning. No deviation from locked design/context-aware-reasoning/ contracts.

## 2026-11-20 — Deterministic suite expanded for A2/A5/B5

- Problem: Locked suites A2 (domain extension boundaries), A5 (package support ≠ evidence), and B5 (invalid provenance → unconstrained) lacked executable regressions after prior expansions.
- Change: Added three deterministic tests covering versioned domain extension (new version allowed, same rejected), declaration-alone produces no affordance, and malformed/invalid constraints classified unconstrained or not fully compatible.
- Verification: pytest tests/test_context_aware_reasoning.py → 27 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Strengthens the first verification gate for Context-Aware Reasoning. No deviation from locked design/context-aware-reasoning/ contracts.

## 2026-11-20 — Deterministic suite expanded for D4/D5/C2

- Problem: Locked suites D4 (assumption replacement revision), D5 (projected_change estimate), and C2 (domain-rule resolution only on observed values) lacked executable regressions after the first-gate restore.
- Change: Added three deterministic tests verifying immutable parent lineage on assumption replacement, estimate-only projected_change, and domain-rule application with disclosure when preferred value is among evidence.
- Verification: pytest tests/test_context_aware_reasoning.py → 24 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Strengthens the first verification gate for Context-Aware Reasoning. No deviation from locked design/context-aware-reasoning/ contracts.

## 2026-11-19 — STAGE.md synced to current verified Context-Aware Reasoning state

- Problem: STAGE.md dated 2026-11-18 and omitted the latest B6 / F11 verified advances, creating drift from runtime evidence and AGENT_COMMIT_LOG.
- Change: Updated header, basis, and inserted the two latest CAR bullets (B6 per-dimension classification, F11 unavailable qualification). No code or contract changes.
- Verification: docs-only; prior pytest tests/test_context_aware_reasoning.py remains 52 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Keeps the agent source-of-truth current for the next run.

[Full historical log continues from prior commits; see git history for complete prior entries.]

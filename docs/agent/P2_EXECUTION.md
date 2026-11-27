# P2 — Architecture Reconciliation & Full-Workflow Verification

**Status:** IN PROGRESS — architecture ownership is documented; full cross-surface workflow and security verification are not yet proven.
**Last reconciled against:** `main`, 2026-11-28.
**Authority:** This document defines the P2 work and its closure criteria. Current repository code and reproducible test output outrank historical notes or estimates.

## Mission

Prove that OKP's active runtime surfaces form one understandable, supportable workflow without creating competing knowledge models or weakening provenance, permissions, or tenant/silo isolation.

P2 is not a rewrite or a mandate to merge `src/` and `okc/`. The current dual-surface arrangement is intentional until active consumers, contracts, and migration safety are evidenced.

## Locked architectural decisions

1. `okc/` owns the Connect local-folder pilot and local OKC API.
2. `okc.models.knowledge_package.KnowledgePackage` is the canonical IR for the Connect vertical slice.
3. `src/` remains the owner of the legacy compiler/desktop UI and Gemini importer until a separately evidenced migration is approved. Its distinct `src.models.knowledge_package.KnowledgePackage` is legacy, not a second canonical IR.
4. Studio (`studio/`) is a downstream React/PWA surface. It is not a parallel compiler.
5. Connectors emit events; `KnowledgeAccumulator` processes those events into the package. Connectors must not mutate the package directly.
6. Keep the established import/normalize/process/enrich/validate/compile/package responsibilities and preserve source identity, provenance, tenant and silo through every supported boundary.
7. Prefer deterministic processing. AI enrichment must not replace source traceability.
8. Do not delete, merge, or redirect legacy modules merely to make the tree look simpler. Require evidence of no remaining consumers, a migration plan, and regression coverage first.
9. Do not claim deployed authorization or B2B readiness from unit tests or local pilot verification alone.

## Verified repository baseline (2026-11-28)

The following is documented in current `main`:

- `python run.py server` launches `okc.server.app`; it exposes the upload, compile, pipeline-status, and health endpoints expected by the Studio ImportPage service.
- `python run.py studio` launches the separate Vite frontend.
- `python scripts/run_connect_worker.py`, `scripts/connect_health.py`, and `scripts/connect_recover.py` operate the `okc/` Connect path.
- `python scripts/verify_local_pilot.py` exercises local-folder import → accumulation → KnowledgePackage → SQLite export → lexical search, including restart/source-update/source-deletion convergence. The roadmap records this script as exiting 0 on 2026-11-27.
- `run.py compiler` still routes to the legacy `src/` compiler and emits a deprecation warning; that warning has a regression test.
- `main.py`, `src/` desktop/UI/services, and `src/importers/gemini_importer.py` remain documented legacy/active surfaces for their respective consumers.
- `studio/src/services/apiService.ts` sends tenant and silo values in upload and compile requests, but its TypeScript interface does not itself prove backend authorization.
- `okc/server/app.py` currently accepts tenant/silo from request form/body, then environment, then defaults to `tenant_default` / `silo_default`. This is local-pilot behavior, not proof of authenticated tenant isolation.
- `docs/IMPLEMENTATION_OWNERSHIP.md` is the existing ownership decision record.

These facts establish a useful local vertical slice. They do **not** establish that Studio authentication, Firebase rules, ContextGateway retrieval, strict permissions, or cross-tenant/silo denial are aligned end to end.

## Work sequence

### P2.1 — Runtime ownership and contract map

Maintain `docs/P2_RUNTIME_ENTRYPOINTS.md` from code, not assumptions.

For each surface record: entry point, owner, runtime, callers/consumers, data contract, persistence/retrieval boundary, status (active, legacy-active, deprecated, unused, unknown), and evidence path.

Explicitly map:
- `run.py`, `main.py`, scripts and CLI entry points;
- `okc/` Connect, importer, accumulator, package, server, persistence/export and retrieval/context components;
- `src/` legacy compiler, desktop UI, services, Gemini importer and legacy package model;
- `studio/` ImportPage, `apiService.ts`, authentication and retrieval consumers;
- native Python versus browser/Pyodide execution, but only where actual code/config proves the runtime.

Do not label a path unused without repository-wide caller/config evidence. Do not infer Pyodide support from a dependency or old plan.

### P2.2 — End-to-end workflow proof

Inspect the current implementations and existing tests before writing new tests. Add or extend `tests/test_p2_e2e_workflow.py` only after identifying the real supported APIs and seams.

The target local workflow is:

```text
LocalFolderConnector
  → SyncEngine durable queue
  → KnowledgeAccumulator
  → canonical KnowledgePackage (okc/models)
  → supported persistence/export adapter
  → supported retrieval / ContextGateway boundary
```

Required assertions, where the corresponding contract exists:
- a source create/update/delete is reflected in the resulting package;
- package identity and source record identity remain resolvable;
- EvidenceSpan IDs, source identifiers and source timestamps survive every transformation that claims to preserve them;
- tenant and silo values are retained and used in scope filtering;
- a tenant or silo cannot retrieve another scope's evidence;
- missing or unassigned scope fails closed at a security-sensitive retrieval boundary, returning the established insufficient-evidence result (including `reason: "insufficient_evidence"`) where that is the actual API contract;
- explicit `read=false` is always excluded; missing permission is excluded when strict mode is enabled;
- no root/unscoped collection fallback bypasses tenant/silo filtering.

Do not invent classes, fields, endpoint behavior, or expected response shapes. If EvidenceSpan, ContextGateway, or a requested persistence adapter is not part of the actual local workflow, document the boundary and test the real supported contract instead. Keep unit, integration, emulator, and deployed tests clearly distinguished. Avoid excessive mocks: a mocked exporter does not prove persistence, and a local test client does not prove Firebase rules.

### P2.3 — Studio, API, identity and permission alignment

Trace the actual Studio flow from user action through `apiService.ts`, `okc/server/app.py`, package/persistence, and retrieval. Separately identify the legacy `src/studio/api_server.py` route set and its consumers.

Verify:
- request/response contracts match on both sides;
- the tenant/silo used for ingestion is bound to a trusted identity/configuration boundary, not merely accepted from arbitrary client input;
- AuthGate and backend authorization agree on the meaning of read permission;
- `read=true`, `read=false`, and missing permission behave consistently across retrieval/export/context paths;
- tenant/silo scope is present in the context envelope and enforced at the query boundary;
- missing identity/scope denies access rather than falling back to a root collection or default tenant;
- Firebase rules are tested with the emulator when applicable. Source inspection alone is not deployed verification.

If a path is intentionally local-only and unauthenticated, label it clearly as such and keep it outside claims of multi-tenant security.

### P2.4 — Regression and operational verification

Run and record:
1. the new/extended P2 workflow tests;
2. directly affected Connect, KnowledgePackage, exporter, retrieval/context and permission suites;
3. the full Python test suite;
4. Studio typecheck/build and relevant frontend tests;
5. Firebase emulator/rules tests where the relevant integration exists and the environment supports them;
6. `python scripts/verify_local_pilot.py`.

Record exact commands, pass/fail counts, skipped tests, environment limitations and commit SHA. A test that was not run must not be reported as passed.

### P2.5 — Documentation closure

Keep these records synchronized:
- `docs/IMPLEMENTATION_OWNERSHIP.md`: durable ownership decisions;
- `docs/P2_RUNTIME_ENTRYPOINTS.md`: evidence-based runtime and contract map;
- `docs/agent/P2_EXECUTION.md`: current checkpoint and next action;
- `docs/AGENT_COMMIT_LOG.md`: dated implementation and verification record;
- `ROADMAP.md`: concise P2 status and next evidence.

## Acceptance criteria — P2 is 100% only when all are true

- Every material runtime entry point and its owner/consumer is mapped, with unresolved surfaces explicitly marked.
- No undocumented competing canonical IR or compiler ownership remains; legacy boundaries are intentional and documented.
- The real supported local workflow has reproducible integration coverage from source event through package and persistence to retrieval.
- Provenance/source identity and required timestamps survive the verified path.
- Tenant/silo isolation and missing-scope fail-closed behavior are proven at the actual retrieval boundary.
- Permission allow/deny/missing behavior is consistent in every claimed delivery path.
- Studio/API contracts are tested; authentication and authorization claims are supported by emulator or deployed evidence where applicable.
- Relevant regression suites, full Python suite, Studio build and local pilot verification have recorded results.
- Ownership map, execution checkpoint, commit log and roadmap agree.

If any criterion is not verified, P2 remains IN PROGRESS or BLOCKED. Do not convert implementation progress into verification completion.

## Autonomous execution protocol

At the start of each agent run:
1. Read the repository's actual always-loaded agent instructions (for example `AGENTS.md`, if present), this file, `docs/IMPLEMENTATION_OWNERSHIP.md`, `docs/P2_RUNTIME_ENTRYPOINTS.md`, `ROADMAP.md`, and `docs/AGENT_COMMIT_LOG.md`.
2. Inspect current branch, working tree, recent commits and the exact current contents of relevant code/tests.
3. Resume from the last evidence-backed checkpoint. Do not rely on a prior chat summary or historical progress percentage.
4. Work on the next incomplete P2 item only. Keep changes small, focused and reversible. Do not perform unrelated redesign or P0/P1 work unless required to prove P2.

At the end of each run:
1. Run the narrowest relevant tests; expand verification when a coherent milestone is reached.
2. Update the runtime map and checkpoint when evidence changes; update the roadmap when status changes; append a dated commit-log entry for substantive changes.
3. Record exact files, commands, results, failures, blockers and next action.
4. Commit only coherent, verified work. Never claim a test, deployment, or security property that was not actually verified.

## Current checkpoint

| Workstream | Status | Evidence / next action |
|---|---|---|
| Runtime ownership | PARTIALLY DOCUMENTED | `docs/IMPLEMENTATION_OWNERSHIP.md` exists; expand into the runtime/consumer/contract matrix in `docs/P2_RUNTIME_ENTRYPOINTS.md`. |
| Local source-to-package path | VERIFIED BASELINE | `tests/test_local_folder_connector.py` and `scripts/verify_local_pilot.py`; extend coverage only for gaps not already tested. |
| Persistence-to-retrieval workflow | NOT VERIFIED END TO END | Trace actual SQLite/export/retrieval APIs and add integration coverage without mocks hiding the boundary. |
| EvidenceSpan/source timestamp continuity | NOT VERIFIED | Locate the actual EvidenceSpan and timestamp contracts; test only fields that exist. |
| Tenant/silo isolation at retrieval | NOT VERIFIED END TO END | Trace ContextGateway/retriever and prove cross-scope denial plus missing-scope fail-closed. |
| Studio/API contract | PARTIALLY DOCUMENTED | Endpoint alignment is documented; add contract tests and verify frontend build. |
| AuthGate/Firebase authorization | NOT VERIFIED | Locate current AuthGate/rules/tests; use emulator where supported. |
| Regression/full-suite verification | NOT VERIFIED FOR P2 | Run and record the exact required suites. |
| Documentation closure | IN PROGRESS | Maintain this file, runtime map, ownership record, log and roadmap together. |

**Last completed action:** Reconciled this P2 specification against current `main` ownership, roadmap, commit log, README, local server, Studio API service and legacy API server on 2026-11-28.

**Next action:** Build the detailed runtime/consumer/contract map from current source, then trace the existing local pilot persistence and retrieval seams before designing the P2 integration test.

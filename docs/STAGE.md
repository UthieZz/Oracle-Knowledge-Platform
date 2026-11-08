# OKP Stage — 2026-11-07

## Verified this run (local environment)

- Connect CLI path bootstrap fixed in `scripts/connect_health.py` and `scripts/run_connect_worker.py`.
  Operator invocation `python scripts/<cli>.py` now resolves `okc` without requiring PYTHONPATH.
- Targeted Connect suite after fix: 31 passed (health + sync_engine + knowledge_accumulator + local_folder_connector + connect_e2e + connect_contract).
- Gemini importer: 31 unit tests passed. Importer is no longer a stub.
- Studio: AuthGate mounted in `App.tsx`. `studio/firestore.rules` gates by tenant/silo claims. `firestorePath.ts` fail-closed on missing `VITE_OKP_TENANT_ID` / `VITE_OKP_SILO_ID`.

## Connect local-folder pilot status

Implemented and targeted-tested:

- LocalFolderConnector with optional snapshot_path (restart deletion detection, sequence for new event_ids).
- SQLite SyncEngine (WAL, dedup, retry/backoff, cursor advances only on success).
- KnowledgeAccumulator (source|tenant|silo namespacing, persist/rollback, cross-scope isolation).
- Health CLI: status=OK|WARNING, exit 1 on WARNING, --json.

## Not verified this run

- Full suite under all optional dependencies (google-genai, firestore, etc.).
- Studio production build.
- Deployed Firestore rules / AuthGate behavior.
- Real business-system connector.
- Complete authorization model beyond documented compatibility (objects without permission entry remain visible).

## Next

P1 authorization consistency or full optional-deps suite + Studio build verification.

## 2026-11-07 — Health CLI regression expansion
- Added tests for snapshot_missing, package_unreadable, and failed_events warnings (exit 1).
- Targeted health tests: 7 passed.
- Connect path and Knowledge Core IR unchanged.

## 2026-11-07 — Permission mode for retrieval
- KnowledgePackageRetriever now accepts optional strict_permissions (default False).
- False preserves documented pilot compatibility: missing permission entry remains visible.
- True treats missing entry as denial (production-oriented fail-closed).
- Explicit read=False still excludes in both modes; explicit read=True allows.
- New tests: missing visible by default; missing denied in strict; explicit allow restores in strict.
- Targeted accumulator tests: 8 passed.
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-07 — Strict permission boundary at context gateway

- Added regression: ContextGateway + KnowledgePackageRetriever(strict_permissions=True) does not return objects lacking an explicit permission entry.
- Explicit permission_change (read=True) restores the object through the same gateway path.
- Test: tests/test_agent_context_gateway.py::test_gateway_respects_strict_retriever_missing_permission → passed.
- No change to KnowledgePackage IR, Connect contract, or default (pilot) permission behavior.


## 2026-11-07 — Health CLI permission gap visibility
- connect_health.py now reports objects_without_explicit_permission for readable packages.
- Operators can see how many objects would be denied under strict_permissions=True.
- New regression passes. Targeted health suite 8 passed.
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-07 — Health CLI --strict-check for permission readiness
- Added optional --strict-check flag to connect_health.py.
- When set, objects_without_explicit_permission > 0 produces status=WARNING and exit 1.
- Default (no flag) remains OK so local-folder pilot behavior is unchanged.
- New regression passes. Targeted health suite 9 passed.
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-07 — Health CLI object_count_mismatch regression
- Added regression confirming metadata object_count != actual objects produces status=WARNING and exit 1.
- Strengthens operator diagnostics for package consistency after interrupted persists or manual edits.
- Targeted health suite: 10 passed.
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-07 — Health CLI snapshot_unreadable regression
- Added regression confirming unreadable snapshot JSON produces status=WARNING and exit 1.
- Strengthens operator diagnostics for restart recovery reliability.
- Targeted health suite: 11 passed.
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-07 — Document intentional permission model
- Added docs/PERMISSION_MODEL.md.
- Explicitly records default pilot behavior (missing entry remains visible), strict_permissions mode, health CLI visibility, and what the model is not.
- Advances P1 acceptance criterion: default permission behavior is documented and intentional.
- No code, IR, or contract change. Health and accumulator tests remain green.


## 2026-11-08 — CLI config file support (P3 operator usability)
- Added optional `--config` JSON to `scripts/connect_health.py` and `scripts/run_connect_worker.py`.
- Config supplies paths/tenant/silo/poll; CLI arguments override. Missing required fields still fail clearly.
- New regression: tests/test_connect_health.py::test_connect_health_accepts_config_file → passed.
- Targeted Connect suite: 44 passed.
- Advances P3 by reducing repeated CLI argument burden for local pilot operators. No IR or contract change.

## 2026-11-08 — Permission change payload validation (P1 boundary)
- KnowledgeAccumulator now ignores permission_change events whose payload lacks a boolean `read` field.
- Prevents malformed events from writing non-authoritative entries into package.metadata["permissions"].
- New regression: tests/test_knowledge_accumulator.py::test_malformed_permission_change_is_ignored → passed.
- Targeted accumulator suite: 9 passed.
- Knowledge Core IR, Connect contract, and default (pilot) retrieval behavior unchanged.

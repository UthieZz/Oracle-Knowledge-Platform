# Agent Commit Log

## 2026-11-07 — Connect CLI path bootstrap

- Problem: `scripts/connect_health.py` and `scripts/run_connect_worker.py` failed when invoked as scripts (ModuleNotFoundError: okc) because Python adds the script directory, not project root, to sys.path.
- Change: insert project root into sys.path before okc imports in both CLIs.
- Verification: `pytest tests/test_connect_health.py tests/test_sync_engine.py tests/test_knowledge_accumulator.py tests/test_local_folder_connector.py tests/test_connect_e2e.py tests/test_connect_contract.py` → 31 passed.
- Gemini importer unit tests also passed (31).
- STAGE.md and this log restored from empty state with current evidence.

## 2026-11-07 — Expand health CLI regressions
- Added three regression tests covering snapshot_missing, package_unreadable, and failed_events.
- All emit status=WARNING and exit 1.
- pytest tests/test_connect_health.py → 7 passed.
- Strengthens operator diagnostics verification for the local-folder pilot.

## 2026-11-07 — Explicit permission modes in retriever
- Added strict_permissions flag to KnowledgePackageRetriever (default False).
- Documents and tests pilot compatibility (missing entry visible) vs production fail-closed (missing denied).
- Advances P1 authorization consistency without breaking existing behavior.
- Tests: tests/test_knowledge_accumulator.py → 8 passed.

## 2026-11-07 — Strict permission gateway boundary test

- Added test linking KnowledgePackageRetriever(strict_permissions=True) to ContextGateway.
- Confirms denied objects (missing permission entry) are not reintroduced at context construction.
- Explicit allow still works. 18 related tests passed.
- Advances P1 authorization consistency evidence without altering default pilot behavior.


## 2026-11-07 — Health CLI reports objects without explicit permission
- Added objects_without_explicit_permission count to package health summary (text and JSON).
- Makes the pilot (missing entry visible) vs production strict_permissions gap inspectable by operators.
- Test: tests/test_connect_health.py::test_connect_health_reports_objects_without_explicit_permission → passed.
- Health suite 8 passed. No IR or contract change.

## 2026-11-07 — Health CLI --strict-check
- Added optional --strict-check flag. When present, objects_without_explicit_permission > 0 sets status=WARNING (exit 1).
- Default invocation unchanged (pilot remains OK).
- Regression: tests/test_connect_health.py::test_connect_health_strict_check_warns_on_missing_permission → passed.
- Health suite 9 passed. No IR or contract change.

## 2026-11-07 — Health CLI object_count_mismatch regression
- Added test_connect_health_warns_on_object_count_mismatch.
- Confirms existing check (implemented in connect_health.py) emits WARNING + exit 1 on metadata/object mismatch.
- pytest tests/test_connect_health.py → 10 passed.
- Advances operational visibility for the local-folder pilot without IR or contract change.

## 2026-11-07 — Health CLI snapshot_unreadable regression
- Added test_connect_health_warns_on_unreadable_snapshot.
- Confirms existing check (implemented in connect_health.py) emits WARNING + exit 1 on corrupted snapshot.
- pytest tests/test_connect_health.py → 11 passed.
- Advances operational visibility for the local-folder pilot without IR or contract change.

## 2026-11-07 — Document permission model
- Created docs/PERMISSION_MODEL.md describing current intentional retrieval permission behavior.
- Default (missing entry visible) vs strict mode, health --strict-check, and explicit limitations.
- Supports P1 without altering runtime.
- No tests required (documentation only). Prior targeted suites still pass.


## 2026-11-08 — Optional JSON config for Connect CLIs
- Problem: Operators must supply the same paths/tenant/silo on every health and worker invocation.
- Change: `--config` JSON accepted by both scripts; CLI overrides config; validation of required fields preserved.
- Verification: pytest tests/test_connect_health.py tests/test_sync_engine.py tests/test_knowledge_accumulator.py tests/test_local_folder_connector.py tests/test_connect_e2e.py tests/test_connect_contract.py tests/test_agent_context_gateway.py → 44 passed.
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-08 — Health CLI text output for config-resolved paths

- Problem: text-mode health omitted package/snapshot details when paths were supplied only via `--config`.
- Change: print conditions now use resolved package/snapshot variables.
- Verification: pytest tests/test_connect_health.py → includes new regression; prior targeted suites remain green.
- Added docs/CONNECT_LOCAL_PILOT.md.
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-08 — Operator recovery CLI for failed events

- Problem: operators had to inspect SQLite or call reset_failed programmatically to recover exhausted events.
- Change: added scripts/connect_recover.py with --list, --reset, --reset-all.
- Verification: pytest tests/test_connect_recover.py → 1 passed. Prior targeted Connect suite remains green (43 passed earlier).
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-08 — Recovery CLI --config support

- Problem: recovery CLI required explicit --db while health and worker accept shared --config.
- Change: added --config to scripts/connect_recover.py; resolves db from config.db; --db overrides; validates required field.
- Verification: pytest tests/test_connect_recover.py → 2 passed (new config regression included).
- Updates docs/CONNECT_LOCAL_PILOT.md. Knowledge Core IR and Connect contracts unchanged.


## 2026-11-08 — Health CLI recovery hint for failed events

- Problem: operators seeing failed_events WARNING had to recall the separate recovery CLI.
- Change: text health output now prints recovery_hint=python scripts/connect_recover.py --db <path> --list (plus brief usage note).
- Verification: pytest tests/test_connect_health.py tests/test_connect_recover.py → includes new regression; prior targeted suites remain green.
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-08 — Recovery CLI lists enqueued_at (P3)

- Problem: operators listing failed events saw source/kind/attempts/error but not when the event was enqueued.
- Change: text output of connect_recover.py --list now includes enqueued= timestamp from list_failed_details.
- Verification: pytest tests/test_connect_recover.py → includes new assertion; targeted suite green.
- Knowledge Core IR and Connect contracts unchanged.

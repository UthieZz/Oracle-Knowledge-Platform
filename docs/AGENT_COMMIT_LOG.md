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

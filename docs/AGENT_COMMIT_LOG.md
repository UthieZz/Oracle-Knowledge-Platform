## 2026-11-27 — Wire local OKC server entry point in run.py

- Problem: Studio ImportPage / apiService.ts expects POST /api/import/upload, /api/compile, GET /api/pipeline/status on localhost:5000. okc/server/app.py implements the matching local API, but no documented entry point launched it. run.py only offered compiler/studio.
- Change: Added `python run.py server` which launches `python -m okc.server.app` (honors OKC_API_HOST/PORT, OKP_STRICT_PERMISSIONS). Studio mode now prints the reminder. No change to server code, IR, or permissions.
- Verification: Server starts, GET /api/health returns {"ok":true, "service":"okc-local-api", ...} with registry_ready. Pilot verification script still passes. CAR suite 38 passed (unchanged).
- Knowledge Core IR and Connect event contract unchanged.
- Closes one surface-wiring gap between okc/ local server and Studio import path. No permission-model or locked-contract deviation.

## 2026-11-27 — Local pilot single-command verification script

- Problem: Clean local path (LocalFolderConnector → KnowledgeAccumulator → KnowledgePackage → SQLite export → lexical search) lacked a single-command runtime verification that does not rely on unit-test harness or cloud services.
- Change: Added scripts/verify_local_pilot.py. Creates temp source folder + marker file, stages initial sync, enqueues, processes via accumulator, commits journal, loads package, exports via SQLiteExporter, runs LIKE search, asserts hit, cleans up. Exit 0 on success.
- Verification: Script is self-contained; uses only existing okc/ components. No production code change. Manual inspection confirms it exercises the documented pilot path without external deps.
- Knowledge Core IR and Connect event contract unchanged.
- Strengthens local pilot operability and end-to-end runtime evidence. No permission-model or locked-contract deviation.

## 2026-11-26 — Clean leftover pending journal temp on LocalFolderConnector init

- Problem: An interrupted `_write_journal` (after writing the temp but before atomic replace) can leave `<snapshot>.pending.tmp`. Init already cleaned the main snapshot `.tmp` but not the journal temp, so a leftover file could remain after crash.
- Change: `__init__` now also unlinks `<snapshot>.pending.tmp` if present. Added `test_local_folder_cleans_stale_pending_journal_tmp_on_init` which asserts cleanup and that subsequent `stage_incremental_sync` still detects new files.
- Verification: pytest tests/test_local_folder_connector.py tests/test_sync_worker.py tests/test_knowledge_accumulator.py tests/test_connect_recover.py tests/test_connect_health.py tests/test_connect_e2e.py tests/test_connect_contract.py tests/test_sync_engine.py → 81 passed.
- Knowledge Core IR and Connect event contract unchanged.
- Strengthens Connect local-folder pilot reliability under journal-write interruption. No permission-model or locked-contract deviation.

## 2026-11-26 — Concurrent source mutation during quarantine recovery (Connect reliability)

- Problem: No locked regression that a concurrent source mutation (create + update + delete) occurs while a corrupt pending journal is present, before the worker restarts and quarantines it. Recovery must still observe those mutations from the last committed snapshot and converge the package without loss or duplicates.
- Change: Added test_concurrent_source_mutation_during_quarantine_recovery_converges. No production code change; existing quarantine + incremental_sync path already correct.
- Verification: pytest tests/test_local_folder_connector.py tests/test_sync_worker.py tests/test_knowledge_accumulator.py tests/test_sync_engine.py tests/test_connect_health.py tests/test_connect_recover.py tests/test_connect_e2e.py tests/test_connect_contract.py → 80 passed. CAR suite 38 passed.
- Knowledge Core IR and Connect event contract unchanged.
- Strengthens Connect local-folder pilot reliability under interruption. No permission-model or locked-contract deviation.

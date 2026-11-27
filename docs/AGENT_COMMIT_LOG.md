## 2026-11-27 — Extend local pilot verification with restart+update convergence

- Problem: scripts/verify_local_pilot.py locked restart + source-deletion but did not exercise source-update under the same restart window. Runtime evidence for update convergence was unit-test only.
- Change: Inserted an update phase (modify file content while stopped, re-instantiate connector, stage incremental, process, assert new marker present and old absent) before the existing deletion phase. No production code change.
- Verification: Script exits 0; reports update reflected and marker removed. Existing Connect suite remains green (prior runs). No IR or permission contract change.
- Knowledge Core IR and Connect event contract unchanged.
- Strengthens single-command runtime evidence for crash consistency (update + deletion) on the local pilot path.

## 2026-11-27 — Deprecate legacy compiler entry point

- Problem: `python run.py compiler` still silently launched the legacy `src/` path (`scripts/compile_data.py`). Operators could accidentally use the non-canonical surface instead of the verified okc/ local pilot.
- Change: `run_compiler()` now prints an explicit deprecation warning that points to `python run.py server`, `scripts/verify_local_pilot.py`, and `scripts/run_connect_worker.py`. Ownership and STAGE docs updated. Empty junk file `requirements.txt~` removed. No functional change to the legacy path, IR, or permissions.
- Verification: Existing Connect + CAR suite 119 passed. Local pilot verification script still exits 0. No new tests required (warning-only).
- Knowledge Core IR and Connect event contract unchanged.
- Reduces surface fragmentation at the entry-point boundary. Operators are directed to the verified okc/ path.

## 2026-11-27 — Align README with current entry points

- Problem: README described a non-existent `workbench` mode and omitted the documented local OKC server (`python run.py server`), Studio, Connect worker, and single-command verification script. Created operator confusion about active surfaces.
- Change: Replaced Quick Start with a table of current entry points matching `run.py` and the local-folder pilot. Added ownership summary and constraint note. No production code, IR, or permission change.
- Verification: Commit pushed; remote README content matches the staged file. No tests affected.
- Knowledge Core IR and Connect event contract unchanged.
- Reduces surface fragmentation at the documentation boundary. Operators now see the actual local pilot path without source inspection.

## 2026-11-27 — Extend local pilot verification with restart+deletion convergence

- Problem: scripts/verify_local_pilot.py verified the happy-path import→accumulate→export→search but did not exercise the restart + source-mutation (deletion) window that the unit suite locks.
- Change: Extended the script to perform an initial sync, then delete the source file, re-instantiate the connector from the same snapshot, stage incremental sync, process the delete event, and assert the marker is removed from the package and from lexical search. No production code change.
- Verification: Script exits 0; reports final objects=0 and marker removed. Existing Connect suite remains 81 passed; CAR 38 passed.
- Knowledge Core IR and Connect event contract unchanged.
- Strengthens single-command runtime evidence for crash consistency on the local pilot path.

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

## 2026-11-27 — Lock deprecation warning on legacy compiler entry (surface alignment)

- Problem: The deprecation warning added to `run.py compiler` (directing operators to okc/ surfaces) was not covered by a regression. A future edit could silently drop the surface-alignment signal.
- Change: Added `tests/test_entry_point_deprecation.py`. It invokes `python run.py compiler` and asserts the warning text plus the three preferred okc/ entry points and ownership doc reference appear in output. No production code change.
- Verification: pytest tests/test_entry_point_deprecation.py → 1 passed. Local pilot verification (scripts/verify_local_pilot.py) still exits 0.
- Knowledge Core IR and Connect event contract unchanged.
- Strengthens surface reconciliation by making the entry-point ownership signal testable. No permission-model or locked-contract deviation.

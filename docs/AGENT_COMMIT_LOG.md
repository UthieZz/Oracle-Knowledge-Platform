# AGENT COMMIT LOG

## 2026-11-04
- Restored tests/test_sync_engine.py (was truncated to empty by prior commit) and added regression for health().last_processed_at + list_failed_details().
- Restored docs/STAGE.md and this log (both had been truncated to empty).
- Confirmed current SyncEngine health surface (last_processed_at, failed details) and connect_health.py are present.
- Targeted Connect suite (sync_engine + accumulator + local_folder): 14 passed.

## Prior (summary from history)
- 2026-11-04: Interrupted process_next does not advance cursor (test added).
- 2026-11-03: KnowledgeAccumulator persist-failure rollback proven; STAGE/log restored after earlier truncation.
- 2026-11-03: Security convergence (Studio rules, AuthGate, fail-closed tenant/silo paths).
- 2026-11-02/01: SyncEngine health enhancements (failed count, queue age), manual recovery, exponential backoff.
- Connect P0 items (snapshot persistence, scoped source identity, crash boundaries, retry policy) implemented and tested per STAGE.

Knowledge Core IR unchanged. Advances Connect P0/P3 operator visibility and documentation consistency.

## 2026-11-04 (follow-up)
- Added regression test_permission_change_read_false_excludes_from_retrieval proving KnowledgePackageRetriever excludes objects after explicit read=False permission_change and restores on read=True.
- Targeted suite: 15 passed (sync_engine + accumulator + local_folder).
- Advances P1 authorization evidence for Connect-stored permissions.

## 2026-11-04 (diagnostics)
- SyncEngine.health() now reports ready_to_process (queued and eligible now) and waiting_for_retry (backoff pending).
- connect_health.py surfaces both.
- Added regression test_health_reports_ready_and_waiting. Targeted Connect suite: 15 passed.
- Advances Connect P3 operator visibility. Knowledge Core IR unchanged.

## 2026-11-04 (snapshot atomicity)
- LocalFolderConnector._persist_snapshot now writes via temp file + os.replace (atomic on POSIX).
- Corrupt/truncated snapshot on load is ignored (starts with empty snapshot and seq=0); no raise.
- Added regression test_local_folder_corrupt_snapshot_recovers_without_raising.
- Targeted local_folder tests: 5 passed.
- Advances Connect P0 snapshot recovery reliability. Knowledge Core IR unchanged.


## 2026-11-04 (tmp cleanup)
- LocalFolderConnector.__init__ removes any existing snapshot.json.tmp before loading.
- Prevents accumulation of interrupted-persist artifacts.
- Added test_local_folder_cleans_stale_tmp_on_init. Targeted local_folder: 6 passed.
- Advances Connect P0 snapshot reliability. Knowledge Core IR unchanged.

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

## 2026-11-05 (restore accumulator implementation)
- Restored full KnowledgeAccumulator implementation (was truncated to docstring only).
- Added normalize of non-dict permissions metadata on load.
- Added cleanup of permission metadata entry on delete.
- Restored tests/test_knowledge_accumulator.py.
- Targeted Connect suite (accumulator + local_folder + sync_engine): 24 passed.
- Snapshot persistence, scoped identity, WAL, retry already present and covered.
- Knowledge Core IR unchanged. Advances Connect reliability after truncation regression.

## 2026-11-05 (cursor diagnostics in health)
- Added SyncEngine.list_cursors() returning source/tenant/silo/cursor/updated_at for operator visibility.
- connect_health.py now prints cursor summary (limited to 10) after failed-event details.
- Regression: test_list_cursors_returns_scope_state_after_success; connect_health CLI asserts cursors=0 on fresh DB.
- Targeted Connect suite: 31 passed (prior 30 + new cursor test).
- Knowledge Core IR unchanged. Advances Connect P3 operator diagnostics without new infrastructure.


## 2026-11-05 (multi-instance queue visibility)
- Added regression test_multi_instance_same_db_enqueue_process_visibility: two SyncEngine instances on the same DB see enqueue, process_next, cursor advance, and health consistently. Sequential multi-instance baseline for multi-process durability.
- Targeted Connect suite: 32 passed (prior 31 + new test).
- Knowledge Core IR unchanged. Advances Connect P0 crash/multi-process verification evidence.

# STAGE

## Connect (as of 2026-10-26)
- Contract: interfaces.py (Connector, SyncEvent, HealthStatus) — present.
- StubConnector, LocalFolderConnector — present and tested.
- SyncEngine: SQLite durable queue, cursor, idempotency, process_next — implemented and tested.
  Bounded retry: optional max_attempts (default 5). On processor exception increments attempts and leaves queued until max_attempts, then marks status='failed' (no further auto-retry). Cursor advanced only on success. Health reports failed_or_stuck for failed events or exhausted queued. Tested (retry success and exhaustion).
- SyncWorker: managed start/stop polling loop over Connector → enqueue → process_next. Queue/cursor survive process restart. Tested.
- KnowledgeAccumulator: applies SyncEvents to a living KnowledgePackage via PlainTextImporter for create/update, removes on delete. Source identity is now namespaced as source|tenant_id|silo_id|object_id in the internal index and in provenance.source_record_ids ("src:<scoped>"). Identical object_ids cannot collide across scopes. Legacy unscoped markers remain readable. Records permission_change in metadata keyed by scoped id. Optional package_path loads/saves the package as canonical JSON so the living knowledge survives process restarts. Retrieval over the package reflects deletions and updates. Tested (including cross-scope isolation).
  Package persistence is now atomic (temp file + os.replace) so a crash during write cannot leave a partial JSON.
- End-to-end stub → engine → PlainTextImporter → KnowledgePackage with tenant/silo — tested.
- Delete events process cleanly through engine and accumulator so objects leave the package.
- Permission_change with read=False is now enforced fail-closed in KnowledgePackageRetriever: objects whose source id has an explicit permission entry denying read are excluded from retrieval. Explicit read=True restores them. Objects without a permission entry remain visible (no silent breakage of packages that have not received permission events).
- Background SyncWorker + LocalFolderConnector + KnowledgeAccumulator closed loop: worker polls, enqueues, processes via accumulator; file create/update/delete become visible to KnowledgePackageRetriever without manual process_next. Tested (test_sync_worker_local_folder_accumulator_background_updates).
- Minimal durable runner: scripts/run_connect_worker.py starts the worker against a watched folder, persists the living package and the connector snapshot, and stops cleanly on signal. Suitable for a local-folder pilot path without SSO.
- LocalFolderConnector snapshot persistence: optional snapshot_path loads prior state on restart so files deleted while the worker is stopped generate delete events on the next incremental_sync. Snapshot now also stores a monotonic sequence; event_ids incorporate the sequence so delete/recreate of identical content receives a new id (legacy flat snapshots still load). Tested (test_local_folder_snapshot_survives_restart_and_detects_delete, test_local_folder_delete_recreate_same_content_gets_new_event_id).
- Not yet: production SSO/onboarding, real business-system connector beyond local folder, full permission enforcement beyond the Connect-stored read flag, admin health UX beyond engine/worker.health() and scripts/connect_health.py CLI, unattended service packaging / installer beyond the runner script.


(2026-10-30) KnowledgeAccumulator.process is now transactional: on exception during mutation or persist, in-memory package objects, source index and metadata are restored to pre-process state. Subsequent retry on the same long-lived accumulator is safe. Persistence remains atomic. Tested (test_process_exception_mid_mutation_rolls_back_and_retry_succeeds). Connect P0 crash-boundary item advanced.

(2026-10-29) GeminiImporter restored from last good commit; ordered-list fix re-applied; test suite valid and 31 passed. Core Gemini import path functional again.

Next highest-leverage: package the local-folder runner as a simple service; or implement one real business-system connector; or further crash-boundary cases (e.g. persist failure after successful mutation).

(2026-10-28) SyncEngine now supports max_attempts; events that fail repeatedly are marked failed and no longer auto-retried. Cursor still advances only on success. Tests: retry-until-success and exhaustion.

(2026-10-31) SyncEngine now applies exponential backoff on processor failures. Events remain queued but are not selected for process_next until next_retry_at (2^attempts seconds, cap 300s). Schema migrates existing DBs by adding next_retry_at. Cursor still advances only on success; max_attempts still marks failed. Tested (existing retry tests updated to wait past delays). Connect P0 retry/backoff item advanced.

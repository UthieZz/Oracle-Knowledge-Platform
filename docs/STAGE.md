# STAGE

## Connect (as of 2026-11-04)
- Contract: interfaces.py (Connector, SyncEvent, HealthStatus) — present.
- StubConnector, LocalFolderConnector — present and tested.
- SyncEngine: SQLite durable queue, cursor, idempotency by event_id, process_next, bounded retry (max_attempts), exponential backoff via next_retry_at, manual recovery for failed events (reset_failed), enhanced health (failed count, queue age, last_processed_at). list_failed_details() returns last_error/attempts/enqueued_at. Cursor advances only on success. Implemented and tested (including interrupted process_next does not advance cursor).
- SyncWorker: managed start/stop polling loop over Connector → enqueue → process_next. Queue/cursor survive process restart. Tested.
- KnowledgeAccumulator: applies SyncEvents to a living KnowledgePackage via PlainTextImporter for create/update, removes on delete. Source identity is namespaced as source|tenant_id|silo_id|object_id in the internal index and in provenance.source_record_ids ("src:<scoped>"). Identical object_ids cannot collide across scopes. Legacy unscoped markers remain readable. Records permission_change in metadata keyed by scoped id. Optional package_path loads/saves the package as canonical JSON (atomic write) so the living knowledge survives process restarts. process() rolls back in-memory package, source index and metadata if _persist raises after mutation; subsequent retry is safe. Retrieval over the package reflects deletions and updates. Tested (including cross-scope isolation and persist-failure rollback).
- End-to-end stub → engine → PlainTextImporter → KnowledgePackage with tenant/silo — tested.
- Delete events process cleanly through engine and accumulator so objects leave the package.
- Permission_change with read=False is enforced fail-closed in KnowledgePackageRetriever for explicit entries. Objects without a permission entry remain visible.
- Background SyncWorker + LocalFolderConnector + KnowledgeAccumulator closed loop: worker polls, enqueues, processes via accumulator; file create/update/delete become visible to KnowledgePackageRetriever. Tested.
- Minimal durable runner: scripts/run_connect_worker.py starts the worker against a watched folder, persists the living package and the connector snapshot, and stops cleanly on signal. Suitable for a local-folder pilot path.
- LocalFolderConnector snapshot persistence: optional snapshot_path loads prior state on restart so files deleted while the worker is stopped generate delete events on the next incremental_sync. Snapshot stores version, monotonic sequence and map; event_ids incorporate sequence so delete/recreate of identical content receives a new id. Tested.
- Operator visibility: scripts/connect_health.py surfaces queued/processed/failed, oldest_queued age, last_processed_at, and limited failed-event summaries (id/attempts/error). Reports package metadata.object_count consistency with actual object count. Also reports cursor state (source/tenant/silo/cursor/updated) via SyncEngine.list_cursors() so operators can verify sync progress without direct DB inspection.
- Not yet: production SSO/onboarding, real business-system connector beyond local folder, complete authorization model beyond the Connect-stored read flag, admin health UX beyond engine/worker.health() and CLI, unattended service packaging beyond the runner script.

Next highest-leverage: additional crash-boundary cases or expand operator diagnostics; or implement one real business-system connector once the local path is further hardened. Security/provenance boundary checks remain open.

## Current Connect status (2026-11-05)
- LocalFolderConnector snapshot persistence (optional snapshot_path) implemented and tested for restart deletion detection.
- Source identity namespaced as source|tenant|silo|object_id.
- SyncEngine: WAL mode, exponential backoff, failed list, reset_failed, health with last_processed_at.
- KnowledgeAccumulator: scoped upsert/delete, permission recording, persist rollback, permissions normalize + delete cleanup. Reprocessing an identical create after successful package persist (simulating engine mark-processed failure) is idempotent: object count and content remain unchanged.

- Runner persists snapshot. connect_health reports package metadata consistency.
- Targeted Connect suite: 35 passed (incl. multi-instance same-DB visibility, concurrent multi-thread enqueue/process, and real subprocess process-restart deletion convergence) (sync_engine + accumulator + local_folder + worker + e2e + health + contract).

- Full suite (this environment): 145 passed, 2 failed (test_firestore_exporter.py requires google-cloud-firestore / mock setup not present here; not a Connect regression).
- Remaining P0: full suite in a complete dependency environment. Real subprocess process-restart deletion convergence now regression-tested (package converges after stop/delete/restart). Concurrent multi-thread writers on WAL queue regression-tested (no loss).


# STAGE

## Connect (as of 2026-11-04)
- Contract: interfaces.py (Connector, SyncEvent, HealthStatus) — present.
- StubConnector, LocalFolderConnector — present and tested.
- SyncEngine: SQLite durable queue, cursor, idempotency by event_id, process_next, bounded retry (max_attempts), exponential backoff via next_retry_at, manual recovery for failed events (reset_failed), enhanced health (failed count, queue age, last_processed_at). list_failed_details() returns last_error/attempts/enqueued_at. Cursor advances only on success. Implemented and tested (including interrupted process_next does not advance cursor).
- SyncWorker: managed start/stop polling loop over Connector → enqueue → process_next. Queue/cursor survive process restart. Tested.
- KnowledgeAccumulator: applies SyncEvents to a living KnowledgePackage via PlainTextImporter for create/update, removes on delete. Source identity is namespaced as source|tenant_id|silo_id|object_id in the internal index and in provenance.source_record_ids ("src:<scoped>"). Identical object_ids cannot collide across scopes. Legacy unscoped markers remain readable. Records permission_change in metadata keyed by scoped id. Optional package_path loads/saves the package as canonical JSON (atomic write) so the living knowledge survives process restarts. process() rolls back in-memory package, source index and metadata if _persist raises after mutation; subsequent retry is safe. Retrieval over the package reflects deletions and updates. Tested (including cross-scope isolation and persist-failure rollback).
- End-to-end stub → engine → PlainTextImporter → KnowledgePackage with tenant/silo — tested.
- Delete events process cleanly through engine and accumulator so objects leave the package.
- Permission_change with read=False is enforced fail-closed in KnowledgePackageRetriever for explicit entries (tested create → revoke → exclude → restore → include).
- Background SyncWorker + LocalFolderConnector + KnowledgeAccumulator closed loop: worker polls, enqueues, processes via accumulator; file create/update/delete become visible to KnowledgePackageRetriever. Tested.
- Minimal durable runner: scripts/run_connect_worker.py starts the worker against a watched folder, persists the living package and the connector snapshot, and stops cleanly on signal. Suitable for a local-folder pilot path.
- LocalFolderConnector snapshot persistence: optional snapshot_path loads prior state on restart so files deleted while the worker is stopped generate delete events on the next incremental_sync. Snapshot stores version, monotonic sequence and map; event_ids incorporate sequence so delete/recreate of identical content receives a new id. Persist uses atomic temp+replace. Corrupt/truncated snapshot is ignored on load (starts clean). Tested.
- Operator visibility: scripts/connect_health.py surfaces queued/ready_to_process/waiting_for_retry/processed/failed, oldest_queued age, last_processed_at, and limited failed-event summaries (id/attempts/error).
- Not yet: production SSO/onboarding, real business-system connector beyond local folder, complete authorization model beyond the Connect-stored read flag, admin health UX beyond engine/worker.health() and CLI, unattended service packaging beyond the runner script, full current-suite verification in this environment.

Next highest-leverage: additional crash-boundary cases or expand operator diagnostics; or implement one real business-system connector once the local path is further hardened. Security/provenance boundary checks remain open.


- LocalFolderConnector init now cleans any leftover snapshot .tmp file from a prior interrupted atomic persist, ensuring no accumulation of temp artifacts and that the last valid snapshot is loaded. Tested.

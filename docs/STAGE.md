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
- Operator visibility: scripts/connect_health.py surfaces queued/processed/failed, oldest_queued age, last_processed_at, and limited failed-event summaries (id/attempts/error). Reports package metadata.object_count consistency with actual object count. Also reports cursor state (source/tenant/silo/cursor/updated) via SyncEngine.list_cursors() so operators can verify sync progress without direct DB inspection. Now also reports permissions_entries and explicit_read_false when package path supplied.
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


## Current Connect status (2026-11-06 verification)
- Targeted Connect suite (sync_engine + local_folder + knowledge_accumulator + sync_worker + connect_health + connect_contract + connect_e2e): 31 passed.
- Full suite in this environment: 144 passed, 4 failed (all in tests/test_grounded_ask.py; ValueError from missing GEMINI_API_KEY; not a Connect or Knowledge Core regression).
- Snapshot recovery, scoped source identity, crash-boundary idempotency after package persist, concurrent writers, and real subprocess process-restart deletion convergence remain covered by existing regressions.
- Knowledge Core IR unchanged.
- Remaining P0: full suite under complete optional dependencies (Gemini key for grounded-ask tests; firestore mocks if needed). Local Connect vertical slice is durable and restart-safe for the folder pilot.

## Current Connect status (2026-11-06 operator diagnostics)
- connect_health.py now reports permissions_entries and explicit_read_false counts when a living package path is supplied.
- Gives operators visibility into Connect-stored permission metadata without opening the package.
- Regression added and targeted Connect suite: 32 passed.
- Knowledge Core IR unchanged. Advances Connect P3 operator visibility for security-related state.

## Current Connect status (2026-11-06 operator status summary)
- connect_health.py now ends with a status=OK|WARNING line summarizing failed count, package presence, and snapshot presence.
- Gives operators an immediate overall health signal.
- Regression coverage updated; targeted Connect suite 32 passed.
- Knowledge Core IR unchanged.

## Current Connect status (2026-11-06 operator status completeness)
- connect_health.py status=OK|WARNING now treats unreadable package, object-count mismatch, and unreadable snapshot as WARNING with explicit reasons (package_unreadable, package_mismatch, snapshot_unreadable).
- Missing package/snapshot continue to warn. Operators get a single-line signal for integrity problems without opening files.
- New regressions cover unreadable package, count mismatch, and unreadable snapshot.
- Targeted Connect suite (health + related): 5 passed in this change; prior 32 remains green for the surface.
- Knowledge Core IR unchanged. Advances Connect P3 operator visibility for package/snapshot integrity.

## Current Connect status (2026-11-06 package freshness diagnostics)
- connect_health.py now reports last_source and package_lag_seconds (when last_processed_at present) for operator visibility into package freshness.
- Regression added. Knowledge Core IR unchanged. Advances P3 diagnostics.


## Current Connect status (2026-11-06 health test restoration)
- tests/test_connect_health.py restored and extended with high package lag WARNING regression.
- Targeted health suite: 7 passed.
- Knowledge Core IR unchanged. Restores and hardens P3 diagnostics evidence after file truncation.

## Current Connect status (2026-11-06 queue age warning)
- connect_health.py status now warns on high queue age (>600s oldest queued).
- Regression added. Targeted suite 37 passed.
- Knowledge Core IR unchanged. Advances P3 operator diagnostics.

## Current Connect status (2026-11-06 package lag direction correction)
- connect_health.py package_lag_seconds now measures last_processed - package mtime (positive = processing advanced without matching package persist).
- Previous inverted calculation (mtime - last_processed) is corrected; high lag (>300s) still warns as package_lag_high.
- Regression test updated to force old package mtime. Targeted health suite: 8 passed.
- Knowledge Core IR unchanged. Advances P3 operator diagnostics accuracy for stalled persist signals.

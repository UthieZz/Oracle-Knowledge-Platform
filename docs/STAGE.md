# STAGE

## Connect (as of 2026-10-21)
- Contract: interfaces.py (Connector, SyncEvent, HealthStatus) — present.
- StubConnector, LocalFolderConnector — present and tested.
- SyncEngine: SQLite durable queue, cursor, idempotency, process_next — implemented and tested.
- SyncWorker: managed start/stop polling loop over Connector → enqueue → process_next. Queue/cursor survive process restart. Tested.
- KnowledgeAccumulator: applies SyncEvents to a living KnowledgePackage via PlainTextImporter for create/update, removes on delete (source id stored in provenance.source_record_ids), records permission_change in metadata. Optional package_path loads/saves the package as canonical JSON so the living knowledge survives process restarts. Retrieval over the package reflects deletions and updates. Tested.
- End-to-end stub → engine → PlainTextImporter → KnowledgePackage with tenant/silo — tested.
- Delete events process cleanly through engine and accumulator so objects leave the package.
- Permission_change with read=False is now enforced fail-closed in KnowledgePackageRetriever: objects whose source id has an explicit permission entry denying read are excluded from retrieval. Explicit read=True restores them. Objects without a permission entry remain visible (no silent breakage of packages that have not received permission events).
- Background SyncWorker + LocalFolderConnector + KnowledgeAccumulator closed loop: worker polls, enqueues, processes via accumulator; file create/update/delete become visible to KnowledgePackageRetriever without manual process_next. Tested (test_sync_worker_local_folder_accumulator_background_updates).
- Minimal durable runner: scripts/run_connect_worker.py starts the worker against a watched folder, persists the living package, and stops cleanly on signal. Suitable for a local-folder pilot path without SSO.
- Not yet: production SSO/onboarding, real business-system connector beyond local folder, full permission enforcement beyond the Connect-stored read flag, admin health UX beyond engine/worker.health() and scripts/connect_health.py CLI, unattended service packaging / installer beyond the runner script.

Next highest-leverage: production identity/SSO boundary or a second real connector that emits permission_change events from an external system; or package the local-folder runner as a simple service/installer with secrets handling.

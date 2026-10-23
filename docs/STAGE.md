# STAGE

## Connect (as of 2026-10-23)
- Contract: interfaces.py (Connector, SyncEvent, HealthStatus) — present.
- StubConnector, LocalFolderConnector — present and tested.
- SyncEngine: SQLite durable queue, cursor, idempotency, process_next — implemented and tested.
- SyncWorker: managed start/stop polling loop over Connector → enqueue → process_next. Queue/cursor survive process restart. Tested.
- KnowledgeAccumulator: applies SyncEvents to a living KnowledgePackage via PlainTextImporter for create/update, removes on delete (source id stored in provenance.source_record_ids), records permission_change in metadata. Optional package_path loads/saves the package as canonical JSON so the living knowledge survives process restarts. Retrieval over the package reflects deletions and updates. Tested.
- End-to-end stub → engine → PlainTextImporter → KnowledgePackage with tenant/silo — tested.
- Delete events process cleanly through engine and accumulator so objects leave the package.
- Permission_change with read=False is now enforced fail-closed in KnowledgePackageRetriever: objects whose source id has an explicit permission entry denying read are excluded from retrieval. Explicit read=True restores them. Objects without a permission entry remain visible (no silent breakage of packages that have not received permission events).
- Background SyncWorker + LocalFolderConnector + KnowledgeAccumulator closed loop: worker polls, enqueues, processes via accumulator; file create/update/delete become visible to KnowledgePackageRetriever without manual process_next. Tested (test_sync_worker_local_folder_accumulator_background_updates).
- Minimal durable runner: scripts/run_connect_worker.py starts the worker against a watched folder, persists the living package and the connector snapshot, and stops cleanly on signal. Suitable for a local-folder pilot path without SSO.
- LocalFolderConnector snapshot persistence: optional snapshot_path loads prior rel_path→hash map on restart so files deleted while the worker is stopped generate delete events on the next incremental_sync. Tested (test_local_folder_snapshot_survives_restart_and_detects_delete).
- Not yet: production SSO/onboarding, real business-system connector beyond local folder, full permission enforcement beyond the Connect-stored read flag, admin health UX beyond engine/worker.health() and scripts/connect_health.py CLI, unattended service packaging / installer beyond the runner script, source-identity namespacing across tenant/silo (currently keyed by object_id alone).

Next highest-leverage: namespace source identity in the accumulator (connector + tenant + silo + object_id) so identical paths cannot collide across scopes; or package the local-folder runner as a simple service (systemd unit or container entrypoint) with config/secrets separation; or add a second connector that emits real permission_change events; or identity/SSO boundary for pilot onboarding. Health CLI now reports package freshness.

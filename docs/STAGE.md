# STAGE

## Connect (as of 2026-10-19)
- Contract: interfaces.py (Connector, SyncEvent, HealthStatus) — present.
- StubConnector, LocalFolderConnector — present and tested.
- SyncEngine: SQLite durable queue, cursor, idempotency, process_next — implemented and tested.
- SyncWorker: managed start/stop polling loop over Connector → enqueue → process_next. Queue/cursor survive process restart. Tested.
- KnowledgeAccumulator: applies SyncEvents to a living KnowledgePackage via PlainTextImporter for create/update, removes on delete (source id stored in provenance.source_record_ids), records permission_change in metadata. Retrieval over the package reflects deletions and updates. Tested.
- End-to-end stub → engine → PlainTextImporter → KnowledgePackage with tenant/silo — tested.
- Delete events process cleanly through engine and accumulator so objects leave the package.
- Permission_change with read=False is now enforced fail-closed in KnowledgePackageRetriever: objects whose source id has an explicit permission entry denying read are excluded from retrieval. Explicit read=True restores them. Objects without a permission entry remain visible (no silent breakage of packages that have not received permission events).
- Not yet: production SSO/onboarding, real business-system connector beyond local folder, full permission enforcement beyond the Connect-stored read flag, admin health UX beyond engine/worker.health() and scripts/connect_health.py CLI, unattended service packaging.

Next highest-leverage: production identity/SSO boundary or a second real connector that emits permission_change events from an external system.

# STAGE

## Connect (as of 2026-10-18)
- Contract: interfaces.py (Connector, SyncEvent, HealthStatus) — present.
- StubConnector, LocalFolderConnector — present and tested.
- SyncEngine: SQLite durable queue, cursor, idempotency, process_next — implemented and tested.
- SyncWorker: managed start/stop polling loop over Connector → enqueue → process_next. Queue/cursor survive process restart. Tested.
- KnowledgeAccumulator: applies SyncEvents to a living KnowledgePackage via PlainTextImporter for create/update, removes on delete (source id stored in provenance.source_record_ids), records permission_change in metadata. Retrieval over the package reflects deletions and updates. Tested.
- End-to-end stub → engine → PlainTextImporter → KnowledgePackage with tenant/silo — tested.
- Delete events process cleanly through engine and accumulator so objects leave the package.
- Not yet: production SSO/onboarding, real business-system connector beyond local folder, full permission enforcement inside retriever, admin health UX beyond engine/worker.health() and scripts/connect_health.py CLI, unattended service packaging.

Next highest-leverage: make permission_change affect retrieval (fail-closed filter) so source-forbidden objects are not returned.

# STAGE

## Connect (as of 2026-10-17)
- Contract: interfaces.py (Connector, SyncEvent, HealthStatus) — present.
- StubConnector, LocalFolderConnector — present and tested.
- SyncEngine: SQLite durable queue, cursor, idempotency, process_next — implemented and tested.
- SyncWorker: managed start/stop polling loop over Connector → enqueue → process_next. Queue/cursor survive process restart. Tested.
- End-to-end stub → engine → PlainTextImporter → KnowledgePackage with tenant/silo — tested.
- Delete events process cleanly through engine.
- Not yet: production SSO/onboarding, real business-system connector beyond local folder, full deletion/permission propagation through retrieval and compiler, admin health UX, unattended service packaging.

Next highest-leverage: wire delete/permission_change through importer/compiler so retrieval reflects them, plus a minimal admin health endpoint or CLI that surfaces SyncEngine.health + worker state.

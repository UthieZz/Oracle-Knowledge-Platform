# STAGE

## Connect (as of 2026-10-16)
- Contract: interfaces.py (Connector, SyncEvent, HealthStatus) — present.
- StubConnector, LocalFolderConnector — present and tested.
- SyncEngine: SQLite durable queue, cursor, idempotency, process_next — implemented and tested.
- End-to-end stub → engine → PlainTextImporter → KnowledgePackage with tenant/silo — tested.
- Not yet: real background worker lifecycle, production SSO/onboarding, real business-system connector beyond local folder, full deletion/permission propagation through retrieval, admin health UX.

Next highest-leverage: managed background worker that polls/enqueues and survives restart, plus explicit delete/permission-change tests end-to-end.

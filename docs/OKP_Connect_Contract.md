# OKP Connect Contract

OKP Connect is the replaceable integration layer. Knowledge Core (KnowledgePackage + compiler) is the stable IP.

## One contract

Every connector implements:

- `authenticate(credentials) -> bool`
- `initial_sync(tenant_id, silo_id) -> List[SyncEvent]`
- `incremental_sync(cursor, tenant_id, silo_id) -> List[SyncEvent]`
- `handle_deletion(object_id, tenant_id, silo_id) -> SyncEvent`
- `permissions(object_id) -> Dict`
- `health() -> HealthStatus`

## SyncEvent

Durable, idempotent unit. Contains `event_id`, `source`, `kind` (create/update/delete/permission_change), optional `cursor`, `payload`, `tenant_id`, `silo_id`.

## Guarantees

- No silent loss: every event is queued.
- Retries with backoff.
- Idempotency via `event_id`.
- Permissions and deletions propagate.
- Tenant/silo isolation enforced before ingestion.
- Outbound-only preferred for local systems.
- Admin-visible health, last sync, failures.

## Ingestion path

Connectors emit SyncEvents → `SyncEngine` (durable SQLite queue, cursor, retry, idempotency) → caller-supplied processor that feeds existing importer/compiler path → KnowledgePackage.

No parallel IR. Connectors and the engine never write KnowledgePackage directly.

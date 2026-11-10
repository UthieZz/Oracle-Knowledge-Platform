# OKP Permission Model — Current Intentional Behavior

**Status:** Documented for the local-folder pilot (as of 2026-11-10).  
**Scope:** Retrieval, export, and health visibility. Not a complete multi-tenant authorization system.

## Default (pilot) behavior

- Objects without an explicit permission entry in `package.metadata["permissions"]` remain visible to retrieval and are included in SQLite export.
- This is deliberate compatibility for the local-folder pilot where sources do not yet emit full permission events.
- Explicit `permission_change` events with `read: false` exclude the object from subsequent retrieval and from export (fail-closed for recorded denials).
- Explicit `read: true` restores visibility and export eligibility.
- Tenant and silo isolation are enforced independently of the permission map.
- Delete events remove the corresponding permission metadata entry.

## Production-oriented mode

- `KnowledgePackageRetriever(strict_permissions=True)` and `SQLiteExporter.export(..., strict_permissions=True)` treat a missing permission entry as denial when a source identifier is present.
- Explicit allow still works; explicit deny still works.
- The ContextGateway respects the retriever mode; denied objects are not reintroduced at context construction.
- FirestoreExporter.export(..., strict_permissions=False) applies the same filter to knowledge_objects when metadata["permissions"] exists (explicit deny always excluded; missing included by default, denied when strict=True).

## Operator visibility

- `scripts/connect_health.py` reports `objects_without_explicit_permission`.
- Optional `--strict-check` elevates any positive count to `status=WARNING` and exit 1.
- Default invocation (no flag) remains OK so the pilot is not broken by the presence of unpermissioned objects.
- Health also reports `permissions_with_event_provenance` and `permissions_missing_event_provenance` so operators can confirm that recorded permission decisions carry their originating event id and see incomplete provenance at a glance.
- Health also reports `orphaned_permission_entries` (permission keys with no matching living object) so operators can detect incomplete cleanup or corruption. Positive count elevates status to WARNING (exit 1).

## Deletion and restoration semantics (verified by regressions)

- A delete event removes the corresponding permission metadata entry.
- After an explicit read=False + delete, a subsequent create of the same object_id is visible under default mode and has no inherited permission entry (stale deny does not survive object lifecycle). The recreated object is also included in SQLite export under default mode.
- An update after an explicit read=False leaves the object denied; the permission map is independent of content upserts.
- A permission_change recorded before the object exists is still applied when the object is later created and excludes it from retrieval.
- An explicit read=False issued after a successful ContextGateway retrieval excludes the object on the subsequent build (live permission map is consulted each time; no improper caching of prior context).

These behaviors are covered by existing targeted tests in tests/test_knowledge_accumulator.py, tests/test_sqlite_exporter_permissions.py, and tests/test_agent_context_gateway.py.

## What this is not

- Not a complete authorization system across ingestion, export, Studio, or administrative APIs.
- Not a substitute for tenant/silo claims and Firestore rules.
- Not automatic promotion of any inference into authoritative knowledge.
- Search filtering or health warnings alone do not constitute full access control.

## Next evidence needed (P1)

Policy tests at remaining boundaries (ingestion, queue, package, admin), full retention policy for packages/exports/caches/backups. The Firestore publishing path filter is implemented and unit-tested (src/exporters/firestore_exporter.py, tests/test_firestore_exporter_permissions.py).

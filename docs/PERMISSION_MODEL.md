# OKP Permission Model — Current Intentional Behavior

**Status:** Documented for the local-folder pilot (as of 2026-11-09).  
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

## Operator visibility

- `scripts/connect_health.py` reports `objects_without_explicit_permission`.
- Optional `--strict-check` elevates any positive count to `status=WARNING` and exit 1.
- Default invocation (no flag) remains OK so the pilot is not broken by the presence of unpermissioned objects.
- Health also reports `permissions_with_event_provenance` and `permissions_missing_event_provenance` so operators can confirm that recorded permission decisions carry their originating event id and see incomplete provenance at a glance.

## What this is not

- Not a complete authorization system across ingestion, export, Studio, or administrative APIs.
- Not a substitute for tenant/silo claims and Firestore rules.
- Not automatic promotion of any inference into authoritative knowledge.
- Search filtering or health warnings alone do not constitute full access control.

## Next evidence needed (P1)

Policy tests at every boundary (ingestion, queue, package, retrieval, context, export, admin), revocation after prior retrieval, and documented retention/deletion semantics.

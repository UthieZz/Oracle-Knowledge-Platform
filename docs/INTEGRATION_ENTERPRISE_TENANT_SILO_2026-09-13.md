# Integration: enterprise-tenant-silo package (2026-09-13)

Source package: `packages/enterprise-tenant-silo-2026-09-05/` (verbatim ZIP snapshot).

## Policy

- Additive integration only.
- Did not delete repository files that the ZIP lacks (validators, relationship exporter, tests, audits, scripts, verify tools, pipeline services, desktop UI, etc.).
- GitHub `src/` remains the live Python namespace. ZIP `okc/` is preserved only inside the package snapshot.

## Brought in from ZIP

- KnowledgeObject IR v2 (`src/models/knowledge_object.py`)
- `SourceIdentityAnalyzer` (`src/analyzers/source_identity.py`)
- `KnowledgeObjectEnricher` (`src/analyzers/knowledge_object_enricher.py`)
- Updated `knowledge_index_builder.py`
- Firestore exporter with required `OKP_TENANT_ID` / `OKP_SILO_ID`, `sourceFingerprints`, IR fields — **plus** retained `ensure_knowledge_object_provenance`
- Studio: `AuthService`, `AuthGate`, updated `FirestoreService`, `firebase`, `SearchPage`, `ImportPage`, `main`, `App`
- `firestore.rules` enterprise tenant/silo rules
- Docs: Enterprise Tenant/Silo, Hybrid Search Contract, KnowledgeObject IR v2, Source Identity

## Explicitly retained from prior repo

- `src/validators/*` (provenance + quality)
- `src/exporters/relationship_index_exporter.py`
- Full `tests/` suite
- Audit docs, scripts, verify_*, multi_source exporter, import services, desktop/studio Python UI

## Operational requirements

Export will refuse without `OKP_TENANT_ID` and `OKP_SILO_ID`.
Studio expects auth claims `okp_silos` / `okp_access` before rendering.

## Not claimed

This does not prove end-to-end deploy of identity provider or claim service. Those remain deployment work.

# OKP Stage — 2026-11-13

**Basis:** Current main (38bbb90 + local readiness health). Implementation, tests, and documented operator visibility distinguished from planned work.

## Knowledge Core
- Canonical KnowledgePackage (okc/models) is the sole IR.
- Provenance, source IDs, tenant/silo preserved.
- Permission model: pilot default keeps missing visible; explicit deny enforced; strict mode available via OKP_STRICT_PERMISSIONS.
- Delivery boundaries (retriever, HybridRAG index, SQLite/Firestore/MultiSource/ProvenanceLedger/RelationshipIndex exporters) honor explicit deny; strict mode excludes missing when source identity present. Unit-tested.

## OKP Connect local-folder pilot
- LocalFolderConnector + persistent snapshot, SQLite SyncEngine, KnowledgeAccumulator implemented and targeted-tested (recent Connect + permission suites green).
- Health CLI (scripts/connect_health.py) and recovery CLI present with structured recovery_hints.
- Operator guide and Docker packaging example exist.

## Local OKC server (okc/server/app.py)
- Upload/compile path honors OKP_STRICT_PERMISSIONS for HybridRAG index and SQLite export.
- /api/health reports strict_permissions mode + basic readiness (upload_dir_writable, db_parent_writable).
- Job status reports mode used.
- Regressions in tests/test_local_server_status.py green.

## Dual surfaces
- Connect owns okc/ + Pydantic KnowledgePackage.
- src/ remains for legacy compiler/UI and Gemini importer (functional, not stub).
- No merge without further evidence. See docs/IMPLEMENTATION_OWNERSHIP.md if present.

## Next
Continue P1 remaining authorization boundaries or further P3 diagnostics. Prefer smallest coherent change with new regression evidence.

**Not claimed:** production-grade multi-tenant authorization, full fail-closed default, B2B readiness, or runtime-verified Studio/Firestore deployment.

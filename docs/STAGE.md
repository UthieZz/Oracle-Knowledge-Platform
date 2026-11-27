# OKP Stage — 2026-11-27

**Basis:** Current main. Local pilot end-to-end verification script added (scripts/verify_local_pilot.py). Single command exercises Import (LocalFolderConnector stage/enqueue) → Accumulate → KnowledgePackage → SQLiteExporter → lexical LIKE search in a temp dir. No cloud deps. Connect reliability journal windows remain locked from prior runs. No IR or permission contract change.

## Knowledge Core
- Canonical KnowledgePackage (okc/models) is the sole IR.
- Provenance, source IDs, tenant/silo preserved.
- Permission model: pilot default keeps missing visible; explicit deny enforced; strict mode available via OKP_STRICT_PERMISSIONS.
- Delivery boundaries honor explicit deny; strict mode excludes missing when source identity present.

## OKP Connect local-folder pilot
- LocalFolderConnector + persistent snapshot, SQLite SyncEngine, KnowledgeAccumulator implemented and targeted-tested.
- Health CLI and recovery CLI present.
- Operator guide and Docker packaging example exist.
- scripts/verify_local_pilot.py provides single-command runtime verification of the clean local path (import → accumulate → export → search).

## Local OKC server (okc/server/app.py)
- Upload/compile path honors OKP_STRICT_PERMISSIONS for HybridRAG index and SQLite export.
- /api/health reports readiness details.

## Dual surfaces
- Connect owns okc/ + Pydantic KnowledgePackage.
- src/ remains for legacy compiler/UI and Gemini importer.
- No merge without further evidence. See docs/IMPLEMENTATION_OWNERSHIP.md.

## Context-Aware Reasoning (locked design)
- Deterministic suite green. 38 passed. No deviation from locked contracts.

## Next
P0: journal reliability locked. Prefer surface alignment of entry points or remaining P1 delivery boundary. Do not treat a green unit suite or this verification script as B2B readiness.

**Not claimed:** production-grade multi-tenant authorization, full fail-closed default, B2B readiness, or runtime-verified Studio/Firestore deployment.

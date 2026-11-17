# OKP Stage — 2026-11-17

**Basis:** Current main (Context-Aware Reasoning Query Context Engine + snapshot wiring). Implementation, tests, and documented operator visibility distinguished from planned work.

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
- /api/health reports strict_permissions mode + basic readiness (upload_dir_writable, db_parent_writable, db_exists) + tenant_configured / silo_configured + google_credentials_configured + active_jobs_count + upload_dir_absolute / db_path_absolute + process_id / cwd_absolute + upload_dir_configured / sqlite_path_configured + registry_ready / registered_plugins_count / registered_importers_count + upload_dir_free_mb / db_parent_free_mb + process_start_time_utc / uptime_seconds + listen_host / listen_port + memory_rss_mb + active_threads_count + cpu_count + load_average + open_file_descriptors_count + python_executable + registered_importer_names.
- Job status reports mode used.
- Regressions in tests/test_local_server_status.py green.

## Dual surfaces
- Connect owns okc/ + Pydantic KnowledgePackage.
- src/ remains for legacy compiler/UI and Gemini importer (functional, not stub).
- No merge without further evidence. See docs/IMPLEMENTATION_OWNERSHIP.md if present.

## Context-Aware Reasoning (locked design)
- Orchestrator: minimal ContextOrchestrator (okc/context/orchestrator.py) coordinates engine + compatibility + answer stage without domain logic (I-11). Suite H1 present. 33 passed. No deviation.
- First gate: models, ContextRegistry, EvidenceCompatibilityEngine under okc/context/; Suites A–E deterministic tests executable.
- Answer Stage: minimal AnswerStage (okc/context/answer.py) producing locked structured output with independent completion flags, assumption/unresolved/conflict disclosure, pre-authorized affordances only. Suite F regressions present. No deviation from contracts.
- Query Context Engine: QueryContextEngine (okc/context/query_engine.py) owns envelope revisions with parent lineage. Assumptions never auto-promote; only explicit user confirmation or new evidence does. When an EvidenceSnapshotStore is attached, promote_with_evidence always creates a new immutable snapshot (I-10). Suite G regressions present (including G5). No deviation from contracts.
- Evidence Snapshot Store: EvidenceSnapshotStore owns immutable snapshots; create rejects re-use of same id. Wired into QueryContextEngine for evidence promotion.
- Orchestrator: ContextOrchestrator coordinates create → affordances → answer without domain logic.

## Next
Continue remaining P1 authorization boundaries or further Context-Aware Reasoning integration. Prefer smallest coherent change with new regression evidence against locked contracts.


Continue Context-Aware Reasoning (orchestrator wiring or remaining P1 authorization boundaries). Prefer smallest coherent change with new regression evidence against locked contracts.

**Not claimed:** production-grade multi-tenant authorization, full fail-closed default, B2B readiness, or runtime-verified Studio/Firestore deployment.

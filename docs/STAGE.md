# OKP Stage — 2026-11-17

**Basis:** Current main (Context-Aware Reasoning package adapter + initial snapshot on process_query + apply_expansion lineage). Implementation, tests, and documented operator visibility distinguished from planned work.

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
- Orchestrator confirmation path + AnswerStage materiality: Suite I7 verifies user confirmation of high-sensitivity dimension yields contextually_complete=True and answer_delivered=True. 40 passed.

- Orchestrator: ContextOrchestrator now exposes confirm_parameter for explicit user confirmation (delegates to engine; I-09 lineage). Suite I6 present. 39 passed.
- Orchestrator: ContextOrchestrator coordinates create → affordances → answer without domain logic (I-11). When snapshot store present and package/spans supplied, create_envelope attaches immutable initial snapshot (I-10). apply_expansion produces immutable revision with parent lineage (I-09); evidence path creates new snapshot, assumption path sets MISSING + disclosed assumption (never auto-promoted). answer_from_envelope coordinates answer on an existing revision without mutation. Suite I2 + I3 + I4 present. 38 passed. No deviation.
- Package adapter: extract_evidence_spans maps KnowledgePackage to evidence spans (existing only + explicit metadata constraints). Suite I1 present.
- First gate: models, ContextRegistry, EvidenceCompatibilityEngine under okc/context/; Suites A–E deterministic tests executable.
- Answer Stage: minimal AnswerStage (okc/context/answer.py) producing locked structured output with independent completion flags, assumption/unresolved/conflict disclosure, pre-authorized affordances only. Suite F regressions present. No deviation from contracts.
- Query Context Engine: QueryContextEngine owns envelope revisions with parent lineage. Assumptions never auto-promote; only explicit user confirmation or new evidence does. promote_with_evidence and create_envelope (when refs supplied) create immutable snapshots when store attached (I-10). Suite G + I2 present. No deviation from contracts.
- Evidence Snapshot Store: EvidenceSnapshotStore owns immutable snapshots; create rejects re-use of same id. Wired into QueryContextEngine for evidence promotion and initial attachment.

## Next
Continue remaining P1 authorization boundaries or further Context-Aware Reasoning integration (e.g. expansion path). Prefer smallest coherent change with new regression evidence against locked contracts.

**Not claimed:** production-grade multi-tenant authorization, full fail-closed default, B2B readiness, or runtime-verified Studio/Firestore deployment.

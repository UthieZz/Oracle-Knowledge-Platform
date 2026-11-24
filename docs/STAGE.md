# OKP Stage — 2026-11-24

**Basis:** Current main. Local-folder suite restored after the 50-line truncation on 1dc67e (the rename regression had been claimed but was not in the last intact 16-test file). KnowledgeAccumulator removes by scoped source marker, now locked by test_rename_while_stopped_converges_package (identical-content sibling survives). SyncWorker commits the connector snapshot only after events are durably enqueued; a pending journal is replayed if the process dies between detection and enqueue (test_crash_after_detect_before_enqueue_still_converges_delete). Verified: local-folder + sync worker + accumulator 35 passed (18 local-folder); connect recover/health/e2e/contract + sync engine 41 passed. CAR suite not re-run. No IR or permission contract change.

## Knowledge Core
- Canonical KnowledgePackage (okc/models) is the sole IR.
- Provenance, source IDs, tenant/silo preserved.
- Permission model: pilot default keeps missing visible; explicit deny enforced; strict mode available via OKP_STRICT_PERMISSIONS.
- Delivery boundaries (retriever, HybridRAG index, SQLite/Firestore/MultiSource/ProvenanceLedger/RelationshipIndex exporters, Context-Aware Reasoning package_adapter, CompilerAdapter pipeline export, operator run_export / run_compiler scripts) honor explicit deny; strict mode excludes missing when source identity present. MultiSourceExporter export() now accepts and forwards strict_permissions (default False). Unit-tested.

## OKP Connect local-folder pilot
- LocalFolderConnector + persistent snapshot, SQLite SyncEngine, KnowledgeAccumulator implemented and targeted-tested (recent Connect + permission suites green on 2026-11-12/13 verification).
- Health CLI (scripts/connect_health.py) and recovery CLI present with structured recovery_hints.
- Operator guide and Docker packaging example exist.

## Local OKC server (okc/server/app.py)
- Upload/compile path honors OKP_STRICT_PERMISSIONS for HybridRAG index and SQLite export.
- /api/health reports strict_permissions mode + basic readiness (upload_dir_writable, db_parent_writable, db_exists) + tenant_configured / silo_configured + google_credentials_configured + active_jobs_count + upload_dir_absolute / db_path_absolute + process_id / cwd_absolute + upload_dir_configured / sqlite_path_configured + registry_ready / registered_plugins_count / registered_importers_count + upload_dir_free_mb / db_parent_free_mb + process_start_time_utc / uptime_seconds + listen_host / listen_port + memory_rss_mb + active_threads_count + cpu_count + load_average + open_file_descriptors_count + python_executable + registered_importer_names.
- Job status reports mode used.
- Regressions in tests/test_local_server_status.py green (as of prior verification).

## Dual surfaces
- Connect owns okc/ + Pydantic KnowledgePackage.
- src/ remains for legacy compiler/UI and Gemini importer (functional, not stub).
- No merge without further evidence. See docs/IMPLEMENTATION_OWNERSHIP.md if present.

## Context-Aware Reasoning (locked design)
- Deterministic suite (tests/test_context_aware_reasoning.py) restored after placeholder incidents and expanded. Covers Suites A (including A2 versioned extension boundaries, A5 declaration ≠ evidence), B (per-dimension classification including B5 invalid provenance → unconstrained and B6 independent classifications on a single span), C (conflict retention, no silent majority, domain-rule only on observed values), D (available/retrievable paths, assumption replacement lineage, projected_change estimate-only), E (assumption non-promotion, promotion paths, snapshot immutability, revision lineage, high-sensitivity incompleteness, unconstrained cannot establish completeness), AnswerStage independent completion flags, and orchestrator retrieval path (I-10 new immutable snapshot + I-09 parent lineage), plus I-08 material claims and I-05 conflict retention by AnswerStage, plus successive retrieve_for_affordance calls producing distinct immutable snapshots with correct parent chain, plus package_adapter permission filtering (explicit deny always excluded; strict mode excludes missing), plus orchestrator propagation of strict_permissions. 38 passed (verified 2026-11-22). No deviation from locked design/context-aware-reasoning/ contracts.
- Prior expansions (B6 per-dimension independence, F-series disclosure, I-series orchestrator paths, D4/D5/C2) remain covered by the restored suite.
- First gate closed with executable regressions. Implementation authorised; further increments must stay smallest coherent against these tests.
- Legacy delivery surfaces: ProvenanceLedgerExporter and RelationshipIndexExporter now honor strict_permissions (default False). Explicit deny always excluded; under strict, source-identity objects without explicit entry are excluded. Aligns remaining P1 boundary with Firestore / SQLite / CAR paths. Regressions added. No deviation from permission model or locked contracts.

## Next
P0: crash-before-enqueue journal is in place for the local-folder worker. Prefer the next interruption case that is not yet locked (for example enqueue succeeds, snapshot commit fails, source mutates again before retry) or a verified remaining P1 delivery boundary. Do not treat a green unit suite as B2B readiness.

**Not claimed:** production-grade multi-tenant authorization, full fail-closed default, B2B readiness, or runtime-verified Studio/Firestore deployment.

# OKP Stage — 2026-11-22

**Basis:** Current main (post-restore). Context-Aware Reasoning deterministic suite restored and expanded: 34 passed (verified 2026-11-22 after B5 + affordance attribute correction) (suite restored after placeholder; including A2/A5/B5/B6, AnswerStage insufficient-evidence path, orchestrator retrieval path locking I-10 new snapshot + I-09 revision lineage, I-06/I-07 AnswerStage pre-authorized affordance pass-through, I-08 material claims in claims array and I-05 conflicts retained by AnswerStage, plus successive retrieval snapshot lineage). Prior Connect, local server, and ownership status carried forward from 2026-11-13/19 evidence. Implementation, tests, and documented operator visibility distinguished from planned work.

## Knowledge Core
- Canonical KnowledgePackage (okc/models) is the sole IR.
- Provenance, source IDs, tenant/silo preserved.
- Permission model: pilot default keeps missing visible; explicit deny enforced; strict mode available via OKP_STRICT_PERMISSIONS.
- Delivery boundaries (retriever, HybridRAG index, SQLite/Firestore/MultiSource/ProvenanceLedger/RelationshipIndex exporters) honor explicit deny; strict mode excludes missing when source identity present. Unit-tested.

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
- Deterministic suite (tests/test_context_aware_reasoning.py) restored after placeholder incidents and expanded. Covers Suites A (including A2 versioned extension boundaries, A5 declaration ≠ evidence), B (per-dimension classification including B5 invalid provenance → unconstrained and B6 independent classifications on a single span), C (conflict retention, no silent majority, domain-rule only on observed values), D (available/retrievable paths, assumption replacement lineage, projected_change estimate-only), E (assumption non-promotion, promotion paths, snapshot immutability, revision lineage, high-sensitivity incompleteness, unconstrained cannot establish completeness), AnswerStage independent completion flags, and orchestrator retrieval path (I-10 new immutable snapshot + I-09 parent lineage), plus I-08 material claims and I-05 conflict retention by AnswerStage, plus successive retrieve_for_affordance calls producing distinct immutable snapshots with correct parent chain. 34 passed (verified 2026-11-22 after B5 + affordance attribute correction). No deviation from locked design/context-aware-reasoning/ contracts.
- Prior expansions (B6 per-dimension independence, F-series disclosure, I-series orchestrator paths, D4/D5/C2) remain covered by the restored suite.
- First gate closed with executable regressions. Implementation authorised; further increments must stay smallest coherent against these tests.

## Next
Continue remaining P1 authorization boundaries (one verified weak boundary with regression) or further Context-Aware Reasoning integration only when higher defects cleared. Prefer smallest coherent change with new regression evidence against locked contracts.

**Not claimed:** production-grade multi-tenant authorization, full fail-closed default, B2B readiness, or runtime-verified Studio/Firestore deployment.

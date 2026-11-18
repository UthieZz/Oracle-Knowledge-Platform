# OKP Roadmap — Knowledge Infrastructure, Connect Reliability, and B2B Pilot

**Updated:** 2026-11-18  
**Basis:** Current-main source, STAGE.md, AGENT_COMMIT_LOG.md, and targeted Connect suite evidence.  
Implementation, recorded test evidence, runtime verification and planned work are intentionally distinguished.  
**Companion analysis:** docs/BUILD_FIRST_TECHNICAL_ANALYSIS_2026-10-22.md

## Mission

Oracle Knowledge Platform (OKP) turns fragmented information from AI systems and other sources into structured, reusable, searchable and traceable knowledge.  
It is knowledge infrastructure—not simply a chatbot or conversation archive.

The near-term product objective is a dependable, demonstrable vertical slice: connect an approved source, synchronize changes in the background, maintain a governed KnowledgePackage, retrieve grounded evidence, and make operational state inspectable.

## Current implementation snapshot — 2026-11-13

### Knowledge Core and application path
- Multi-source importer architecture and PluginRegistry present.
- Canonical KnowledgePackage (okc/models) is the sole IR.
- Provenance, source IDs, tenant/silo preserved through processing.
- Permission model documented; explicit deny honored; strict mode available; default pilot keeps missing entries visible for compatibility.
- FirestoreExporter applies permission filter (unit-tested).
- MultiSourceExporter applies permission filter to content, indexes, and manifests (unit-tested).
- ProvenanceLedgerExporter and RelationshipIndexExporter exclude explicit-deny knowledge objects (unit-tested).
- Studio AuthGate and firestore.rules present (deployed behavior not fully verified).
- Local OKC server (okc/server/app.py) honors OKP_STRICT_PERMISSIONS for HybridRAG index and SQLite export on upload/compile path; job status now reports the mode used.

### OKP Connect local-folder pilot
Implemented and targeted-tested (recent runs: health suite 25 passed; broader Connect suite 69 passed on 2026-11-11 verification (health 25 + related); targeted after json import fix: 64 passed; current-main Connect + permission suite 70 passed on 2026-11-12 verification; re-verified 70 passed on 2026-11-13 clone):
- LocalFolderConnector with persistent snapshot (restart deletion detection, sequence for event_ids).
- SQLite SyncEngine (WAL, dedup, retry/backoff, cursor advances only on success).
- KnowledgeAccumulator (source|tenant|silo namespacing, persist/rollback, cross-scope isolation).
- Health CLI (scripts/connect_health.py): status=OK|WARNING, exit 1 on WARNING, --json, --config, --strict-check. Reports package/snapshot consistency, provenance gaps, orphaned entries, queue age, lag, etc. Emits structured recovery_hints for all current WARNING reasons.
- Recovery CLI (scripts/connect_recover.py): list/reset failed events with filters, config support, clean JSON.
- Operator guide: docs/CONNECT_LOCAL_PILOT.md (includes Docker volume-mounted start example).
- Dockerfile updated for Connect worker entrypoint and volume packaging.

Knowledge Core IR and Connect contracts unchanged by recent health/recovery/packaging/export work.

### Ownership
- Connect path owns okc/ and Pydantic KnowledgePackage.
- src/ remains for legacy compiler/UI and Gemini importer.
- No merge without further evidence of overlap and migration safety. See docs/IMPLEMENTATION_OWNERSHIP.md.

## Priorities (ordered)

### P0 — Connect reliability (local-folder pilot)
**Status:** Substantially implemented and targeted-tested.  
Snapshot recovery, deletion detection after restarts, source identity, event lifecycle, persistent cursors, retries, idempotency present.  
**Next evidence:** continued restart/update/delete/retry interrupted-processing tests under realistic interruption.  
**Acceptance:** package converges to source after worker stop/restart with concurrent source changes; no silent loss or duplicate objects.

### P1 — Security / provenance / authorization consistency
**Status:** Partial. Explicit permission_change (read=False/True) enforced on retrieval, context gateway (strict), Firestore export, MultiSourceExporter, ProvenanceLedgerExporter, and RelationshipIndexExporter. Orphaned and missing-event-provenance elevate health WARNING. Lifecycle semantics documented in docs/PERMISSION_MODEL.md. Local server path now configurable via OKP_STRICT_PERMISSIONS; job status reports the mode.  
**Gaps:** remaining boundaries (e.g., admin paths, cache invalidation, other legacy surfaces); full fail-closed production mode not default.  
**Next:** identify and close one verified weak boundary with regression.  
**Acceptance:** no cross-tenant/silo leakage; revocation survives updates; missing permission denied under strict mode across all delivery paths; provenance complete on permission decisions.

### P2 — Architecture consistency
**Status:** Ownership map recorded. Dual src/okc surfaces intentional for now.  
**Next:** keep mapping current; avoid unnecessary migrations.  
**Acceptance:** documented active/obsolete paths; no competing IRs.

### P3 — Local pilot operability
**Status:** Strong progress. Config files, recovery CLI, health recovery_hints, cursor/snapshot visibility, operator guide, Docker packaging example. Local server now supports strict mode via env and reports it in job status.  
**Next:** diagnostics under optional deps or further one-command packaging refinements.  
**Acceptance:** operator can start, inspect, recover, and stop the local-folder pilot from documented steps without source inspection.

### P4 — Business integration
**Status:** Planned. Local-folder is the proven path.  
**Next:** select one valuable, feasible, secure integration and complete its testable end-to-end path before expanding catalogue.  
**Acceptance:** one real business system produces events that survive the full pipeline into a permission-aware package with provenance.

### P5 — B2B validation
**Status:** Not ready. Identity, access, onboarding, tenant admin, deployment, operations, and measurable pilot outcomes required.  
**Acceptance:** defined readiness evidence (not architecture claims or unit tests alone).

## Constraints
- Firebase Spark / no-cost. No unapproved paid services.
- KnowledgePackage sole canonical IR.
- Preserve pipeline: IMPORT → NORMALIZE → PROCESS → ENRICH → VALIDATE → COMPILE → PACKAGE.
- Small, reversible, tested changes. Protect unrelated work.
- Do not claim B2B readiness without evidence.

## Recent verified advances (2026-11-18)
- Context-Aware Reasoning D4 assumption replacement creates new revision with parent lineage; original assumption preserved. Suite D4 added. 43 passed. No deviation from I-09. Next: remaining P1 boundaries or further retrieval integration.

- Context-Aware Reasoning domain-rule resolution for simple conflicts: EvidenceCompatibilityEngine.apply_simple_domain_rules + ContextOrchestrator applies optional domain_rules only when preferred_value is among observed evidence (C2). Creates new revision with source="domain_rule", discloses rationale, preserves conflicting values in claim. Suite I9 added. 42 passed. No domain logic in orchestrator, no silent invention. Next: remaining P1 boundaries or further retrieval integration.

- Context-Aware Reasoning simple conflict detection: EvidenceCompatibilityEngine.detect_simple_conflicts + ContextOrchestrator auto-disclosure of multi-value constraints (C1). Suite I8 added. 41 passed. No domain logic, no silent override. Next: remaining P1 boundaries or further retrieval integration.

## Recent verified advances (2026-11-17)
- Context-Aware Reasoning confirmation completeness loop: ContextOrchestrator.confirm_parameter + answer_from_envelope after process_query with assumption. AnswerStage now treats RESOLVED parameters as material for answer_delivered. Suite I7 added. 40 passed. No deviation from locked contracts. Next: remaining P1 boundaries or further retrieval integration.


- Context-Aware Reasoning user confirmation path: ContextOrchestrator.confirm_parameter delegates to promote_with_user_confirmation. Produces new immutable revision with parent lineage (I-09). Status becomes RESOLVED with source="user". No domain logic (I-11). Suite I6 added. 39 passed. No deviation from locked contracts. Next: remaining P1 boundaries or further retrieval integration.

- Context-Aware Reasoning retrieval path: ContextOrchestrator.retrieve_for_affordance coordinates package/spans → promote_with_evidence for RETRIEVABLE affordances (new immutable snapshot + revision). No domain logic (I-11). Suite I5 added. 38 passed. No deviation from locked contracts. Next: remaining P1 boundaries or further retrieval integration.
- Context-Aware Reasoning expansion answer loop: ContextOrchestrator.answer_from_envelope coordinates compatibility + AnswerStage on an existing revised envelope (after apply_expansion). No envelope mutation, no domain logic (I-11). Suite I4 added. 38 passed. No deviation from locked contracts. Next: remaining P1 boundaries or further retrieval integration.

- Context-Aware Reasoning initial evidence snapshot: QueryContextEngine.create_envelope creates immutable snapshot (I-10) when store present and evidence_refs supplied. Orchestrator wires package-derived span_ids. Suite I2 added. 35 passed. No domain logic. Next: remaining P1 boundaries or expansion path integration.

- Context-Aware Reasoning package evidence adapter: extract_evidence_spans under okc/context/package_adapter.py maps KnowledgePackage objects to evidence span dicts (existing spans + explicit metadata constraints only). ContextOrchestrator accepts optional package and uses adapter when evidence_spans omitted. Suite I1 added. 34 passed. No inference, no domain logic. Next: remaining P1 boundaries or further retrieval integration.

- Context-Aware Reasoning orchestrator minimal increment: ContextOrchestrator under okc/context/orchestrator.py coordinates QueryContextEngine + EvidenceCompatibilityEngine + AnswerStage. Creates envelope, requests pre-authorized affordances, produces structured answer. No domain logic (I-11). Suite H1 added. 33 passed. No deviation from locked contracts. Next: remaining P1 boundaries or further integration.


- Context-Aware Reasoning snapshot wiring: QueryContextEngine now accepts optional EvidenceSnapshotStore. promote_with_evidence always creates a new immutable snapshot (I-10) when store is attached; preferred id used if free, else unique suffix. Suite G5 added. 32 passed. No deviation from locked contracts. Next: remaining P1 boundaries or further integration.

- Context-Aware Reasoning Evidence Snapshot Store minimal increment: EvidenceSnapshotStore under okc/context/snapshot_store.py owns immutable snapshots. create_snapshot always produces a new frozen object with parent lineage; re-creation of same id rejected; get returns original. Suite E3 now verifies immutability and new-on-retrieval. 31 passed. No deviation from locked contracts (I-10). Next: wire store into QueryContextEngine or remaining P1 boundaries.
- Context-Aware Reasoning Query Context Engine minimal increment: QueryContextEngine under okc/context/query_engine.py owns envelope creation and revisions with parent lineage. Assumptions never auto-promote to RESOLVED; only explicit user confirmation or new evidence does. New evidence updates snapshot ref. Suite G regressions added. 31 passed. No deviation from locked contracts. Next: evidence snapshot store or remaining P1 boundaries.
- Context-Aware Reasoning Answer Stage minimal increment: AnswerStage under okc/context/answer.py produces locked structured output (independent answer_delivered and contextually_complete flags, assumption disclosure, unresolved high-sensitivity forcing incomplete, insufficient evidence path, pre-authorized affordances only). Suite F regressions added. No deviation from locked contracts. Next: Query Context Engine or evidence snapshot handling.
- Context-Aware Reasoning first implementation gate: deterministic tests now executable (tests/test_context_aware_reasoning.py). Minimal ContextDimension, QueryContextEnvelope, ExpansionAffordance, ContextRegistry, and EvidenceCompatibilityEngine under okc/context/ obey locked contracts in design/context-aware-reasoning/. Suites A–E covered. 23 passed. No deviation from locked design. Implementation authorised; next increments remain smallest coherent against these tests.

## Recent verified advances (2026-11-16)
- Local OKC server /api/health now reports `python_executable` (sys.executable) (P3). Operators can confirm the exact Python interpreter running the local pilot without process inspection. API version 0.2.12-local. New regression asserts. Tests updated to match.
- Local OKC server /api/health now reports `open_file_descriptors_count` (P3). Operators can observe open file descriptor usage (useful for detecting leaks in long-running pilot processes) without external tooling. API version 0.2.11-local. New regression asserts. Tests updated to match.

- Local OKC server /api/health now reports `registered_importer_names` (sorted list of importer plugin names) (P3). Operators can confirm exactly which source importers are available without starting a job or reading code. API version 0.2.10-local. New regression asserts. Tests updated to match.

- Local OKC server /api/health now reports `active_threads_count` and `cpu_count` (P3). Operators can observe thread usage (relevant for background pipeline jobs) and CPU availability without external tooling. API version 0.2.8-local. New regression asserts. Tests updated to match.

- Local OKC server /api/health now reports `memory_rss_mb` (P3). Operators can observe process resident set size without external tooling. API version 0.2.7-local. New regression asserts. Tests updated to match.

## Recent verified advances (2026-11-15)
- Local OKC server /api/health now reports `listen_host` and `listen_port` (P3). Operators can confirm the binding address and port without process inspection. New regression asserts. API version bumped to 0.2.6-local.

## Recent verified advances (2026-11-15)

## Recent verified advances (2026-11-15)
- Local OKC server /api/health now reports `process_start_time_utc` and `uptime_seconds` (P3). Operators can observe process lifetime without external tooling. API version 0.2.5-local. New regression asserts. Tests updated to match.

- Local OKC server /api/health now reports `upload_dir_free_mb` and `db_parent_free_mb` (P3). Operators can detect approaching disk exhaustion on upload and persistence volumes without shell inspection. New regression asserts added. API version bumped to 0.2.4-local.


- Local OKC server /api/health now reports `registry_ready`, `registered_plugins_count`, and `registered_importers_count` (P3). Operators can confirm the plugin registry loaded and see importer/plugin counts without starting a job. New regression asserts added. API version bumped to 0.2.3-local.
- Local OKC server /api/health now reports `process_id`, `cwd_absolute`, `upload_dir_configured`, and `sqlite_path_configured` (P3). Operators can confirm process identity, working directory for relative paths, and whether upload/DB paths were overridden via env without shell inspection. New regression asserts added. API version bumped to 0.2.2-local.

## Recent verified advances (2026-11-14)
- Local OKC server /api/health now reports `upload_dir_absolute` and `db_path_absolute` (P3). Operators can confirm the exact resolved filesystem locations used by the local pilot without source or env inspection. New regression asserts added. API version bumped to 0.2.1-local.

- Local OKC server /api/health now reports `google_credentials_configured` and `active_jobs_count` (P3). Operators can confirm whether GOOGLE_APPLICATION_CREDENTIALS is set and see the current in-memory job count without inspecting process state. New regression asserts added.
- Local OKC server /api/health now reports `db_exists` boolean for local SQLite persistence state (P3). Operators can confirm whether the DB file has been created without filesystem inspection. New regression asserts added.
- Local OKC server /api/health now reports `python_version`, `platform`, and `api_version` for environment and code-identity diagnostics (P3). Operators can confirm runtime without source inspection. New regression asserts added. Documented in PERMISSION_MODEL.md.
- Local OKC server /api/health now reports `tenant_configured` and `silo_configured` booleans (P3). Operators can confirm required OKP_TENANT_ID / OKP_SILO_ID env presence without starting a job. New regressions added. Documented in PERMISSION_MODEL.md operator visibility.

- Restored ROADMAP.md and AGENT_COMMIT_LOG.md after accidental placeholder overwrite in 87abccb. Source of truth for agents re-established. No functional change.

## Recent verified advances (2026-11-13)
- Local OKC server /api/health now reports current OKP_STRICT_PERMISSIONS mode as a boolean (P1/P3). Operators can confirm the mode without starting a compile job. New regressions added. Documented in PERMISSION_MODEL.md operator visibility.

- Added regression tests for local OKC server job status API exposing strict_permissions boolean (P1/P3).
- Local OKC server job status API now returns structured `strict_permissions` boolean when present (in addition to mode in message). Operators and API clients can observe the mode without parsing text (P1/P3).
- Local OKC server job completion now reports permission mode (pilot|strict) in status message and job record. Operators can verify OKP_STRICT_PERMISSIONS was honored (P1/P3).

## Recent verified advances (2026-11-12)
- Local OKC server (okc/server/app.py) now honors OKP_STRICT_PERMISSIONS env for HybridRAG index and SQLite export on the upload/compile path (P1/P3). Default remains pilot mode.
- HybridRAGEngine.index_package(strict_permissions=True) excludes objects with source identity but no permission entry. New regression tests/test_okc_v2.py::test_hybrid_rag_strict_excludes_missing_permission passed.
- Baseline Connect + permission suite re-verified on current main (a156c62): 70 passed. No regressions from recent P1 filters.
- HybridRAGEngine.index_package now excludes objects with explicit read=False (same filter as retriever/exporters). Denied content is not indexed or searchable. New regression passed.
- ProvenanceLedgerExporter and RelationshipIndexExporter now exclude knowledge_objects with explicit read=False in package.metadata["permissions"] (aligned with other delivery boundaries). New regressions added and passed.
- MultiSourceExporter (legacy src/ path) now excludes conversations with explicit read=False from content files, indexes, platform.json, unit manifests, and root compilation totals. Regression extended.
- Health CLI recovery_hints for all common WARNING reasons (including queue and provenance).
- permissions_missing_event_provenance and orphaned_permission_entries elevate WARNING.
- FirestoreExporter permission filter unit-tested.
- Baseline Connect suite green (69 passed on prior verification; 64 on targeted after json import fix).
- Dockerfile and operator guide updated with reproducible Docker start for the local-folder Connect worker (P3).

## Next highest-value action
Continue remaining P1 authorization boundaries or further Context-Aware Reasoning integration (C4 multi-alternative affordances now implemented) (e.g., real evidence retrieval path). Prefer smallest coherent change with new regression evidence against locked contracts.


Continue Context-Aware Reasoning (orchestrator wiring of QueryContextEngine + snapshot store) or remaining P1 authorization boundaries. Prefer the smallest coherent change that produces new regression evidence against locked contracts.

- Fixed missing json import in run_connect_worker.py so --config path works (P3).
- Docker packaging for Connect pilot documented (P3).

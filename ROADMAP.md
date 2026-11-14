# OKP Roadmap — Knowledge Infrastructure, Connect Reliability, and B2B Pilot

**Updated:** 2026-11-14  
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

## Recent verified advances (2026-11-14)
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
Continue P1 remaining authorization boundaries (e.g., other in-memory indexes, caches, Studio surfaces, or ingestion paths) or advance further P3 diagnostics under optional dependencies. Prefer the smallest coherent change that produces new regression evidence. Local server mode visibility is now documented.

- Fixed missing json import in run_connect_worker.py so --config path works (P3).
- Docker packaging for Connect pilot documented (P3).

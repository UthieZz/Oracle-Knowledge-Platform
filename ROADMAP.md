# OKP Roadmap — Knowledge Infrastructure, Connect Reliability, and B2B Pilot

**Updated:** 2026-11-11  
**Basis:** Current-main source, STAGE.md, AGENT_COMMIT_LOG.md, and targeted Connect suite evidence.  
Implementation, recorded test evidence, runtime verification and planned work are intentionally distinguished.  
**Companion analysis:** docs/BUILD_FIRST_TECHNICAL_ANALYSIS_2026-10-22.md

## Mission

Oracle Knowledge Platform (OKP) turns fragmented information from AI systems and other sources into structured, reusable, searchable and traceable knowledge.  
It is knowledge infrastructure—not simply a chatbot or conversation archive.

The near-term product objective is a dependable, demonstrable vertical slice: connect an approved source, synchronize changes in the background, maintain a governed KnowledgePackage, retrieve grounded evidence, and make operational state inspectable.

## Current implementation snapshot — 2026-11-11

### Knowledge Core and application path
- Multi-source importer architecture and PluginRegistry present.
- Canonical KnowledgePackage (okc/models) is the sole IR.
- Provenance, source IDs, tenant/silo preserved through processing.
- Permission model documented; explicit deny honored; strict mode available; default pilot keeps missing entries visible for compatibility.
- FirestoreExporter applies permission filter (unit-tested).
- Studio AuthGate and firestore.rules present (deployed behavior not fully verified).

### OKP Connect local-folder pilot
Implemented and targeted-tested (recent runs: health suite 25 passed; broader Connect suite 65 passed on 2026-11-10 baseline):
- LocalFolderConnector with persistent snapshot (restart deletion detection, sequence for event_ids).
- SQLite SyncEngine (WAL, dedup, retry/backoff, cursor advances only on success).
- KnowledgeAccumulator (source|tenant|silo namespacing, persist/rollback, cross-scope isolation).
- Health CLI (scripts/connect_health.py): status=OK|WARNING, exit 1 on WARNING, --json, --config, --strict-check. Reports package/snapshot consistency, provenance gaps, orphaned entries, queue age, lag, etc. Emits structured recovery_hints for all current WARNING reasons.
- Recovery CLI (scripts/connect_recover.py): list/reset failed events with filters, config support, clean JSON.
- Operator guide: docs/CONNECT_LOCAL_PILOT.md.

Knowledge Core IR and Connect contracts unchanged by recent health/recovery work.

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
**Status:** Partial. Explicit permission_change (read=False/True) enforced on retrieval, context gateway (strict), and Firestore export. Orphaned and missing-event-provenance elevate health WARNING. Lifecycle semantics documented in docs/PERMISSION_MODEL.md.  
**Gaps:** remaining boundaries (e.g., other exporters, admin paths, cache invalidation); full fail-closed production mode not default.  
**Next:** identify and close one verified weak boundary with regression.  
**Acceptance:** no cross-tenant/silo leakage; revocation survives updates; missing permission denied under strict mode across all delivery paths; provenance complete on permission decisions.

### P2 — Architecture consistency
**Status:** Ownership map recorded. Dual src/okc surfaces intentional for now.  
**Next:** keep mapping current; avoid unnecessary migrations.  
**Acceptance:** documented active/obsolete paths; no competing IRs.

### P3 — Local pilot operability
**Status:** Strong progress. Config files, recovery CLI, health recovery_hints, cursor/snapshot visibility, operator guide.  
**Next:** reproducible setup packaging (Docker/entrypoints or documented one-command start), diagnostics under optional deps.  
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

## Recent verified advances (2026-11-10/11)
- Health CLI recovery_hints for all common WARNING reasons (including queue and provenance).
- permissions_missing_event_provenance and orphaned_permission_entries elevate WARNING.
- FirestoreExporter permission filter unit-tested.
- Baseline Connect suite green (65 passed).

## Next highest-value action
Continue P1 remaining authorization boundaries or advance P3 reproducible operator packaging. Prefer the smallest coherent change that produces new regression evidence.

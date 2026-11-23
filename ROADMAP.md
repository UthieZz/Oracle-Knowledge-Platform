# OKP Roadmap — Knowledge Infrastructure, Connect Reliability, and B2B Pilot

**Updated:** 2026-11-23
**Basis:** Current-main source, STAGE.md, AGENT_COMMIT_LOG.md, and targeted Connect suite evidence.
Implementation, recorded test evidence, runtime verification and planned work are intentionally distinguished.
**Companion analysis:** docs/BUILD_FIRST_TECHNICAL_ANALYSIS_2026-10-22.md

## Recent verified advances (2026-11-23)
- LocalFolderConnector mixed changes under persist failure: regression locks that create+update+delete applied while a persist fails roll back in-memory and on-disk prior snapshot; subsequent retry emits the correct events and package converges with no loss or duplicates. Local-folder suite 14 passed. Strengthens Connect reliability under interruption. No IR or permission contract change.

## Recent verified advances (2026-11-23)
- LocalFolderConnector persist failure: regression locks that a simulated atomic-replace failure after .tmp write leaves the prior valid snapshot intact and loadable on next init. No data loss of the last successful snapshot. Test added; local-folder suite 12 passed. Strengthens Connect reliability under interruption. No IR or permission contract change.


## Mission

Oracle Knowledge Platform (OKP) turns fragmented information from AI systems and other sources into structured, reusable, searchable and traceable knowledge.  
It is knowledge infrastructure—not simply a chatbot or conversation archive.

The near-term product objective is a dependable, demonstrable vertical slice: connect an approved source, synchronize changes in the background, maintain a governed KnowledgePackage, retrieve grounded evidence, and make operational state inspectable.

## Recent verified advances (2026-11-22)
- ExportService.export_knowledge: now reads OKP_STRICT_PERMISSIONS and forwards strict_permissions to every registered exporter (MultiSource, RelationshipIndex, ProvenanceLedger, Firestore). Pilot default (False) preserved. Aligns legacy ExportService path with CompilerAdapter / local server / CAR / other exporters. Regression added (2 passed). No IR or Connect contract change.

## Recent verified advances (2026-11-22)
- MultiSourceExporter: export() and internal filtering now accept and honor optional strict_permissions (default False). Explicit deny always excluded; under strict, source-identity conversations without explicit entry are excluded. Aligns remaining legacy multi-source delivery boundary with Firestore / SQLite / CAR / ledger / relationship / CompilerAdapter. Regression added (6 passed). No IR or Connect contract change.

## Recent verified advances (2026-11-22)
- Context-Aware Reasoning orchestrator: process_query and retrieve_for_affordance now accept and forward strict_permissions to extract_evidence_spans. Missing-permission evidence is excluded under strict mode before it can enter the CAR pipeline. Aligns orchestrator with package_adapter / retriever / exporters. Suite expanded. 38 passed. No deviation from locked contracts.
- Context-Aware Reasoning package_adapter: extract_evidence_spans now filters by permission model (explicit read=False always excluded; strict_permissions excludes missing when source identity present). Aligns CAR evidence path with retriever/exporters. Suite expanded. 37 passed. No deviation from locked contracts.
- Context-Aware Reasoning suite restored to green: malformed constraints treated as unconstrained (B5); AnswerStage expansion_affordances attribute alignment (I-06/I-07). 34 passed (prior). No deviation from locked contracts.
- ProvenanceLedgerExporter and RelationshipIndexExporter: now accept optional strict_permissions (default False). Under strict mode, objects with source identity but no explicit permission entry are excluded (aligned with FirestoreExporter / SQLite / HybridRAG / CAR adapter). Explicit deny remains always-excluded. Pilot default unchanged. New regressions added. No IR or Connect contract change.

- Context-Aware Reasoning orchestrator: process_query and retrieve_for_affordance now accept and forward strict_permissions to extract_evidence_spans. Missing-permission evidence is excluded under strict mode before it can enter the CAR pipeline. Aligns orchestrator with package_adapter / retriever / exporters. Suite expanded. 38 passed. No deviation from locked contracts.
- Context-Aware Reasoning package_adapter: extract_evidence_spans now filters by permission model (explicit read=False always excluded; strict_permissions excludes missing when source identity present). Aligns CAR evidence path with retriever/exporters. Suite expanded. 37 passed. No deviation from locked contracts.
- Context-Aware Reasoning suite restored to green: malformed constraints treated as unconstrained (B5); AnswerStage expansion_affordances attribute alignment (I-06/I-07). 34 passed (prior). No deviation from locked contracts.

## Recent verified advances (2026-11-21)
- Context-Aware Reasoning successive retrieval lineage: locks that successive retrieve_for_affordance calls create distinct immutable snapshots with correct parent_snapshot_id chain and corresponding envelope revisions with parent_revision (I-10/I-09). Suite expanded. 34 passed. No deviation.
- Context-Aware Reasoning I-08/I-05: locks that every material factual claim from supporting evidence appears in the claims array (support_status + evidence_refs) and that conflicts passed to AnswerStage are retained in context.conflicted_dimensions + qualifications (no silent removal; neither alternative treated as established). Suite I expanded. 33 passed. No deviation.

## Recent verified advances (2026-11-20)
- Context-Aware Reasoning I-06/I-07: locks that AnswerStage receives only pre-authorized affordances and passes them through unmodified (eligibility and execution metadata unchanged). Suite expanded. 31 passed. No deviation.


- Context-Aware Reasoning orchestrator retrieval path: locks I-10 (retrieval creates new immutable evidence snapshot with parent link) and I-09 (new envelope revision with parent_revision) on retrieve_for_affordance for RETRIEVABLE affordances. Suite I. 29 passed. No deviation.

- Context-Aware Reasoning AnswerStage insufficient-evidence path: locks answer_delivered=false + reason=insufficient_evidence when no material evidence/assumptions, independent contextually_complete=false, no invented claims, high-sensitivity non-assumable disclosed as unresolved+unavailable, disclosure summary includes flags. Suite F. 28 passed. No deviation.

- Context-Aware Reasoning A2/A5/B5: domain extension via new version (same-version rejected), package support declaration alone does not emit affordance, invalid provenance classified unconstrained. Suite expanded. 27 passed (prior). No deviation.

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

## Recent verified advances (2026-11-19)
- Context-Aware Reasoning per-dimension classification: Suite B6 verifies independent per-dimension classification on a single span (unconstrained / fully compatible / partially compatible). 52 passed. Locks consistency-review clarification. No deviation.


- Context-Aware Reasoning unavailable dimensions: AnswerStage discloses high-sensitivity missing dimensions that cannot be assumed as unavailable_dimensions (subset of unresolved). Suite F10. 50 passed. No deviation. Next: remaining P1 boundaries or further retrieval integration.

- Context-Aware Reasoning presentation disclosure: AnswerResult.to_disclosure_summary emits content + qualifications + independent completion flags/reason + unresolved/conflicts. Suite F9. 49 passed. No deviation. Next: remaining P1 boundaries or further retrieval integration.

- Context-Aware Reasoning conflicts as claims: AnswerStage emits support_status=conflicted claim for retained conflicts (neither treated as established). Suite F8. 48 passed. No deviation. Next: remaining P1 boundaries or further retrieval integration.

- Context-Aware Reasoning completion reason: Suite F7 verifies conflicts_retained is disclosed when answer delivered under retained conflicts and no high-sensitivity unresolved. 47 passed. No deviation. Next: remaining P1 boundaries or further retrieval integration.


- Context-Aware Reasoning completion reason disclosure: AnswerStage sets specific reason when delivered under incomplete high-sensitivity or conflicts. Suite F6. 46 passed. No deviation. Next: remaining P1 boundaries.

- Context-Aware Reasoning retrieval path completeness: Suite I10 added verifying retrieve_for_affordance followed by answer_from_envelope sets contextually_complete=True when high-sensitivity dimension is resolved by retrieved evidence. 45 passed. No deviation from I-09/I-10/I-11/I-12. Next: remaining P1 boundaries or further retrieval integration.

- Context-Aware Reasoning AnswerStage partial/background disclosure: produce now emits claims with support_status=partial and =background when those evidence classes are present, plus explicit partial qualification. has_material includes partial. Suite F5 added. 44 passed. Aligns with I-08 and Answer-Stage contract (partial requires qualification; unconstrained = background only). Next: remaining P1 boundaries or further retrieval integration.

## Recent verified advances (2026-11-18)

- Context-Aware Reasoning D5 projected_change: EvidenceCompatibilityEngine.generate_affordances now populates projected_change with an estimate-only string on all emitted affordances (AVAILABLE and RETRIEVABLE). Suite D1/D2 regressions extended. 43 passed. No deviation from D5 (estimate, not promise) or I-11. Next: remaining P1 boundaries or further retrieval integration.

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
- Local OKC server /api/health now reports `process_id`, `cwd_absolute`, `upload_dir_configured`, and `sqlite_path_configured` (P3). Operators can confirm process identity, working directory, and configured paths without shell inspection. New regression asserts. API version 0.2.2-local.

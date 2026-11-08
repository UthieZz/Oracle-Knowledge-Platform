# OKP Roadmap — Knowledge Infrastructure, Connect Reliability, and B2B Pilot

**Updated:** 2026-11-07  
**Basis:** Current-main source and documentation review. Implementation, recorded test evidence, runtime verification and planned work are intentionally distinguished.  
**Companion analysis:** [Build-First Technical Analysis — 2026-10-22](docs/BUILD_FIRST_TECHNICAL_ANALYSIS_2026-10-22.md)

## Mission

Oracle Knowledge Platform (OKP) turns fragmented information from AI systems and other sources into structured, reusable, searchable and traceable knowledge. It is knowledge infrastructure—not simply a chatbot or conversation archive.

The near-term product objective is a dependable, demonstrable vertical slice: connect an approved source, synchronize changes in the background, maintain a governed KnowledgePackage, retrieve grounded evidence, and make operational state inspectable. Prove that path with one useful workflow before broadening connector coverage or deployment complexity.

The current local-folder runner is a practical foundation for a pilot, not a claim that the complete B2B product is finished. Commercial readiness must be established through reproducible tests, a supported deployment, clear access boundaries and a customer-measured outcome.

## How to interpret roadmap status

- **Implemented:** code or contracts exist in the current repository.
- **Recorded tested:** project documentation records targeted test evidence. Historical results are not equivalent to a fresh full-suite run.
- **Needs verification:** the code path exists but requires stronger regression, runtime or end-to-end evidence.
- **Planned:** work not yet established as complete.
- **Not verified by this roadmap update:** live Firebase/Firestore configuration, deployed Studio behavior, production credentials/rules, complete branch/PR reconciliation, a full secret scan, full test-suite execution and customer-pilot results.

Do not turn a recorded test into a production-readiness claim. Update status when new evidence exists.

## Product and architecture invariants

1. `KnowledgePackage` remains the canonical intermediate representation (IR) and knowledge boundary.
2. Connectors and SyncEngine emit and deliver events; they do not mutate KnowledgePackage directly. A processor uses the existing importer/compiler path.
3. Canonical knowledge remains separate from feedback records, audit events and memory candidates. Memory candidates are not promoted automatically.
4. Source identity, provenance, chronology and tenant/silo scope must survive import, compilation, persistence, retrieval and export.
5. Access policy must be enforced at each relevant boundary, not inferred from tenant/silo fields merely being present.
6. Source deletions and permission revocations must affect subsequent retrieval and relevant derived context according to a documented retention policy.
7. Sync is designed for durable, retryable and idempotent delivery. Exactly-once effects must not be claimed without a defined transaction/replay strategy and tests.
8. PluginRegistry remains dispatch/discovery infrastructure, not a second IR.
9. Deterministic processing is preferred where sufficient. AI can enrich and reason over knowledge but does not replace source traceability.
10. Keep model providers, connectors, storage adapters and UI separable from Knowledge Core.
11. Preserve the current Firebase Spark/no-cost constraint recorded in `GEMINI.md`; do not add paid services or billing without an explicit decision.
12. Avoid a compiler/IR rewrite, wholesale Studio rewrite, broad connector marketplace or new infrastructure without evidence of measurable value.

## Current implementation snapshot — 2026-11-07

### Knowledge Core and application path

- Multi-source importer architecture and PluginRegistry are present; the README lists AI conversation exports, Markdown, PDF, HTML and plain text as supported input categories.
- `KnowledgePackage` schema v2 defines structured knowledge objects, provenance, evidence spans, entities, attachments, relationships and citations, with JSON serialization and rehydration.
- PackageCompiler is documented as a structural/provenance validation boundary.
- Firestore publishing and React/PWA Studio code paths exist in the repository. Root `firestore.rules` now gate reads by tenant/silo claims and deny client writes.
- Older `src/` and newer `okc/` implementation surfaces coexist. Their ownership and deployment references need deliberate reconciliation. Connect path uses `okc/`.
- The README's input list is not proof that every format has equal current test coverage. Keep importer/attachment maturity tied to fixtures and test evidence.

### OKP Connect — built vertical slice (P0 largely complete for local-folder pilot)

Current code and `docs/STAGE.md` (updated through 2026-11-07) record these components, with targeted tests passing:

1. **Connector contract:** authentication, initial and incremental sync, deletion, permissions and health; SyncEvent carries event ID, source, kind, cursor/payload, tenant and silo.
2. **SQLite SyncEngine:** durable event queue (WAL), cursor table, event-ID deduplication, processor invocation, attempt/error tracking, bounded retry with exponential backoff, manual recovery (`reset_failed`), enhanced health (failed count, queue age, last_processed_at, waiting_for_retry). Cursor advances only on success. Interrupted `process_next` does not advance cursor. Multi-instance and concurrent multi-thread writers tested.
3. **SyncWorker:** managed start/stop background polling, connector polling, queue enqueue/drain and worker/connector health. Queue/cursor survive process restart.
4. **LocalFolderConnector:** recursive `.txt` / `.md` scanning, content hashes and create/update/delete events. Optional `snapshot_path` loads prior state on restart so files deleted while stopped generate delete events. Snapshot stores version, monotonic sequence and map; event_ids incorporate sequence so delete/recreate of identical content receives a new id. Tested, including real subprocess process-restart deletion convergence.
5. **KnowledgeAccumulator:** imports text through PlainTextImporter, upserts by source marker, removes deleted objects and records permission-change metadata. Source identity namespaced as `source|tenant_id|silo_id|object_id` (legacy unscoped readable). Optional package_path loads/saves canonical JSON (atomic write). Process rolls back in-memory state if persist fails. Identical create after successful persist is idempotent. Cross-scope isolation tested.
6. **Persistent living package:** survives process restarts. Real process-restart test confirms package converges after stop/delete/restart.
7. **Pilot runner and health CLI:** `scripts/run_connect_worker.py` (tenant/silo required) and `scripts/connect_health.py`. Health reports queued/processed/failed, oldest age, last_processed_at, failed details, cursors, package object_count consistency, permissions_entries/explicit_read_false, last_source, package_lag_seconds, and ends with `status=OK|WARNING` (exit 1 on WARNING). Warnings cover failed, missing/unreadable package/snapshot, mismatch, high queue age, high package lag, high waiting_retry, no_ready_events.
8. **Retrieval permission behavior:** filtering for explicit `read=False` entries; objects without entry remain visible (documented compatibility). Not a complete authorization system.

**Current verification evidence (this environment, 2026-11-07):** targeted Connect suite (sync_engine + accumulator + local_folder + worker + health + e2e + contract) 40 passed. Full suite previously recorded 144-145 passed with failures only in optional-dependency tests (grounded_ask missing GEMINI_API_KEY; firestore exporter). Knowledge Core IR unchanged.

### Still to prove before production claims

- Complete authorization across ingestion, persistence, retrieval, context, export and administrative access (P1).
- End-to-end provenance/citation integrity across the actual application path (P1/P2).
- Supported service packaging, setup/configuration, credential handling, upgrades, backup and recovery (P3).
- A real business-system connector, onboarding/identity integration, and a measured pilot (P4+).
- Current full Python suite under complete optional dependencies, Studio build and deployed-runtime verification.
- Reconciliation of `src/` vs `okc/` ownership without breaking working paths.

## Target user journey

`Install/deploy → sign in → select tenant/silo → authorize source → initial sync → background updates → governed search/context → inspect evidence and sync health`

Manual import remains a supported fallback. The product goal is to reduce repeated manual export/import for sources that can be safely and legitimately synchronized.

## Priority roadmap

### P0 — Harden the existing Connect vertical slice — largely complete for local-folder pilot (as of 2026-11-07)

**Goal:** Make the implemented local-folder path recoverable, scope-safe and repeatable before expanding source breadth. **Status: implemented and targeted-tested for the local path.** Remaining: full optional-deps suite, Studio build, and production claims require P1+ evidence.

1. **Persist or reconstruct connector snapshots.** Implemented via optional `snapshot_path` on LocalFolderConnector. Loads prior state on restart; deletions while stopped generate delete events. Sequence in snapshot ensures new event_ids on delete/recreate of identical content. Tested, including real subprocess restart convergence. 
2. **Namespace source identity.** Implemented. Accumulator keys by `source|tenant_id|silo_id|object_id`. Identical object_ids cannot collide across scopes. Legacy unscoped markers remain readable. Tested.
3. **Define event lifecycle IDs.** Implemented via sequence in snapshot/event_ids. Retry deduplication preserved; delete/recreate of same content gets new id. Regression covered.
4. **Prove crash boundaries.** Interrupted `process_next` does not advance cursor. Persist-failure rolls back accumulator state. Real process-restart test confirms package convergence. Multi-instance and concurrent multi-thread writers on WAL queue tested (no loss).
5. **Define retry and recovery policy.** Bounded retry (max_attempts), exponential backoff via `next_retry_at`, manual `reset_failed`, failed list with details. Cursor advances only on success. Tested.
6. **Add explicit regression cases:** stopped-worker deletion (real subprocess), delete/recreate via sequence, cross-scope isolation, persist rollback, concurrent writers, retry exhaustion (with backoff adjustment in test), permission recording. Present and passing.
7. **Run and record current verification:** Targeted Connect suite 40 passed (2026-11-07 this environment). Full suite historically 144-145 passed with optional-dep failures only. Studio production build and deployed runtime not re-verified in this run.

**Acceptance evidence (local pilot):** package converges to source after restart (verified); events replay without silent loss or duplicate knowledge; identical source IDs cannot cross scopes; failure state is visible via health CLI (status=WARNING + exit 1) and recoverable; current targeted test outcomes recorded in STAGE.md and AGENT_COMMIT_LOG.md.

**Next within/after P0:** full suite under complete optional dependencies; any additional crash-boundary cases if new evidence of gaps appears. Shift focus to P1 authorization consistency or P3 operator packaging for the pilot.

### P1 — Make authorization and provenance consistent

**Goal:** Preserve the trust properties that make knowledge reusable in a multi-source and potentially multi-tenant platform.

1. Define an explicit access-policy model for tenant, silo, user/source permissions and missing permission data.
2. Apply and test policy at ingestion, queue processing, package access, retrieval, context construction, publishing/export and administrative operations.
3. Test read revocation after prior retrieval, context/cache invalidation, deletion, restoration and tenant/silo mismatch.
4. Document the current compatibility behavior where objects without a permission entry remain visible; decide whether pilot and production modes need different defaults. **Done for pilot:** see docs/PERMISSION_MODEL.md (default visible; strict_permissions and --strict-check available).
5. Trace provenance from source through importer, compiler, package persistence, exporter, retrieval and final citation. Ensure a cited source actually supports the answer rather than being attached merely because it was retrieved.
6. Reconcile provenance and source-identity handling across `okc/` and `src/`, especially where exporter object identity or relationship/attachment lineage may differ.
7. Document retention and deletion semantics for packages, exports, caches, backups and tenant offboarding.

**Acceptance evidence:** policy tests cover every relevant boundary; revoked content is not returned by subsequent governed retrieval; citations and source identity are traceable; default permission behavior is documented and intentional.

### P2 — Reconcile the implementation surfaces and verify the end-to-end product path

**Goal:** Keep the architecture explainable without disrupting working paths.

1. Map each runtime entry point to its authoritative implementation across `okc/`, `src/` and `studio/`.
2. Inspect current branches and pull requests before merging, closing or retiring anything; compare diffs against main and avoid duplicating changes already landed.
3. Verify the KnowledgePackage/compiler → export/publish → Studio → retrieval/context path with representative data.
4. Confirm tenant/silo scope and provenance survive the publishing path. Inspect live Firebase configuration and security rules only through authorized access; distinguish code presence from deployed state.
5. Reconcile README, stage notes, roadmap and agent log with current evidence.
6. Remove or retire duplicate/legacy paths only after references, deployment usage and tests establish that doing so is safe.

**Acceptance evidence:** the primary runtime paths are documented; no critical merge ambiguity is hidden by roadmap wording; the main product workflow is reproducible and source evidence survives it.

### P3 — Operate the local pilot reliably
**Recent (2026-11-08):** Added scripts/connect_recover.py for listing and resetting failed events (manual recovery without DB inspection). Health CLI text output now includes a recovery_hint when failed events are present.

**Recent (2026-11-08):** Optional JSON config file support added to health and worker CLIs (CLI overrides config). Reduces operator argument repetition for the local pilot.
**Recent (2026-11-08 continued):** Health CLI text output now reports package/snapshot details when paths come from `--config`. Added `docs/CONNECT_LOCAL_PILOT.md` with exact operator commands and config example.

**Goal:** Turn the runner into a repeatable pilot installation without prematurely building a full control plane.

1. Define the initial supported operating environment and local-folder trust boundary.
2. Separate configuration from code; document root path, database path, package path, tenant/silo selection and safe file permissions.
3. Provide setup, start/stop, restart, backup/restore, upgrade and recovery instructions.
4. Package the runner for the selected environment (for example, a system service or container entrypoint only if appropriate to the target).
5. Expand health output to cover last successful sync, last poll, queue age/lag, retry/stuck events, connector health and package freshness.
6. Ensure secrets are not committed, included in logs, or exposed in diagnostics.
7. Test filesystem permission errors, unavailable roots, malformed files, disk-full/write failures, network-independent restarts and graceful shutdown.

**Acceptance evidence:** a new operator can follow documented steps, inspect whether the package is current, recover from a failed run and avoid founder-only knowledge. Keep the CLI if it is sufficient for the first pilot; build an admin UI only when user evidence justifies it.

### P4 — Implement one real business-system connector

**Goal:** Prove that the Connect contract generalizes beyond a local directory.

1. Choose one source based on a concrete customer workflow, API feasibility, authorization scopes and likely value.
2. Implement it behind the existing connector contract; preserve SyncEvent → SyncEngine → processor/importer/compiler → KnowledgePackage.
3. Support initial and incremental sync according to the source's actual API semantics.
4. Test create/update/delete, permission changes where available, revoked credentials, rate limits, pagination, partial failures, duplicate delivery and recovery.
5. Record supported scopes, source limitations, rate limits, data retention and operator actions.
6. Do not build a broad connector marketplace before this connector and workflow are reliable.

**Acceptance evidence:** repeated sync from a real source survives restart and failures, with verified identity/provenance and a documented permission model.

### P5 — Onboarding, identity and supported deployment

**Goal:** Let a pilot customer set up and operate OKP without ad hoc developer intervention.

1. Choose the deployment shape before choosing installer and identity technologies.
2. Build the minimum journey: install/deploy → sign in → tenant/silo setup → source authorization → initial sync → visible status.
3. Keep application sign-in separate from source-connector authorization.
4. Store credentials through an appropriate secret mechanism and apply least-privilege source scopes.
5. Define identity, tenant administration, silo membership and offboarding boundaries before adding SSO.
6. Add SSO only when required by the target deployment and when its identity model can be tested.
7. Establish upgrade/rollback, backup/restore, support and operational procedures.

**Acceptance evidence:** a new pilot operator can configure the system, understand what source data it can access, see sync status, re-authenticate and recover without losing queued work or scope guarantees.

### P6 — Grounded intelligence and measurable pilot

**Goal:** Demonstrate that better-organized knowledge produces measurable utility.

1. Create fixtures for source conflicts, duplicate/stale content, missing evidence, permission-filtered retrieval and unsupported questions.
2. Measure retrieval relevance, citation correctness, freshness, compilation reliability and failure recovery.
3. Keep direct source evidence distinct from derived fields and model-generated synthesis.
4. Choose one customer workflow and agree on baseline/success criteria before the pilot.
5. Measure time to find evidence, time to reconstruct project/business context, duplicate research avoided, retrieval/citation correctness, sync reliability and operator effort.
6. Record limitations and failure cases as well as successful demonstrations.

**Acceptance evidence:** repeatable demonstration and customer-confirmed results support a clear decision about what to productize next.

### P7 — Commercial packaging and IP diligence

Prepare:
- architecture and data-flow diagrams;
- KnowledgePackage, compiler, provenance and Connect contracts;
- tested connector/deployment matrix;
- access-control model and threat-model evidence;
- install, upgrade, backup, restore and operations guide;
- dependency and third-party/open-source inventory;
- reproducible test results, known limitations and pilot results;
- ownership, contribution and licensing documentation.

Keep implemented, test-verified, runtime-verified, planned and experimental work explicitly distinct. Do not use an estimated readiness percentage unless the criteria and evidence behind it are defined.

### P8 — Expand only when evidence warrants it

Potential later work includes more connectors, private/customer-controlled deployment, hybrid operation, stronger policy controls, advanced identity, metering and larger-scale hosting. Choose these based on pilot demand and operational evidence. Keep the canonical package and connector contracts stable across deployment shapes.

## Local-first and cloud direction

OKP should keep the knowledge core independent of any single storage or hosting provider. Firestore may remain a useful publishing/operational adapter for the current Studio path, while local/customer-controlled deployment evolves incrementally.

Preserve this integration pipeline:

`Source/Connector → SyncEvent → SyncEngine → Processor/Importer → KnowledgePackage → Compiler/Analysis → Storage/Retrieval/Context`

This is an integration and persistence evolution, not a compiler rewrite. Existing cloud and Studio paths should remain stable until alternatives are implemented and verified.

## Explicit non-goals unless evidence changes

- No parallel canonical IR.
- No direct connector-to-KnowledgePackage writes.
- No new vector database, knowledge graph, microservices split or paid infrastructure merely for appearance.
- No broad connector marketplace before one real connector and one pilot are reliable.
- No wholesale Studio rewrite.
- No automatic promotion of agent memory into canonical knowledge.
- No claim of full authorization, SSO, exactly-once processing, automatic background reliability or production readiness without relevant end-to-end evidence.

## Engineering session rule

For every implementation session:

1. Inspect current main, recent commits, this roadmap, relevant stage/docs, tests and runtime state where available.
2. Choose the highest-value unfinished dependency in the priority order.
3. Verify the current implementation and branch/PR state before editing.
4. Make the smallest coherent change that improves the vertical slice.
5. Test the affected boundary and record exact commands/results.
6. Update stage notes and agent log only when evidence changes.
7. Report what changed, what was tested, what remains unverified and the next highest-leverage action.

Conversation history and earlier audit documents are context, not stronger evidence than current source, current tests and deployed runtime.

## Definition of success

OKP is ready for serious B2B/IP evaluation when an operator can set up a supported deployment, authorize a source, rely on recoverable background sync, retrieve grounded knowledge within verified access boundaries, inspect provenance and operational health, and demonstrate measurable value in a repeatable pilot.

**Useful + grounded + isolated + recoverable + observable + easy to operate + measurable.**

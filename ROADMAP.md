# OKP Roadmap — B2B Productization, OKP Connect, and IP Readiness

Status captured 2026-10-12 against repository files and recorded agent/test evidence. This roadmap separates implemented code, verified behavior, operator/runtime verification, and future work. Roadmap status is not a substitute for tests or production evidence.

## Mission

OKP's next milestone is a deployable B2B knowledge infrastructure product: a business installs or deploys it, signs in, connects approved knowledge sources, and then OKP maintains governed knowledge in the background without repeated manual import/export.

The user experience should feel like a local business system or intranet integration: configure access once, then background synchronization does the routine work while administrators can inspect sync health, permissions, failures, and provenance.

Commercial objective: demonstrate that OKP can be piloted, licensed, partnered, or evaluated for acquisition. Prioritize a narrow end-to-end business workflow and measurable value over feature accumulation.

**Closed Beta:** previously recorded as complete.  
**B2B / IP readiness:** previous estimate was approximately 60% engineering assessment; reassess only against explicit evidence. This is a planning estimate, not a measured KPI.

## Architectural invariants

- `KnowledgePackage` remains the sole canonical intermediate representation (IR).
- Connectors and the sync engine must not write KnowledgePackage directly; they feed the existing importer/compiler pipeline.
- Canonical knowledge stays distinct from agent feedback, audit events, and memory candidates.
- Memory candidates must never be promoted automatically at the feedback gateway.
- Tenant and silo isolation is enforced before ingestion and at every relevant read/write boundary.
- Source identity and provenance must survive normalization, compilation, storage, retrieval, and export.
- Permission changes and deletions must propagate; inaccessible source content must not remain retrievable.
- Sync delivery is durable, retryable, and idempotent. A retry must not create duplicate knowledge.
- PluginRegistry remains discovery/dispatch infrastructure, not a second IR.
- Deterministic processing is preferred where sufficient. AI enriches knowledge but does not replace source traceability.
- Model providers and agent frameworks remain replaceable, optional integrations.
- Do not rewrite the compiler/IR to solve persistence, connector, UX, or commercial concerns.
- Keep cloud/local storage and deployment adapters separable from Knowledge Core.
- Do not claim silent background operation, SSO, production security, or real-source integration until end-to-end behavior has been verified.

## Verified repository state — 2026-10-12

### Knowledge Core and existing pipeline

The repository records the following implementation state:

- PluginRegistry provides runtime dispatch; importers resolve by extension rather than silently falling back to JSON.
- `.json` uses `json_v2_importer`; `.txt` and `.md` use `plain_text_importer`.
- PackageCompiler is registered as the compile orchestrator and validates structure/provenance.
- KnowledgePackageRetriever is tenant/silo scoped.
- Feedback and memory candidates remain outside canonical knowledge.
- SQLite feedback persistence exists in the code history; do not treat an open PR's status as proof that its branch is merged.
- Attachment processing is registry-driven. PDF/image/audio package importers and richer source handling must be tracked against actual code/tests rather than assumed complete.
- The repository has both legacy `src/` and newer `okc/` paths. Migration/reconciliation is an explicit maintenance concern; avoid creating new duplicate implementations.

### OKP Connect — current maturity

Repository files and the 2026-10-12 agent log record:

1. **Connector contract landed:** authentication, initial/incremental sync, deletion handling, permissions, and health interfaces; a `SyncEvent` includes event ID, source, event kind, cursor/payload, tenant, and silo.
2. **Persistent SyncEngine landed:** SQLite-backed durable queue, cursor handling, retries/backoff, idempotency, and attempt tracking.
3. **Stub end-to-end path landed:** a test proves stub authentication → initial sync → SyncEngine → PlainTextImporter → KnowledgePackage with tenant/silo provenance.
4. **Tests recorded by the agent:** SyncEngine + Connect contract + OKC v2 + PluginRegistry, 31 passed; stub e2e + SyncEngine + contract, 4 passed. These are recorded test results, not a claim that the full suite or production deployment passes.
5. **Not yet proven:** a real business-system connector, unattended background service lifecycle, install/sign-in onboarding, SSO, permission/deletion propagation from a real source, admin health UX, and a production pilot.

Reference contract: `docs/OKP_Connect_Contract.md`. Stage summary: `docs/STAGE.md`. Agent evidence log: `docs/AGENT_COMMIT_LOG.md`.

## Product target: install once, sync continuously

Target journey:

`Install / deploy → sign in → create or select tenant and silo → authorize approved sources → initial sync → background incremental sync → governed search/context → inspect evidence and sync health`

The ordinary user should not have to export from a business application and manually import into OKP every time information changes. Manual import remains a supported fallback, not the primary enterprise integration story.

### Required behavior

- A repeatable install/deploy and upgrade path, with configuration separated from application code.
- Authentication and authorization suitable for the selected deployment; support enterprise SSO only after the identity model and threat boundaries are defined.
- A connector onboarding flow that makes source, account, scopes, tenant, and silo explicit.
- A background worker/service with durable queue and cursor state that survives restart.
- Initial sync followed by incremental sync or polling/webhook delivery, according to connector capabilities.
- Idempotent create/update/delete/permission-change handling.
- Fail-closed behavior when tenant/silo, credentials, or source permissions cannot be verified.
- Visible sync status: last successful sync, lag, queue depth, failures, retry state, and connector health.
- Audit trail for authorization, sync, permission, deletion, and administrative actions.
- A recovery/re-authentication path that does not silently discard queued events or cursor state.
- Clear source-to-KnowledgeObject provenance and evidence inspection after sync.
- A narrow, demonstrable pilot connector before building a broad connector marketplace.

## Priority roadmap

### P0 — Protect the core and reconcile repository state

1. Keep KnowledgePackage, provenance, tenant/silo isolation, and feedback boundaries stable.
2. Run targeted tests for Connect, compiler/importers, retrieval, feedback, and export after every relevant change; record full-suite status separately.
3. Reconcile open PRs #12 (SQLite feedback store) and #13 (PackageCompiler) against current `main`: compare diffs and tests, identify already-landed or superseded changes, then merge, close, or rebase deliberately. Do not blindly merge stale branches or duplicate changes.
4. Audit the remaining `src/` versus `okc/` split and document which path is canonical for each runtime entry point. Remove legacy paths only after references, deployment paths, and tests prove they are safe to retire.
5. Recheck the Firestore tenant/silo operator gate wherever that deployment path remains active.
6. Keep `docs/AGENT_COMMIT_LOG.md` and `docs/STAGE.md` aligned with verified repository changes; do not inflate maturity estimates.

**Exit evidence:** clean, explainable mainline; relevant tests recorded; no unresolved duplicate implementation or merge ambiguity hidden by roadmap wording.

### P1 — Finish the Connect execution loop

1. Preserve the existing connector contract and SyncEngine; do not introduce a parallel IR or direct connector-to-KnowledgePackage writes.
2. Add a first real connector or local-folder connector using the same SyncEvent → durable SyncEngine → existing importer/compiler path.
3. Prove restart recovery, cursor continuity, duplicate-event idempotency, retry/backoff, and dead-letter/manual-recovery behavior.
4. Add explicit tests for delete events, permission changes, revoked credentials, partial failures, and tenant/silo isolation.
5. Add a managed background worker lifecycle: start/stop, restart, configuration, health reporting, and graceful shutdown.
6. Ensure sync events cannot be acknowledged as processed until the configured processor has completed successfully and durable state is consistent.

**Exit evidence:** a real source can be connected and synchronized repeatedly without manual export/import; restart and failure tests pass; provenance and isolation survive the full path.

### P2 — Deliver the business onboarding experience

1. Define the first deployment target and supported operating environment before choosing installer/runtime details.
2. Implement a minimal install/deploy → sign-in → tenant/silo setup → connector authorization journey.
3. Store secrets through an appropriate credential mechanism; never commit credentials or customer data.
4. Keep onboarding configuration separate from Knowledge Core and connector implementations.
5. Make first sync progress, errors, re-authentication, and last-sync status visible.
6. Establish least-privilege scopes and explain exactly which source data OKP can read, update, or delete.
7. Add SSO only after the deployment and identity requirements are explicit; do not confuse application sign-in with source-connector authorization.

**Exit evidence:** a new pilot customer can set up OKP from documented instructions without founder-only intervention, and can tell whether sources are connected and current.

### P3 — Trustworthy background operations and governance

1. Propagate source permission changes and deletions end-to-end; retrieval must re-check the applicable access policy.
2. Establish audit events for connection changes, sync actions, permission changes, deletions, and administrative access.
3. Define retention, deletion, backup/restore, migration, and tenant offboarding behavior.
4. Separate development, test, and production configuration; define upgrade/rollback behavior.
5. Test credential expiry, network loss, rate limits, malformed source data, queue growth, and source outages.
6. Add operational alerts and safe recovery procedures based on measured needs.
7. Threat-model connector credentials, local service boundaries, tenant isolation, data exfiltration, and logs.

**Exit evidence:** a documented threat model, tested access boundaries, recoverable sync state, and operator-visible failures. Do not claim enterprise-grade security solely because controls are documented.

### P4 — Evidence quality and grounded intelligence

1. Make provenance navigable from a retrieved answer/object to the exact source and source version where available.
2. Separate direct evidence, derived/enriched fields, and model-generated synthesis in the user experience.
3. Build repeatable fixtures for source conflicts, stale content, duplicate content, missing citations, and permission-filtered retrieval.
4. Measure retrieval precision, citation correctness, sync/compile reliability, and stale-data behavior.
5. Improve PDF, image/OCR, audio, and office-document handling only against concrete fixtures and verified provenance requirements.
6. Preserve a clear user journey: connect/import → compile → search/ask → inspect evidence → export.

**Exit evidence:** regression data and acceptance criteria demonstrate that source grounding and access controls have not weakened.

### P5 — One measurable B2B pilot

Choose one customer workflow and one source integration. Do not build a broad connector catalogue before validating value.

Measure a baseline and post-OKP result for:
- time to find supporting evidence;
- time to reconstruct project/business knowledge;
- duplicate research avoided;
- retrieval and citation correctness;
- sync and compilation reliability;
- onboarding time and ongoing operator effort;
- useful knowledge reuse across approved AI systems.

Define pilot success thresholds with the customer before the pilot. Capture limitations and failures, not just successful demonstrations.

**Exit evidence:** a repeatable demonstration, customer-confirmed baseline/results, documented operating cost, and a clear decision on what to productize next.

### P6 — Commercial packaging and IP diligence

Prepare a buyer/customer-readable package containing:
- architecture and data-flow diagrams;
- KnowledgePackage, compiler, provenance, and Connect contracts;
- supported deployment and connector matrix;
- security/threat model and tenant isolation evidence;
- install, upgrade, backup, recovery, and operations guides;
- dependency and third-party/open-source inventory;
- test reports, known limitations, and reproducible pilot results;
- ownership, contribution, and licensing documentation.

Keep implemented behavior, test-verified behavior, operator-verified runtime behavior, planned work, and experimental concepts explicitly distinct. Decide licensing deliberately before distributing commercial artifacts.

### P7 — Scale only after the pilot proves the need

Consider hosted multi-tenant SaaS, customer-controlled private deployment, hybrid mode, broader connector coverage, advanced identity/policy controls, metering, and larger-scale operations only when pilot evidence justifies them. Keep the same KnowledgePackage and connector contracts across deployment shapes.

## Local-first and cloud direction

The long-term product should support installable/customer-controlled deployments and should not make the knowledge core dependent on Firebase/Firestore. Cloud sync may remain an optional adapter where useful. Existing cloud/Studio paths must remain stable until the local-first migration is implemented and verified incrementally.

Preserve the existing pipeline:

`Source / Connector → SyncEvent → SyncEngine → Importer / Processor → KnowledgePackage → Compiler / Analysis → Storage / Retrieval / Context`

This is an integration and persistence evolution, not a compiler rewrite.

## Explicit non-goals unless evidence changes

- No parallel canonical IR.
- No knowledge graph, vector database, Cloud Run migration, microservices split, or analytics cockpit merely for appearance.
- No premature full enterprise control plane.
- No agent SDK or model-provider lock-in.
- No autonomous promotion of agent memory into canonical knowledge.
- No wholesale Studio rewrite.
- No broad connector marketplace before one connector and one pilot work reliably.
- No claims of automatic background sync, SSO, or production readiness without end-to-end evidence.

## Daily agent operating rule

Every implementation session must inspect current `main`, recent commits, this roadmap, relevant docs, tests, and runtime state where available.

Then:
1. Select the highest-value unfinished dependency in the priority order.
2. Verify current code and branch/PR state before editing.
3. Make the smallest coherent change.
4. Test the affected boundary and report exact commands/results.
5. Update roadmap/stage/log only when the evidence changes.
6. Report what changed, what was tested, what remains unverified, and the next highest-leverage action.

Conversation history and AI-generated plans are context, not stronger evidence than current repository/runtime evidence.

## Definition of success

OKP is ready for serious B2B/IP evaluation when a customer can install or deploy it, authorize a source, and rely on background sync to keep governed knowledge current; source permissions and provenance remain intact; failures are visible and recoverable; the core workflow is reproducible; and a pilot demonstrates measurable value.

**Useful + grounded + isolated + recoverable + easy to onboard + measurable + commercially legible.**

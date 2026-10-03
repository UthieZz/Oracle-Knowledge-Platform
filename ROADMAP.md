# OKP Roadmap — Post-Beta B2B / IP Readiness

Status captured 2026-10-03 against current `main` runtime evidence.

## Mission

OKP Closed Beta is complete. The next objective is not another architecture rewrite or feature accumulation.

The target is to make OKP a technically credible, commercially packaged, diligence-ready B2B knowledge infrastructure asset that can be piloted, licensed, partnered, or evaluated for acquisition.

**Closed Beta:** 100% complete  
**B2B / IP sale-readiness:** approximately 60% engineering assessment

The B2B percentage is a planning assessment, not a measured KPI.

## Architectural invariants

- KnowledgePackage remains the sole canonical intermediate representation.
- Canonical knowledge is distinct from agent feedback and memory candidates.
- Memory candidates are never promoted at the feedback gateway.
- Tenant / silo isolation is enforced at every relevant boundary.
- Provenance must survive every transformation and export boundary.
- PluginRegistry is discovery / dispatch infrastructure, not a second IR.
- Deterministic processing is preferred whenever sufficient.
- AI enriches knowledge but does not replace source traceability.
- Do not rewrite the compiler or IR to solve persistence, UX, or commercial concerns.
- External AI providers remain optional integrations, not the knowledge store.

## Current runtime state — 2026-10-03

Recent verified implementation work on `main`:

- PluginRegistry is the runtime dispatch layer.
- Importers resolve by extension; no silent JSON fallback.
- `.json` uses `json_v2_importer`.
- `.txt` / `.md` use `plain_text_importer`.
- PackageCompiler is registered and performs structural identity/provenance validation.
- SQLiteFeedbackLedger persists AgentFeedbackPackage outside canonical knowledge.
- KnowledgePackageRetriever provides tenant/silo-scoped retrieval.
- AgentFeedbackPackage explicitly separates citations, tool events, memory candidates, and audit records.
- Memory candidates cannot be accepted directly at the gateway.
- Attachment processors remain registry-driven.
- PDF/image/audio do not yet have package importers.
- Firestore export still has an operator tenant/silo setup gate.
- Existing Studio / cloud runtime remains part of the current product surface while the local-first direction is evaluated and implemented incrementally.

Recent commits include:

- `41f6c864` — extension-resolved plain-text importer.
- `00fb3e96` — registered structural PackageCompiler.
- `6e07c191` / `37d08582` — SQLite feedback ledger and isolation tests.
- `8cd5f1b6` — feedback ledger / compiler-contract documentation.

## Current maturity bar

| Area | Current assessment | Target |
|---|---:|---:|
| Core IP / architecture | 95% | 100% |
| Working product / Studio | 90% | 100% |
| Compiler / ingestion | 92% | 100% |
| Knowledge quality / evidence | 72% | 100% |
| Retrieval / grounded intelligence | 78% | 100% |
| Production hardening | 65% | 100% |
| Security / governance | 40% | 100% |
| Scale / deployment | 50% | 100% |
| Commercial packaging | 35% | 100% |
| IP / technical diligence | 35% | 100% |
| Customer pilot / ROI proof | 15% | 100% |

## Priority order — post-beta

### P0 — Protect the core

1. Keep KnowledgePackage, provenance, tenant/silo isolation, and canonical-knowledge boundaries stable.
2. Continue deterministic tests around PluginRegistry, importers, compiler, retrieval, feedback, and exports.
3. Close the Firestore tenant/silo operator gate where that path remains active.
4. Do not introduce architectural abstractions without measurable value.

### P1 — Make the knowledge product trustworthy

1. Improve provenance visibility from knowledge object to exact source.
2. Improve evidence and citation quality.
3. Test conflict handling and source attribution.
4. Improve retrieval relevance without weakening tenant/silo isolation.
5. Establish repeatable quality fixtures and regression datasets.
6. Preserve source integrity through every compiler/export path.

### P2 — Productize the intelligence surface

1. Make the core user journey obvious: import → compile → search / ask → inspect evidence → export.
2. Make evidence inspection a first-class UX capability.
3. Make grounded Ask visibly distinguish evidence from synthesis.
4. Reduce friction in import and compilation.
5. Keep Studio focused on demonstrating the knowledge system rather than becoming a second knowledge engine.

### P3 — Enterprise trust layer

Add only controls justified by real B2B use:

1. Identity and access model.
2. Tenant / silo authorization.
3. Auditability.
4. Data retention and deletion controls.
5. Secret and credential handling.
6. Backup / recovery.
7. Deployment and environment separation.
8. Security review and threat-model evidence.

Do not build a full enterprise control plane prematurely.

### P4 — Commercial proof

Create a controlled pilot path that can demonstrate measurable value.

Candidate metrics:

- time to locate supporting evidence;
- time to reconstruct project knowledge;
- duplicate research avoided;
- retrieval precision / citation correctness;
- compilation reliability;
- onboarding time;
- knowledge reuse across AI systems.

The goal is evidence of customer value, not vanity usage metrics.

### P5 — IP / diligence package

Prepare a buyer-readable technical package containing:

- system architecture;
- compiler / KnowledgePackage explanation;
- provenance model;
- plugin model;
- retrieval and feedback boundaries;
- dependency inventory;
- third-party / open-source inventory;
- deployment model;
- security model;
- test and verification evidence;
- known limitations;
- roadmap;
- ownership / licensing documentation.

Clearly separate implemented functionality, verified behavior, planned work, and experimental concepts.

### P6 — Sale / licensing readiness

The system is ready for serious B2B evaluation when:

- the core workflow is repeatable;
- evidence and provenance are demonstrable;
- security boundaries are documented;
- deployment is reproducible;
- a pilot can measure ROI;
- IP ownership and dependencies are clear;
- the architecture can be explained without founder-only knowledge;
- the buyer can understand what they are acquiring and how it integrates.

Possible commercial forms remain open: license, strategic partnership, acquisition, or managed B2B deployment.

## Local-first direction

The previous roadmap decision remains valid as a migration target:

OKP should evolve toward an installable, local-first application where the core knowledge system does not require Firebase / Firestore.

However:

- this is a migration boundary, not a compiler rewrite;
- preserve Importers → KnowledgePackage → Analyzers → Compiler → Exporters;
- local persistence should be introduced incrementally;
- cloud sync may remain optional;
- do not destabilize the currently working product merely to accelerate the migration.

The local-first target remains:

`Download → Install → Import → Compile → Search / Ask → Export`

## Explicit non-goals until justified

Do not add merely because they sound enterprise-grade:

- knowledge graphs;
- vector databases;
- premature enterprise RBAC;
- Cloud Run;
- analytics cockpits;
- wholesale Studio rewrites;
- agent SDK lock-in;
- autonomous memory promotion;
- unnecessary microservices;
- duplicate knowledge representations.

## Daily agent operating rule

Every daily agent session must begin by inspecting:

1. current `main` state;
2. recent commits;
3. this roadmap;
4. relevant tests;
5. the actual runtime state when available.

Then:

- identify the highest-value unfinished item;
- verify before editing;
- make the smallest coherent change;
- test the affected boundary;
- update documentation only when implementation evidence warrants it;
- report what changed, what was verified, what remains uncertain, and the recommended next action.

Never treat an old conversation, generated plan, or AI suggestion as stronger evidence than current repository/runtime evidence.

## Definition of success

OKP is not finished when every conceivable feature exists.

OKP is ready for B2B/IP commercialization when the existing core is:

**Useful + trustworthy + reproducible + secure enough for the target buyer + commercially legible + technically defensible.**

The compiler and knowledge architecture should become increasingly stable while the remaining effort moves toward evidence quality, product experience, operational trust, customer proof, and diligence readiness.

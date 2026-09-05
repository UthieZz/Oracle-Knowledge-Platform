# OKP Roadmap — next stage

Status captured 2026-09-05 after Stage 3.5 infusion contract.

## Architectural direction — Local-First Desktop OKP

**Decision: OKP will transition toward a fully self-contained, installable desktop application with no Firebase or Firestore dependency in the final architecture.**

The knowledge system should operate from the user's local machine: importing, parsing, analyzing, compiling, searching, browsing, storing, and exporting knowledge locally. Local persistence should use an embedded database such as SQLite plus the local filesystem for source and compiled artifacts.

External AI providers remain optional services for reasoning/enrichment. They are not the knowledge store and are not required for the core knowledge pipeline.

This is a migration target, not a rewrite of the compiler/IR. Preserve the existing Importers → KnowledgePackage → Analyzers → Compiler → Exporters architecture and replace the cloud persistence/application shell incrementally.

The final product should follow:

`Download → Install → Import → Compile → Search / Ask → Export`

with the core application usable without Firebase, Firestore, or a hosted backend.

Cloud synchronization, collaboration, or backup may be considered later as optional capabilities, but cloud infrastructure must not be foundational to the knowledge system.

## Immediate product improvements

- Work on exporter as well.
- Import should work directly through the browser/UI rather than requiring users to manually place uploads into an `uploads` folder.

## What already exists

| Surface | Repo | State |
|---|---|---|
| Compiler / IR / exporters | `UthieZz/Oracle-Knowledge-Platform` | Live. Stage 2 verified by operator. |
| Studio workspace | same repo `studio/` | Live React/PWA (Firebase). Current canonical UI during migration. |
| Satellite Studio | `UthieZz/OKP-Studio` | Separate stack (TanStack/PGlite). Reference only. |
| Grounded Ask | Studio TS + Python chat path | Stage 3 code complete; runtime check pending |

Do **not** add before freeze: knowledge graphs, enterprise RBAC, Cloud Run, vector DBs, analytics cockpits, wholesale `OKP-Studio` copy into `studio/`.

## Priority order (frozen)

1. Knowledge objects mapping — generation → stable IDs → Firestore `knowledgeObjects` → Studio count. (Stage 2)
2. Provenance survival — ChatGPT / Gemini / Grok keep `source_platform`. (Stage 2)
3. Dispatcher enforcement — Grok files never compile via GeminiImporter. (Stage 2)
4. Grounded Ask — retrieve compiled objects → cite or decline. (Stage 3 code)
5. Studio infusion contract — document how satellite Studio may donate modules without replacing `studio/`. (Stage 3.5 docs)
6. Attachments understanding — detection exists; processing still immature.
7. Markdown packer — verified at 4 MB. Leave it.
8. Local-first migration — replace Firebase/Firestore persistence with local embedded storage and evolve Studio into the installable desktop application without destabilizing the compiler/IR.

## Stage status

- Stage 1 COMPLETE.
- Stage 2 COMPLETE (operator-confirmed Firestore counts).
- Stage 3 CODE COMPLETE. RUNTIME UNVERIFIED (`tests/test_grounded_ask.py` + live Studio Ask).
- Stage 3.5 DOCS COMPLETE (`docs/studio-infusion.md`). NO subtree / no `studio/` overwrite.
- Stage 4 LOCAL-FIRST DESKTOP TRANSITION — **DECIDED / NOT YET IMPLEMENTED**.

## Stage 4 — Local-first desktop transition

1. Define the local persistence contract and data model.
2. Introduce local embedded storage without changing the KnowledgePackage/IR or compiler contracts.
3. Migrate knowledge objects, provenance, sources, and compiled artifacts from Firestore/local hybrid operation to local storage.
4. Replace Firebase-dependent Studio data access incrementally.
5. Implement direct browser/UI import so manual `uploads` folder placement is unnecessary.
6. Package the application as a downloadable/installable desktop product.
7. Preserve external AI providers as optional integrations for Ask/enrichment.
8. Verify backup, export, migration, provenance, and recovery behavior.
9. Remove Firebase/Firestore from the production architecture only after the local path is fully verified.

**Important:** Do not begin by rewriting the compiler or KnowledgePackage. The migration boundary is persistence and application shell, not the knowledge compilation architecture.

## Freeze criteria for Stage 3

- pytest `tests/test_grounded_ask.py` green.
- Ask with evidence → citations present.
- Ask without evidence → explicit refusal, no invention.

## Freeze criteria for Stage 3.5

- Infusion contract exists on `main`.
- Operator has pulled `main` and confirmed `studio/` still builds.
- No PGlite / TanStack Start / better-auth runtime landed in `studio/`.

## Stage 4 architectural success criteria

- OKP core runs without Firebase or Firestore.
- Knowledge persists locally across application restarts.
- Original sources and provenance remain traceable.
- Existing compiler/IR behavior remains intact.
- Import → compile → browse/search → Ask → export works locally.
- Application can be installed and used as normal desktop software.
- External AI usage is optional, not a storage dependency.
- No unnecessary cloud infrastructure is required for the core product.

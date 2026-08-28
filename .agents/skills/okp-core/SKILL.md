# OKP Core Skill

This skill provides architectural guidance and procedural rules for the Oracle Knowledge Platform (OKP).

## Core Principles

- **Firebase Spark/No-Cost Plan is a HARD constraint.** No paid infrastructure.
- **Compiler is canonical.** The Python compiler is the truth-processing engine. Do not duplicate in frontend.
- **Firestore is operational.** Firestore is the published knowledge store.
- **Studio is interface.** Oracle Studio is the user interface.

## Quota-Efficient Agent Workflow

1.  **Context First:** Read `GEMINI.md` and this `SKILL.md` at session start.
2.  **Verify:** Check `git status`. Only inspect files needed for the current task.
3.  **Target:** Use targeted searches (`grep`, `glob`), not broad scans.
4.  **Deterministic:** Prefer deterministic local inspection over AI reasoning.
5.  **Smallest Change:** Implement the smallest viable slice.
6.  **Verify:** Always verify with test data before claiming completion.

## Architectural Truths

- KnowledgePackage is the canonical intermediate representation.
- Firestore publishing path is the established proven flow.
- Real production AI archives have NOT been ingested. Use sample/test data only.
- Current Firestore reads in Studio are functional.

## Development Priorities

- Fix/Verify Import/Upload workflow (Browser → Import → Importer → KnowledgePackage → Compiler → Firestore → Studio).
- Maintain Firebase Spark compatibility.
- Ensure provenance and traceability are preserved in all data processing.

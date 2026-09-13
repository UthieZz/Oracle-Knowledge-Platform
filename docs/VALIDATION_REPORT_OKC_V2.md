# OKC v2 Additive Path — Validation Report

Date: 2026-09-13
Repo: UthieZz/Oracle-Knowledge-Platform (main)
Scope: additive `okc/` package only (does not replace `src/`)

## 1. End-to-End Pipeline

Command:
```bash
PYTHONPATH=. python3 scripts/run_compiler.py
```

Result: **PASS**

```
Initializing Oracle Knowledge Compiler Pipeline...
Loading input file: uploads/sample_export.json
Executing AttachmentProcessingPass across KnowledgeObjects...
WARNING Image file not found: diagram.png   # expected (placeholder path)
Hybrid Search Validation Hits: 1
Exported 1 objects to local SQLite DB: okp_local.db
Pipeline run completed successfully.
```

## 2. Local SQLite Persistence

Tables created: `knowledge_objects`, `evidence_spans`

Sample row:
```
object_id=obj_001
tenant_id=tenant_default
silo_id=silo_default
source_platform=chatgpt
title=System Architecture Notes
content=Discussed Python and SQLite integration for OKP using React frontend.
```

evidence_spans count = 0 for the synthetic sample (no EvidenceSpan attached in driver). Export path itself works.

## 3. Component Unit Checks (additive okc/)

Custom validation script covering:

| Check | Result |
|-------|--------|
| schema_version frozen at 2.0.0 | PASS |
| Evidence + provenance round-trip via model_dump | PASS |
| EntityExtractor gazetteer (python, sqlite, react, openai) | PASS |
| HybridRAG tenant/silo isolation (correct tenant hits, wrong tenant blocked) | PASS |
| SQLiteExporter write + read of knowledge_objects + evidence_spans | PASS |

All assertions passed: `ALL_OKC_V2_TESTS_PASSED`

## 4. Studio UI Component

Path corrected on push: `studio/src/components/IngestionModal.tsx` (not top-level `src/`)

Structural checks:
- exports `IngestionModal`
- accepts `isOpen` / `onClose` / `onUploadSuccess`
- uses `FormData` + `POST /api/ingest`
- accept list includes json/pdf/media types

Full `npm run build` not executed in this environment (network/time limits on `npm install`). Component is syntactically consistent with the Studio React/TS stack.

## 5. Existing pytest suite

Not re-run against full `src/` tree in this session (clone/sparse checkout bandwidth constraints). Additive `okc/` does not modify `src/` modules, so no expected regressions in the existing suite from these commits.

## Gaps / notes

- Attachment processors are still placeholder extractors (OCR/transcript/PDF text are stubs).
- HybridRAG uses deterministic dummy embeddings, not a real embedding model.
- `scripts/run_compiler.py` builds a synthetic KnowledgePackage; it does not yet call real importers.
- `/api/ingest` endpoint for the modal is not implemented in this set of commits.
- No formal pytest files yet under `tests/` for the `okc/` package; validation was script-based.

## Verdict

Additive v2 path is executable end-to-end for: IR construction → attachment pass → entity extraction → hybrid index/search with tenant isolation → local SQLite export.

Ready for next wiring step (real importers into v2 IR, or real embedding backend) when you choose it.

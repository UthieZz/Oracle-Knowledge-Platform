# Implementation Ownership — Current Evidence (2026-11-08)

**Status:** Recorded from current main. Not a migration plan.

## Active paths

| Runtime entry | Authoritative surface | Notes |
|---------------|-----------------------|-------|
| `scripts/run_connect_worker.py`, `scripts/connect_health.py`, `scripts/connect_recover.py` | `okc/` | Connect local-folder pilot. Uses `okc.connect.*`, `okc.models.knowledge_package.KnowledgePackage` (Pydantic). |
| `okc/connect/knowledge_accumulator.py` | `okc/` | Processor that applies SyncEvents to living KnowledgePackage. |
| `main.py` (Qt UI) | `src/` | Legacy desktop entry. Uses `src.controllers`, `src.ui`. |
| `run.py compiler` → `scripts/compile_data.py` | `src/` | Legacy compilation path. |
| Gemini importer | `src/importers/gemini_importer.py` | Functional (31 unit tests pass). Maps to `src.models`. |
| Studio (Vite) | `studio/` | React/PWA. Consumes published knowledge. |

## KnowledgePackage

- Connect path: `okc.models.knowledge_package.KnowledgePackage` (Pydantic BaseModel). Sole canonical IR for the Connect vertical slice.
- Legacy path: `src.models.knowledge_package.KnowledgePackage` (distinct class). Not used by Connect.

No automatic promotion or dual-write exists. Connectors never mutate KnowledgePackage directly; the accumulator is the processor.

## Decision

Do not merge `src/` and `okc/` without evidence of overlapping active use, a migration plan, and verification that both the Connect pilot and any remaining legacy compiler consumers continue to function. Prefer explicit ownership over speculative consolidation.

This document records the current state so future sessions do not rediscover the dual surfaces.

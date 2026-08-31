# OKP Roadmap — next stage

Status captured 2026-08-31 after Stage 3 code push.

## What already exists

| Surface | Repo | State |
|---|---|---|
| Compiler / IR / exporters | `UthieZz/Oracle-Knowledge-Platform` | Live. Stage 2 verified by operator. |
| Studio workspace | same repo `studio/` + `UthieZz/OKP-Studio` | Live React/PWA |
| Grounded Ask | Studio TS + Python chat path | Stage 3 code complete; runtime check pending |

Do **not** add before freeze: knowledge graphs, enterprise RBAC, Cloud Run, vector DBs, analytics cockpits.

## Priority order (frozen)

1. Knowledge objects mapping — generation → stable IDs → Firestore `knowledgeObjects` → Studio count. (Stage 2)
2. Provenance survival — ChatGPT / Gemini / Grok keep `source_platform`. (Stage 2)
3. Dispatcher enforcement — Grok files never compile via GeminiImporter. (Stage 2)
4. Grounded Ask — retrieve compiled objects → cite or decline. (Stage 3 code)
5. Attachments understanding — detection exists; processing still immature.
6. Markdown packer — verified at 4 MB. Leave it.

## Stage status

- Stage 1 COMPLETE.
- Stage 2 COMPLETE (operator-confirmed Firestore counts).
- Stage 3 CODE COMPLETE. RUNTIME UNVERIFIED (`tests/test_grounded_ask.py` + live Studio Ask).

## Freeze criteria for Stage 3

- pytest `tests/test_grounded_ask.py` green.
- Ask with evidence → citations present.
- Ask without evidence → explicit refusal, no invention.

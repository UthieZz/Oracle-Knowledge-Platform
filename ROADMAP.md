# OKP Roadmap — next stage

Status captured 2026-08-29 after Stage 2 push + Stage 3 plan lock.
HEAD: `d1de21d3` then this docs commit.

## What already exists

| Surface | Repo | State |
|---|---|---|
| Compiler / IR / exporters | `UthieZz/Oracle-Knowledge-Platform` | Live. Stage 2 code on `main`. |
| Studio workspace | same repo `studio/` + `UthieZz/OKP-Studio` | Live React/PWA |
| Grounded Ask | `studio/src/services/ChatService.ts` | Implemented in Studio; Python path still conversation-first |

Do **not** add before freeze: knowledge graphs, enterprise RBAC, Cloud Run, vector DBs, analytics cockpits.

## Priority order (frozen)

1. Knowledge objects mapping — generation → stable IDs → Firestore `knowledgeObjects` → Studio count.
2. Provenance survival — ChatGPT / Gemini / Grok must keep `source_platform`.
3. Dispatcher enforcement — Grok files never compile via GeminiImporter.
4. Grounded Ask — retrieve compiled objects → cite or decline.
5. Attachments understanding — detection exists; processing still immature.
6. Markdown packer — verified at 4 MB. Leave it.

## Stage status

- Stage 1 COMPLETE (compiler on GitHub).
- Stage 2 CODE COMPLETE. RUNTIME UNVERIFIED.
- Stage 3 QUEUED (see `docs/STAGE3_GROUNDED_ASK.md`).

## Freeze criteria

- Studio Knowledge Objects count equals Firestore collection size.
- Sample conversations from ChatGPT, Gemini, Grok all retain correct `source_platform`.
- Dispatcher regression: Grok files never compile via GeminiImporter.
- Ask Oracle cites objects or explicitly declines.

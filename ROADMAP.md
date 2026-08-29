# OKP Roadmap — next stage

Status captured 2026-08-29 after compiler push.

## What already exists

| Surface | Repo | State |
|---|---|---|
| Compiler / IR / exporters | `UthieZz/Oracle-Knowledge-Platform` | **Live.** `run.py`, importers, exporters, models, tests present. |
| Studio workspace | `UthieZz/OKP-Studio` (private) | Live TanStack/React app |
| Drive | connected | No separate OKP roadmap doc required |

Studio corpus previously locked Beta at ~94% engineering. Remaining work is verification and mapping fixes, not new architecture.

Do **not** add before freeze: knowledge graphs, enterprise RBAC, Cloud Run, vector DBs, analytics cockpits.

## Priority order (frozen)

1. **Knowledge objects mapping** — generation → stable IDs → Firestore `knowledgeObjects` → Studio count. Dashboard `0` while collection exists is a mapping defect.
2. **Provenance survival** — `source_platform` must not be `Unknown` or fake `Other`. Map ChatGPT, Gemini, Grok from importer → package → exporter.
3. **Dispatcher enforcement** — stop GeminiImporter eating Grok JSON (`prod-grok-backend.json`, `grok-test.json`). Mixed-source regression test required.
4. **Grounded Ask** — retrieval → rank → context → model → citation check. Decline when evidence is thin.
5. **Attachments understanding** — detection exists; processing pass still immature.
6. **Markdown packer** — already verified at 4 MB. Leave it.

## Stage status

- Stage 1 COMPLETE (compiler on GitHub).
- Stage 2 IN PROGRESS (mapping + provenance + dispatcher).
- Stage 3 QUEUED (grounded Ask).

## Freeze criteria

- Studio Knowledge Objects count equals Firestore collection size.
- Sample conversations from ChatGPT, Gemini, Grok all retain correct `source_platform`.
- Dispatcher regression: Grok files never compile via GeminiImporter.
- Ask Oracle cites objects or explicitly declines.

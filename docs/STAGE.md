# Current stage

Verified 2026-08-29 ~04:30 SAST via GitHub connector as `UthieZz`.

- Stage 0 COMPLETE: GitHub awareness, Studio located, compiler repo seeded.
- Stage 1 COMPLETE: Real compiler tree is on `UthieZz/Oracle-Knowledge-Platform`.
  Confirmed present: `run.py`, `src/importers/` (gemini, grok, chatgpt),
  `src/exporters/firestore_exporter.py`, `src/services/import_dispatcher.py`,
  `src/models/`, `tests/`, `scripts/`.
- Stage 2 IN PROGRESS: Knowledge Objects mapping + provenance survival +
  dispatcher enforcement.
- Stage 3 QUEUED: grounded Ask verification against published Firestore.

Repos:
- Compiler (canonical): `UthieZz/Oracle-Knowledge-Platform` @ `cb2a94f` (post-push tree).
- Studio workspace (separate): `UthieZz/OKP-Studio` last known push 2026-08-27.

## Stage 2 evidence snapshot

| Concern | Current state |
|---|---|
| Dispatcher | `detect_source_type` exists; Gemini checked first (MyActivity / header), then Grok (`conversations` or `grok` in name), then ChatGPT. Tests are minimal dummy-file only. |
| Grok provenance | `GrokImporter` hardcodes `source_platform: "Grok"` on Conversation + KnowledgeObject. |
| Firestore KO write | `_write_knowledge_objects` writes to `knowledgeObjects`, falls back from `Other`/empty via `_derive_platform`. Dashboard meta counts `len(package.knowledge_objects)`. |
| Known risk | Calling `run_gemini_import` directly on a Grok file bypasses dispatcher. Filename-based detection is the main guard for `prod-grok-backend.json`. |

Do not add graphs, Cloud Run, or vector DBs.

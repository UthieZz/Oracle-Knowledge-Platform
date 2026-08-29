# Current stage

Verified 2026-08-29 ~04:30 SAST; Stage 2 fixes pushed same session.

- Stage 0 COMPLETE
- Stage 1 COMPLETE: compiler source on GitHub
- Stage 2 COMPLETE (code): dispatcher hardened, Grok single-file import fixed,
  cross-importer refusal guards, expanded regression tests, provenance locked on Grok path
- Stage 2 remaining (runtime verification): run pytest + one real export against Firestore
  and confirm Studio dashboard KO count matches `knowledgeObjects` collection size
- Stage 3 QUEUED: grounded Ask verification

## Stage 2 changes

1. `import_dispatcher.py` — filename-first rules; `grok` in name always → GROK;
   `myactivity` → GEMINI; stronger content markers.
2. `grok_importer.py` — single-file `file_path` mode (fixes `prod-grok-backend.json`
   being missed by `grok-*.json` glob only); always sets `source_platform=Grok` on
   Conversation + KnowledgeObject.
3. `import_service.py` — `run_grok_import` passes explicit file path; GeminiImporter
   refuses Grok/ChatGPT-classified files; GrokImporter refuses Gemini-classified files;
   post-import provenance assert on Grok path.
4. Tests — real filename patterns + single-file + cross-importer refusal.

Repos: `UthieZz/Oracle-Knowledge-Platform` main after Stage 2 commit.

No graphs. No Cloud Run. No vector DB.

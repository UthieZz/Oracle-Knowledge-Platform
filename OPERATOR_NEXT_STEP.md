# Exact next step for the operator

Stage 1 is complete. Compiler source is on GitHub.

## Stage 2 — what Grok will do next (or what you can verify)

1. **Dispatcher regression**
   - Confirm `prod-grok-backend.json` and `grok-test.json` detect as `SourceType.GROK`.
   - Confirm a real MyActivity file detects as `GEMINI`.
   - Strengthen tests if any real file mis-routes.

2. **Provenance end-to-end**
   - Import one Grok + one Gemini sample.
   - Inspect `KnowledgeObject.source_platform` and Firestore `knowledgeObjects.*.source_platform`.
   - No `Unknown` / bare `Other` allowed for known platforms.

3. **Knowledge Objects count**
   - After export, `meta/dashboard.knowledge_objects` must equal number of docs in `knowledgeObjects`.
   - Studio dashboard must show the same number (if it still shows 0, the defect is in Studio read path or export never ran against that project).

## You can help by running locally

```bash
cd /path/to/Oracle-Knowledge-Platform
python3 -m pytest tests/test_import_dispatcher.py -q
python3 verify_grok_import.py   # if still valid
```

Then reply with results, or say:

`run Stage 2 fixes`

and I will implement the smallest safe code changes (dispatcher hardening + provenance asserts + KO id/mapping checks) and push them.

No graphs. No Cloud Run. No vector DB.

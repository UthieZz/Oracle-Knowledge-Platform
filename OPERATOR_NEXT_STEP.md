# Exact next step for the operator

Stage 2 code is on GitHub. Verify locally, then we close Stage 2 fully.

```bash
cd /path/to/Oracle-Knowledge-Platform
python3 -m pytest tests/test_import_dispatcher.py tests/test_grok_single_file_and_provenance.py -q
```

Optional smoke on sample:

```bash
python3 verify_grok_import.py
```

Then, if you have credentials configured for Firestore:

1. Import one Grok sample + one Gemini sample via dispatcher.
2. Export with FirestoreExporter.
3. Confirm `meta/dashboard.knowledge_objects` equals number of docs in `knowledgeObjects`.
4. Confirm Studio dashboard shows the same count (if still 0 while collection has docs, the defect is Studio read path — Stage 2b).

Reply with pytest output, or:

`Stage 2 verified`

to move to Stage 3 (grounded Ask), or paste any failures.

No graphs. No Cloud Run. No vector DB.

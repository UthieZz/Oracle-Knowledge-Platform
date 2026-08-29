# Exact next step for the operator

Git is not empty. Compiler repo is live at `UthieZz/Oracle-Knowledge-Platform` on `main` (`d1de21d3`).
Stage 2 code is pushed. Stage 3 plan is written. Runtime evidence is still missing.

Do this on your machine and paste the output back. I cannot run pytest against your Firestore from here.

```bash
cd /path/to/Oracle-Knowledge-Platform
git pull origin main
python3 -m pytest tests/test_import_dispatcher.py tests/test_grok_single_file_and_provenance.py -q
python3 verify_grok_import.py
```

If Firestore credentials are configured:

```bash
python3 verify_publishing.py
```

Then report three numbers:

1. pytest result (pass/fail + any traceback)
2. `knowledgeObjects` document count in Firestore
3. Studio dashboard Knowledge Objects count

Reply with one of:

- `Stage 2 verified` plus the three numbers → I start Stage 3 code (grounded Ask alignment + tests)
- pytest / exporter output if anything fails → I patch the first broken boundary
- `Studio count is 0, Firestore count is N` → Stage 2b (Studio read path), not Stage 3

Do not add graphs, Cloud Run, or a vector database.

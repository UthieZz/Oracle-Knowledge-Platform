# Exact next step for the operator

Stage 3 code is on `main`. Python grounded Ask is aligned with Studio: KO-first retrieval, empty-evidence refusal, citation shape.

Do this and paste results:

```bash
cd /path/to/Oracle-Knowledge-Platform
git pull origin main
git log -3 --oneline
python3 -m pytest tests/test_grounded_ask.py -q
```

Then in Studio Chat:

1. Ask a question that should hit a known knowledge object → expect citations.
2. Ask nonsense with no matches → expect the insufficient-evidence refusal.

Reply with:

- pytest result (pass/fail)
- one screenshot or paste of a cited answer
- one paste of the refusal path

Labels:

- `Stage 3 verified` → freeze Stage 3, pick next roadmap item (attachments or polish)
- failure output → I patch the first broken boundary

Do not add graphs, Cloud Run, or a vector database.

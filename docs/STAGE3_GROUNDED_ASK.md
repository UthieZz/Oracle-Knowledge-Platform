# Stage 3 — Grounded Ask

Status: QUEUED. Do not implement until Stage 2 runtime verification is pasted back.

## Contract

```text
Question
  → retrieve compiled knowledge objects (not raw conversations as default)
  → rank / bound context (top 6)
  → construct evidence block with stable IDs + source_platform
  → model
  → answer with [Source N] citations
  → decline when evidence is thin
```

Studio `ChatService.ts` already implements this shape against Firestore search.
Python `src/studio/services/chat_service.py` still hydrates raw conversation messages. That is a Stage 3 defect, not a Stage 2 defect.

## Stage 3 acceptance

1. Ask with evidence present → answer cites Knowledge Object IDs / titles.
2. Ask with no matching objects → explicit insufficient-evidence refusal. No invention.
3. Citations shown in Studio ChatPage match retrieved objects.
4. Retrieval default is compiled knowledge, not raw conversation dumps.
5. No vector DB. No Cloud Run. No Flask revival.

## Implementation slice (after verification)

1. Align Python chat path with Studio: search knowledge objects first.
2. Add `tests/test_grounded_ask.py` for empty-evidence refusal + citation shape.
3. Verify ChatPage renders citations from real Firestore results.
4. Only then mark Stage 3 code complete.

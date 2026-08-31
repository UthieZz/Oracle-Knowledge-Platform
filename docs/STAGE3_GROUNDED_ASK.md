# Stage 3 — Grounded Ask

Status: CODE COMPLETE. Runtime verification pending.

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
Python `src/studio/services/chat_service.py` now mirrors that contract over portable `output/`:
- search prefers knowledge objects
- empty retrieval → explicit insufficient-evidence refusal (no model call)
- citations carry id, title, platform, source_index, type

## Stage 3 acceptance

1. Ask with evidence present → answer cites Knowledge Object IDs / titles.
2. Ask with no matching objects → explicit insufficient-evidence refusal. No invention.
3. Citations shown in Studio ChatPage match retrieved objects.
4. Retrieval default is compiled knowledge, not raw conversation dumps.
5. No vector DB. No Cloud Run. No Flask revival as permanent architecture.

## Implementation done

1. `studio_knowledge_service.search_knowledge` ranks KO first.
2. `chat_service.chat` declines on empty context; bounds top 6.
3. `tests/test_grounded_ask.py` covers empty refusal + KO citation shape.

## Operator verification

```bash
git pull origin main
python3 -m pytest tests/test_grounded_ask.py -q
```

Then one live Ask in Studio with a known KO term and one nonsense query.

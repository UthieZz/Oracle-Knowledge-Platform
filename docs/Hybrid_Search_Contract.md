# Hybrid Search Contract

OKP search is intentionally two-stage:

1. **Lexical retrieval** is deterministic and available directly from the Studio. It searches normalized titles, extracted OCR text, transcripts, summaries, and indexed conversation content.
2. **Semantic retrieval** is performed only by a secured server-side service. The browser must not create embeddings or hold a provider credential.

## Studio configuration

Set `VITE_SEARCH_API_URL` to the base URL of the trusted search service. The Studio will `POST /search` with:

```json
{ "query": "user query", "limit": 50 }
```

The service response is:

```json
{
  "results": [
    {
      "id": "record-id",
      "type": "knowledge",
      "title": "Record title",
      "content": "Safe preview text",
      "source_platform": "ChatGPT",
      "semantic_score": 0.82
    }
  ]
}
```

The Studio merges this response with lexical results by stable `type:id`, retaining provenance and showing semantic results only when the service responds successfully.

## Indexing requirements

The compiler exports `search_text` and `search_terms` for conversations, knowledge objects, entities, and attachments. Attachments include OCR text or transcripts only when actual source content or a configured local extraction engine produces it. Placeholder text must never enter the search index.

The server-side indexer should chunk `search_text`, generate embeddings, preserve document ID and provenance, and filter results by authorised user and source scope before returning them.

# KnowledgeObject IR v2

The KnowledgeObject is the canonical representation used between source import, deterministic analysis, model-assisted extraction, retrieval, and export.

## Provenance invariant

Every object must retain `source_platform`, `source_file`, and immutable source evidence. Every extracted candidate must reference one or more `evidence_spans[].id` values. A model may refine or reject a candidate, but must not replace source evidence or silently convert a candidate into a fact.

## Core layers

- **Source identity:** `id`, `conversation_id`, `source_record_ids`, timestamps, and provenance.
- **Evidence:** normalized messages and `evidence_spans`, each with a source message ID and metadata.
- **Structured extraction:** entities, relationships, attachments, temporal signals, questions, candidate claims, decisions, and action items.
- **Retrieval:** source-faithful chunks and lexical search text. Semantic embedding is server-indexed and stays `pending_server_index` until created.
- **Quality:** evidence and attachment counts plus provenance validation errors.

## Candidate rule

Fields including `claims`, `decisions`, `action_items`, and `questions` are extraction candidates. Each carries:

```json
{
  "text": "candidate text",
  "evidence_ids": ["ev_00001"],
  "kind": "action",
  "status": "candidate"
}
```

This preserves a clear distinction between source material and machine interpretation.

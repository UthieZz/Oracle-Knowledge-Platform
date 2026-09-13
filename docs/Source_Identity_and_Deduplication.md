# Source Identity and Deduplication

OKP identifies a previously processed conversation with a deterministic SHA-256 fingerprint of its normalized, ordered message role and content sequence. Platform name, filename, timestamps, and export-specific IDs are intentionally excluded from this identity calculation.

This means the same underlying conversation can be recognized when it is imported from a different source export or a different platform representation.

## What is retained

Nothing is silently deleted or overwritten. Every matching import retains:

- Its original platform and source file.
- Its source record ID.
- Its own conversation record.
- The shared content fingerprint.
- A canonical conversation ID.
- A full source alias list.
- `duplicate_status`: `canonical` or `duplicate_same_content`.

## Scope

This detects exact normalized evidence only. It does not merge paraphrases, summaries, translations, or similar-but-different conversations. Those require a separate semantic-deduplication review step, because automatic merging would weaken provenance.

## Persistence

The Firestore exporter writes `sourceFingerprints/{content_fingerprint}`. This registry carries aliases across compiler runs, allowing a source to be recognized after the original import session has ended.

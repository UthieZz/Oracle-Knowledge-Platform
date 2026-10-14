# Current stage

Updated 2026-10-14 SAST after LocalFolderConnector + e2e tests.

- Stage 0 COMPLETE
- Stage 1 COMPLETE: compiler source on GitHub (`UthieZz/Oracle-Knowledge-Platform`)
- Stage 2 CODE + OPERATOR-VERIFIED (Firestore counts exist; pytest path previously green)
- Stage 3 CODE COMPLETE (Python chat path aligned to KO-first retrieval + empty-evidence refusal)
- Stage 3 RUNTIME: verify locally as needed
- **OKP Connect:** contract + persistent SyncEngine (cursor, durable queue, retry/idempotency) + minimal SyncWorker (start/stop loop) + LocalFolderConnector landed (`okc/connect/`). Stub and local-folder e2e prove auth→initial/incremental_sync→SyncEngine→PlainTextImporter→KnowledgePackage with tenant/silo provenance. Restart recovery, delete events, and folder incremental/delete verified by tests.
- **Agent trail:** append-only log at `docs/AGENT_COMMIT_LOG.md` — update on every intentional agent commit.

Repos: `UthieZz/Oracle-Knowledge-Platform` (compiler + embedded Studio) and `UthieZz/OKP-Studio`.

No graphs. No Cloud Run. No vector DB. KnowledgePackage remains sole canonical IR.

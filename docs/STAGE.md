# OKP Stage — 2026-11-07

## Verified this run (local environment)

- Connect CLI path bootstrap fixed in `scripts/connect_health.py` and `scripts/run_connect_worker.py`.
  Operator invocation `python scripts/<cli>.py` now resolves `okc` without requiring PYTHONPATH.
- Targeted Connect suite after fix: 31 passed (health + sync_engine + knowledge_accumulator + local_folder_connector + connect_e2e + connect_contract).
- Gemini importer: 31 unit tests passed. Importer is no longer a stub.
- Studio: AuthGate mounted in `App.tsx`. `studio/firestore.rules` gates by tenant/silo claims. `firestorePath.ts` fail-closed on missing `VITE_OKP_TENANT_ID` / `VITE_OKP_SILO_ID`.

## Connect local-folder pilot status

Implemented and targeted-tested:

- LocalFolderConnector with optional snapshot_path (restart deletion detection, sequence for new event_ids).
- SQLite SyncEngine (WAL, dedup, retry/backoff, cursor advances only on success).
- KnowledgeAccumulator (source|tenant|silo namespacing, persist/rollback, cross-scope isolation).
- Health CLI: status=OK|WARNING, exit 1 on WARNING, --json.

## Not verified this run

- Full suite under all optional dependencies (google-genai, firestore, etc.).
- Studio production build.
- Deployed Firestore rules / AuthGate behavior.
- Real business-system connector.
- Complete authorization model beyond documented compatibility (objects without permission entry remain visible).

## Next

P1 authorization consistency or full optional-deps suite + Studio build verification.

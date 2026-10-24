# Agent Commit Log

## 2026-10-16
- Implemented real SQLite SyncEngine (okc/connect/sync_engine.py) replacing placeholder.
  - enqueue (idempotent by event_id), process_next (caller processor, cursor advance on success, simple retry on exception), get_cursor, health, list_queued.
- Added tests/test_sync_engine.py.
- Verified: tests/test_sync_engine.py + test_connect_e2e.py + test_local_folder_connector.py + test_connect_contract.py → 6 passed.
- Knowledge Core untouched. Connect layer now has durable queue matching contract and existing e2e tests.

## 2026-10-17
- Added okc/connect/sync_worker.py: SyncWorker with start/stop, polling (initial or incremental via cursor), enqueue + drain via process_next.
- State is SQLite-backed; restart test proves already-processed events are not re-emitted and cursor persists.
- Added tests/test_sync_worker.py covering poll/process, restart survival, delete event path, health.
- Verified: tests/test_sync_worker.py + test_sync_engine.py + test_connect_e2e.py + test_local_folder_connector.py → 8 passed.
- Knowledge Core untouched. Connect now has a managed background lifecycle on the durable engine.

## 2026-10-18
- Added okc/connect/knowledge_accumulator.py: processes SyncEvents into a living KnowledgePackage.
  - create/update: PlainTextImporter path, injects "src:<object_id>" into provenance.source_record_ids, upserts by source id.
  - delete: removes matching object so subsequent retrieval no longer returns it.
  - permission_change: recorded in package.metadata["permissions"] (enforcement later).
- Exported from okc.connect.
- Added tests/test_knowledge_accumulator.py proving create→retrieve, delete→absent, update→new content.
- Verified: tests/test_knowledge_accumulator.py + test_connect_e2e.py + test_sync_worker.py + test_local_folder_connector.py + test_sync_engine.py → 10 passed.
- Knowledge Core IR unchanged. Connect now has a processor that makes deletion visible to retrieval.

## 2026-10-21
- KnowledgeAccumulator now accepts optional package_path. Loads existing canonical JSON on init; writes after every process. Living KnowledgePackage survives process restarts without changing the IR or Connect contract.
- Added KnowledgePackage.from_json classmethod.
- Added scripts/run_connect_worker.py: minimal durable runner for LocalFolderConnector + SyncWorker + KnowledgeAccumulator. Ctrl-C clean stop. Suitable for local-folder pilot path.
- Added test_knowledge_accumulator_package_path_survives_restart.
- Verified: targeted Connect tests (accumulator, worker, local folder, engine, e2e, contract) pass.
- Knowledge Core IR unchanged. Connect pilot path now has durable living knowledge.

## 2026-10-22
- Extended scripts/connect_health.py to optionally accept a living package JSON path and report exists/mtime/object count alongside SyncEngine queue health. Improves operator visibility for the local-folder pilot runner without changing Connect contract or Knowledge Core.
- Verified: script runs, reports queue counts and package status correctly when package is supplied.

## 2026-10-23
- LocalFolderConnector now accepts optional snapshot_path. Loads prior rel_path→content_hash map on init; persists after every initial_sync and incremental_sync. On restart, incremental_sync detects files deleted while the process was stopped and emits delete events. Engine idempotency by event_id prevents duplicate knowledge. Knowledge Core IR unchanged.
- Updated scripts/run_connect_worker.py to pass a snapshot path (default <db>.snapshot.json).
- Added test_local_folder_snapshot_survives_restart_and_detects_delete.
- Verified: new test + existing local-folder tests pass (manual review of logic; full suite not re-run in this session).
- Connect vertical slice now recovers from stopped-worker deletions. Next: source-identity namespacing in accumulator.

## 2026-10-24
- Namespaced source identity in KnowledgeAccumulator: index and provenance markers now use source|tenant_id|silo_id|object_id. Identical object_ids (relative paths) no longer collide across connectors, tenants or silos. Legacy unscoped "src:object_id" markers remain readable. Permission metadata also keyed by scoped id.
- Added test_source_identity_namespaced_across_scopes covering create/delete isolation across tenant/silo/source.
- Updated STAGE.md.
- Knowledge Core IR unchanged. Connect P0 source-identity isolation item advanced.

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

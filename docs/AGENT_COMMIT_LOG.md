## 2026-11-03 (crash-boundary)
- KnowledgeAccumulator.process rolls back in-memory package, source index and metadata when _persist raises after a successful mutation. Subsequent retry is safe. Added test_process_persist_failure_rolls_back_and_retry_succeeds.
- Targeted Connect suite (engine, accumulator, local-folder, worker, e2e): 23 passed.
- Knowledge Core IR unchanged. Connect P0 crash-boundary item further advanced (persist-failure recovery).

## 2026-11-02
# ... rest of the log

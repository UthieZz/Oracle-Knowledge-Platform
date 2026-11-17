## 2026-11-17 — Context-Aware Reasoning package evidence adapter (real IR path)

- Problem: Orchestrator accepted only caller-supplied evidence_spans; no path from canonical KnowledgePackage to compatibility without embedding logic.
- Change: Added okc/context/package_adapter.py (extract_evidence_spans). Pure extraction of existing EvidenceSpan + explicit constraints from package/object metadata. No inference. ContextOrchestrator.process_query now accepts optional KnowledgePackage; uses adapter when evidence_spans is None. Exported. Suite I1 added.
- Verification: pytest tests/test_context_aware_reasoning.py → 34 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances locked Context-Aware Reasoning by one smallest coherent increment toward real evidence retrieval. No deviation from I-02 / I-11.

## 2026-11-17 — Context-Aware Reasoning orchestrator minimal increment (I-11)

- Problem: QueryContextEngine, CompatibilityEngine, and AnswerStage existed independently; no thin coordinator to demonstrate locked pipeline without embedding domain logic.
- Change: Added okc/context/orchestrator.py (ContextOrchestrator). Coordinates create_envelope → generate_affordances → produce. Exports from package. Suite H1 regression added verifying no mutation, pre-authorized affordances passed through, independent completion flags.
- Verification: pytest tests/test_context_aware_reasoning.py → 33 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances locked Context-Aware Reasoning by one smallest coherent increment. No deviation.


## 2026-11-17 — Context-Aware Reasoning snapshot wiring into QueryContextEngine (I-10)

- Problem: EvidenceSnapshotStore existed but was not used by QueryContextEngine; promote_with_evidence only accepted a caller-supplied ref without enforcing new immutable snapshot creation on evidence application.
- Change: QueryContextEngine.__init__ now accepts optional EvidenceSnapshotStore. promote_with_evidence creates a fresh immutable snapshot via the store when attached (preferred id if free, unique suffix otherwise), records parent_snapshot_id from prior envelope, and sets evidence_set_ref to the new snapshot. Backward compatible without store. Suite G5 added. Exported types unchanged.
- Verification: pytest tests/test_context_aware_reasoning.py → 32 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances locked Context-Aware Reasoning by wiring I-10 into the engine. No deviation.


## 2026-11-17 — Context-Aware Reasoning Evidence Snapshot Store minimal increment

- Problem: Suite E3 was a placeholder; evidence snapshots required for I-10 (retrieval creates new immutable snapshot) were unowned.
- Change: Added okc/context/snapshot_store.py (EvidenceSnapshot frozen model + EvidenceSnapshotStore). create_snapshot rejects duplicate ids, stores immutable tuple of refs with optional parent. get returns original. Suite E3 now verifies immutability and new-on-retrieval. Exported from package.
- Verification: pytest tests/test_context_aware_reasoning.py → 31 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances locked Context-Aware Reasoning by one smallest coherent increment. No deviation.

## 2026-11-17 — Context-Aware Reasoning Query Context Engine minimal increment

- Problem: Answer Stage and compatibility present; envelope revision management, assumption non-promotion, and lineage still lacked an owning engine, leaving Suite E as placeholders.
- Change: Added okc/context/query_engine.py (QueryContextEngine). Creates envelopes/revisions with parent lineage. apply_assumption never promotes status to RESOLVED. Explicit promote_with_user_confirmation and promote_with_evidence only. New evidence sets snapshot ref. Exported from package. Suite G regressions added (G1–G4).
- Verification: pytest tests/test_context_aware_reasoning.py → 31 passed (prior 27 + 4 new).
- Knowledge Core IR and Connect contracts unchanged.
- Advances locked Context-Aware Reasoning by one smallest coherent increment against Suite E rules. No deviation.

## 2026-11-17 — Context-Aware Reasoning Answer Stage minimal increment

- Problem: first gate (models/registry/compatibility + Suites A–E) complete; Answer Stage contract remained unimplemented, blocking structured grounded answers with independent completion flags.
- Change: Added okc/context/answer.py (AnswerStage + locked output models). Produces answer_delivered / contextually_complete independently, discloses assumptions and unresolved high-sensitivity dimensions, retains conflicts, emits only pre-authorized affordances, returns insufficient_evidence when no material content. Suite F regressions added to tests/test_context_aware_reasoning.py. Exported from package.
- Verification: Code written to locked contracts (03-answer-stage-contract.md, 05-integration-contract.md). Local pytest of tests/test_context_aware_reasoning.py required to confirm Suite F passes (expected: prior 23 + 4 new).
- Knowledge Core IR and Connect contracts unchanged.
- Advances locked Context-Aware Reasoning capability by one smallest coherent increment. No deviation.

## 2026-11-16 — Health reports Python executable path (P3)

- Problem: operators diagnosing local OKC server had no structured signal of the exact Python interpreter path without process inspection.
- Change: /api/health now includes `python_executable` (sys.executable). API_VERSION bumped to 0.2.12-local. Tests updated to assert the new field and correct version.
- Verification: pytest tests/test_local_server_status.py → 7 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by making the runtime interpreter observable from the health surface without shell access.


## 2026-11-16 — Health reports open file descriptors count (P3)

- Problem: operators diagnosing long-running local OKC server processes had no structured signal of open file descriptor usage, making resource-leak detection harder without external tools.
- Change: /api/health now includes `open_file_descriptors_count` (len of /proc/self/fd when available, else None). API_VERSION bumped to 0.2.11-local. Tests updated to assert the new field and correct version.
- Verification: pytest tests/test_local_server_status.py → 7 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by making FD usage observable from the health surface without shell access.

## 2026-11-16 — Health reports registered importer names (P3)

- Problem: operators diagnosing local OKC server could see importer count but not the actual names of available source importers without inspecting code or starting a job.
- Change: /api/health now includes `registered_importer_names` (sorted list of plugin names from the registry). API_VERSION bumped to 0.2.10-local. Tests updated to assert the new field, its type, non-empty strings, and length match to count.
- Verification: pytest tests/test_local_server_status.py → 7 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by making the available ingestion surface observable from the health endpoint.

## 2026-11-16 — Health reports system load average (P3)

- Problem: operators diagnosing local OKC server had no structured signal of system load (1/5/15-minute averages), making overload detection harder without external tools.
- Change: /api/health now includes `load_average` (list of three floats from os.getloadavg() when available, else None). API_VERSION bumped to 0.2.9-local. Tests updated to assert the new field and correct version.
- Verification: pytest tests/test_local_server_status.py → 7 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by making system load observable from the health surface without shell access.

## 2026-11-16 — Health reports active threads and CPU count (P3)

- Problem: operators diagnosing local OKC server had no structured signal of active thread count (relevant for background pipeline jobs) or available CPUs.
- Change: /api/health now includes `active_threads_count` (threading.active_count()) and `cpu_count` (os.cpu_count() or 0). API_VERSION bumped to 0.2.8-local. Tests updated to assert the new fields and correct version.
- Verification: pytest tests/test_local_server_status.py → 7 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by making thread usage and CPU availability observable from the health surface without external tooling.

[Full historical log continues from prior commits; see git history for complete prior entries.]

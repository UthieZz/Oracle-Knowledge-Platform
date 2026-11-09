# OKP Stage — 2026-11-09

## Verified this run (local environment)

- Connect CLI path bootstrap fixed in `scripts/connect_health.py` and `scripts/run_connect_worker.py`.
  Operator invocation `python scripts/<cli>.py` now resolves `okc` without requiring PYTHONPATH.
- Targeted Connect suite after fix: 31 passed (health + sync_engine + knowledge_accumulator + local_folder_connector + connect_e2e + connect_contract).
- Gemini importer: 31 unit tests passed. Importer is no longer a stub.
- Studio: AuthGate mounted in `App.tsx`. `studio/firestore.rules` gates by tenant/silo claims. `firestorePath.ts` fail-closed on missing `VITE_OKP_TENANT_ID` / `VITE_OKP_SILO_ID`.

## Connect local-folder pilot status

Implemented and targeted-tested:

- LocalFolderConnector with optional `snapshot_path` (restart deletion detection, sequence for new event_ids).
- SQLite SyncEngine (WAL, dedup, retry/backoff, cursor advances only on success).
- KnowledgeAccumulator (source|tenant|silo namespacing, persist/rollback, cross-scope isolation).
- Health CLI: status=OK|WARNING, exit 1 on WARNING, --json. Text output now includes snapshot_seq and version when the snapshot is readable.

## Not verified this run

- Full suite under all optional dependencies (google-genai, firestore, etc.).
- Studio production build.
- Deployed Firestore rules / AuthGate behavior.
- Real business-system connector.
- Complete authorization model beyond documented compatibility (objects without permission entry remain visible).

## Next

P1 authorization consistency or full optional-deps suite + Studio build verification.

## 2026-11-07 — Health CLI regression expansion

- Added tests for snapshot_missing, package_unreadable, and failed_events warnings (exit 1).
- Targeted health tests: 7 passed.
- Connect path and Knowledge Core IR unchanged.

## 2026-11-07 — Permission mode for retrieval

- KnowledgePackageRetriever now accepts optional `strict_permissions` (default False).
- False preserves documented pilot compatibility: missing permission entry remains visible.
- True treats missing entry as denial (production-oriented fail-closed).
- Explicit read=False still excludes in both modes; explicit read=True allows.
- New tests: missing visible by default; missing denied in strict; explicit allow restores in strict.
- Targeted accumulator tests: 8 passed.
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-07 — Strict permission boundary at context gateway

- Added regression: ContextGateway + KnowledgePackageRetriever(strict_permissions=True) does not return objects lacking an explicit permission entry.
- Explicit permission_change (read=True) restores the object through the same gateway path.
- Test: tests/test_agent_context_gateway.py::test_gateway_respects_strict_retriever_missing_permission → passed.
- No change to KnowledgePackage IR, Connect contract, or default (pilot) permission behavior.

## 2026-11-07 — Health CLI permission gap visibility

- connect_health.py now reports objects_without_explicit_permission for readable packages.
- Operators can see how many objects would be denied under strict_permissions=True.
- New regression passes. Targeted health suite 8 passed.
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-07 — Health CLI --strict-check for permission readiness

- Added optional --strict-check flag to connect_health.py.
- When set, objects_without_explicit_permission > 0 produces status=WARNING and exit 1.
- Default (no flag) remains OK so local-folder pilot behavior is unchanged.
- New regression passes. Targeted health suite 9 passed.
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-07 — Health CLI object_count_mismatch regression

- Added regression confirming metadata object_count != actual objects produces status=WARNING and exit 1.
- Strengthens operator diagnostics for package consistency after interrupted persists or manual edits.
- Targeted health suite: 10 passed.
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-07 — Health CLI snapshot_unreadable regression

- Added regression confirming unreadable snapshot JSON produces status=WARNING and exit 1.
- Strengthens operator diagnostics for restart recovery reliability.
- Targeted health suite: 11 passed.
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-07 — Document intentional permission model

- Added docs/PERMISSION_MODEL.md.
- Explicitly records default pilot behavior (missing entry remains visible), strict_permissions mode, health CLI visibility, and what the model is not.
- Advances P1 acceptance criterion: default permission behavior is documented and intentional.
- No code, IR, or contract change. Health and accumulator tests remain green.

## 2026-11-08 — CLI config file support (P3 operator usability)

- Added optional --config JSON to scripts/connect_health.py and scripts/run_connect_worker.py.
- Config supplies paths/tenant/silo/poll; CLI arguments override. Missing required fields still fail clearly.
- New regression: tests/test_connect_health.py::test_connect_health_accepts_config_file → passed.
- Targeted Connect suite: 44 passed.
- Advances P3 by reducing repeated CLI argument burden for local pilot operators. No IR or contract change.

## 2026-11-08 — Permission change payload validation (P1 boundary)

- KnowledgeAccumulator now ignores permission_change events whose payload lacks a boolean read field.
- Prevents malformed events from writing non-authoritative entries into package.metadata["permissions"].
- New regression: tests/test_knowledge_accumulator.py::test_malformed_permission_change_is_ignored → passed.
- Targeted accumulator suite: 9 passed.
- Knowledge Core IR, Connect contract, and default (pilot) retrieval behavior unchanged.

## 2026-11-08 — Health CLI text output respects config paths (P3 operator UX)

- Fixed: text-mode package and snapshot details now print when paths come from --config (previously required the CLI flag).
- New regression: tests/test_connect_health.py::test_connect_health_text_output_uses_config_package → passed.
- Targeted health suite remains green.
- Knowledge Core IR and Connect contracts unchanged.
- Added docs/CONNECT_LOCAL_PILOT.md with exact config and invocation examples.

## 2026-11-08 — Operator recovery CLI for failed events (P3)

- Added scripts/connect_recover.py: lists failed event details and resets one or all back to queued (attempts=0).
- Does not advance cursors; reprocessing remains operator/worker responsibility.
- New regression: tests/test_connect_recover.py → passed.
- Targeted recovery suite green. Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by making manual recovery of exhausted retries explicit and scriptable without DB inspection.

## 2026-11-08 — Recovery CLI --config support (P3)

- Added optional --config to scripts/connect_recover.py. Resolves db from config.db; --db overrides. Required field validated.
- New regression: tests/test_connect_recover.py::test_connect_recover_accepts_config_file → passed.
- Updates operator guide. Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by aligning recovery CLI with health/worker config pattern for local pilot operators.

## 2026-11-08 — Recovery CLI lists source and kind (P3)

- list_failed_details now returns source and kind for failed events.
- scripts/connect_recover.py --list displays them so operators can identify the failing event type without DB inspection.
- New assertion in tests/test_connect_recover.py confirms the fields appear.
- Targeted recovery suite green. Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by improving failed-event diagnostics for local pilot operators.

## 2026-11-08 — Health CLI recovery hint (P3)

- Text-mode health now emits recovery_hint= when failed events exist, pointing operators at connect_recover.py --list (and --reset).
- New regression: tests/test_connect_health.py::test_connect_health_emits_recovery_hint_on_failed → passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by making the next recovery action discoverable from the health output itself.

## 2026-11-08 — Recovery CLI lists enqueued_at (P3)

* list_failed_details already returned enqueued_at; text --list now displays it.
* Operators can see when the failed event was first enqueued without DB inspection.
* New assertion in tests/test_connect_recover.py confirms the field appears.
* Targeted recovery suite green. Knowledge Core IR and Connect contracts unchanged.
* Advances P3 by improving failed-event diagnostics for local pilot operators.


## 2026-11-08 — Recovery CLI source filter (P3)

- Added optional --source to scripts/connect_recover.py --list.
- Operators can filter failed events by source without DB inspection (useful as multi-source connectors are added).
- New regression: tests/test_connect_recover.py::test_connect_recover_filters_by_source → passed.
- Targeted recovery suite green. Knowledge Core IR and Connect contracts unchanged.
- Advances P3 operator diagnostics for the local pilot.

## 2026-11-08 — Recovery CLI lists tenant and silo (P3)

- list_failed_details now returns tenant_id and silo_id for failed events.
- scripts/connect_recover.py --list text output displays them so operators can identify the failing scope without DB inspection.
- New assertion in tests/test_connect_recover.py confirms the fields appear.
- Targeted recovery + sync_engine suite: 12 passed. Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by improving failed-event diagnostics for multi-scope local pilot operators.


## 2026-11-08 — Recovery CLI tenant and silo filters (P3)

- Added optional --tenant and --silo to scripts/connect_recover.py --list.
- Operators can filter failed events by scope without DB inspection (useful for multi-tenant local pilots).
- New regression: tests/test_connect_recover.py::test_connect_recover_filters_by_tenant_and_silo → passed.
- Targeted recovery suite: 4 passed. Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by improving failed-event diagnostics for multi-scope operators.

## 2026-11-08 — Ownership record (P2)

- Added docs/IMPLEMENTATION_OWNERSHIP.md recording current evidence: Connect path owns okc/ and its Pydantic KnowledgePackage; src/ remains for legacy compiler/UI and Gemini importer.
- No code change. Supports P2 mapping of runtime entry points without migration.
- Targeted Connect suite and core tests remain green (prior runs: 46 Connect, 162 core).

## 2026-11-09 — Recovery CLI consistent JSON output (P3)

- Fixed: --json with --reset / --reset-all no longer emits mixed text + JSON.
- Reset path now returns structured {"reset": N, "ids": [...]} when --json; error cases also JSON.
- New regression: tests/test_connect_recover.py::test_connect_recover_json_reset → passed.
- Targeted recovery suite: 5 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by making recovery scriptable without output parsing fragility.


## 2026-11-09 — Health CLI text shows cursor summary (P3)

- Text-mode health now prints cursor count and up to 3 sample cursors (source/tenant/silo/cursor).
- Operators can verify sync progress without --json or direct DB inspection.
- New regression: tests/test_connect_health.py::test_connect_health_text_shows_cursors → passed.
- Targeted health + recover suite: 20 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 operator diagnostics for the local-folder pilot.

## 2026-11-09 — Pilot guide sync for recovery JSON consistency (P3)

- Updated docs/CONNECT_LOCAL_PILOT.md with clean JSON examples for --reset / --reset-all.
- Aligns operator instructions with the verified clean JSON output for recovery resets (no mixed text+JSON).
- No code or test change. Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by keeping documented operator steps current with tested CLI output.

## 2026-11-09 — Health CLI reports snapshot sequence (P3)

- Text-mode health now prints snapshot_seq and version when the snapshot JSON is readable.
- Operators can confirm restart-recovery state (monotonic sequence used for event_ids) without inspecting the file.
- New regression: tests/test_connect_health.py::test_connect_health_text_shows_snapshot_seq → passed (code+test committed).
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 operator diagnostics for local-folder pilot restart reliability.

## 2026-11-09 — Update after permission deny does not restore visibility (P1)

- Added regression: an update event after explicit read=False permission_change leaves the object denied on subsequent retrieval (default mode).
- Permission map is independent of content upserts; revoke survives update and package reload.
- New test: tests/test_knowledge_accumulator.py::test_update_after_permission_deny_does_not_restore_visibility → passed.
- Targeted accumulator suite: 10 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 authorization consistency evidence for the local-folder pilot.

## 2026-11-09 — Recreate after delete-following-deny is visible (P1)

- Added regression: after explicit read=False + delete (permission entry cleaned), a subsequent create of the same object_id is visible under default mode and has no inherited permission entry.
- Confirms restoration semantics; stale deny does not survive object lifecycle.
- New test: tests/test_knowledge_accumulator.py::test_recreate_after_delete_following_deny_is_visible_by_default → passed.
- Targeted accumulator suite remains green.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 authorization consistency evidence for deletion and restoration.

## 2026-11-09 — Permission entries record event provenance (P1)

- KnowledgeAccumulator stores recorded_from_event and recorded_at on permission_change entries.
- Makes the source event for an explicit allow/deny recoverable from the package without external logs.
- New regression: tests/test_knowledge_accumulator.py::test_permission_entry_records_event_provenance → passed.
- Targeted accumulator suite: 12 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 provenance consistency for authorization decisions in the local-folder pilot.

## 2026-11-09 — SQLiteExporter respects permission model (P1)

- SQLiteExporter.export now accepts optional strict_permissions (default False).
- Explicit read=False entries are always excluded from export.
- Default mode includes objects lacking a permission entry (pilot compatibility).
- strict_permissions=True excludes objects that have a source identity but no permission entry.
- New regressions: tests/test_sqlite_exporter_permissions.py (3 tests) → passed.
- docs/PERMISSION_MODEL.md updated to include export boundary.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 by applying the documented permission policy at the export boundary.

## 2026-11-09 — Export lifecycle: recreate after deny+delete is exported (P1)

- Added regression: after explicit read=False + delete (permission cleaned), re-create of same object_id is included in SQLite export under default mode.
- Confirms no stale denial survives object lifecycle at the export boundary.
- New test: tests/test_sqlite_exporter_permissions.py::test_sqlite_exporter_recreate_after_deny_and_delete_is_exported → passed.
- Targeted exporter + accumulator suite remains green.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 authorization consistency for deletion/restoration semantics at export.

## 2026-11-09 — Health CLI reports permission event provenance (P1/P3)

- connect_health.py now counts and displays permissions_with_event_provenance (entries that carry recorded_from_event).
- Operators can see whether recorded permission decisions are fully traced without opening the package.
- New regression: tests/test_connect_health.py::test_connect_health_reports_permission_event_provenance → passed.
- Targeted health + accumulator + exporter suites: 33 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 provenance visibility and P3 operator diagnostics for the local-folder pilot.

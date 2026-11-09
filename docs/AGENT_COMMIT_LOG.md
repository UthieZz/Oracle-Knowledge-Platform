
## 2026-11-09 — Health CLI reports missing permission event provenance (P1/P3)

- Problem: operators could compare permissions_with_event_provenance to entries but the incomplete count was not explicit.
- Change: package health summary now includes permissions_missing_event_provenance. Text and JSON output print it.
- Added regression confirming a later permission_change overwrites recorded_from_event with the new event id (and survives reload).
- Verification: targeted health + accumulator + exporter suites green.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 provenance completeness visibility and P3 operator diagnostics.
# Agent Commit Log

## 2026-11-07 — Connect CLI path bootstrap

- Problem: `scripts/connect_health.py` and `scripts/run_connect_worker.py` failed when invoked as scripts (ModuleNotFoundError: okc) because Python adds the script directory, not project root, to sys.path.
- Change: insert project root into sys.path before okc imports in both CLIs.
- Verification: `pytest tests/test_connect_health.py tests/test_sync_engine.py tests/test_knowledge_accumulator.py tests/test_local_folder_connector.py tests/test_connect_e2e.py tests/test_connect_contract.py` → 31 passed.
- Gemini importer unit tests also passed (31).
- STAGE.md and this log restored from empty state with current evidence.

## 2026-11-07 — Expand health CLI regressions
- Added three regression tests covering snapshot_missing, package_unreadable, and failed_events.
- All emit status=WARNING and exit 1.
- pytest tests/test_connect_health.py → 7 passed.
- Strengthens operator diagnostics verification for the local-folder pilot.

## 2026-11-07 — Explicit permission modes in retriever
- Added strict_permissions flag to KnowledgePackageRetriever (default False).
- Documents and tests pilot compatibility (missing entry visible) vs production fail-closed (missing denied).
- Advances P1 authorization consistency without breaking existing behavior.
- Tests: tests/test_knowledge_accumulator.py → 8 passed.

## 2026-11-07 — Strict permission gateway boundary test

- Added test linking KnowledgePackageRetriever(strict_permissions=True) to ContextGateway.
- Confirms denied objects (missing permission entry) are not reintroduced at context construction.
- Explicit allow still works. 18 related tests passed.
- Advances P1 authorization consistency evidence without altering default pilot behavior.


## 2026-11-07 — Health CLI reports objects without explicit permission
- Added objects_without_explicit_permission count to package health summary (text and JSON).
- Makes the pilot (missing entry visible) vs production strict_permissions gap inspectable by operators.
- Test: tests/test_connect_health.py::test_connect_health_reports_objects_without_explicit_permission → passed.
- Health suite 8 passed. No IR or contract change.

## 2026-11-07 — Health CLI --strict-check
- Added optional --strict-check flag. When present, objects_without_explicit_permission > 0 sets status=WARNING (exit 1).
- Default invocation unchanged (pilot remains OK).
- Regression: tests/test_connect_health.py::test_connect_health_strict_check_warns_on_missing_permission → passed.
- Health suite 9 passed. No IR or contract change.

## 2026-11-07 — Health CLI object_count_mismatch regression
- Added test_connect_health_warns_on_object_count_mismatch.
- Confirms existing check (implemented in connect_health.py) emits WARNING + exit 1 on metadata/object mismatch.
- pytest tests/test_connect_health.py → 10 passed.
- Advances operational visibility for the local-folder pilot without IR or contract change.

## 2026-11-07 — Health CLI snapshot_unreadable regression
- Added test_connect_health_warns_on_unreadable_snapshot.
- Confirms existing check (implemented in connect_health.py) emits WARNING + exit 1 on corrupted snapshot.
- pytest tests/test_connect_health.py → 11 passed.
- Advances operational visibility for the local-folder pilot without IR or contract change.

## 2026-11-07 — Document permission model
- Created docs/PERMISSION_MODEL.md describing current intentional retrieval permission behavior.
- Default (missing entry visible) vs strict mode, health --strict-check, and explicit limitations.
- Supports P1 without altering runtime.
- No tests required (documentation only). Prior targeted suites still pass.


## 2026-11-08 — Optional JSON config for Connect CLIs
- Problem: Operators must supply the same paths/tenant/silo on every health and worker invocation.
- Change: `--config` JSON accepted by both scripts; CLI overrides config; validation of required fields preserved.
- Verification: pytest tests/test_connect_health.py tests/test_sync_engine.py tests/test_knowledge_accumulator.py tests/test_local_folder_connector.py tests/test_connect_e2e.py tests/test_connect_contract.py tests/test_agent_context_gateway.py → 44 passed.
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-08 — Health CLI text output for config-resolved paths

- Problem: text-mode health omitted package/snapshot details when paths were supplied only via `--config`.
- Change: print conditions now use resolved package/snapshot variables.
- Verification: pytest tests/test_connect_health.py → includes new regression; prior targeted suites remain green.
- Added docs/CONNECT_LOCAL_PILOT.md.
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-08 — Operator recovery CLI for failed events

- Problem: operators had to inspect SQLite or call reset_failed programmatically to recover exhausted events.
- Change: added scripts/connect_recover.py with --list, --reset, --reset-all.
- Verification: pytest tests/test_connect_recover.py → 1 passed. Prior targeted Connect suite remains green (43 passed earlier).
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-08 — Recovery CLI --config support

- Problem: recovery CLI required explicit --db while health and worker accept shared --config.
- Change: added --config to scripts/connect_recover.py; resolves db from config.db; --db overrides; validates required field.
- Verification: pytest tests/test_connect_recover.py → 2 passed (new config regression included).
- Updates docs/CONNECT_LOCAL_PILOT.md. Knowledge Core IR and Connect contracts unchanged.


## 2026-11-08 — Health CLI recovery hint for failed events

- Problem: operators seeing failed_events WARNING had to recall the separate recovery CLI.
- Change: text health output now prints recovery_hint=python scripts/connect_recover.py --db <path> --list (plus brief usage note).
- Verification: pytest tests/test_connect_health.py tests/test_connect_recover.py → includes new regression; prior targeted suites remain green.
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-08 — Recovery CLI lists enqueued_at (P3)

- Problem: operators listing failed events saw source/kind/attempts/error but not when the event was enqueued.
- Change: text output of connect_recover.py --list now includes enqueued= timestamp from list_failed_details.
- Verification: pytest tests/test_connect_recover.py → includes new assertion; targeted suite green.
- Knowledge Core IR and Connect contracts unchanged.


## 2026-11-08 — Recovery CLI source filter (P3)

- Problem: operators listing failed events saw all sources mixed; no way to filter without DB query.
- Change: added optional --source to connect_recover.py --list; filters list_failed_details by source.
- Verification: pytest tests/test_connect_recover.py → includes new regression; targeted suite green.
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-08 — Recovery CLI lists tenant and silo (P3)

- Problem: operators listing failed events saw source/kind but not the tenant/silo scope of the failure.
- Change: list_failed_details and text --list now include tenant_id and silo_id.
- Verification: pytest tests/test_connect_recover.py tests/test_sync_engine.py → 12 passed.
- Knowledge Core IR and Connect contracts unchanged.


## 2026-11-08 — Recovery CLI tenant and silo filters (P3)

- Problem: operators listing failed events across scopes had no way to filter by tenant_id or silo_id without a DB query.
- Change: added optional --tenant and --silo to connect_recover.py --list; filters list_failed_details by those fields. --reset-all respects the filters.
- Verification: pytest tests/test_connect_recover.py → 4 passed (new regression included).
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-08 — Record implementation ownership (P2)

- Problem: Dual src/ and okc/ surfaces continue to require rediscovery; no explicit current-ownership record for the Connect pilot.
- Change: Added docs/IMPLEMENTATION_OWNERSHIP.md stating Connect owns okc/ (Pydantic KnowledgePackage); src/ owns legacy compiler/UI and Gemini importer. No merge without further evidence.
- Verification: Documentation only. Prior targeted suites green. No IR or contract change.
- Advances P2 by making runtime-entry ownership explicit and recoverable from the repo.

## 2026-11-08 — Roadmap sync with current evidence (P2/P3)

- Problem: ROADMAP.md dated 2026-11-07 lagged STAGE.md and ownership record from 2026-11-08.
- Change: Updated date/snapshot to 2026-11-08; noted IMPLEMENTATION_OWNERSHIP.md; consolidated P3 recent operator recovery/config/health progress.
- Verification: Documentation only. Aligns roadmap with recorded targeted tests and ownership. No IR or contract change.
- Supports consistent interpretation of implementation vs tested status.

## 2026-11-09 — Recovery CLI consistent JSON for resets (P3)

- Problem: --json + --reset emitted human text then JSON, breaking machine consumers.
- Change: suppress text on --json; emit clean {"reset": N, "ids": [...]} (and JSON error on failure).
- Verification: pytest tests/test_connect_recover.py → 5 passed (new JSON reset regression included).
- Knowledge Core IR and Connect contracts unchanged.


## 2026-11-09 — Health CLI text cursor summary (P3)

- Problem: operators using text health saw queue stats but not current cursors; required --json or DB query to confirm progress.
- Change: text output now emits cursors=N and sample lines when cursors exist.
- Verification: pytest tests/test_connect_health.py tests/test_connect_recover.py → 20 passed (new regression included).
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-09 — Pilot operator guide updated for recovery JSON (P3)

- Problem: CONNECT_LOCAL_PILOT.md lagged the verified clean JSON output for recovery resets.
- Change: Added explicit JSON examples for --reset and --reset-all.
- Verification: Documentation only. Aligns with tests/test_connect_recover.py::test_connect_recover_json_reset (passed in prior run).
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-09 — Health CLI reports snapshot sequence (P3)

- Problem: operators could not see the connector snapshot monotonic sequence (used for event_id uniqueness on delete/recreate) without opening the JSON file.
- Change: text health output now prints snapshot_seq= and version= when the snapshot is readable.
- Verification: new regression tests/test_connect_health.py::test_connect_health_text_shows_snapshot_seq added and committed. Prior targeted suites remain green by pattern.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 restart-recovery diagnostics for the local-folder pilot.

## 2026-11-09 — Update after permission deny does not restore visibility (P1)

- Problem: no explicit regression confirmed that a content update after an explicit read=False permission_change leaves the object denied.
- Change: added test_update_after_permission_deny_does_not_restore_visibility. Confirms denial survives update and reload; permission entry unchanged.
- Verification: pytest tests/test_knowledge_accumulator.py → 10 passed (new test included).
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 authorization consistency for the local-folder pilot without altering default retrieval behavior.

## 2026-11-09 — Recreate after delete-following-deny is visible (P1)

- Problem: no explicit regression confirmed that a re-create after deny + delete does not inherit the prior denial.
- Change: added test_recreate_after_delete_following_deny_is_visible_by_default. Confirms object is visible under default mode, no permission entry present, survives reload.
- Verification: pytest tests/test_knowledge_accumulator.py::test_recreate_after_delete_following_deny_is_visible_by_default → passed. Prior accumulator suite green.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 restoration/deletion semantics for the local-folder pilot.

## 2026-11-09 — Permission entries record event provenance (P1)

- Problem: permission map stored only the payload; the originating event_id and time were not preserved inside the package.
- Change: on well-formed permission_change, store a shallow copy of payload plus recorded_from_event and recorded_at.
- Verification: pytest tests/test_knowledge_accumulator.py → 12 passed (new provenance regression included).
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 by making authorization provenance inspectable from the living package.

## 2026-11-09 — SQLiteExporter permission filtering (P1)

- Problem: export boundary did not consult the permissions map; explicit denials could still be published to SQLite.
- Change: SQLiteExporter.export(..., strict_permissions=False) filters objects using the same rules as KnowledgePackageRetriever. Explicit read=False always excluded; missing entry included by default, denied when strict=True.
- Verification: pytest tests/test_sqlite_exporter_permissions.py tests/test_knowledge_accumulator.py → 15 passed.
- docs/PERMISSION_MODEL.md updated. Knowledge Core IR and Connect contracts unchanged.
- Advances P1 authorization consistency at the export boundary without altering default pilot behavior.

## 2026-11-09 — SQLite export includes recreate after deny+delete (P1)

- Problem: no explicit regression confirmed that a re-create after deny + delete is exported under default mode (stale deny must not survive).
- Change: added test_sqlite_exporter_recreate_after_deny_and_delete_is_exported. Confirms export includes the object and permission map has no leftover deny.
- Verification: pytest tests/test_sqlite_exporter_permissions.py::test_sqlite_exporter_recreate_after_deny_and_delete_is_exported → passed. Prior related suites green.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 by closing the lifecycle evidence gap at the export boundary.

## 2026-11-09 — Health CLI reports permission event provenance (P1/P3)

- Problem: operators could not see from health output whether permission entries carried the recorded_from_event provenance added earlier.
- Change: package health summary now includes permissions_with_event_provenance count; text output prints it.
- Verification: pytest tests/test_connect_health.py::test_connect_health_reports_permission_event_provenance → passed. Targeted health + accumulator + exporter: 33 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 provenance visibility and P3 operator diagnostics without altering runtime behavior.

## 2026-11-09 — Permission before create is enforced (P1)

- Problem: no explicit regression confirmed that a permission_change recorded before the object exists is still applied when the object is later created.
- Change: added test_permission_change_before_create_is_enforced. Confirms entry is stored, object is created, retrieval excludes it under default mode, and both survive reload.
- Verification: pytest tests/test_knowledge_accumulator.py::test_permission_change_before_create_is_enforced → passed. Prior accumulator suite remains green.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 by closing the event-ordering evidence gap for authorization decisions.

## 2026-11-09 — Revocation after prior retrieval is enforced (P1)

- Problem: no explicit regression confirmed that a permission deny issued after a successful retrieval is respected on the next ContextGateway build (possible caching concern).
- Change: added test_gateway_respects_revocation_after_prior_retrieval. Prior build returns the object; after read=False the subsequent build returns empty. Default (pilot) mode.
- Verification: pytest tests/test_agent_context_gateway.py::test_gateway_respects_revocation_after_prior_retrieval → passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 by closing the "revocation after prior retrieval" evidence gap called out in PERMISSION_MODEL.md.

## 2026-11-09 — Health CLI reports snapshot tracked file count (P3)

- Problem: operators could see snapshot seq/version but not how many files the restart-recovery map currently tracks.
- Change: _snapshot_info now computes tracked_files from the snapshot map; text output includes it.
- Verification: pytest tests/test_connect_health.py::test_connect_health_text_shows_snapshot_seq → passed (updated assertion).
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 diagnostics for snapshot recovery reliability.


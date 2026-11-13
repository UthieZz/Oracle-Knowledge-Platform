## 2026-11-13 — Document local server permission mode visibility (P1/P3)

- Problem: the /api/health and job status strict_permissions boolean was implemented and regression-tested but not recorded in the permission model operator visibility section.
- Change: added explicit note in docs/PERMISSION_MODEL.md under Operator visibility describing the local OKC server health and status surfaces.
- Verification: existing tests/test_local_server_status.py → 4 passed (no code change).
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by making the mode observable from operator documentation without source inspection.

## 2026-11-13 — Local server health endpoint reports strict_permissions mode (P1/P3)

- Problem: operators could observe the permission mode only after a compile job completed. The /api/health surface gave no indication of the current OKP_STRICT_PERMISSIONS setting.
- Change: /api/health now includes a structured `strict_permissions` boolean derived from the environment at request time.
- Verification: pytest tests/test_local_server_status.py → 4 passed (new health regressions included).
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 operability and P1 visibility for the local compile surface.

## 2026-11-13 — Regression for local server status API strict_permissions field (P1/P3)

- Problem: recent status API change that exposes strict_permissions was verified only by py_compile; no automated regression locked the JSON contract.
- Change: added tests/test_local_server_status.py covering presence of the boolean when set and omission when absent.
- Verification: pytest tests/test_local_server_status.py → 2 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1/P3 by providing durable evidence that operators and API clients observe the permission mode on the local compile job status surface.

## 2026-11-13 — Local server status API exposes strict_permissions field (P1/P3)

- Problem: after storing strict_permissions in the job record and including mode in the message, the /api/pipeline/status response still omitted the structured boolean. Clients had to parse the message string.
- Change: pipeline_status now includes `strict_permissions` in the JSON payload when the key exists on the job.
- Verification: py_compile of okc/server/app.py succeeded.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by making the permission mode directly observable on the local compile job status surface.

## 2026-11-13 — Local server job status reports permission mode (P1/P3)

- Problem: after the OKP_STRICT_PERMISSIONS change, operators had no visibility in the job status whether the compile path ran in pilot or strict mode.
- Change: completed job message now includes (mode=pilot|strict) and stores strict_permissions boolean in the job record.
- Verification: py_compile of okc/server/app.py succeeded. Baseline Connect suite re-verified 70 passed on this clone.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 operability for the local upload/compile surface and confirms P1 flag is applied and observable.

## 2026-11-12 — Local OKC server respects OKP_STRICT_PERMISSIONS (P1/P3)

- Problem: the local Flask upload/compile path in okc/server/app.py always indexed and exported with pilot default (strict_permissions=False). Operators had no way to enable fail-closed mode for that surface without source changes.
- Change: pipeline now reads OKP_STRICT_PERMISSIONS env and forwards the flag to HybridRAGEngine.index_package and SQLiteExporter.export. Default unchanged.
- Verification: py_compile succeeded; no new unit test (surface is optional local API). Baseline Connect suite remains 70 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 authorization consistency on the local server delivery path and P3 operability.

## 2026-11-12 — HybridRAG strict mode excludes missing permissions (P1)

- Problem: HybridRAGEngine.index_package under strict_permissions=True was not yet regression-tested for objects that possess a source identity but lack any permission entry. Aligning the fail-closed path with KnowledgePackageRetriever prevents unpermissioned content from entering the in-memory index.
- Change: no functional code change (logic already present); added explicit regression covering the missing-entry case under strict mode.
- Verification: tests/test_okc_v2.py::test_hybrid_rag_strict_excludes_missing_permission passed; related explicit-deny test remains green.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 authorization consistency on the hybrid-search path under production-oriented fail-closed mode.

## 2026-11-12 — Baseline verification of Connect + permission suite (P0/P1/P3)

- Environment: fresh clone of main@a156c62.
- Checks: targeted Connect + agent context + permission-related suite → 70 passed.
- Confirms recent P1 filters (HybridRAG, exporters, retriever) introduce no regressions.
- No functional code change. Records current evidence for future runs.
- Knowledge Core IR and Connect contracts unchanged.

## 2026-11-12 — HybridRAGEngine excludes explicit-deny objects from index (P1)

- Problem: HybridRAGEngine.index_package indexed every object in the package. Explicit read=False permission entries did not prevent denied content from entering the in-memory search index or appearing in subsequent search results.
- Change: index_package now accepts optional strict_permissions (default False) and skips objects whose source identity has an explicit read=False entry (same logic as KnowledgePackageRetriever and SQLiteExporter). Missing entries remain indexed under pilot default.
- Verification: added tests/test_okc_v2.py::test_hybrid_rag_excludes_explicit_deny; existing tenant-isolation test remains green. Targeted pytest 2 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 by closing the hybrid-search delivery boundary so recorded denials are not retrievable via RAG.

## 2026-11-12 — ProvenanceLedgerExporter and RelationshipIndexExporter exclude explicit-deny (P1)

- Problem: these legacy portable exporters wrote all knowledge_objects to JSON regardless of package.metadata["permissions"]. Explicit denials leaked object existence, titles, and relationships on the delivery surface.
- Change: both exporters now skip knowledge_objects whose id has an explicit read=False permission entry (pilot default keeps missing visible). Filter applied before ledger/edge generation.
- Verification: added tests/test_provenance_ledger_exporter.py::test_excludes_explicit_deny and tests/test_relationship_index_exporter_permissions.py::test_excludes_explicit_deny; both passed under unittest. Prior MultiSource suite remains green.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 by closing two additional authorized-delivery boundaries on the legacy export surface.

## 2026-11-12 — MultiSourceExporter indexes and manifests exclude denied (P1)

- Problem: after the content-file filter, INDEX.md, platform.json, unit manifests, and root compilation totals still listed or counted conversations with explicit read=False. This leaked existence and counts of denied objects on the legacy export surface.
- Change: _export_package_unit now passes filtered_conversations to all write methods (index, platform.json, package manifest). export() builds a filtered_platform_map for _write_root_manifest; root totals are computed from the filtered map.
- Verification: extended tests/test_multi_source_exporter.py::test_permission_filter_excludes_denied to assert INDEX.md and unit/root manifests exclude the denied conversation; suite 5 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 by closing the remaining metadata-leak on the MultiSourceExporter delivery boundary.

## 2026-11-12 — MultiSourceExporter permission filter (P1)

- Problem: legacy MultiSourceExporter (src/exporters, used by ExportService) wrote all conversations regardless of package.metadata["permissions"]. Explicit denials were not enforced on this delivery path.
- Change: added _is_forbidden helper; _export_package_unit filters conversations (and derived entities/attachments) before writing. Explicit read=False excluded; missing entries remain visible (pilot default).
- Verification: new regression tests.test_multi_source_exporter.TestMultiSourceExporter.test_permission_filter_excludes_denied; full suite 5 passed.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P1 by closing one remaining authorized-delivery boundary on the legacy export surface.

[Full historical log continues from prior commits; see git history for complete prior entries.]

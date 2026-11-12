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
# P2 Runtime Entry Points & Ownership Matrix

**Last inspected:** 2026-11-28  
**Source of truth:** Current `main` source. This is an evidence map, not a migration plan. Unknown or unverified behavior is labelled rather than inferred.

## Runtime map

| Entry point / surface | Owner | Runtime | Role and contract | Status / evidence |
|---|---|---|---|---|
| `python run.py server` | `okc/server/app.py` | Native Python process; Flask | Local API: upload, compile, pipeline status, health. | Active local pilot entry. `run.py`, `okc/server/app.py`, README. |
| `python run.py studio` | `studio/` | Node/Vite development process + browser | Starts the separate React/PWA frontend; server is a separate process. | Active UI entry. README and `run.py`. |
| `python scripts/run_connect_worker.py` | `okc/connect/` | Native Python worker | Polls configured source, stages events, durable queue and package processing. | Active Connect worker. README, ownership record and tests. |
| `python scripts/connect_health.py` | `okc/connect/` | Native Python CLI | Reports Connect health and recovery hints. | Active operator CLI. README/roadmap. |
| `python scripts/connect_recover.py` | `okc/connect/` | Native Python CLI | Lists/resets failed Connect events. | Active operator CLI. README/roadmap. |
| `python scripts/verify_local_pilot.py` | `okc/` | Native Python one-shot process | Verifies local folder → accumulator → KnowledgePackage → SQLite export → lexical search, including restart/update/delete convergence. | Active verification command; roadmap/log record exit 0 on 2026-11-27. |
| `python run.py compiler` | `scripts/compile_data.py` and `src/` | Native Python | Legacy compilation path. | Legacy-active/deprecated; warning regression in `tests/test_entry_point_deprecation.py`. |
| `main.py` | `src/controllers`, `src/ui` | Python desktop/Qt | Legacy desktop UI. | Legacy-active; ownership record. |
| Gemini importer | `src/importers/gemini_importer.py` | Native Python | Legacy importer maps into `src.models`. | Functional legacy surface per ownership record; migration not approved. |
| Studio ImportPage | `studio/src` | Browser | User-facing import workflow. | Active consumer; inspect current page and auth wiring during P2. |
| Studio API client | `studio/src/services/apiService.ts` | Browser | Calls `POST /api/import/upload`, `POST /api/compile`, `GET /api/pipeline/status`; sends tenant/silo fields. | Active client; contract counterpart is `okc/server/app.py`. Client-supplied scope is not authorization proof. |
| Local OKC API | `okc/server/app.py` | Native Python / Flask | Receives upload, starts compile thread, reports job state, exports SQLite and indexes HybridRAG in pipeline. | Active local API. No evidence here of authenticated multi-tenant authorization. |
| Legacy Studio API | `src/studio/api_server.py` | Native Python / Flask | Legacy dashboard, upload, compile, search/chat endpoints backed by `src.services`. | Legacy-active/consumer status needs caller check before retirement. Not interchangeable with the OKC API. |
| Connect connector | `okc/connect/local_folder_connector.py` | Native Python | Emits create/update/delete SyncEvents with source and scope metadata. | Active; tests in `tests/test_local_folder_connector.py`. |
| Durable queue | `okc/connect/sync_engine.py` | Native Python + SQLite | Enqueues/deduplicates events and processes queue through callback. | Active; Connect test suites. |
| Package accumulator | `okc/connect/knowledge_accumulator.py` | Native Python | Applies SyncEvents to persisted living KnowledgePackage. | Active; Connect test suites. |
| Canonical package model | `okc/models/knowledge_package.py` | Python / Pydantic | Canonical IR for Connect vertical slice. | Active canonical model; ownership record. |
| Legacy package model | `src/models/knowledge_package.py` | Python | Distinct model used by legacy compiler/importers. | Legacy model; not used by Connect. Do not merge without migration evidence. |
| Export/persistence adapters | `okc/exporters/` and related registered plugins | Native Python | Publish package to supported stores (local pilot includes SQLite). | Active; enumerate exact adapters and schemas during P2. |
| Retrieval / ContextGateway | `okc/` retrieval/context modules | Native Python | Expected downstream evidence boundary. | Exact active entry point and end-to-end linkage remain to be verified; inspect code/tests before naming a canonical route. |
| AuthGate / Firebase rules | Studio/auth and Firebase config paths | Browser + Firebase | Identity, permission and data access policy. | Existence and deployed behavior not established by this map; locate current files and emulator tests. |

## Known contracts and boundaries

### Studio ↔ local API

The current Studio service sends:
- upload: `file`, `tenant_id`, `silo_id`;
- compile: `job_id`, `tenant_id`, `silo_id`;
- status: `job_id` query parameter.

The local server exposes the matching routes. This is route-level alignment only. It does not prove authorization, trusted scope derivation, or parity with the legacy `src/studio/api_server.py`.

### Connect → canonical package

The tested local-folder path is:

```text
LocalFolderConnector
  → SyncEvent
  → SyncEngine (SQLite queue)
  → KnowledgeAccumulator
  → okc.models.knowledge_package.KnowledgePackage
```

Tests already cover source create/update/delete, tenant/silo metadata on events/package provenance, restart convergence and durable queue behavior. The standalone verification script extends this into SQLite export and lexical search. Do not duplicate existing tests without identifying a missing assertion.

### Canonical and legacy model boundary

- Canonical Connect IR: `okc.models.knowledge_package.KnowledgePackage`.
- Legacy model: `src.models.knowledge_package.KnowledgePackage`.
- No automatic promotion or dual-write is documented.
- `src/` and `okc/` remain separate owners for different active consumers.

## Explicit unknowns for P2

1. Full list of current importers, exporters, retrievers and ContextGateway implementations, including exact call graph and public interfaces.
2. Whether EvidenceSpan IDs and source timestamps are retained through the actual selected persistence and retrieval path.
3. Whether the local server's request scope is trusted, authenticated, and isolated; current code accepts request scope values and falls back to defaults.
4. Whether Studio AuthGate is enforced by the backend and Firebase rules at every relevant read path.
5. Whether any Pyodide/browser-Python execution surface exists in current configuration. Do not assert one without code evidence.
6. Whether the legacy API server has active consumers beyond historical UI paths.

## Inspection protocol

For each unknown, search all imports, route registrations, CLI references, build configuration, tests and runtime wiring. Record exact file paths and tests. Use "unknown" until evidence resolves it. Update this matrix in the same change that alters ownership or a runtime contract.

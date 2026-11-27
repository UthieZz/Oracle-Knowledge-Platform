# OKP Stage — 2026-11-28

**Basis:** Current main. Block 2: Studio local read path unified with SQLiteExporter. `SQLiteKnowledgeReader` + `/api/dashboard`, `/api/knowledge-objects`, `/api/search` on okc server; Studio `knowledgeStore` defaults to local API (`VITE_OKP_DATA_MODE=local`). AuthGate skips Firebase in local mode. ImportPage accepts `.json,.txt,.md`. Reader empty-DB + tenant isolation locked by tests (Flask HTTP tests skip when flask absent). Connect reliability and IR unchanged.

## Knowledge Core
- Canonical KnowledgePackage (okc/models) is the sole IR.
- Provenance, source IDs, tenant/silo preserved.
- Permission model: pilot default keeps missing visible; explicit deny enforced; strict mode available via OKP_STRICT_PERMISSIONS.
- Delivery boundaries honor explicit deny; strict mode excludes missing when source identity present.

## OKP Connect local-folder pilot
- LocalFolderConnector + persistent snapshot, SQLite SyncEngine, KnowledgeAccumulator implemented and targeted-tested.
- Health CLI and recovery CLI present.
- Operator guide and Docker packaging example exist.
- scripts/verify_local_pilot.py provides single-command runtime verification of the clean local path (import → accumulate → export → search) plus restart+update+deletion convergence.

## Local OKC server (okc/server/app.py)
- Upload/compile path honors OKP_STRICT_PERMISSIONS for HybridRAG index and SQLite export.
- Read path: SQLiteKnowledgeReader serves dashboard, knowledge-objects, search (tenant/silo scoped).
- /api/health reports readiness details including sqlite_readable.
- Entry point wired: `python run.py server` launches the server expected by studio (default 127.0.0.1:5000). Studio Vite remains separate (`python run.py studio`).
- Studio: KnowledgeStore routes Dashboard / KO browser / Search / Chat retrieval to local API by default; FirestoreService preserved for VITE_OKP_DATA_MODE=firestore.

## Dual surfaces
- Connect owns okc/ + Pydantic KnowledgePackage.
- src/ remains for legacy compiler/UI and Gemini importer.
- `python run.py compiler` now emits a deprecation warning directing operators to the okc/ surfaces (server, verify_local_pilot, connect worker). No functional change to the legacy path.
- No merge without further evidence. See docs/IMPLEMENTATION_OWNERSHIP.md.

## Context-Aware Reasoning (locked design)
- Deterministic suite green. 38 passed. No deviation from locked contracts.

## Next
P0: journal reliability locked. Block 2 local Studio read path landed. Prefer remaining P1 delivery boundary or full flask-backed HTTP verification of the new routes. Do not treat unit suite green as B2B readiness.

**Not claimed:** production-grade multi-tenant authorization, full fail-closed default, B2B readiness, or runtime-verified Studio/Firestore deployment.

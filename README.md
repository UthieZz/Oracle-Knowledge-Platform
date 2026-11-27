# Oracle Knowledge Platform

Local-first knowledge infrastructure that turns fragmented sources into a governed, searchable KnowledgePackage.

## Current entry points (as of 2026-11-27)

| Command | What it does |
|---------|--------------|
| `python run.py server` | Starts the local OKC API (`okc.server.app`) on 127.0.0.1:5000. Matches the endpoints expected by Studio ImportPage. Honors `OKP_STRICT_PERMISSIONS`. |
| `python run.py studio` | Starts the Studio Vite frontend (separate process). Reminds you to also start the server. |
| `python run.py compiler` | Legacy compiler path (`scripts/compile_data.py` / `src/`). |
| `python scripts/verify_local_pilot.py` | Single-command runtime verification of the clean local-folder Connect path: Import → Accumulate → KnowledgePackage → SQLite export → lexical search, plus restart + source-deletion convergence. Exit 0 on success. No cloud deps. |
| `python scripts/run_connect_worker.py` | Background Connect worker for a local folder source. |

## Local pilot verification

```bash
python scripts/verify_local_pilot.py
```

See `docs/CONNECT_LOCAL_PILOT.md` for the full operator guide, config, Docker example, health, and recovery.

## Ownership

- Connect / local pilot / local server: `okc/` + Pydantic KnowledgePackage (canonical IR).
- Legacy compiler / desktop UI / Gemini importer: `src/`.
- Studio: `studio/`.

No automatic merge. See `docs/IMPLEMENTATION_OWNERSHIP.md` and `docs/STAGE.md`.

## Constraints

KnowledgePackage is the sole canonical IR. Preserve provenance, tenant/silo isolation, and the pipeline order. Do not treat unit tests or the verification script as B2B readiness.

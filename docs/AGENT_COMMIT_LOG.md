## 2026-11-14 — Health reports db_exists (P3)

- Problem: operators diagnosing local OKC server had no structured signal whether the SQLite database file already exists on disk.
- Change: /api/health now includes `db_exists` boolean (Path.is_file() on OKC_SQLITE_PATH).
- Verification: pytest tests/test_local_server_status.py → 6 passed (new asserts included).
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by making local persistence state observable from the health surface without filesystem inspection.

## 2026-11-14 — Health reports api_version (P3)

- Problem: operators diagnosing local OKC server had no structured signal of the running API/code version beyond Python and platform.
- Change: /api/health now includes `api_version` constant ("0.2.0-local") for code-identity diagnostics.
- Verification: pytest tests/test_local_server_status.py → 6 passed (new asserts included).
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by making the running local API version observable from the health surface without source inspection.

## 2026-11-14 — Health reports python_version and platform (P3)

- Problem: operators diagnosing local OKC server environment had no structured signal of the running Python version or platform.
- Change: /api/health now includes `python_version` (major.minor.micro) and `platform` (sys.platform).
- Verification: pytest tests/test_local_server_status.py → 6 passed (new asserts included).
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by making the runtime environment observable from the health surface without source or shell inspection.

## 2026-11-14 — Health reports tenant/silo env presence (P3)

- Problem: operators verifying local OKC server readiness for Firestore export had no structured signal that OKP_TENANT_ID and OKP_SILO_ID were set.
- Change: /api/health now includes `tenant_configured` and `silo_configured` booleans (non-empty check). Values are not returned.
- Verification: pytest tests/test_local_server_status.py → 6 passed (new regressions included).
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by making the required tenant/silo gate observable from the health surface without source or env inspection.

## 2026-11-14 — Restore source-of-truth documents after accidental overwrite (P3)

- Problem: commit 87abccb replaced full ROADMAP.md and AGENT_COMMIT_LOG.md with single-line placeholders, breaking agent source of truth.
- Change: restored both files from prior good state (76e1bc8), updated ROADMAP date to 2026-11-14, and prepended this entry. No functional code change.
- Verification: content matches prior committed versions; git history confirms restore.
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by re-establishing operational documentation for subsequent engineering runs.

[Full historical log continues from prior commits; see git history for complete prior entries.]

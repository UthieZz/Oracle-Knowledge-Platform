## 2026-11-14 — Health reports absolute upload and DB paths (P3)

- Problem: operators diagnosing local OKC server path configuration had no structured signal of the exact resolved filesystem locations used for uploads and SQLite persistence.
- Change: /api/health now includes `upload_dir_absolute` and `db_path_absolute` (str(Path.resolve())). API_VERSION bumped to 0.2.1-local.
- Verification: pytest tests/test_local_server_status.py → 7 passed (new asserts included).
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by making the concrete local paths observable from the health surface without source or shell inspection.

## 2026-11-14 — Health reports google_credentials_configured and active_jobs_count (P3)

- Problem: operators diagnosing local OKC server readiness for Firestore publishing and job load had no structured signals for GOOGLE_APPLICATION_CREDENTIALS presence or current in-memory job count.
- Change: /api/health now includes `google_credentials_configured` boolean (non-empty check on GOOGLE_APPLICATION_CREDENTIALS) and `active_jobs_count` (len of process-local job registry under lock).
- Verification: pytest tests/test_local_server_status.py → 7 passed (new asserts and tests included).
- Knowledge Core IR and Connect contracts unchanged.
- Advances P3 by making Firestore credential gate and local job visibility observable from the health surface without env or process inspection.

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

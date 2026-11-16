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

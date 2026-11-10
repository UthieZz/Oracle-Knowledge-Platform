# OKP Connect — Local-Folder Pilot Operator Guide

**Status:** Implemented and targeted-tested for the local path (as of 2026-11-09).  
**Scope:** Local-folder source → durable SyncEngine → KnowledgeAccumulator → living KnowledgePackage.  
**Not:** Complete authorization, Studio deployment, or production multi-tenant claims.

## Prerequisites

- Python 3.10+
- `pip install -r requirements.txt`
- Tenant and silo identifiers chosen (required by worker)

## Minimal config file (optional, recommended)

Create `pilot.json`:

```json
{
  "folder": "/path/to/watched/docs",
  "tenant": "acme",
  "silo": "default",
  "db": "/var/okp/sync.db",
  "package": "/var/okp/living-package.json",
  "snapshot": "/var/okp/sync.snapshot.json",
  "poll": 5.0,
  "strict_check": false
}
```

CLI arguments override any value from the file.

## Start the background worker

```bash
python scripts/run_connect_worker.py --config pilot.json
```

Or fully explicit:

```bash
python scripts/run_connect_worker.py \
  --folder /path/to/watched/docs \
  --tenant acme --silo default \
  --db /var/okp/sync.db \
  --package /var/okp/living-package.json
```

Stop with SIGINT/SIGTERM; queue and cursor survive restart.

## Inspect health
Text mode now also surfaces a cursor summary (count + samples) so operators can confirm last successful positions without --json.

```bash
python scripts/connect_health.py --config pilot.json
```

Text output includes status, queue counts, package object count, permissions summary, and lag.  
Exit code 1 on any WARNING (failed events, missing/unreadable package or snapshot, high lag/age, orphaned permissions, snapshot/package count mismatch, unexpected snapshot version, etc.). When failed events are present, text output includes a recovery_hint pointing at connect_recover.py.

JSON:

```bash
python scripts/connect_health.py --config pilot.json --json
```

Production-oriented permission readiness check (warns if any object lacks an explicit permission entry):

```bash
python scripts/connect_health.py --config pilot.json --strict-check
```

## Expected behavior

- Create/update/delete of `.txt`/`.md` under the folder produces SyncEvents.
- Snapshot enables deletion detection after worker restart.
- Package converges after process restart (verified by targeted tests).
- Objects without permission entries remain visible by default (pilot compatibility). Use `--strict-check` or `strict_permissions=True` in retrieval for fail-closed.

## Related

- Permission model: `docs/PERMISSION_MODEL.md`
- Contract: `docs/OKP_Connect_Contract.md`
- Health regressions: `tests/test_connect_health.py`

This guide reduces operator argument repetition and documents the intentional pilot defaults. It does not claim B2B readiness.

## Recover failed events

```bash
python scripts/connect_recover.py --config pilot.json --list
python scripts/connect_recover.py --db /var/okp/sync.db --list
python scripts/connect_recover.py --db /var/okp/sync.db --list --source local_folder

python scripts/connect_recover.py --db /var/okp/sync.db --list --tenant acme --silo default
python scripts/connect_recover.py --db /var/okp/sync.db --list  # now also shows tenant= silo=
python scripts/connect_recover.py --config pilot.json --reset EVENT_ID
python scripts/connect_recover.py --config pilot.json --reset-all
```

After reset, restart the worker (or wait for next poll) to reprocess. Cursors are not advanced by reset. `--config` supplies the db path; `--db` overrides.

JSON recovery output is clean (no mixed text):
```bash
python scripts/connect_recover.py --db /var/okp/sync.db --reset EVENT_ID --json
# {"reset": 1, "ids": ["EVENT_ID"]}
python scripts/connect_recover.py --db /var/okp/sync.db --reset-all --json
```

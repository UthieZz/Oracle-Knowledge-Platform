#!/usr/bin/env python3
"""Minimal durable runner for the local-folder Connect pilot path.

Starts a SyncWorker that polls a LocalFolderConnector and processes events
through KnowledgeAccumulator. The living KnowledgePackage is persisted to
a JSON file so it survives process restarts. Queue and cursor remain in the
SyncEngine SQLite DB. Connector snapshot is also persisted so deletions that
occur while the worker is stopped are detected on restart.

Usage:
  python scripts/run_connect_worker.py \\
    --folder /path/to/watched \\
    --tenant acme \\
    --silo default \\
    --db /path/to/sync.db \\
    --package /path/to/living.json

Ctrl-C stops the worker cleanly. Does not require SSO or new architecture.
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path

# Bootstrap project root so `python scripts/run_connect_worker.py` works without PYTHONPATH
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from okc.connect.knowledge_accumulator import KnowledgeAccumulator
from okc.connect.local_folder_connector import LocalFolderConnector
from okc.connect.sync_engine import SyncEngine
from okc.connect.sync_worker import SyncWorker


def _load_config(path: str | None) -> dict:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"Config not found: {path}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"Invalid config JSON: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run durable local-folder Connect worker")
    parser.add_argument("--config", help="JSON config with folder/tenant/silo/db/package/snapshot/poll (CLI overrides)")
    parser.add_argument("--folder", help="Directory to watch for .txt/.md")
    parser.add_argument("--tenant", help="Tenant id")
    parser.add_argument("--silo", help="Silo id")
    parser.add_argument("--db", help="SQLite path for SyncEngine queue/cursor")
    parser.add_argument("--package", help="JSON path for durable KnowledgePackage")
    parser.add_argument("--snapshot", help="JSON path for connector snapshot (default: <db>.snapshot.json)")
    parser.add_argument("--poll", type=float, help="Poll interval seconds")
    args = parser.parse_args()

    cfg = _load_config(args.config)
    folder = args.folder or cfg.get("folder")
    tenant = args.tenant or cfg.get("tenant")
    silo = args.silo or cfg.get("silo")
    db = args.db or cfg.get("db")
    package = args.package or cfg.get("package")
    if not all([folder, tenant, silo, db, package]):
        raise SystemExit("folder, tenant, silo, db, package required (via CLI or config)")
    poll = args.poll if args.poll is not None else cfg.get("poll", 5.0)
    snapshot_path = args.snapshot or cfg.get("snapshot") or str(Path(db).with_suffix(".snapshot.json"))

    connector = LocalFolderConnector(folder, snapshot_path=snapshot_path)
    if not connector.authenticate({}):
        print("LocalFolderConnector authentication failed", file=sys.stderr)
        sys.exit(1)

    engine = SyncEngine(db)
    accumulator = KnowledgeAccumulator(package_path=package)
    worker = SyncWorker(
        engine,
        connector,
        tenant,
        silo,
        accumulator.process,
        poll_interval=poll,
    )

    stop = False

    def _handle_sig(_sig, _frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _handle_sig)
    signal.signal(signal.SIGTERM, _handle_sig)

    worker.start()
    print(
        f"Connect worker running: folder={folder} tenant={tenant} "
        f"silo={silo} db={db} package={package} snapshot={snapshot_path}"
    )
    try:
        while not stop:
            time.sleep(0.5)
    finally:
        worker.stop()
        print("Worker stopped. Package and snapshot persisted.")


if __name__ == "__main__":
    main()

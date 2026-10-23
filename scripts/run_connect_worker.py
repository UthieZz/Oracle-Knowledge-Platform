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
import signal
import sys
import time
from pathlib import Path

from okc.connect.knowledge_accumulator import KnowledgeAccumulator
from okc.connect.local_folder_connector import LocalFolderConnector
from okc.connect.sync_engine import SyncEngine
from okc.connect.sync_worker import SyncWorker


def main() -> None:
    parser = argparse.ArgumentParser(description="Run durable local-folder Connect worker")
    parser.add_argument("--folder", required=True, help="Directory to watch for .txt/.md")
    parser.add_argument("--tenant", required=True, help="Tenant id")
    parser.add_argument("--silo", required=True, help="Silo id")
    parser.add_argument("--db", required=True, help="SQLite path for SyncEngine queue/cursor")
    parser.add_argument("--package", required=True, help="JSON path for durable KnowledgePackage")
    parser.add_argument("--snapshot", help="JSON path for connector snapshot (default: <db>.snapshot.json)")
    parser.add_argument("--poll", type=float, default=5.0, help="Poll interval seconds")
    args = parser.parse_args()

    snapshot_path = args.snapshot or str(Path(args.db).with_suffix(".snapshot.json"))

    connector = LocalFolderConnector(args.folder, snapshot_path=snapshot_path)
    if not connector.authenticate({}):
        print("LocalFolderConnector authentication failed", file=sys.stderr)
        sys.exit(1)

    engine = SyncEngine(args.db)
    accumulator = KnowledgeAccumulator(package_path=args.package)
    worker = SyncWorker(
        engine,
        connector,
        args.tenant,
        args.silo,
        accumulator.process,
        poll_interval=args.poll,
    )

    stop = False

    def _handle_sig(_sig, _frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _handle_sig)
    signal.signal(signal.SIGTERM, _handle_sig)

    worker.start()
    print(
        f"Connect worker running: folder={args.folder} tenant={args.tenant} "
        f"silo={args.silo} db={args.db} package={args.package} snapshot={snapshot_path}"
    )
    try:
        while not stop:
            time.sleep(0.5)
    finally:
        worker.stop()
        print("Worker stopped. Package and snapshot persisted.")


if __name__ == "__main__":
    main()

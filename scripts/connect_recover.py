#!/usr/bin/env python3
"""Connect recovery CLI for the local-folder pilot.

Lists failed events and optionally resets one or all for manual recovery.
Does not advance cursors; reprocessing is the caller's responsibility via the worker.

Supports --config JSON (same schema as health/worker) for db path. CLI overrides config.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from okc.connect.sync_engine import SyncEngine


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
    parser = argparse.ArgumentParser(description="OKP Connect failed-event recovery")
    parser.add_argument("--config", help="JSON config file with db (CLI overrides)")
    parser.add_argument("--db", help="Path to SyncEngine SQLite DB")
    parser.add_argument("--list", action="store_true", help="List failed event details")
    parser.add_argument("--source", help="When listing, only show events from this source")
    parser.add_argument("--reset", help="Reset a specific failed event_id to queued")
    parser.add_argument("--reset-all", action="store_true", help="Reset all failed events to queued")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    cfg = _load_config(args.config)
    db = args.db or cfg.get("db")
    if not db:
        raise SystemExit("--db or config.db is required")

    engine = SyncEngine(db)
    details = engine.list_failed_details()
    if args.source:
        details = [d for d in details if d.get("source") == args.source]

    if args.list or (not args.reset and not args.reset_all):
        if args.json:
            print(json.dumps(details, indent=2))
        else:
            if not details:
                print("No failed events.")
            else:
                for d in details:
                    print(f"{d['event_id']}\tsource={d.get('source','')}\tkind={d.get('kind','')}\tattempts={d['attempts']}\tenqueued={d.get('enqueued_at','')}\terror={d['last_error']}")
        if not args.reset and not args.reset_all:
            return

    reset_count = 0
    if args.reset:
        if engine.reset_failed(args.reset):
            reset_count += 1
            print(f"Reset {args.reset}")
        else:
            print(f"Not found or not failed: {args.reset}", file=sys.stderr)
            sys.exit(1)
    if args.reset_all:
        for d in details:
            if engine.reset_failed(d["event_id"]):
                reset_count += 1
        print(f"Reset {reset_count} events")

    if args.json and (args.reset or args.reset_all):
        print(json.dumps({"reset": reset_count}, indent=2))


if __name__ == "__main__":
    main()

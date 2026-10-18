#!/usr/bin/env python3
"""Minimal operator health view for OKP Connect.

Prints SyncEngine.health() (and optionally SyncWorker.health() if a running
worker is not available in this process). Does not mutate state.
Usage: python scripts/connect_health.py /path/to/sync.db
"""
import sys
from okc.connect.sync_engine import SyncEngine

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/connect_health.py <db_path>", file=sys.stderr)
        sys.exit(2)
    db = sys.argv[1]
    eng = SyncEngine(db)
    h = eng.health()
    print(f"queued={h['queued']} processed={h['processed']} failed_or_stuck={h['failed_or_stuck']} db={h['db_path']}")

if __name__ == "__main__":
    main()

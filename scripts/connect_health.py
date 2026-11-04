#!/usr/bin/env python3
"""Minimal operator health view for OKP Connect.

Prints SyncEngine.health() and, if a package path is supplied, basic
living-KnowledgePackage freshness (exists, mtime, object count).
Does not mutate state.

Usage:
  python scripts/connect_health.py <db_path> [package_json_path]
"""
import sys
from pathlib import Path

from okc.connect.sync_engine import SyncEngine
from okc.models.knowledge_package import KnowledgePackage


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/connect_health.py <db_path> [package_json_path]", file=sys.stderr)
        sys.exit(2)
    db = sys.argv[1]
    eng = SyncEngine(db)
    h = eng.health()
    age = h.get("oldest_queued_age_seconds")
    age_s = f"{age:.0f}s" if age is not None else "none"
    last_p = h.get("last_processed_at") or "none"
    print(
        f"queued={h['queued']} processed={h['processed']} failed={h.get('failed', 0)} "
        f"failed_or_stuck={h['failed_or_stuck']} oldest_queued={age_s} last_processed={last_p} db={h['db_path']}"
    )
    if h.get("failed", 0) > 0:
        details = eng.list_failed_details()
        for d in details[:5]:  # limit output
            err = (d.get("last_error") or "")[:120]
            print(f"  failed event={d['event_id']} attempts={d['attempts']} error={err}")
        if len(details) > 5:
            print(f"  ... and {len(details)-5} more failed")

    if len(sys.argv) >= 3:
        pkg_path = Path(sys.argv[2])
        if not pkg_path.exists():
            print(f"package=MISSING path={pkg_path}")
        else:
            try:
                pkg = KnowledgePackage.from_json(pkg_path.read_text(encoding="utf-8"))
                mtime = pkg_path.stat().st_mtime
                print(f"package=OK objects={len(pkg.objects)} mtime={mtime:.0f} path={pkg_path}")
            except Exception as exc:
                print(f"package=UNREADABLE error={exc} path={pkg_path}")


if __name__ == "__main__":
    main()

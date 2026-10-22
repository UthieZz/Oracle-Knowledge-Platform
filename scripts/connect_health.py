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
    print(f"queued={h['queued']} processed={h['processed']} failed_or_stuck={h['failed_or_stuck']} db={h['db_path']}")

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

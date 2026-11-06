#!/usr/bin/env python3
"""Minimal operator health view for OKP Connect.

Prints SyncEngine.health() and, if a package path is supplied, basic
living-KnowledgePackage freshness (exists, mtime, object count).
Optionally reports connector snapshot status (existence, version, sequence,
tracked file count, mtime) when a snapshot path is provided.
Does not mutate state.

Usage:
  python scripts/connect_health.py <db_path> [package_json_path] [snapshot_json_path]
"""
import json
import sys
from pathlib import Path

from okc.connect.sync_engine import SyncEngine
from okc.models.knowledge_package import KnowledgePackage


def _report_snapshot(snap_path: Path) -> None:
    if not snap_path.exists():
        print(f"snapshot=MISSING path={snap_path}")
        return
    try:
        raw = json.loads(snap_path.read_text(encoding="utf-8"))
        mtime = snap_path.stat().st_mtime
        if isinstance(raw, dict) and "version" in raw and "seq" in raw and "snapshot" in raw:
            tracked = len(raw.get("snapshot") or {})
            print(
                f"snapshot=OK version={raw.get('version')} seq={raw.get('seq')} "
                f"tracked={tracked} mtime={mtime:.0f} path={snap_path}"
            )
        elif isinstance(raw, dict):
            tracked = len(raw)
            print(f"snapshot=LEGACY tracked={tracked} mtime={mtime:.0f} path={snap_path}")
        else:
            print(f"snapshot=UNREADABLE reason=unexpected_type path={snap_path}")
    except Exception as exc:
        print(f"snapshot=UNREADABLE error={exc} path={snap_path}")


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: python scripts/connect_health.py <db_path> [package_json_path] [snapshot_json_path]",
            file=sys.stderr,
        )
        sys.exit(2)
    db = sys.argv[1]
    eng = SyncEngine(db)
    h = eng.health()
    age = h.get("oldest_queued_age_seconds")
    age_s = f"{age:.0f}s" if age is not None else "none"
    last_p = h.get("last_processed_at") or "none"
    ready = h.get("ready_to_process", h["queued"])
    waiting = h.get("waiting_for_retry", 0)
    print(
        f"queued={h['queued']} ready={ready} waiting_retry={waiting} processed={h['processed']} failed={h.get('failed', 0)} "
        f"failed_or_stuck={h['failed_or_stuck']} oldest_queued={age_s} last_processed={last_p} db={h['db_path']}"
    )
    if h.get("failed", 0) > 0:
        details = eng.list_failed_details()
        for d in details[:5]:  # limit output
            err = (d.get("last_error") or "")[:120]
            print(f"  failed event={d['event_id']} attempts={d['attempts']} error={err}")
        if len(details) > 5:
            print(f"  ... and {len(details)-5} more failed")

    cursors = eng.list_cursors()
    if cursors:
        print(f"cursors={len(cursors)}")
        for c in cursors[:10]:  # limit for readability
            print(
                f"  cursor source={c['source']} tenant={c['tenant_id']} silo={c['silo_id']} "
                f"cursor={c['cursor'] or 'none'} updated={c['updated_at'] or 'none'}"
            )
        if len(cursors) > 10:
            print(f"  ... and {len(cursors)-10} more cursors")
    else:
        print("cursors=0")

    if len(sys.argv) >= 3:
        pkg_path = Path(sys.argv[2])
        if not pkg_path.exists():
            print(f"package=MISSING path={pkg_path}")
        else:
            try:
                pkg = KnowledgePackage.from_json(pkg_path.read_text(encoding="utf-8"))
                mtime = pkg_path.stat().st_mtime
                actual = len(pkg.objects)
                meta_count = pkg.metadata.get("object_count")
                consistent = "consistent" if meta_count == actual else f"MISMATCH meta={meta_count}"
                perms = pkg.metadata.get("permissions", {})
                perm_count = len(perms) if isinstance(perms, dict) else 0
                read_false = sum(
                    1 for v in (perms.values() if isinstance(perms, dict) else [])
                    if isinstance(v, dict) and v.get("read") is False
                )
                print(
                    f"package=OK objects={actual} meta_object_count={meta_count} {consistent} "
                    f"permissions_entries={perm_count} explicit_read_false={read_false} "
                    f"mtime={mtime:.0f} path={pkg_path}"
                )
            except Exception as exc:
                print(f"package=UNREADABLE error={exc} path={pkg_path}")

    if len(sys.argv) >= 4:
        _report_snapshot(Path(sys.argv[3]))

    # Operator summary line for quick status
    status = "OK"
    reasons = []
    if h.get("failed", 0) > 0:
        status = "WARNING"
        reasons.append(f"failed={h.get('failed')}")
    if len(sys.argv) >= 3 and not Path(sys.argv[2]).exists():
        status = "WARNING"
        reasons.append("package_missing")
    if len(sys.argv) >= 4 and not Path(sys.argv[3]).exists():
        status = "WARNING"
        reasons.append("snapshot_missing")
    reason_s = " (" + ",".join(reasons) + ")" if reasons else ""
    print(f"status={status}{reason_s}")


if __name__ == "__main__":
    main()

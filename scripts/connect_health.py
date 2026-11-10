#!/usr/bin/env python3
"""Connect health CLI for the local-folder pilot.

Reports SyncEngine queue state, package consistency, snapshot presence,
and operator warnings. Exit code 1 on any WARNING so monitoring can alert.

Supports --json for structured machine-readable output.

Does not mutate KnowledgePackage or Connect state.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Bootstrap project root so `python scripts/connect_health.py` works without PYTHONPATH
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from okc.connect.sync_engine import SyncEngine
from okc.models.knowledge_package import KnowledgePackage


def _package_info(package_path: str | None) -> dict:
    info = {"exists": False, "object_count": None, "mtime": None, "readable": False, "error": None}
    if not package_path:
        return info
    p = Path(package_path)
    info["exists"] = p.exists()
    if not info["exists"]:
        return info
    try:
        info["mtime"] = p.stat().st_mtime
        pkg = KnowledgePackage.from_json(p.read_text(encoding="utf-8"))
        info["object_count"] = len(pkg.objects)
        info["readable"] = True
        perms = pkg.metadata.get("permissions") or {}
        info["permissions_entries"] = len(perms)
        info["explicit_read_false"] = sum(
            1 for v in perms.values()
            if isinstance(v, dict) and v.get("read") is False
        )
        # Provenance completeness for recorded permission decisions.
        with_prov = sum(
            1 for v in perms.values()
            if isinstance(v, dict) and v.get("recorded_from_event")
        )
        info["permissions_with_event_provenance"] = with_prov
        info["permissions_missing_event_provenance"] = info["permissions_entries"] - with_prov
        # Count objects that have a src: marker but no matching permission entry.
        # Useful for operators deciding when to enable strict_permissions.
        missing = 0
        for obj in pkg.objects:
            src_ids = [rid[4:] for rid in (obj.provenance.source_record_ids or []) if rid.startswith("src:")]
            if src_ids and not any(sid in perms for sid in src_ids):
                missing += 1
        info["objects_without_explicit_permission"] = missing
        # Orphaned permission entries: keys that do not match any living object src id.
        # Helps operators detect incomplete cleanup or external corruption.
        living_src_ids = set()
        for obj in pkg.objects:
            for rid in (obj.provenance.source_record_ids or []):
                if rid.startswith("src:"):
                    living_src_ids.add(rid[4:])
        orphaned = sum(1 for k in perms if k not in living_src_ids)
        info["orphaned_permission_entries"] = orphaned
        info["last_source"] = pkg.metadata.get("last_source")
    except Exception as exc:  # noqa: BLE001
        info["error"] = str(exc)[:200]
        info["readable"] = False
    return info


def _snapshot_info(snapshot_path: str | None) -> dict:
    info = {"exists": False, "readable": False, "error": None, "version": None, "seq": None, "tracked_files": None}
    if not snapshot_path:
        return info
    p = Path(snapshot_path)
    info["exists"] = p.exists()
    if not info["exists"]:
        return info
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        info["readable"] = isinstance(data, dict)
        if info["readable"]:
            info["version"] = data.get("version")
            info["seq"] = data.get("seq")
            snap_map = data.get("snapshot")
            if isinstance(snap_map, dict):
                info["tracked_files"] = len(snap_map)
            else:
                info["tracked_files"] = 0
    except Exception as exc:  # noqa: BLE001
        info["error"] = str(exc)[:200]
        info["readable"] = False
    return info


def _package_lag(engine_health: dict, package_info: dict) -> float | None:
    """Positive lag means last processed advanced without matching package persist."""
    last = engine_health.get("last_processed_at")
    mtime = package_info.get("mtime")
    if not last or mtime is None:
        return None
    try:
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        # package mtime is epoch seconds
        pkg_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
        return (last_dt - pkg_dt).total_seconds()
    except Exception:
        return None


def collect_health(db_path: str, package_path: str | None = None, snapshot_path: str | None = None, strict_check: bool = False) -> dict:
    engine = SyncEngine(db_path)
    h = engine.health()
    pkg = _package_info(package_path)
    snap = _snapshot_info(snapshot_path)
    lag = _package_lag(h, pkg)

    reasons = []
    status = "OK"

    if h.get("failed", 0) > 0:
        reasons.append("failed_events")
        status = "WARNING"
    if package_path and not pkg["exists"]:
        reasons.append("package_missing")
        status = "WARNING"
    if package_path and pkg["exists"] and not pkg["readable"]:
        reasons.append("package_unreadable")
        status = "WARNING"
    if snapshot_path and not snap["exists"]:
        reasons.append("snapshot_missing")
        status = "WARNING"
    if snapshot_path and snap["exists"] and not snap["readable"]:
        reasons.append("snapshot_unreadable")
        status = "WARNING"
    # Snapshot format version: connector writes integer 1; other values indicate
    # legacy/flat or corrupted state that may lose sequence on restart.
    if snapshot_path and snap.get("readable") and snap.get("version") != 1:
        reasons.append("snapshot_version_unexpected")
        status = "WARNING"
    oldest = h.get("oldest_queued_age_seconds") or 0
    if oldest > 600:
        reasons.append("queue_age_high")
        status = "WARNING"
    if lag is not None and lag > 300:
        reasons.append("package_lag_high")
        status = "WARNING"
    waiting = h.get("waiting_for_retry", 0)
    if waiting > 5:
        reasons.append("waiting_retry_high")
        status = "WARNING"
    if h.get("queued", 0) > 0 and h.get("ready_to_process", 0) == 0:
        reasons.append("no_ready_events")
        status = "WARNING"

    # Strict production readiness: missing explicit permission is a gap
    if strict_check and pkg.get("readable") and pkg.get("objects_without_explicit_permission", 0) > 0:
        reasons.append("objects_without_explicit_permission")
        status = "WARNING"

    # object count consistency (metadata vs actual)
    if pkg.get("readable") and package_path:
        meta_count = None
        try:
            raw = json.loads(Path(package_path).read_text(encoding="utf-8"))
            meta_count = raw.get("metadata", {}).get("object_count")
        except Exception:
            pass
        if meta_count is not None and meta_count != pkg["object_count"]:
            reasons.append("object_count_mismatch")
            status = "WARNING"

    # orphaned permission entries indicate incomplete cleanup or corruption
    if pkg.get("readable") and pkg.get("orphaned_permission_entries", 0) > 0:
        reasons.append("orphaned_permission_entries")
        status = "WARNING"

    # snapshot tracked files vs package objects (both must be readable)
    if (
        snapshot_path
        and snap.get("readable")
        and pkg.get("readable")
        and snap.get("tracked_files") is not None
        and snap["tracked_files"] != pkg["object_count"]
    ):
        reasons.append("snapshot_package_count_mismatch")
        status = "WARNING"

    summary = {
        "status": status,
        "reasons": reasons,
        "queued": h.get("queued"),
        "processed": h.get("processed"),
        "failed": h.get("failed"),
        "ready_to_process": h.get("ready_to_process"),
        "waiting_for_retry": h.get("waiting_for_retry"),
        "oldest_queued_age_seconds": h.get("oldest_queued_age_seconds"),
        "last_processed_at": h.get("last_processed_at"),
        "package_lag_seconds": lag,
        "package": pkg,
        "snapshot": snap,
        "cursors": engine.list_cursors(),
        "failed_details": engine.list_failed_details() if h.get("failed") else [],
        "db_path": db_path,
    }
    return summary


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
    parser = argparse.ArgumentParser(description="OKP Connect health inspector")
    parser.add_argument("--config", help="JSON config file with db/package/snapshot/strict_check (CLI overrides)")
    parser.add_argument("--db", help="Path to SyncEngine SQLite DB")
    parser.add_argument("--package", help="Path to living KnowledgePackage JSON")
    parser.add_argument("--snapshot", help="Path to connector snapshot JSON")
    parser.add_argument("--json", action="store_true", help="Emit single JSON summary instead of text")
    parser.add_argument("--strict-check", action="store_true", help="Treat objects without explicit permission as WARNING (for production readiness check)")
    args = parser.parse_args()

    cfg = _load_config(args.config)
    db = args.db or cfg.get("db")
    if not db:
        raise SystemExit("--db or config.db is required")
    package = args.package or cfg.get("package")
    snapshot = args.snapshot or cfg.get("snapshot")
    strict = args.strict_check or bool(cfg.get("strict_check"))

    summary = collect_health(db, package, snapshot, strict_check=strict)

    if args.json:
        print(json.dumps(summary, default=str, indent=2))
    else:
        print(f"status={summary['status']}")
        if summary["reasons"]:
            print(f"reasons={','.join(summary['reasons'])}")
        print(f"queued={summary['queued']} processed={summary['processed']} failed={summary['failed']}")
        print(f"ready_to_process={summary['ready_to_process']} waiting_for_retry={summary['waiting_for_retry']}")
        print(f"oldest_queued_age_seconds={summary['oldest_queued_age_seconds']}")
        print(f"last_processed_at={summary['last_processed_at']}")
        print(f"package_lag_seconds={summary['package_lag_seconds']}")
        if package:
            pkg = summary['package']
            print(f"package_exists={pkg['exists']} readable={pkg['readable']} object_count={pkg['object_count']}")
            if pkg.get('readable'):
                print(f"permissions_entries={pkg.get('permissions_entries', 0)} explicit_read_false={pkg.get('explicit_read_false', 0)} objects_without_explicit_permission={pkg.get('objects_without_explicit_permission', 0)} permissions_with_event_provenance={pkg.get('permissions_with_event_provenance', 0)} permissions_missing_event_provenance={pkg.get('permissions_missing_event_provenance', 0)} orphaned_permission_entries={pkg.get('orphaned_permission_entries', 0)}")
        if snapshot:
            snap = summary['snapshot']
            print(f"snapshot_exists={snap['exists']} readable={snap['readable']}")
            if snap.get('readable') and snap.get('seq') is not None:
                print(f"snapshot_seq={snap['seq']} version={snap.get('version')} tracked_files={snap.get('tracked_files')}")
        cursors = summary.get("cursors") or []
        if cursors:
            print(f"cursors={len(cursors)}")
            for c in cursors[:3]:
                print(f"  cursor source={c.get('source')} tenant={c.get('tenant_id')} silo={c.get('silo_id')} cursor={c.get('cursor')}")
            if len(cursors) > 3:
                print(f"  ... and {len(cursors)-3} more")

        # Operator recovery hint when failed events exist (P3 usability)
        if summary.get("failed", 0) > 0:
            db_display = summary.get("db_path", "<db>")
            print(f"recovery_hint=python scripts/connect_recover.py --db {db_display} --list")
            print("  (or --config if using shared config; --reset / --reset-all to recover)")

    if summary["status"] == "WARNING":
        sys.exit(1)


if __name__ == "__main__":
    main()

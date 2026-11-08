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
        # Count objects that have a src: marker but no matching permission entry.
        # Useful for operators deciding when to enable strict_permissions.
        missing = 0
        for obj in pkg.objects:
            src_ids = [rid[4:] for rid in (obj.provenance.source_record_ids or []) if rid.startswith("src:")]
            if src_ids and not any(sid in perms for sid in src_ids):
                missing += 1
        info["objects_without_explicit_permission"] = missing
        info["last_source"] = pkg.metadata.get("last_source")
    except Exception as exc:  # noqa: BLE001
        info["error"] = str(exc)[:200]
        info["readable"] = False
    return info


def _snapshot_info(snapshot_path: str | None) -> dict:
    info = {"exists": False, "readable": False, "error": None}
    if not snapshot_path:
        return info
    p = Path(snapshot_path)
    info["exists"] = p.exists()
    if not info["exists"]:
        return info
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        info["readable"] = isinstance(data, dict)
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
                print(f"permissions_entries={pkg.get('permissions_entries', 0)} explicit_read_false={pkg.get('explicit_read_false', 0)} objects_without_explicit_permission={pkg.get('objects_without_explicit_permission', 0)}")
        if snapshot:
            print(f"snapshot_exists={summary['snapshot']['exists']} readable={summary['snapshot']['readable']}")

        # Operator recovery hint when failed events exist (P3 usability)
        if summary.get("failed", 0) > 0:
            db_display = summary.get("db_path", "<db>")
            print(f"recovery_hint=python scripts/connect_recover.py --db {db_display} --list")
            print("  (or --config if using shared config; --reset / --reset-all to recover)")

    if summary["status"] == "WARNING":
        sys.exit(1)


if __name__ == "__main__":
    main()

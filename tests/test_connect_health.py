"""Regressions for scripts/connect_health.py operator diagnostics.

Covers status=WARNING exit-1 behavior and --json structured output.
Knowledge Core IR unchanged.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Ensure project root on path for okc imports when running tests
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _run_health(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "connect_health.py"), *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def test_connect_health_ok_empty_db(tmp_path: Path):
    db = tmp_path / "sync.db"
    # Create empty engine DB via import
    from okc.connect.sync_engine import SyncEngine
    SyncEngine(str(db))

    r = _run_health("--db", str(db))
    assert r.returncode == 0
    assert "status=OK" in r.stdout


def test_connect_health_json_mode(tmp_path: Path):
    db = tmp_path / "sync.db"
    from okc.connect.sync_engine import SyncEngine
    SyncEngine(str(db))

    r = _run_health("--db", str(db), "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["status"] == "OK"
    assert "queued" in data
    assert "reasons" in data


def test_connect_health_warns_on_missing_package(tmp_path: Path):
    db = tmp_path / "sync.db"
    from okc.connect.sync_engine import SyncEngine
    SyncEngine(str(db))

    r = _run_health("--db", str(db), "--package", str(tmp_path / "missing.json"))
    assert r.returncode == 1
    assert "status=WARNING" in r.stdout
    assert "package_missing" in r.stdout


def test_connect_health_json_warning(tmp_path: Path):
    db = tmp_path / "sync.db"
    from okc.connect.sync_engine import SyncEngine
    SyncEngine(str(db))

    r = _run_health("--db", str(db), "--package", str(tmp_path / "missing.json"), "--json")
    assert r.returncode == 1
    data = json.loads(r.stdout)
    assert data["status"] == "WARNING"
    assert "package_missing" in data["reasons"]


def test_connect_health_warns_on_missing_snapshot(tmp_path: Path):
    db = tmp_path / "sync.db"
    from okc.connect.sync_engine import SyncEngine
    SyncEngine(str(db))

    r = _run_health("--db", str(db), "--snapshot", str(tmp_path / "missing.snapshot.json"))
    assert r.returncode == 1
    assert "status=WARNING" in r.stdout
    assert "snapshot_missing" in r.stdout


def test_connect_health_warns_on_unreadable_package(tmp_path: Path):
    db = tmp_path / "sync.db"
    from okc.connect.sync_engine import SyncEngine
    SyncEngine(str(db))
    bad = tmp_path / "bad.json"
    bad.write_text("not-json", encoding="utf-8")

    r = _run_health("--db", str(db), "--package", str(bad))
    assert r.returncode == 1
    assert "status=WARNING" in r.stdout
    assert "package_unreadable" in r.stdout


def test_connect_health_warns_on_failed_events(tmp_path: Path):
    db = tmp_path / "sync.db"
    from okc.connect.sync_engine import SyncEngine
    engine = SyncEngine(str(db))
    # Insert a failed event directly
    with engine._conn() as conn:
        conn.execute(
            """
            INSERT INTO events (event_id, source, kind, payload, tenant_id, silo_id, status, attempts, enqueued_at)
            VALUES (?, ?, ?, ?, ?, ?, 'failed', 1, ?)
            """,
            ("evt-failed", "local", "create", "{}", "t", "s", "2026-01-01T00:00:00+00:00"),
        )

    r = _run_health("--db", str(db))
    assert r.returncode == 1
    assert "status=WARNING" in r.stdout
    assert "failed_events" in r.stdout


def test_connect_health_reports_objects_without_explicit_permission(tmp_path: Path):
    """Operator visibility: count objects that have src markers but no permission entry.
    Advances P1/P3 by making the pilot vs strict_permissions gap inspectable.
    """
    from okc.connect.knowledge_accumulator import KnowledgeAccumulator
    from okc.connect.sync_engine import SyncEngine
    from okc.models.knowledge_package import KnowledgePackage

    db = tmp_path / "sync.db"
    pkg_path = tmp_path / "pkg.json"
    SyncEngine(str(db))

    # Minimal package with one object lacking a permission entry
    from okc.models.knowledge_package import KnowledgeObject, Provenance
    obj = KnowledgeObject(
        object_id="obj1",
        title="t",
        content="c",
        provenance=Provenance(
            source_platform="local",
            source_file="file1",
            tenant_id="t1",
            silo_id="s1",
            source_record_ids=["src:local|t1|s1|file1"],
        ),
    )
    pkg = KnowledgePackage(package_id="pkg1", objects=[obj], metadata={"permissions": {}})
    pkg_path.write_text(pkg.to_json(), encoding="utf-8")

    r = _run_health("--db", str(db), "--package", str(pkg_path), "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["package"]["objects_without_explicit_permission"] == 1
    assert data["package"]["permissions_entries"] == 0


def test_connect_health_strict_check_warns_on_missing_permission(tmp_path: Path):
    """--strict-check elevates objects_without_explicit_permission to WARNING.
    Default (no flag) remains OK so pilot behavior is unchanged.
    """
    from okc.connect.knowledge_accumulator import KnowledgeAccumulator
    from okc.connect.sync_engine import SyncEngine
    from okc.connect.interfaces import SyncEvent

    db = tmp_path / "sync.db"
    pkg = tmp_path / "pkg.json"
    SyncEngine(str(db))
    acc = KnowledgeAccumulator(package_path=str(pkg))
    # Create an object with no permission entry
    event = SyncEvent(
        event_id="e1",
        source="local",
        kind="create",
        payload={"object_id": "doc1", "text": "hello visible"},
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(event)

    # Default: OK
    r = _run_health("--db", str(db), "--package", str(pkg))
    assert r.returncode == 0
    assert "status=OK" in r.stdout
    assert "objects_without_explicit_permission=1" in r.stdout

    # With --strict-check: WARNING
    r2 = _run_health("--db", str(db), "--package", str(pkg), "--strict-check")
    assert r2.returncode == 1
    assert "status=WARNING" in r2.stdout
    assert "objects_without_explicit_permission" in r2.stdout


def test_connect_health_warns_on_object_count_mismatch(tmp_path: Path):
    """Metadata object_count must match actual objects; mismatch is operator WARNING.
    Prevents silent inconsistency after interrupted persists or manual edits.
    """
    from okc.connect.knowledge_accumulator import KnowledgeAccumulator
    from okc.connect.sync_engine import SyncEngine
    from okc.connect.interfaces import SyncEvent
    import json

    db = tmp_path / "sync.db"
    pkg = tmp_path / "pkg.json"
    SyncEngine(str(db))
    acc = KnowledgeAccumulator(package_path=str(pkg))
    event = SyncEvent(
        event_id="e1",
        source="local",
        kind="create",
        payload={"object_id": "doc1", "text": "content"},
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(event)

    # Corrupt metadata object_count while leaving actual objects unchanged
    raw = json.loads(pkg.read_text(encoding="utf-8"))
    raw["metadata"]["object_count"] = 999
    pkg.write_text(json.dumps(raw), encoding="utf-8")

    r = _run_health("--db", str(db), "--package", str(pkg))
    assert r.returncode == 1
    assert "status=WARNING" in r.stdout
    assert "object_count_mismatch" in r.stdout


def test_connect_health_warns_on_unreadable_snapshot(tmp_path: Path):
    """Unreadable snapshot JSON is an operator WARNING.
    Prevents silent reliance on a corrupted restart snapshot.
    """
    db = tmp_path / "sync.db"
    from okc.connect.sync_engine import SyncEngine
    SyncEngine(str(db))
    bad = tmp_path / "bad.snapshot.json"
    bad.write_text("not-json", encoding="utf-8")

    r = _run_health("--db", str(db), "--snapshot", str(bad))
    assert r.returncode == 1
    assert "status=WARNING" in r.stdout
    assert "snapshot_unreadable" in r.stdout


def test_connect_health_accepts_config_file(tmp_path):
    """Config file supplies db/package; CLI can override."""
    db = tmp_path / "sync.db"
    pkg = tmp_path / "pkg.json"
    cfg = tmp_path / "config.json"
    # Minimal valid package
    pkg.write_text('{"schema_version":"2.0.0","package_id":"test-pkg","objects":[],"metadata":{}}')
    cfg.write_text(json.dumps({"db": str(db), "package": str(pkg)}))
    # Empty DB will be created by SyncEngine on use; health should run
    from okc.connect.sync_engine import SyncEngine
    SyncEngine(str(db))  # create empty
    r = subprocess.run(
        [sys.executable, "scripts/connect_health.py", "--config", str(cfg), "--json"],
        capture_output=True, text=True, cwd=Path(__file__).parents[1]
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["status"] in ("OK", "WARNING")
    assert data["db_path"] == str(db)


def test_connect_health_text_output_uses_config_package(tmp_path: Path):
    """Text mode reports package details when package comes from --config, not only CLI flag."""
    db = tmp_path / "sync.db"
    pkg = tmp_path / "pkg.json"
    cfg = tmp_path / "config.json"
    pkg.write_text('{"schema_version":"2.0.0","package_id":"test-pkg","objects":[],"metadata":{}}')
    cfg.write_text(json.dumps({"db": str(db), "package": str(pkg)}))
    from okc.connect.sync_engine import SyncEngine
    SyncEngine(str(db))

    r = _run_health("--config", str(cfg))
    assert r.returncode == 0, r.stderr
    assert "status=OK" in r.stdout
    assert "package_exists=True" in r.stdout
    assert "object_count=0" in r.stdout


def test_connect_health_emits_recovery_hint_on_failed(tmp_path: Path):
    """When failed events exist, text health output includes an actionable recovery hint."""
    db = tmp_path / "sync.db"
    from okc.connect.sync_engine import SyncEngine
    engine = SyncEngine(str(db))
    with engine._conn() as conn:
        conn.execute(
            """
            INSERT INTO events (event_id, source, kind, payload, tenant_id, silo_id, status, attempts, enqueued_at)
            VALUES (?, ?, ?, ?, ?, ?, 'failed', 5, ?)
            """,
            ("evt-failed", "local", "create", "{}", "t", "s", "2026-01-01T00:00:00+00:00"),
        )

    r = _run_health("--db", str(db))
    assert r.returncode == 1
    assert "status=WARNING" in r.stdout
    assert "failed_events" in r.stdout
    assert "recovery_hint=" in r.stdout
    assert "connect_recover.py" in r.stdout
    assert str(db) in r.stdout


def test_connect_health_text_shows_cursors(tmp_path: Path):
    """Text output surfaces cursor count and sample so operators can verify sync progress without --json or DB inspection."""
    db = tmp_path / "sync.db"
    from okc.connect.sync_engine import SyncEngine
    engine = SyncEngine(str(db))
    # Advance a cursor via the public path (simulate successful processing)
    with engine._conn() as conn:
        conn.execute(
            "INSERT INTO cursors (source, tenant_id, silo_id, cursor, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("local-folder", "acme", "default", "file:readme.md", "2026-01-01T00:00:00+00:00"),
        )

    r = _run_health("--db", str(db))
    assert r.returncode == 0
    assert "status=OK" in r.stdout
    assert "cursors=1" in r.stdout
    assert "source=local-folder" in r.stdout
    assert "tenant=acme" in r.stdout
    assert "cursor=file:readme.md" in r.stdout


def test_connect_health_text_shows_snapshot_seq(tmp_path: Path):
    """Text output surfaces snapshot sequence and version for restart-recovery diagnostics."""
    db = tmp_path / "sync.db"
    from okc.connect.sync_engine import SyncEngine
    SyncEngine(str(db))
    snap = tmp_path / "sync.snapshot.json"
    snap.write_text(json.dumps({"version": 1, "seq": 42, "snapshot": {}}), encoding="utf-8")

    r = _run_health("--db", str(db), "--snapshot", str(snap))
    assert r.returncode == 0
    assert "status=OK" in r.stdout
    assert "snapshot_exists=True" in r.stdout
    assert "snapshot_seq=42" in r.stdout
    assert "version=1" in r.stdout


def test_connect_health_reports_permission_event_provenance(tmp_path: Path):
    """Health text/JSON reports how many permission entries carry recorded_from_event provenance."""
    db = tmp_path / "sync.db"
    from okc.connect.sync_engine import SyncEngine
    SyncEngine(str(db))
    pkg_path = tmp_path / "package.json"
    from okc.models.knowledge_package import KnowledgePackage
    pkg = KnowledgePackage(
        package_id="health-prov-test",
        schema_version="2.0",
        objects=[],
        metadata={
            "permissions": {
                "src:with-prov": {"read": True, "recorded_from_event": "evt-1", "recorded_at": "2026-01-01T00:00:00Z"},
                "src:without": {"read": False},
            }
        },
    )
    pkg_path.write_text(pkg.model_dump_json(), encoding="utf-8")

    r = _run_health("--db", str(db), "--package", str(pkg_path))
    assert r.returncode == 0
    assert "permissions_with_event_provenance=1" in r.stdout
    assert "permissions_entries=2" in r.stdout

    r_json = _run_health("--db", str(db), "--package", str(pkg_path), "--json")
    data = json.loads(r_json.stdout)
    assert data["package"]["permissions_with_event_provenance"] == 1
    assert data["package"]["permissions_entries"] == 2

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

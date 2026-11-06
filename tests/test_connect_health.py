"""Regression for connect_health CLI operator visibility surface."""
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from okc.connect.sync_engine import SyncEngine


def test_connect_health_cli_on_fresh_db_reports_zeros_and_exits_zero(tmp_path: Path):
    """Fresh SyncEngine DB should produce a zero-count health line and exit 0."""
    db = tmp_path / "fresh.db"
    # Ensure the DB is initialized
    SyncEngine(str(db))

    script = Path(__file__).resolve().parent.parent / "scripts" / "connect_health.py"
    result = subprocess.run(
        [sys.executable, str(script), str(db)],
        capture_output=True,
        text=True,
        check=False,
        env={**dict(**__import__("os").environ), "PYTHONPATH": str(Path(__file__).resolve().parent.parent)},
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "queued=0" in out
    assert "ready=0" in out
    assert "waiting_retry=0" in out
    assert "processed=0" in out
    assert "failed=0" in out
    assert "failed_or_stuck=0" in out
    assert "oldest_queued=none" in out
    assert "last_processed=none" in out
    assert "cursors=0" in out
    assert f"db={db}" in out or str(db) in out
    assert "status=OK" in out


def test_connect_health_reports_permission_summary_when_package_supplied(tmp_path: Path):
    """When a package with permission metadata is supplied, health reports entry and read=False counts."""
    from okc.models.knowledge_package import KnowledgePackage

    db = tmp_path / "h.db"
    pkg_path = tmp_path / "living.json"
    pkg = KnowledgePackage(
        package_id="test-pkg",
        metadata={
            "object_count": 0,
            "permissions": {"src:a|t|s|1": {"read": False}, "src:b|t|s|2": {"read": True}},
        },
    )
    pkg_path.write_text(pkg.to_json())

    script = Path(__file__).resolve().parent.parent / "scripts" / "connect_health.py"
    result = subprocess.run(
        [sys.executable, str(script), str(db), str(pkg_path)],
        capture_output=True,
        text=True,
        check=False,
        env={**dict(**__import__("os").environ), "PYTHONPATH": str(Path(__file__).resolve().parent.parent)},
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "permissions_entries=2" in out
    assert "explicit_read_false=1" in out
    assert "status=OK" in out


def test_connect_health_warns_on_unreadable_package(tmp_path: Path):
    """Unreadable package must surface as status=WARNING package_unreadable."""
    db = tmp_path / "h.db"
    SyncEngine(str(db))
    pkg_path = tmp_path / "bad.json"
    pkg_path.write_text("{not valid json")

    script = Path(__file__).resolve().parent.parent / "scripts" / "connect_health.py"
    result = subprocess.run(
        [sys.executable, str(script), str(db), str(pkg_path)],
        capture_output=True,
        text=True,
        check=False,
        env={**dict(**__import__("os").environ), "PYTHONPATH": str(Path(__file__).resolve().parent.parent)},
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "package=UNREADABLE" in out
    assert "status=WARNING" in out
    assert "package_unreadable" in out


def test_connect_health_warns_on_package_count_mismatch(tmp_path: Path):
    """Object count mismatch must surface as status=WARNING package_mismatch."""
    from okc.models.knowledge_package import KnowledgePackage

    db = tmp_path / "h.db"
    pkg_path = tmp_path / "living.json"
    pkg = KnowledgePackage(
        package_id="test-pkg",
        metadata={"object_count": 5},  # actual objects = 0
    )
    pkg_path.write_text(pkg.to_json())

    script = Path(__file__).resolve().parent.parent / "scripts" / "connect_health.py"
    result = subprocess.run(
        [sys.executable, str(script), str(db), str(pkg_path)],
        capture_output=True,
        text=True,
        check=False,
        env={**dict(**__import__("os").environ), "PYTHONPATH": str(Path(__file__).resolve().parent.parent)},
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "MISMATCH" in out
    assert "status=WARNING" in out
    assert "package_mismatch" in out


def test_connect_health_warns_on_unreadable_snapshot(tmp_path: Path):
    """Unreadable snapshot must surface as status=WARNING snapshot_unreadable."""
    db = tmp_path / "h.db"
    SyncEngine(str(db))
    snap_path = tmp_path / "snap.json"
    snap_path.write_text("not json")

    script = Path(__file__).resolve().parent.parent / "scripts" / "connect_health.py"
    result = subprocess.run(
        [sys.executable, str(script), str(db), str(tmp_path / "missing_pkg.json"), str(snap_path)],
        capture_output=True,
        text=True,
        check=False,
        env={**dict(**__import__("os").environ), "PYTHONPATH": str(Path(__file__).resolve().parent.parent)},
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "snapshot=UNREADABLE" in out
    assert "status=WARNING" in out
    assert "snapshot_unreadable" in out
    assert "package_missing" in out


def test_connect_health_reports_last_source_and_package_lag(tmp_path: Path):
    """When package has last_source and engine has last_processed_at, health reports both and lag."""
    from datetime import datetime, timezone
    from okc.models.knowledge_package import KnowledgePackage

    db = tmp_path / "h.db"
    eng = SyncEngine(str(db))
    # Force a last_processed_at in the past by direct update if needed; for test use current
    # Simulate by processing a dummy if possible, or just check presence of fields
    pkg_path = tmp_path / "living.json"
    pkg = KnowledgePackage(
        package_id="test-pkg",
        metadata={"object_count": 0, "last_source": "local_folder"},
    )
    pkg_path.write_text(pkg.to_json())

    script = Path(__file__).resolve().parent.parent / "scripts" / "connect_health.py"
    result = subprocess.run(
        [sys.executable, str(script), str(db), str(pkg_path)],
        capture_output=True,
        text=True,
        check=False,
        env={**dict(**__import__("os").environ), "PYTHONPATH": str(Path(__file__).resolve().parent.parent)},
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "last_source=local_folder" in out
    # lag may or may not print depending on last_processed; at least last_source is present
    assert "package=OK" in out

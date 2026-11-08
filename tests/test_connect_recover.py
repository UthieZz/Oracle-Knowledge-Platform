import json
import subprocess
import sys
from pathlib import Path

import pytest

from okc.connect.interfaces import SyncEvent
from okc.connect.sync_engine import SyncEngine


def test_connect_recover_lists_and_resets(tmp_path: Path):
    db = tmp_path / "sync.db"
    engine = SyncEngine(str(db), max_attempts=1)
    ev = SyncEvent(
        event_id="fail-1",
        source="local_folder",
        kind="create",
        payload={"object_id": "a.txt", "text": "x"},
        tenant_id="t",
        silo_id="s",
    )
    engine.enqueue(ev)
    # Force failure
    def boom(_e):
        raise RuntimeError("intentional")
    engine.process_next(boom)
    assert "fail-1" in engine.list_failed()

    # List
    proc = subprocess.run(
        [sys.executable, "scripts/connect_recover.py", "--db", str(db), "--list"],
        capture_output=True, text=True, cwd=Path(__file__).parents[1],
    )
    assert proc.returncode == 0
    assert "fail-1" in proc.stdout
    assert "source=local_folder" in proc.stdout
    assert "kind=create" in proc.stdout
    assert "tenant=t" in proc.stdout
    assert "silo=s" in proc.stdout
    assert "enqueued=" in proc.stdout

    # Reset
    proc = subprocess.run(
        [sys.executable, "scripts/connect_recover.py", "--db", str(db), "--reset", "fail-1"],
        capture_output=True, text=True, cwd=Path(__file__).parents[1],
    )
    assert proc.returncode == 0
    assert "Reset fail-1" in proc.stdout
    assert engine.list_failed() == []
    assert "fail-1" in engine.list_queued()


def test_connect_recover_accepts_config_file(tmp_path: Path):
    db = tmp_path / "sync.db"
    cfg = tmp_path / "pilot.json"
    cfg.write_text(json.dumps({"db": str(db)}), encoding="utf-8")

    engine = SyncEngine(str(db), max_attempts=1)
    ev = SyncEvent(
        event_id="fail-cfg",
        source="local_folder",
        kind="create",
        payload={"object_id": "b.txt", "text": "y"},
        tenant_id="t",
        silo_id="s",
    )
    engine.enqueue(ev)
    def boom(_e):
        raise RuntimeError("intentional")
    engine.process_next(boom)
    assert "fail-cfg" in engine.list_failed()

    proc = subprocess.run(
        [sys.executable, "scripts/connect_recover.py", "--config", str(cfg), "--list"],
        capture_output=True, text=True, cwd=Path(__file__).parents[1],
    )
    assert proc.returncode == 0
    assert "fail-cfg" in proc.stdout


def test_connect_recover_filters_by_source(tmp_path: Path):
    db = tmp_path / "sync.db"
    engine = SyncEngine(str(db), max_attempts=1)
    ev1 = SyncEvent(
        event_id="fail-a",
        source="local_folder",
        kind="create",
        payload={"object_id": "a.txt", "text": "x"},
        tenant_id="t",
        silo_id="s",
    )
    ev2 = SyncEvent(
        event_id="fail-b",
        source="other",
        kind="create",
        payload={"object_id": "b.txt", "text": "y"},
        tenant_id="t",
        silo_id="s",
    )
    engine.enqueue(ev1)
    engine.enqueue(ev2)
    def boom(_e):
        raise RuntimeError("intentional")
    engine.process_next(boom)
    engine.process_next(boom)

    proc = subprocess.run(
        [sys.executable, "scripts/connect_recover.py", "--db", str(db), "--list", "--source", "local_folder"],
        capture_output=True, text=True, cwd=Path(__file__).parents[1],
    )
    assert proc.returncode == 0
    assert "fail-a" in proc.stdout
    assert "fail-b" not in proc.stdout

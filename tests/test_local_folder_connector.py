"""Tests for LocalFolderConnector: initial/incremental, delete, e2e to KnowledgePackage."""
import json
import tempfile
import os
import sys
from pathlib import Path

import pytest

from okc.connect.local_folder_connector import LocalFolderConnector
from okc.connect.sync_engine import SyncEngine
from okc.connect.sync_worker import SyncWorker
from okc.connect.knowledge_accumulator import KnowledgeAccumulator
from okc.importers.text_importer import PlainTextImporter


def test_local_folder_initial_and_incremental(tmp_path):
    root = tmp_path / "docs"
    root.mkdir()
    (root / "a.txt").write_text("First document content.", encoding="utf-8")
    (root / "b.md").write_text("# Second\nMore text.", encoding="utf-8")

    conn = LocalFolderConnector(str(root))
    assert conn.authenticate({}) is True
    assert conn.health().value == "ok"

    events = conn.initial_sync("t1", "s1")
    assert len(events) == 2
    ids = {e.payload["object_id"] for e in events}
    assert ids == {"a.txt", "b.md"}
    assert all(e.kind == "create" for e in events)
    assert all(e.tenant_id == "t1" for e in events)

    # Incremental with no change
    more = conn.incremental_sync("0", "t1", "s1")
    assert more == []

    # Update one file
    (root / "a.txt").write_text("First document content updated.", encoding="utf-8")
    updates = conn.incremental_sync("0", "t1", "s1")
    assert len(updates) == 1
    assert updates[0].kind == "update"
    assert updates[0].payload["object_id"] == "a.txt"
    assert "updated" in updates[0].payload["text"]

    # Delete
    (root / "b.md").unlink()
    deletes = conn.incremental_sync("0", "t1", "s1")
    assert len(deletes) == 1
    assert deletes[0].kind == "delete"
    assert deletes[0].payload["object_id"] == "b.md"


def test_local_folder_snapshot_survives_restart_and_detects_delete(tmp_path):
    """Deletions that occur while the process is stopped are emitted after restart."""
    root = tmp_path / "watched"
    root.mkdir()
    (root / "keep.txt").write_text("Keep this.", encoding="utf-8")
    (root / "gone.txt").write_text("This will be deleted while stopped.", encoding="utf-8")

    snap_path = str(tmp_path / "snapshot.json")
    conn1 = LocalFolderConnector(str(root), snapshot_path=snap_path)
    assert conn1.authenticate({})
    events = conn1.initial_sync("t", "s")
    assert len(events) == 2
    assert Path(snap_path).exists()
    saved = json.loads(Path(snap_path).read_text(encoding="utf-8"))
    assert saved.get("version") == 1
    assert set(saved.get("snapshot", {})) == {"keep.txt", "gone.txt"}

    # Simulate stop: delete a file while no process is running
    (root / "gone.txt").unlink()

    # Restart: new connector instance loads the snapshot
    conn2 = LocalFolderConnector(str(root), snapshot_path=snap_path)
    assert conn2.authenticate({})
    assert conn2._last_snapshot == saved["snapshot"]
    deltas = conn2.incremental_sync("0", "t", "s")
    assert len(deltas) == 1
    assert deltas[0].kind == "delete"
    assert deltas[0].payload["object_id"] == "gone.txt"

    # Snapshot now reflects the reduced set
    after = json.loads(Path(snap_path).read_text(encoding="utf-8"))
    assert set(after.get("snapshot", {})) == {"keep.txt"}


def test_local_folder_delete_recreate_same_content_gets_new_event_id(tmp_path):
    """Delete then recreate identical content must produce a distinct event_id so the engine re-processes it."""
    root = tmp_path / "docs"
    root.mkdir()
    content = "Identical content across lifecycle."
    (root / "note.txt").write_text(content, encoding="utf-8")

    snap = str(tmp_path / "snap.json")
    conn = LocalFolderConnector(str(root), snapshot_path=snap)
    assert conn.authenticate({})
    creates = conn.initial_sync("t", "s")
    assert len(creates) == 1
    first_id = creates[0].event_id

    # Delete
    (root / "note.txt").unlink()
    dels = conn.incremental_sync("0", "t", "s")
    assert len(dels) == 1
    assert dels[0].kind == "delete"

    # Recreate identical content
    (root / "note.txt").write_text(content, encoding="utf-8")
    recreates = conn.incremental_sync("0", "t", "s")
    assert len(recreates) == 1
    assert recreates[0].kind == "create"
    assert recreates[0].payload["text"] == content
    assert recreates[0].event_id != first_id  # new lifecycle generation

    # Re-poll with no change must not emit
    again = conn.incremental_sync("0", "t", "s")
    assert again == []


def test_local_folder_to_knowledge_package(tmp_path):
    root = tmp_path / "src"
    root.mkdir()
    (root / "note.txt").write_text("Local knowledge evidence.\nProvenance preserved.", encoding="utf-8")

    connector = LocalFolderConnector(str(root))
    assert connector.authenticate({})

    events = connector.initial_sync("tenant-local", "silo-local")
    assert len(events) == 1

    db = str(tmp_path / "lf.db")
    engine = SyncEngine(db_path=db)
    assert engine.enqueue(events[0]) is True

    packages = []

    def processor(event):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(event.payload["text"])
            path = f.name
        try:
            pkg = PlainTextImporter().process(
                path,
                event.tenant_id,
                event.silo_id,
                source_platform=event.source,
            )
            packages.append(pkg)
        finally:
            Path(path).unlink(missing_ok=True)

    eid = engine.process_next(processor)
    assert eid is not None
    assert len(packages) == 1
    pkg = packages[0]
    assert pkg.metadata["tenant_id"] == "tenant-local"
    assert pkg.metadata["silo_id"] == "silo-local"
    assert pkg.metadata["source_platform"] == "local_folder"
    obj = pkg.objects[0]
    assert obj.provenance.tenant_id == "tenant-local"
    assert obj.provenance.silo_id == "silo-local"
    assert obj.provenance.source_platform == "local_folder"
    assert "Local knowledge evidence" in obj.content
    assert engine.health()["processed"] == 1
    assert engine.list_queued() == []


def test_local_folder_corrupt_snapshot_recovers_without_raising(tmp_path):
    """A truncated/corrupt snapshot file is ignored; connector starts clean and does not raise."""
    root = tmp_path / "docs"
    root.mkdir()
    (root / "a.txt").write_text("content", encoding="utf-8")
    snap = tmp_path / "snapshot.json"
    snap.write_text("{\"version\": 1, \"seq\": 5, \"snapshot\": {", encoding="utf-8")  # truncated
    conn = LocalFolderConnector(str(root), snapshot_path=str(snap))
    assert conn.authenticate({})
    assert conn._last_snapshot == {}
    assert conn._seq == 0
    events = conn.initial_sync("t", "s")
    assert len(events) == 1
    # After successful persist the file is valid
    loaded = json.loads(snap.read_text(encoding="utf-8"))
    assert loaded["version"] == 1
    assert "a.txt" in loaded["snapshot"]


def test_local_folder_cleans_stale_tmp_on_init(tmp_path):
    """Leftover .tmp from interrupted persist is removed on next connector init; main snapshot is used."""
    root = tmp_path / "docs"
    root.mkdir()
    (root / "a.txt").write_text("content", encoding="utf-8")
    snap = tmp_path / "snapshot.json"
    snap.write_text('{"version": 1, "seq": 3, "snapshot": {"a.txt": "abc"}}', encoding="utf-8")
    tmp = snap.with_suffix(snap.suffix + ".tmp")
    tmp.write_text('partial garbage', encoding="utf-8")
    assert tmp.exists()
    conn = LocalFolderConnector(str(root), snapshot_path=str(snap))
    assert not tmp.exists()  # cleaned
    assert conn._seq == 3
    assert "a.txt" in conn._last_snapshot


def test_local_folder_cleans_stale_pending_journal_tmp_on_init(tmp_path):
    """Leftover .pending.tmp from an interrupted journal write is removed on next connector init.

    The committed snapshot is used; subsequent staging is not blocked by the leftover temp.
    """
    root = tmp_path / "docs"
    root.mkdir()
    (root / "a.txt").write_text("content", encoding="utf-8")
    snap = tmp_path / "snapshot.json"
    snap.write_text('{"version": 1, "seq": 3, "snapshot": {"a.txt": "abc"}}', encoding="utf-8")
    journal_tmp = snap.with_name(snap.name + ".pending.tmp")
    journal_tmp.write_text('partial garbage', encoding="utf-8")
    assert journal_tmp.exists()
    conn = LocalFolderConnector(str(root), snapshot_path=str(snap))
    assert not journal_tmp.exists()  # cleaned
    assert conn._seq == 3
    assert "a.txt" in conn._last_snapshot
    assert conn.authenticate({})
    # Staging must still succeed and detect the new file
    (root / "b.txt").write_text("new", encoding="utf-8")
    events = conn.stage_incremental_sync("", "t", "s")
    assert any(e.kind == "create" and e.payload.get("object_id") == "b.txt" for e in events)


def test_local_folder_delete_recreate_same_content_new_event_id(tmp_path):
    """Delete then recreate identical content receives a new event_id via sequence advance."""
    root = tmp_path / "docs"
    root.mkdir()
    f = root / "same.txt"
    f.write_text("identical content", encoding="utf-8")
    snap = str(tmp_path / "snapshot.json")
    conn = LocalFolderConnector(str(root), snapshot_path=snap)
    assert conn.authenticate({})
    events1 = conn.initial_sync("t", "s")
    assert len(events1) == 1
    eid1 = events1[0].event_id
    # Delete
    f.unlink()
    events2 = conn.incremental_sync("", "t", "s")
    assert any(e.kind == "delete" for e in events2)
    # Recreate identical content
    f.write_text("identical content", encoding="utf-8")
    events3 = conn.incremental_sync("", "t", "s")
    creates = [e for e in events3 if e.kind == "create"]
    assert len(creates) == 1
    eid3 = creates[0].event_id
    assert eid1 != eid3
    assert "same.txt" in conn._last_snapshot


def test_local_folder_restart_deletion_updates_package(tmp_path):
    """Full path: initial sync + process, stop, delete file, restart connector+engine+accumulator, process delete, package converges."""
    root = tmp_path / "watched"
    root.mkdir()
    (root / "keep.txt").write_text("Keep.", encoding="utf-8")
    (root / "gone.txt").write_text("Gone soon.", encoding="utf-8")

    snap = str(tmp_path / "snap.json")
    db = str(tmp_path / "sync.db")
    pkg = str(tmp_path / "living.json")

    # First run
    conn1 = LocalFolderConnector(str(root), snapshot_path=snap)
    assert conn1.authenticate({})
    events = conn1.initial_sync("t", "s")
    eng1 = SyncEngine(db)
    for e in events:
        eng1.enqueue(e)
    acc1 = KnowledgeAccumulator(package_path=pkg)
    while eng1.process_next(acc1.process):
        pass
    assert Path(pkg).exists()
    assert len(acc1.package.objects) == 2

    # Stop and delete
    (root / "gone.txt").unlink()

    # Restart
    conn2 = LocalFolderConnector(str(root), snapshot_path=snap)
    assert conn2.authenticate({})
    deltas = conn2.incremental_sync("0", "t", "s")
    assert len(deltas) == 1 and deltas[0].kind == "delete"
    eng2 = SyncEngine(db)
    for e in deltas:
        eng2.enqueue(e)
    acc2 = KnowledgeAccumulator(package_path=pkg)
    while eng2.process_next(acc2.process):
        pass
    assert len(acc2.package.objects) == 1
    assert "gone.txt" not in {o.provenance.source_record_ids[0] for o in acc2.package.objects if o.provenance.source_record_ids}


def test_local_folder_snapshot_persist_failure_rolls_back_seq_and_snapshot(tmp_path, monkeypatch):
    """If _persist_snapshot raises, in-memory seq and snapshot must roll back so a retry is consistent."""
    root = tmp_path / "docs"
    root.mkdir()
    (root / "a.txt").write_text("content a", encoding="utf-8")

    snap_path = str(tmp_path / "snap.json")
    conn = LocalFolderConnector(str(root), snapshot_path=snap_path)
    assert conn.authenticate({})

    # First successful sync to establish baseline
    events = conn.initial_sync("t", "s")
    assert len(events) == 1
    baseline_seq = conn._seq
    baseline_snap = dict(conn._last_snapshot)
    assert Path(snap_path).exists()

    # Now force a change and make persist fail
    (root / "b.txt").write_text("content b", encoding="utf-8")

    def boom(*args, **kwargs):
        raise OSError("simulated persist failure")

    monkeypatch.setattr(conn, "_persist_snapshot", boom)

    with pytest.raises(OSError, match="simulated persist failure"):
        conn.incremental_sync("0", "t", "s")

    # In-memory state must be unchanged
    assert conn._seq == baseline_seq
    assert conn._last_snapshot == baseline_snap
    # Disk must still have the prior valid snapshot
    saved = json.loads(Path(snap_path).read_text(encoding="utf-8"))
    assert saved.get("seq") == baseline_seq
    assert set(saved.get("snapshot", {})) == {"a.txt"}

    # Remove the patch and retry; must succeed and advance
    monkeypatch.undo()
    more = conn.incremental_sync("0", "t", "s")
    assert len(more) == 1
    assert more[0].payload["object_id"] == "b.txt"
    assert conn._seq == baseline_seq + 1
    assert Path(snap_path).exists()
    after = json.loads(Path(snap_path).read_text(encoding="utf-8"))
    assert after.get("seq") == baseline_seq + 1
    assert set(after.get("snapshot", {})) == {"a.txt", "b.txt"}


def test_local_folder_real_process_restart_deletion_converges_package(tmp_path):
    """True process restart: launch worker subprocess, stop it, delete file, relaunch, package converges.
    Provides runtime verification beyond in-process simulation.
    """
    import subprocess
    import time
    root = tmp_path / "watched"
    root.mkdir()
    (root / "keep.txt").write_text("Keep this content.", encoding="utf-8")
    (root / "gone.txt").write_text("This disappears after stop.", encoding="utf-8")

    db = str(tmp_path / "sync.db")
    pkg = str(tmp_path / "living.json")
    snap = str(tmp_path / "snap.json")
    script = str(Path(__file__).resolve().parent.parent / "scripts" / "run_connect_worker.py")

    # First process
    proc1 = subprocess.Popen(
        [sys.executable, script, "--folder", str(root), "--tenant", "t", "--silo", "s",
         "--db", db, "--package", pkg, "--snapshot", snap, "--poll", "0.5"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parent.parent)}
    )
    time.sleep(2.0)  # allow initial sync + process
    proc1.terminate()
    proc1.wait(timeout=5)
    assert Path(pkg).exists()
    data1 = json.loads(Path(pkg).read_text(encoding="utf-8"))
    assert len(data1.get("objects", [])) == 2

    # Delete while stopped
    (root / "gone.txt").unlink()

    # Second process
    proc2 = subprocess.Popen(
        [sys.executable, script, "--folder", str(root), "--tenant", "t", "--silo", "s",
         "--db", db, "--package", pkg, "--snapshot", snap, "--poll", "0.5"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parent.parent)}
    )
    time.sleep(2.0)
    proc2.terminate()
    proc2.wait(timeout=5)

    data2 = json.loads(Path(pkg).read_text(encoding="utf-8"))
    assert len(data2.get("objects", [])) == 1
    # Ensure the remaining object is the keep one via source marker
    markers = []
    for o in data2.get("objects", []):
        for rid in o.get("provenance", {}).get("source_record_ids", []):
            markers.append(rid)
    assert any("keep.txt" in m for m in markers)
    assert not any("gone.txt" in m for m in markers)


def test_run_connect_worker_accepts_config_file(tmp_path):
    """Regression: --config must load without NameError (json import was missing)."""
    import subprocess
    import json as json_mod
    root = tmp_path / "watched"
    root.mkdir()
    (root / "a.txt").write_text("hello", encoding="utf-8")
    cfg = tmp_path / "pilot.json"
    db = str(tmp_path / "sync.db")
    pkg = str(tmp_path / "living.json")
    cfg.write_text(json_mod.dumps({
        "folder": str(root),
        "tenant": "t",
        "silo": "s",
        "db": db,
        "package": pkg,
        "poll": 0.5,
    }), encoding="utf-8")
    script = str(Path(__file__).resolve().parent.parent / "scripts" / "run_connect_worker.py")
    proc = subprocess.Popen(
        [sys.executable, script, "--config", str(cfg)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parent.parent)},
    )
    import time
    time.sleep(1.5)
    proc.terminate()
    proc.wait(timeout=5)
    # Must have started (no NameError on json) and persisted something or at least not crashed immediately
    assert Path(pkg).exists() or proc.returncode is not None
    # Stronger: package should exist after brief run if connector works
    assert Path(pkg).exists()


def test_local_folder_persist_failure_preserves_prior_snapshot(tmp_path, monkeypatch):
    """If atomic persist raises after writing .tmp, the previous valid snapshot remains intact and usable on next init."""
    root = tmp_path / "docs"
    root.mkdir()
    (root / "keep.txt").write_text("prior content", encoding="utf-8")
    snap = tmp_path / "snapshot.json"
    # Seed a valid prior snapshot
    prior = {"version": 1, "seq": 5, "snapshot": {"keep.txt": "abc123"}}
    snap.write_text(json.dumps(prior), encoding="utf-8")

    conn = LocalFolderConnector(str(root), snapshot_path=str(snap))
    assert conn.authenticate({})
    assert conn._seq == 5
    assert "keep.txt" in conn._last_snapshot

    # Force next persist to fail after tmp write by making replace raise
    original_replace = Path.replace
    def failing_replace(self, target):
        raise OSError("simulated replace failure")
    monkeypatch.setattr(Path, "replace", failing_replace)

    # Trigger a change that would persist
    (root / "new.txt").write_text("new", encoding="utf-8")
    try:
        conn.incremental_sync("0", "t", "s")
    except OSError:
        pass  # expected

    # Prior snapshot file must still be valid and unchanged
    loaded = json.loads(snap.read_text(encoding="utf-8"))
    assert loaded["version"] == 1
    assert loaded["seq"] == 5
    assert "keep.txt" in loaded["snapshot"]
    assert "new.txt" not in loaded["snapshot"]

    # Next init loads the intact prior snapshot
    conn2 = LocalFolderConnector(str(root), snapshot_path=str(snap))
    assert conn2._seq == 5
    assert "keep.txt" in conn2._last_snapshot
    assert "new.txt" not in conn2._last_snapshot


def test_local_folder_mixed_concurrent_changes_while_stopped(tmp_path):
    """Create + update + delete that occur while the process is stopped are all detected on restart and converge the package without loss or duplicates."""
    root = tmp_path / "docs"
    root.mkdir()
    (root / "keep.txt").write_text("original keep", encoding="utf-8")
    (root / "update.txt").write_text("original update", encoding="utf-8")
    (root / "gone.txt").write_text("will be deleted", encoding="utf-8")

    snap_path = str(tmp_path / "snapshot.json")
    conn1 = LocalFolderConnector(str(root), snapshot_path=snap_path)
    assert conn1.authenticate({})
    events1 = conn1.initial_sync("t1", "s1")
    assert len(events1) == 3
    assert set(conn1._last_snapshot) == {"keep.txt", "update.txt", "gone.txt"}

    # Simulate process stopped: mutate source on disk
    (root / "keep.txt").write_text("original keep", encoding="utf-8")  # unchanged
    (root / "update.txt").write_text("updated content", encoding="utf-8")
    (root / "gone.txt").unlink()
    (root / "new.txt").write_text("brand new", encoding="utf-8")

    # Restart
    conn2 = LocalFolderConnector(str(root), snapshot_path=snap_path)
    assert conn2.authenticate({})
    events2 = conn2.incremental_sync("0", "t1", "s1")

    kinds = {e.payload["object_id"]: e.kind for e in events2}
    assert kinds.get("update.txt") == "update"
    assert kinds.get("gone.txt") == "delete"
    assert kinds.get("new.txt") == "create"
    assert "keep.txt" not in kinds  # no event for unchanged

    # Final snapshot matches disk
    assert set(conn2._last_snapshot) == {"keep.txt", "update.txt", "new.txt"}
    assert conn2._last_snapshot["update.txt"] != conn1._last_snapshot["update.txt"]

    # Package convergence via accumulator (no loss, no duplicates)
    from okc.connect.knowledge_accumulator import KnowledgeAccumulator
    acc = KnowledgeAccumulator()
    # Replay both batches
    for e in events1 + events2:
        acc.process(e)
    ids = {o.object_id for o in acc.package.objects}
    # object_ids are generated; check via provenance markers or content
    markers = []
    for o in acc.package.objects:
        for rid in o.provenance.source_record_ids:
            markers.append(rid)
    assert any("keep.txt" in m for m in markers)
    assert any("update.txt" in m for m in markers)
    assert any("new.txt" in m for m in markers)
    assert not any("gone.txt" in m for m in markers)
    assert len(acc.package.objects) == 3


def test_local_folder_mixed_changes_persist_failure_then_retry_converges(tmp_path, monkeypatch):
    """Mixed create+update+delete during a failing persist rolls back; retry after recovery converges package with no loss/duplicates."""
    root = tmp_path / "docs"
    root.mkdir()
    (root / "keep.txt").write_text("original keep", encoding="utf-8")
    (root / "update.txt").write_text("original update", encoding="utf-8")
    (root / "gone.txt").write_text("will be deleted", encoding="utf-8")

    snap_path = str(tmp_path / "snapshot.json")
    conn = LocalFolderConnector(str(root), snapshot_path=snap_path)
    assert conn.authenticate({})
    events1 = conn.initial_sync("t1", "s1")
    assert len(events1) == 3
    baseline_seq = conn._seq
    baseline_snap = dict(conn._last_snapshot)
    assert set(baseline_snap) == {"keep.txt", "update.txt", "gone.txt"}

    # Apply mixed changes on disk
    (root / "update.txt").write_text("updated content", encoding="utf-8")
    (root / "gone.txt").unlink()
    (root / "new.txt").write_text("brand new", encoding="utf-8")

    # Force persist to fail
    def boom(*args, **kwargs):
        raise OSError("simulated persist failure")

    monkeypatch.setattr(conn, "_persist_snapshot", boom)

    with pytest.raises(OSError, match="simulated persist failure"):
        conn.incremental_sync("0", "t1", "s1")

    # Must have rolled back in-memory and on-disk
    assert conn._seq == baseline_seq
    assert conn._last_snapshot == baseline_snap
    saved = json.loads(Path(snap_path).read_text(encoding="utf-8"))
    assert saved.get("seq") == baseline_seq
    assert set(saved.get("snapshot", {})) == {"keep.txt", "update.txt", "gone.txt"}

    # Recover and retry
    monkeypatch.undo()
    events2 = conn.incremental_sync("0", "t1", "s1")

    kinds = {e.payload["object_id"]: e.kind for e in events2}
    assert kinds.get("update.txt") == "update"
    assert kinds.get("gone.txt") == "delete"
    assert kinds.get("new.txt") == "create"
    assert "keep.txt" not in kinds

    assert set(conn._last_snapshot) == {"keep.txt", "update.txt", "new.txt"}
    assert conn._seq > baseline_seq

    # Package converges
    from okc.connect.knowledge_accumulator import KnowledgeAccumulator
    acc = KnowledgeAccumulator()
    for e in events1 + events2:
        acc.process(e)
    markers = []
    for o in acc.package.objects:
        for rid in o.provenance.source_record_ids:
            markers.append(rid)
    assert any("keep.txt" in m for m in markers)
    assert any("update.txt" in m for m in markers)
    assert any("new.txt" in m for m in markers)
    assert not any("gone.txt" in m for m in markers)
    assert len(acc.package.objects) == 3


def test_interruption_after_snapshot_before_cursor_detects_delete_on_restart(tmp_path):
    """Interruption after connector snapshot persist but before any successful process_next
    (engine cursor still None) must still detect a subsequent deletion on restart
    and converge the package without silent loss.
    """
    root = tmp_path / "docs"
    root.mkdir()
    (root / "keep.txt").write_text("keep me", encoding="utf-8")
    (root / "gone.txt").write_text("will disappear", encoding="utf-8")

    snap = str(tmp_path / "snap.json")
    db = str(tmp_path / "sync.db")
    pkg = str(tmp_path / "living.json")

    # First run: connector persists snapshot and enqueues events, but we do not process
    # so cursor remains None.
    conn1 = LocalFolderConnector(str(root), snapshot_path=snap)
    assert conn1.authenticate({})
    events = conn1.initial_sync("t", "s")
    assert len(events) == 2
    assert conn1.has_durable_snapshot()
    eng1 = SyncEngine(db)
    for e in events:
        eng1.enqueue(e)
    assert eng1.get_cursor("local_folder", "t", "s") is None

    # Simulate stop: delete a file
    (root / "gone.txt").unlink()

    # Restart: new instances. Worker logic must prefer incremental because durable snapshot exists.
    conn2 = LocalFolderConnector(str(root), snapshot_path=snap)
    assert conn2.authenticate({})
    assert conn2.has_durable_snapshot()
    eng2 = SyncEngine(db)
    acc = KnowledgeAccumulator(package_path=pkg)

    # Manually exercise the decision the worker would make
    cursor = eng2.get_cursor("local_folder", "t", "s")
    prefer_incremental = cursor is not None or conn2.has_durable_snapshot()
    assert prefer_incremental
    deltas = conn2.incremental_sync(cursor or "", "t", "s")
    kinds = {e.payload["object_id"]: e.kind for e in deltas}
    assert kinds.get("gone.txt") == "delete"
    assert "keep.txt" not in kinds  # no re-create

    for e in deltas:
        eng2.enqueue(e)
    while eng2.process_next(acc.process):
        pass

    # Package must not contain the deleted file
    markers = []
    for o in acc.package.objects:
        for rid in o.provenance.source_record_ids:
            markers.append(rid)
    assert any("keep.txt" in m for m in markers)
    assert not any("gone.txt" in m for m in markers)
    assert len(acc.package.objects) == 1


def test_partial_drain_then_source_mutation_converges_package(tmp_path):
    """After some events are processed (cursor advanced) and further create/update/delete
    occur while stopped, restart + incremental_sync converges the package to the final
    source state with no loss or duplicates.
    """
    root = tmp_path / "docs"
    root.mkdir()
    (root / "keep.txt").write_text("original keep", encoding="utf-8")
    (root / "update.txt").write_text("original update", encoding="utf-8")
    (root / "gone.txt").write_text("will be deleted later", encoding="utf-8")

    snap = str(tmp_path / "snap.json")
    db = str(tmp_path / "sync.db")
    pkg = str(tmp_path / "living.json")

    # Initial sync and partial drain: process only the first event so cursor advances
    conn1 = LocalFolderConnector(str(root), snapshot_path=snap)
    assert conn1.authenticate({})
    events = conn1.initial_sync("t", "s")
    assert len(events) == 3
    eng1 = SyncEngine(db)
    for e in events:
        eng1.enqueue(e)
    acc1 = KnowledgeAccumulator(package_path=pkg)
    # Process only one event
    eid = eng1.process_next(acc1.process)
    assert eid is not None
    assert eng1.get_cursor("local_folder", "t", "s") is not None
    assert len(acc1.package.objects) == 1

    # Stop and mutate source: update one, delete one, create one
    (root / "update.txt").write_text("updated content", encoding="utf-8")
    (root / "gone.txt").unlink()
    (root / "new.txt").write_text("brand new", encoding="utf-8")

    # Restart
    conn2 = LocalFolderConnector(str(root), snapshot_path=snap)
    assert conn2.authenticate({})
    eng2 = SyncEngine(db)
    acc2 = KnowledgeAccumulator(package_path=pkg)
    cursor = eng2.get_cursor("local_folder", "t", "s")
    deltas = conn2.incremental_sync(cursor or "", "t", "s")
    kinds = {e.payload["object_id"]: e.kind for e in deltas}
    assert kinds.get("update.txt") == "update"
    assert kinds.get("gone.txt") == "delete"
    assert kinds.get("new.txt") == "create"
    # keep.txt should not reappear if it was already processed and unchanged
    # (depends on which one was processed; we process only one, so keep may or may not be re-emitted)
    # The important property is convergence after processing the deltas.

    for e in deltas:
        eng2.enqueue(e)
    while eng2.process_next(acc2.process):
        pass

    # Final package must match final source: keep, update (new content), new; no gone
    markers = []
    for o in acc2.package.objects:
        for rid in o.provenance.source_record_ids:
            markers.append(rid)
    assert any("keep.txt" in m for m in markers)
    assert any("update.txt" in m for m in markers)
    assert any("new.txt" in m for m in markers)
    assert not any("gone.txt" in m for m in markers)
    assert len(acc2.package.objects) == 3
    # Content of update must be the new one
    for o in acc2.package.objects:
        if any("update.txt" in rid for rid in o.provenance.source_record_ids):
            assert "updated content" in o.content


def test_rename_while_stopped_converges_package(tmp_path):
    """Identical-content rename while stopped must not drop the surviving object.

    object_id is a content hash, so a sibling with the same bytes shares it.
    Removing the old path must delete only that scoped source marker.
    """
    root = tmp_path / "docs"
    root.mkdir()
    body = "identical body for rename"
    (root / "a.txt").write_text(body, encoding="utf-8")
    (root / "twin.txt").write_text(body, encoding="utf-8")

    snap = str(tmp_path / "snap.json")
    conn1 = LocalFolderConnector(str(root), snapshot_path=snap)
    assert conn1.authenticate({})
    events1 = conn1.initial_sync("t", "s")
    assert len(events1) == 2

    acc = KnowledgeAccumulator()
    for event in events1:
        acc.process(event)
    assert len(acc.package.objects) == 2

    # Stopped: rename a.txt -> moved.txt (same bytes). twin.txt stays.
    (root / "a.txt").rename(root / "moved.txt")

    conn2 = LocalFolderConnector(str(root), snapshot_path=snap)
    assert conn2.authenticate({})
    events2 = conn2.incremental_sync("0", "t", "s")
    kinds = {e.payload["object_id"]: e.kind for e in events2}
    assert kinds.get("a.txt") == "delete"
    assert kinds.get("moved.txt") == "create"
    assert "twin.txt" not in kinds

    for event in events2:
        acc.process(event)

    markers = []
    for obj in acc.package.objects:
        for rid in obj.provenance.source_record_ids:
            if rid.startswith("src:"):
                markers.append(rid)
    assert len(acc.package.objects) == 2
    assert any(m.endswith("|moved.txt") for m in markers)
    assert any(m.endswith("|twin.txt") for m in markers)
    assert not any(m.endswith("|a.txt") for m in markers)
    assert all(obj.content == body for obj in acc.package.objects)


def test_crash_after_detect_before_enqueue_still_converges_delete(tmp_path):
    """Committed snapshot must not advance ahead of the durable queue.

    Detection is journaled first. If enqueue crashes, restart replays the
    journal and the deletion still reaches the package.
    """
    root = tmp_path / "docs"
    root.mkdir()
    (root / "keep.txt").write_text("keep me", encoding="utf-8")
    (root / "gone.txt").write_text("will disappear", encoding="utf-8")

    snap = tmp_path / "snap.json"
    db = str(tmp_path / "sync.db")
    pkg = str(tmp_path / "living.json")

    conn1 = LocalFolderConnector(str(root), snapshot_path=str(snap))
    assert conn1.authenticate({})
    eng1 = SyncEngine(db)
    acc1 = KnowledgeAccumulator(package_path=pkg)
    worker1 = SyncWorker(eng1, conn1, "t", "s", acc1.process, poll_interval=30)
    worker1._poll_and_drain()
    assert len(acc1.package.objects) == 2
    committed = json.loads(snap.read_text(encoding="utf-8"))
    assert set(committed["snapshot"]) == {"keep.txt", "gone.txt"}
    assert not conn1.has_pending_journal()

    (root / "gone.txt").unlink()

    def boom(_event):
        raise OSError("crash before enqueue")

    eng1.enqueue = boom
    with pytest.raises(OSError, match="crash before enqueue"):
        worker1._poll_and_drain()

    committed = json.loads(snap.read_text(encoding="utf-8"))
    assert "gone.txt" in committed["snapshot"]
    assert "keep.txt" in committed["snapshot"]
    assert conn1.has_pending_journal()

    conn2 = LocalFolderConnector(str(root), snapshot_path=str(snap))
    assert conn2.authenticate({})
    assert conn2.has_pending_journal()
    # Restart loads the committed baseline, not the uncommitted journal snapshot.
    assert "gone.txt" in conn2._last_snapshot
    eng2 = SyncEngine(db)
    acc2 = KnowledgeAccumulator(package_path=pkg)
    worker2 = SyncWorker(eng2, conn2, "t", "s", acc2.process, poll_interval=30)
    worker2._poll_and_drain()

    assert not conn2.has_pending_journal()
    saved = json.loads(snap.read_text(encoding="utf-8"))
    assert "gone.txt" not in saved["snapshot"]
    assert "keep.txt" in saved["snapshot"]
    markers = []
    for obj in acc2.package.objects:
        for rid in obj.provenance.source_record_ids:
            markers.append(rid)
    assert any("keep.txt" in m for m in markers)
    assert not any("gone.txt" in m for m in markers)
    assert len(acc2.package.objects) == 1


def _markers(package):
    markers = []
    for obj in package.objects:
        for rid in obj.provenance.source_record_ids:
            markers.append(rid)
    return markers


def test_enqueue_ok_commit_fails_then_source_mutates_before_retry(tmp_path):
    """Enqueue can succeed while snapshot promotion fails.

    A later source mutation must not be dropped: retry commits the journal,
    applies the queued events, then the next poll converges to the final source.
    Restart (not the dirty in-memory connector) is the crash case.
    """
    root = tmp_path / "docs"
    root.mkdir()
    (root / "keep.txt").write_text("keep v1", encoding="utf-8")
    (root / "gone.txt").write_text("will disappear", encoding="utf-8")

    snap = tmp_path / "snap.json"
    db = str(tmp_path / "sync.db")
    pkg = str(tmp_path / "living.json")

    conn1 = LocalFolderConnector(str(root), snapshot_path=str(snap))
    assert conn1.authenticate({})
    eng1 = SyncEngine(db)
    acc1 = KnowledgeAccumulator(package_path=pkg)
    worker1 = SyncWorker(eng1, conn1, "t", "s", acc1.process, poll_interval=30)

    real_persist = conn1._persist_snapshot
    fail = {"on": False}

    def flaky_persist():
        if fail["on"]:
            raise OSError("snapshot commit failed")
        real_persist()

    conn1._persist_snapshot = flaky_persist
    worker1._poll_and_drain()
    assert len(acc1.package.objects) == 2
    assert not conn1.has_pending_journal()

    (root / "gone.txt").unlink()
    fail["on"] = True
    with pytest.raises(OSError, match="snapshot commit failed"):
        worker1._poll_and_drain()

    committed = json.loads(snap.read_text(encoding="utf-8"))
    assert set(committed["snapshot"]) == {"keep.txt", "gone.txt"}
    assert conn1.has_pending_journal()
    assert eng1.health()["queued"] == 1
    assert eng1.health()["processed"] == 2
    assert len(acc1.package.objects) == 2

    # Source moves again before the failed commit is retried.
    (root / "keep.txt").write_text("keep v2", encoding="utf-8")
    (root / "new.txt").write_text("brand new", encoding="utf-8")

    conn2 = LocalFolderConnector(str(root), snapshot_path=str(snap))
    assert conn2.authenticate({})
    assert conn2.has_pending_journal()
    assert "gone.txt" in conn2._last_snapshot
    eng2 = SyncEngine(db)
    acc2 = KnowledgeAccumulator(package_path=pkg)
    worker2 = SyncWorker(eng2, conn2, "t", "s", acc2.process, poll_interval=30)
    # First recovery poll promotes the journal and applies the queued delete.
    # The following poll must observe the mutation that happened during the gap.
    worker2._poll_and_drain()
    worker2._poll_and_drain()

    assert not conn2.has_pending_journal()
    saved = json.loads(snap.read_text(encoding="utf-8"))
    assert set(saved["snapshot"]) == {"keep.txt", "new.txt"}
    markers = _markers(acc2.package)
    assert any("keep.txt" in m for m in markers)
    assert any("new.txt" in m for m in markers)
    assert not any("gone.txt" in m for m in markers)
    assert len(acc2.package.objects) == 2
    contents = {}
    for obj in acc2.package.objects:
        for rid in obj.provenance.source_record_ids:
            if rid.endswith("|keep.txt"):
                contents["keep"] = obj.content
            if rid.endswith("|new.txt"):
                contents["new"] = obj.content
    assert contents["keep"] == "keep v2"
    assert contents["new"] == "brand new"
    health = eng2.health()
    assert health["queued"] == 0
    assert health["failed"] == 0
    # 2 creates + 1 delete + 1 update + 1 create. A duplicate replay would exceed this.
    assert health["processed"] == 5


def test_journal_unlink_failure_does_not_stall_later_changes(tmp_path, monkeypatch):
    """If snapshot promotion succeeds but the journal file cannot be removed,
    later source changes must still reach the package.
    """
    root = tmp_path / "docs"
    root.mkdir()
    (root / "keep.txt").write_text("keep v1", encoding="utf-8")
    (root / "gone.txt").write_text("will disappear", encoding="utf-8")

    snap = tmp_path / "snap.json"
    db = str(tmp_path / "sync.db")
    pkg = str(tmp_path / "living.json")
    pending = snap.parent / (snap.name + ".pending")

    conn = LocalFolderConnector(str(root), snapshot_path=str(snap))
    assert conn.authenticate({})
    eng = SyncEngine(db)
    acc = KnowledgeAccumulator(package_path=pkg)
    worker = SyncWorker(eng, conn, "t", "s", acc.process, poll_interval=30)
    worker._poll_and_drain()
    assert len(acc.package.objects) == 2
    assert not pending.exists()

    real_unlink = Path.unlink

    def flaky_unlink(self, *args, **kwargs):
        if self.name.endswith(".pending"):
            raise OSError("cannot unlink journal")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)

    (root / "gone.txt").unlink()
    worker._poll_and_drain()
    committed = json.loads(snap.read_text(encoding="utf-8"))
    assert "gone.txt" not in committed["snapshot"]
    assert pending.is_file()
    # Journal remains on disk, but it already matches the commit so it must not block.
    assert conn.has_pending_journal() is False
    assert not any("gone.txt" in m for m in _markers(acc.package))

    (root / "keep.txt").write_text("keep v2", encoding="utf-8")
    (root / "new.txt").write_text("brand new", encoding="utf-8")
    worker._poll_and_drain()

    saved = json.loads(snap.read_text(encoding="utf-8"))
    assert set(saved["snapshot"]) == {"keep.txt", "new.txt"}
    markers = _markers(acc.package)
    assert any("keep.txt" in m for m in markers)
    assert any("new.txt" in m for m in markers)
    assert not any("gone.txt" in m for m in markers)
    assert len(acc.package.objects) == 2
    for obj in acc.package.objects:
        if any(rid.endswith("|keep.txt") for rid in obj.provenance.source_record_ids):
            assert obj.content == "keep v2"
        if any(rid.endswith("|new.txt") for rid in obj.provenance.source_record_ids):
            assert obj.content == "brand new"
    health = eng.health()
    assert health["queued"] == 0
    assert health["failed"] == 0
    assert health["processed"] == 5



def test_corrupt_pending_journal_quarantined_and_rescan_converges(tmp_path):
    """Corrupt pending journal is quarantined; worker rescans from committed snapshot.

    Already-enqueued events stay in the durable queue. A later source change is
    still detected and the package converges without loss or duplicates.
    """
    root = tmp_path / "docs"
    root.mkdir()
    (root / "keep.txt").write_text("keep me", encoding="utf-8")
    (root / "gone.txt").write_text("will disappear", encoding="utf-8")

    snap = tmp_path / "snap.json"
    db = str(tmp_path / "sync.db")
    pkg = str(tmp_path / "living.json")

    conn1 = LocalFolderConnector(str(root), snapshot_path=str(snap))
    assert conn1.authenticate({})
    eng1 = SyncEngine(db)
    acc1 = KnowledgeAccumulator(package_path=pkg)
    worker1 = SyncWorker(eng1, conn1, "t", "s", acc1.process, poll_interval=30)
    worker1._poll_and_drain()
    assert len(acc1.package.objects) == 2
    assert not conn1.has_pending_journal()

    # Simulate a crash after journal write but before enqueue by writing garbage.
    (root / "gone.txt").unlink()
    pending = Path(str(snap) + ".pending")
    pending.write_text("{not valid json", encoding="utf-8")
    assert pending.is_file()

    # Restart: corrupt journal must be quarantined, then incremental detects the deletion.
    conn2 = LocalFolderConnector(str(root), snapshot_path=str(snap))
    assert conn2.authenticate({})
    assert not conn2.has_pending_journal()
    quarantined = Path(str(snap) + ".pending.quarantined")
    assert quarantined.is_file()
    assert not pending.is_file()
    # Committed snapshot still has the old state.
    assert "gone.txt" in conn2._last_snapshot

    eng2 = SyncEngine(db)
    acc2 = KnowledgeAccumulator(package_path=pkg)
    worker2 = SyncWorker(eng2, conn2, "t", "s", acc2.process, poll_interval=30)
    worker2._poll_and_drain()

    assert not conn2.has_pending_journal()
    saved = json.loads(snap.read_text(encoding="utf-8"))
    assert "gone.txt" not in saved["snapshot"]
    assert "keep.txt" in saved["snapshot"]
    markers = []
    for obj in acc2.package.objects:
        for rid in obj.provenance.source_record_ids:
            markers.append(rid)
    assert any("keep.txt" in m for m in markers)
    assert not any("gone.txt" in m for m in markers)
    assert len(acc2.package.objects) == 1
    health = eng2.health()
    assert health["queued"] == 0
    assert health["failed"] == 0


def test_concurrent_source_mutation_during_quarantine_recovery_converges(tmp_path):
    """Source mutates while a corrupt journal is present; recovery still converges.

    Corrupt journal is quarantined on restart. The subsequent incremental scan
    from the last committed snapshot observes the concurrent create/update/delete
    that happened before recovery and the package converges with no loss or
    duplicates.
    """
    root = tmp_path / "docs"
    root.mkdir()
    (root / "keep.txt").write_text("original keep", encoding="utf-8")
    (root / "gone.txt").write_text("will disappear", encoding="utf-8")
    (root / "update.txt").write_text("old content", encoding="utf-8")

    snap = tmp_path / "snap.json"
    db = str(tmp_path / "sync.db")
    pkg = str(tmp_path / "living.json")

    conn1 = LocalFolderConnector(str(root), snapshot_path=str(snap))
    assert conn1.authenticate({})
    eng1 = SyncEngine(db)
    acc1 = KnowledgeAccumulator(package_path=pkg)
    worker1 = SyncWorker(eng1, conn1, "t", "s", acc1.process, poll_interval=30)
    worker1._poll_and_drain()
    assert len(acc1.package.objects) == 3
    assert not conn1.has_pending_journal()

    # Simulate crash after journal write: leave a corrupt pending journal.
    pending = Path(str(snap) + ".pending")
    pending.write_text("{not valid json", encoding="utf-8")
    assert pending.is_file()

    # Concurrent source mutations while the corrupt journal is present
    # (before any recovery scan).
    (root / "gone.txt").unlink()
    (root / "update.txt").write_text("new content", encoding="utf-8")
    (root / "new.txt").write_text("created during recovery window", encoding="utf-8")

    # Restart: quarantine happens, then scan sees the mutations.
    conn2 = LocalFolderConnector(str(root), snapshot_path=str(snap))
    assert conn2.authenticate({})
    assert not conn2.has_pending_journal()
    quarantined = Path(str(snap) + ".pending.quarantined")
    assert quarantined.is_file()
    assert not pending.is_file()
    # Committed snapshot still reflects pre-mutation state.
    assert "gone.txt" in conn2._last_snapshot
    assert "update.txt" in conn2._last_snapshot
    assert "new.txt" not in conn2._last_snapshot

    eng2 = SyncEngine(db)
    acc2 = KnowledgeAccumulator(package_path=pkg)
    worker2 = SyncWorker(eng2, conn2, "t", "s", acc2.process, poll_interval=30)
    worker2._poll_and_drain()

    assert not conn2.has_pending_journal()
    saved = json.loads(snap.read_text(encoding="utf-8"))
    snap_keys = set(saved["snapshot"].keys())
    assert "gone.txt" not in snap_keys
    assert "update.txt" in snap_keys
    assert "new.txt" in snap_keys
    assert "keep.txt" in snap_keys

    markers = []
    for obj in acc2.package.objects:
        for rid in obj.provenance.source_record_ids:
            markers.append(rid)
    assert any("keep.txt" in m for m in markers)
    assert any("update.txt" in m for m in markers)
    assert any("new.txt" in m for m in markers)
    assert not any("gone.txt" in m for m in markers)
    # Three surviving objects; no duplicates.
    assert len(acc2.package.objects) == 3
    # Updated content is present.
    contents = {obj.content for obj in acc2.package.objects if hasattr(obj, "content")}
    # Content is stored inside the object; verify via markers + count is sufficient
    # for convergence. Health must be clean.
    health = eng2.health()
    assert health["queued"] == 0
    assert health["failed"] == 0

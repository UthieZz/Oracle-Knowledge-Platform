"""Tests for LocalFolderConnector: initial/incremental, delete, e2e to KnowledgePackage."""
import json
import tempfile
from pathlib import Path

from okc.connect.local_folder_connector import LocalFolderConnector
from okc.connect.sync_engine import SyncEngine
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

"""Tests for LocalFolderConnector: initial/incremental, delete, e2e to KnowledgePackage."""
import json
import tempfile
from pathlib import Path

from okc.connect.local_folder_connector import LocalFolderConnector
from okc.connect.sync_engine import SyncEngine
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
    assert set(saved) == {"keep.txt", "gone.txt"}

    # Simulate stop: delete a file while no process is running
    (root / "gone.txt").unlink()

    # Restart: new connector instance loads the snapshot
    conn2 = LocalFolderConnector(str(root), snapshot_path=snap_path)
    assert conn2.authenticate({})
    assert conn2._last_snapshot == saved
    deltas = conn2.incremental_sync("0", "t", "s")
    assert len(deltas) == 1
    assert deltas[0].kind == "delete"
    assert deltas[0].payload["object_id"] == "gone.txt"

    # Snapshot now reflects the reduced set
    after = json.loads(Path(snap_path).read_text(encoding="utf-8"))
    assert set(after) == {"keep.txt"}


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

"""Tests for SyncWorker lifecycle, restart survival, and delete events."""
import tempfile
import time
from pathlib import Path

from okc.connect.interfaces import SyncEvent
from okc.connect.stub_connector import StubConnector
from okc.connect.sync_engine import SyncEngine
from okc.connect.sync_worker import SyncWorker


def test_worker_polls_processes_and_survives_restart(tmp_path):
    db = str(tmp_path / "worker.db")
    docs = [{"id": "d1", "text": "first"}, {"id": "d2", "text": "second"}]
    conn = StubConnector(docs)
    assert conn.authenticate({}) is True

    processed = []

    def proc(e: SyncEvent):
        processed.append((e.event_id, e.kind, e.payload.get("text") or e.payload.get("object_id")))

    eng = SyncEngine(db)
    worker = SyncWorker(eng, conn, "t1", "s1", proc, poll_interval=0.2)
    worker.start()
    # Allow at least one poll cycle
    time.sleep(0.6)
    worker.stop()

    assert len(processed) == 2
    assert all(k == "create" for _, k, _ in processed)
    assert eng.list_queued() == []
    assert eng.health()["processed"] == 2

    # Restart: new engine on same DB, no re-processing of already processed
    eng2 = SyncEngine(db)
    processed2 = []
    worker2 = SyncWorker(eng2, conn, "t1", "s1", lambda e: processed2.append(e.event_id), poll_interval=0.2)
    worker2.start()
    time.sleep(0.4)
    worker2.stop()
    assert processed2 == []  # nothing new, and processed events stay processed
    assert eng2.get_cursor("stub", "t1", "s1") is not None


def test_delete_event_processed(tmp_path):
    db = str(tmp_path / "del.db")
    conn = StubConnector([])
    conn.authenticate({})
    eng = SyncEngine(db)

    deleted = []

    def proc(e: SyncEvent):
        if e.kind == "delete":
            deleted.append(e.payload["object_id"])

    # Manually enqueue a delete (as a connector would)
    del_ev = conn.handle_deletion("obj-x", "t", "s")
    assert eng.enqueue(del_ev) is True

    worker = SyncWorker(eng, conn, "t", "s", proc, poll_interval=10.0)  # no auto-poll needed
    # Process directly to avoid timing
    eid = eng.process_next(proc)
    assert eid == del_ev.event_id
    assert deleted == ["obj-x"]
    assert eng.list_queued() == []


def test_worker_health_reports_running(tmp_path):
    db = str(tmp_path / "h.db")
    conn = StubConnector([])
    conn.authenticate({})
    eng = SyncEngine(db)
    worker = SyncWorker(eng, conn, "t", "s", lambda e: None, poll_interval=1.0)
    h = worker.health()
    assert h["worker_running"] is False
    worker.start()
    time.sleep(0.1)
    h = worker.health()
    assert h["worker_running"] is True
    worker.stop()
    assert worker.is_running is False

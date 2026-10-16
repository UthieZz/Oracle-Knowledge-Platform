"""Unit tests for SyncEngine durability, idempotency, and cursor."""
import tempfile
from pathlib import Path

from okc.connect.interfaces import SyncEvent
from okc.connect.sync_engine import SyncEngine


def test_enqueue_idempotent_and_process(tmp_path):
    db = str(tmp_path / "eng.db")
    eng = SyncEngine(db)
    ev = SyncEvent(
        event_id="e1",
        source="stub",
        kind="create",
        cursor="1",
        payload={"text": "hello"},
        tenant_id="t",
        silo_id="s",
    )
    assert eng.enqueue(ev) is True
    assert eng.enqueue(ev) is False  # idempotent
    assert eng.list_queued() == ["e1"]

    processed = []

    def proc(e):
        processed.append(e.event_id)
        assert e.payload["text"] == "hello"

    eid = eng.process_next(proc)
    assert eid == "e1"
    assert processed == ["e1"]
    assert eng.list_queued() == []
    assert eng.get_cursor("stub", "t", "s") == "1"
    h = eng.health()
    assert h["processed"] == 1
    assert h["queued"] == 0


def test_process_empty_returns_none(tmp_path):
    eng = SyncEngine(str(tmp_path / "empty.db"))
    assert eng.process_next(lambda e: None) is None

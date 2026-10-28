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


def test_retry_until_success_then_advances_cursor(tmp_path):
    """Processor fails twice, then succeeds. Event stays queued, cursor not advanced until success."""
    db = str(tmp_path / "retry.db")
    eng = SyncEngine(db, max_attempts=5)
    ev = SyncEvent(
        event_id="retry1",
        source="stub",
        kind="create",
        cursor="c1",
        payload={"text": "retry me"},
        tenant_id="t",
        silo_id="s",
    )
    eng.enqueue(ev)

    calls = []

    def proc(e):
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("transient")

    assert eng.process_next(proc) is None
    assert eng.list_queued() == ["retry1"]
    assert eng.get_cursor("stub", "t", "s") is None
    h = eng.health()
    assert h["queued"] == 1
    assert h["failed_or_stuck"] == 0

    assert eng.process_next(proc) is None
    assert eng.list_queued() == ["retry1"]

    eid = eng.process_next(proc)
    assert eid == "retry1"
    assert eng.list_queued() == []
    assert eng.get_cursor("stub", "t", "s") == "c1"
    assert eng.health()["processed"] == 1


def test_retry_exhaustion_marks_failed_no_cursor(tmp_path):
    """After max_attempts the event is marked failed and cursor is not advanced."""
    db = str(tmp_path / "exhaust.db")
    eng = SyncEngine(db, max_attempts=2)
    ev = SyncEvent(
        event_id="fail1",
        source="stub",
        kind="create",
        cursor="c2",
        payload={"text": "will fail"},
        tenant_id="t",
        silo_id="s",
    )
    eng.enqueue(ev)

    def proc(e):
        raise ValueError("permanent")

    assert eng.process_next(proc) is None
    assert eng.list_queued() == ["fail1"]
    assert eng.get_cursor("stub", "t", "s") is None

    assert eng.process_next(proc) is None
    # Now failed, no longer queued
    assert eng.list_queued() == []
    assert eng.get_cursor("stub", "t", "s") is None
    h = eng.health()
    assert h["failed_or_stuck"] >= 1
    assert h["queued"] == 0
    assert h["processed"] == 0

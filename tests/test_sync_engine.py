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

    import time
    time.sleep(2.1)  # wait past first backoff
    assert eng.process_next(proc) is None
    assert eng.list_queued() == ["retry1"]

    time.sleep(4.1)  # wait past second backoff (4s)
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

    import time
    time.sleep(2.1)  # wait past backoff before second attempt
    assert eng.process_next(proc) is None
    # Now failed, no longer queued
    assert eng.list_queued() == []
    assert eng.get_cursor("stub", "t", "s") is None
    h = eng.health()
    assert h["failed_or_stuck"] >= 1
    assert h["queued"] == 0
    assert h["processed"] == 0


def test_reset_failed_allows_manual_recovery(tmp_path):
    """Failed events can be reset to queued for operator-initiated recovery."""
    db = str(tmp_path / "recover.db")
    eng = SyncEngine(db, max_attempts=1)
    ev = SyncEvent(
        event_id="stuck1",
        source="stub",
        kind="create",
        cursor="c3",
        payload={"text": "needs recovery"},
        tenant_id="t",
        silo_id="s",
    )
    eng.enqueue(ev)

    def fail(e):
        raise RuntimeError("permanent")

    assert eng.process_next(fail) is None
    assert eng.list_failed() == ["stuck1"]
    assert eng.list_queued() == []
    assert eng.get_cursor("stub", "t", "s") is None

    assert eng.reset_failed("stuck1") is True
    assert eng.list_failed() == []
    assert eng.list_queued() == ["stuck1"]

    # Now succeeds on recovery
    def succeed(e):
        pass

    eid = eng.process_next(succeed)
    assert eid == "stuck1"
    assert eng.list_queued() == []
    assert eng.get_cursor("stub", "t", "s") == "c3"
    assert eng.reset_failed("nonexistent") is False



def test_health_reports_failed_and_queue_age(tmp_path):
    """Health includes explicit failed count and oldest queued age."""
    db = str(tmp_path / "age.db")
    eng = SyncEngine(db, max_attempts=1)
    ev = SyncEvent(
        event_id="aged1",
        source="stub",
        kind="create",
        cursor=None,
        payload={"text": "old"},
        tenant_id="t",
        silo_id="s",
    )
    eng.enqueue(ev)
    # Force failure
    def fail(e):
        raise RuntimeError("x")
    eng.process_next(fail)
    h = eng.health()
    assert h["failed"] == 1
    assert h["queued"] == 0
    assert h["failed_or_stuck"] >= 1
    assert h["oldest_queued_age_seconds"] is None

    # Enqueue a live one
    ev2 = SyncEvent(
        event_id="live1",
        source="stub",
        kind="create",
        cursor=None,
        payload={"text": "new"},
        tenant_id="t",
        silo_id="s",
    )
    eng.enqueue(ev2)
    h = eng.health()
    assert h["queued"] == 1
    assert h["oldest_queued_age_seconds"] is not None
    assert h["oldest_queued_age_seconds"] >= 0


def test_interrupted_after_processor_success_does_not_advance_cursor(tmp_path):
    """If the processor raises after doing its work, the event stays queued,
    cursor is not advanced, and a later successful process_next completes
    and advances the cursor. Models a crash between processor effect and
    durable mark/cursor update.
    """
    db = str(tmp_path / "interrupt.db")
    eng = SyncEngine(db)
    ev = SyncEvent(
        event_id="int1",
        source="stub",
        kind="create",
        cursor="c-int",
        payload={"text": "interrupt me"},
        tenant_id="t",
        silo_id="s",
    )
    eng.enqueue(ev)

    calls = []

    def proc(e):
        calls.append(e.event_id)
        if len(calls) == 1:
            # First attempt: do work then fail (crash boundary)
            raise RuntimeError("simulated crash after processor work")
        # Second attempt: succeed

    eid = eng.process_next(proc)
    assert eid is None
    assert eng.list_queued() == ["int1"]
    assert eng.get_cursor("stub", "t", "s") is None
    assert len(calls) == 1

    # Make the event immediately eligible again (ignore backoff for this crash-boundary case)
    with eng._conn() as conn:
        conn.execute("UPDATE events SET next_retry_at = NULL WHERE event_id = ?", ("int1",))

    eid2 = eng.process_next(proc)
    assert eid2 == "int1"
    assert eng.list_queued() == []
    assert eng.get_cursor("stub", "t", "s") == "c-int"
    assert len(calls) == 2


def test_health_last_processed_and_failed_details(tmp_path):
    """health() returns last_processed_at; list_failed_details surfaces last_error/attempts."""
    db = str(tmp_path / "h.db")
    eng = SyncEngine(db)
    # Process one successfully
    ev_ok = SyncEvent(
        event_id="ok1",
        source="stub",
        kind="create",
        cursor=None,
        payload={"text": "ok"},
        tenant_id="t",
        silo_id="s",
    )
    eng.enqueue(ev_ok)
    assert eng.process_next(lambda e: None) == "ok1"
    h = eng.health()
    assert h["processed"] == 1
    assert h["last_processed_at"] is not None
    assert "T" in h["last_processed_at"] or "-" in h["last_processed_at"]  # ISO-ish

    # Fail one
    ev_fail = SyncEvent(
        event_id="fail1",
        source="stub",
        kind="create",
        cursor=None,
        payload={"text": "fail"},
        tenant_id="t",
        silo_id="s",
    )
    eng.enqueue(ev_fail)
    def boom(e):
        raise ValueError("boom detail")
    # exhaust retries
    for _ in range(eng.max_attempts):
        eng.process_next(boom)
        # clear backoff so we can exhaust quickly
        with eng._conn() as conn:
            conn.execute("UPDATE events SET next_retry_at = NULL WHERE event_id = ?", ("fail1",))
    assert "fail1" in eng.list_failed()
    details = eng.list_failed_details()
    assert len(details) == 1
    d = details[0]
    assert d["event_id"] == "fail1"
    assert d["attempts"] == eng.max_attempts
    assert "boom" in (d["last_error"] or "")
    assert d["enqueued_at"]


def test_health_reports_ready_and_waiting(tmp_path):
    from datetime import datetime, timedelta, timezone
    eng = SyncEngine(str(tmp_path / "h.db"), max_attempts=3)
    # Immediate ready
    eng.enqueue(SyncEvent(event_id="r1", source="s", kind="create", cursor=None, payload={}, tenant_id="t", silo_id="s"))
    # Waiting for retry
    eng.enqueue(SyncEvent(event_id="w1", source="s", kind="create", cursor=None, payload={}, tenant_id="t", silo_id="s"))
    future = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
    with eng._conn() as conn:
        conn.execute("UPDATE events SET next_retry_at = ?, status = 'queued' WHERE event_id = ?", (future, "w1"))
    h = eng.health()
    assert h["queued"] == 2
    assert h["ready_to_process"] == 1
    assert h["waiting_for_retry"] == 1
    assert h["failed"] == 0

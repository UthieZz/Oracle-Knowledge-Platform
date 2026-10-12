"""Tests for persistent SyncEngine: enqueue, idempotency, cursor, process, retry."""
from okc.connect.interfaces import SyncEvent
from okc.connect.sync_engine import SyncEngine


def test_enqueue_idempotent_and_cursor(tmp_path):
    db = str(tmp_path / "sync.db")
    eng = SyncEngine(db_path=db)
    ev = SyncEvent(
        event_id="e1",
        source="dummy",
        kind="create",
        cursor="c1",
        payload={"text": "hello"},
        tenant_id="t",
        silo_id="s",
    )
    assert eng.enqueue(ev) is True
    assert eng.enqueue(ev) is False  # duplicate event_id
    assert eng.get_cursor("dummy", "t", "s") is None
    queued = eng.list_queued()
    assert len(queued) == 1
    assert queued[0].event_id == "e1"

    processed = []

    def processor(e: SyncEvent) -> None:
        processed.append(e.event_id)

    eid = eng.process_next(processor)
    assert eid == "e1"
    assert processed == ["e1"]
    assert eng.get_cursor("dummy", "t", "s") == "c1"
    assert eng.list_queued() == []
    health = eng.health()
    assert health["processed"] == 1
    assert health["queued"] == 0


def test_retry_then_fail(tmp_path):
    db = str(tmp_path / "sync.db")
    eng = SyncEngine(db_path=db)
    ev = SyncEvent(
        event_id="e2",
        source="dummy",
        kind="update",
        tenant_id="t",
        silo_id="s",
    )
    eng.enqueue(ev)

    def failing(_e: SyncEvent) -> None:
        raise RuntimeError("boom")

    try:
        eng.process_next(failing, max_attempts=2)
    except RuntimeError:
        pass
    # still queued after first failure
    assert len(eng.list_queued()) == 1
    try:
        eng.process_next(failing, max_attempts=2)
    except RuntimeError:
        pass
    # now failed
    assert eng.list_queued() == []
    health = eng.health()
    assert health["failed"] == 1

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


def test_restart_recovery(tmp_path):
    """Queued events survive process restart (new SyncEngine on same DB)."""
    db = str(tmp_path / "restart.db")
    eng1 = SyncEngine(db_path=db)
    ev = SyncEvent(
        event_id="recover-1",
        source="dummy",
        kind="create",
        cursor="c-recover",
        payload={"text": "survives restart"},
        tenant_id="t",
        silo_id="s",
    )
    assert eng1.enqueue(ev) is True
    # Simulate crash: drop eng1, open new instance
    eng2 = SyncEngine(db_path=db)
    queued = eng2.list_queued()
    assert len(queued) == 1
    assert queued[0].event_id == "recover-1"
    assert eng2.get_cursor("dummy", "t", "s") is None

    processed = []

    def processor(e: SyncEvent) -> None:
        processed.append(e.payload["text"])

    eid = eng2.process_next(processor)
    assert eid == "recover-1"
    assert processed == ["survives restart"]
    assert eng2.get_cursor("dummy", "t", "s") == "c-recover"
    assert eng2.health()["processed"] == 1
    assert eng2.list_queued() == []


def test_delete_event_processed(tmp_path):
    """Delete events are queued and marked processed after successful handler."""
    db = str(tmp_path / "del.db")
    eng = SyncEngine(db_path=db)
    ev = SyncEvent(
        event_id="del-1",
        source="dummy",
        kind="delete",
        payload={"object_id": "obj-42"},
        tenant_id="t",
        silo_id="s",
    )
    assert eng.enqueue(ev) is True

    seen = []

    def processor(e: SyncEvent) -> None:
        assert e.kind == "delete"
        seen.append(e.payload["object_id"])

    eid = eng.process_next(processor)
    assert eid == "del-1"
    assert seen == ["obj-42"]
    assert eng.health()["processed"] == 1
    assert eng.list_queued() == []


def test_worker_processes_and_stops(tmp_path):
    """Minimal worker drains queue then can be observed via health."""
    from okc.connect.sync_engine import SyncWorker

    db = str(tmp_path / "worker.db")
    eng = SyncEngine(db_path=db)
    for i in range(2):
        eng.enqueue(
            SyncEvent(
                event_id=f"w{i}",
                source="dummy",
                kind="create",
                payload={"i": i},
                tenant_id="t",
                silo_id="s",
            )
        )

    processed = []

    def processor(e: SyncEvent) -> None:
        processed.append(e.event_id)

    worker = SyncWorker(eng, processor, poll_interval=0.01)
    # Run a bounded number of iterations so the test finishes.
    worker.start(max_iterations=5)
    assert set(processed) == {"w0", "w1"}
    assert eng.health()["processed"] == 2
    assert eng.health()["queued"] == 0
    h = worker.health()
    assert h["running"] is False

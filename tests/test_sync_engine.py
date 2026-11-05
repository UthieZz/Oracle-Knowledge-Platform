"""Unit tests for SyncEngine durability, idempotency, and cursor."""
import tempfile
from pathlib import Path

import pytest

from okc.connect.sync_engine import SyncEngine
from okc.connect.interfaces import SyncEvent


def test_enqueue_is_idempotent_by_event_id(tmp_path):
    db = str(tmp_path / "q.db")
    eng = SyncEngine(db)
    ev = SyncEvent(
        event_id="e1",
        source="stub",
        kind="create",
        cursor="c1",
        payload={"text": "hello"},
        tenant_id="t1",
        silo_id="s1",
    )
    assert eng.enqueue(ev) is True
    assert eng.enqueue(ev) is False  # duplicate
    assert eng.list_queued() == ["e1"]


def test_process_next_marks_processed_and_advances_cursor(tmp_path):
    db = str(tmp_path / "q.db")
    eng = SyncEngine(db)
    ev = SyncEvent(
        event_id="e1",
        source="stub",
        kind="create",
        cursor="c1",
        payload={"text": "hello"},
        tenant_id="t1",
        silo_id="s1",
    )
    eng.enqueue(ev)
    assert eng.process_next(lambda e: None) == "e1"
    assert eng.list_queued() == []
    assert eng.get_cursor("stub", "t1", "s1") == "c1"


def test_process_next_failure_retries_then_fails(tmp_path):
    db = str(tmp_path / "q.db")
    eng = SyncEngine(db, max_attempts=2)
    ev = SyncEvent(
        event_id="e1",
        source="stub",
        kind="create",
        cursor="c1",
        payload={"text": "hello"},
        tenant_id="t1",
        silo_id="s1",
    )
    eng.enqueue(ev)

    def boom(e):
        raise RuntimeError("fail")

    assert eng.process_next(boom) is None
    assert eng.list_queued() == ["e1"]
    assert eng.process_next(boom) is None
    assert eng.list_queued() == []
    assert eng.list_failed() == ["e1"]


def test_reset_failed_returns_to_queued(tmp_path):
    db = str(tmp_path / "q.db")
    eng = SyncEngine(db, max_attempts=1)
    ev = SyncEvent(
        event_id="e1",
        source="stub",
        kind="create",
        cursor="c1",
        payload={"text": "hello"},
        tenant_id="t1",
        silo_id="s1",
    )
    eng.enqueue(ev)
    eng.process_next(lambda e: (_ for _ in ()).throw(RuntimeError("x")))
    assert eng.list_failed() == ["e1"]
    assert eng.reset_failed("e1") is True
    assert eng.list_queued() == ["e1"]
    assert eng.list_failed() == []


def test_interrupted_process_does_not_advance_cursor(tmp_path):
    db = str(tmp_path / "q.db")
    eng = SyncEngine(db)
    ev = SyncEvent(
        event_id="e1",
        source="stub",
        kind="create",
        cursor="c1",
        payload={"text": "hello"},
        tenant_id="t1",
        silo_id="s1",
    )
    eng.enqueue(ev)

    def crash(e):
        raise RuntimeError("simulated crash")

    assert eng.process_next(crash) is None
    assert eng.get_cursor("stub", "t1", "s1") is None
    assert eng.list_queued() == ["e1"]


def test_health_includes_last_processed_and_failed_details(tmp_path):
    db = str(tmp_path / "q.db")
    eng = SyncEngine(db)
    ev = SyncEvent(
        event_id="e1",
        source="stub",
        kind="create",
        cursor="c1",
        payload={"text": "hello"},
        tenant_id="t1",
        silo_id="s1",
    )
    eng.enqueue(ev)
    eng.process_next(lambda e: None)
    h = eng.health()
    assert h["processed"] == 1
    assert "last_processed_at" in h
    details = eng.list_failed_details()
    assert isinstance(details, list)


def test_list_cursors_returns_scope_state_after_success(tmp_path):
    db = str(tmp_path / "q.db")
    eng = SyncEngine(db)
    ev = SyncEvent(
        event_id="e1",
        source="stub",
        kind="create",
        cursor="c1",
        payload={"text": "hello"},
        tenant_id="t1",
        silo_id="s1",
    )
    eng.enqueue(ev)
    eng.process_next(lambda e: None)
    cursors = eng.list_cursors()
    assert len(cursors) == 1
    assert cursors[0]["source"] == "stub"
    assert cursors[0]["tenant_id"] == "t1"
    assert cursors[0]["silo_id"] == "s1"
    assert cursors[0]["cursor"] == "c1"
    assert "updated_at" in cursors[0]


def test_multi_instance_same_db_enqueue_process_visibility(tmp_path):
    db = str(tmp_path / "q.db")
    eng_a = SyncEngine(db)
    eng_b = SyncEngine(db)

    ev = SyncEvent(
        event_id="shared1",
        source="stub",
        kind="create",
        cursor="c1",
        payload={"text": "visible"},
        tenant_id="t1",
        silo_id="s1",
    )
    assert eng_a.enqueue(ev) is True
    # Second instance sees the queued event
    assert eng_b.list_queued() == ["shared1"]
    h_b = eng_b.health()
    assert h_b["queued"] == 1
    assert h_b["ready_to_process"] == 1

    # Process from instance A
    assert eng_a.process_next(lambda e: None) == "shared1"
    # Instance B sees it processed and cursor advanced
    assert eng_b.list_queued() == []
    assert eng_b.health()["processed"] == 1
    assert eng_b.get_cursor("stub", "t1", "s1") == "c1"
    assert eng_a.get_cursor("stub", "t1", "s1") == "c1"

    # Idempotent re-enqueue from either does not re-queue
    assert eng_b.enqueue(ev) is False
    assert eng_a.list_queued() == []


def test_concurrent_enqueue_and_process_from_multiple_threads(tmp_path):
    """True parallel writers (threads) on the same WAL DB enqueue and process without loss or corruption.

    Advances remaining P0 concurrent failure case. Sequential multi-instance already covered.
    """
    import threading

    db = str(tmp_path / "concurrent.db")
    eng = SyncEngine(db)
    results = []
    errors = []

    def worker(i: int):
        try:
            local = SyncEngine(db)
            for j in range(5):
                ev = SyncEvent(
                    event_id=f"t{i}-{j}",
                    source="stub",
                    kind="create",
                    cursor=f"c{i}",
                    payload={"n": i * 10 + j},
                    tenant_id="t1",
                    silo_id="s1",
                )
                local.enqueue(ev)
            # Process some
            for _ in range(3):
                local.process_next(lambda e: None)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"thread errors: {errors}"

    final = SyncEngine(db)
    health = final.health()
    # 4 threads * 5 enqueues = 20 unique events
    assert health["processed"] + health["queued"] + health["failed"] == 20
    assert health["failed"] == 0
    # All eventually processable; run remaining
    while final.process_next(lambda e: None):
        pass
    assert final.health()["processed"] == 20
    assert final.health()["queued"] == 0
    assert final.get_cursor("stub", "t1", "s1") is not None

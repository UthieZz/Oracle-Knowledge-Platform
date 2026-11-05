"""KnowledgeAccumulator: applies SyncEvents to a living KnowledgePackage."""
from pathlib import Path

from okc.connect.knowledge_accumulator import KnowledgeAccumulator
from okc.connect.interfaces import SyncEvent
from okc.agent.retrievers import KnowledgePackageRetriever


def test_accumulator_create_update_delete_reflected_in_retrieval(tmp_path):
    pkg_path = str(tmp_path / "living.json")
    acc = KnowledgeAccumulator(package_path=pkg_path)

    create = SyncEvent(
        event_id="e1",
        source="local",
        kind="create",
        cursor=None,
        payload={"object_id": "doc1", "text": "Initial content."},
        occurred_at="2026-11-05T00:00:00Z",
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(create)
    assert len(acc.package.objects) == 1

    update = SyncEvent(
        event_id="e2",
        source="local",
        kind="update",
        cursor=None,
        payload={"object_id": "doc1", "text": "Updated content."},
        occurred_at="2026-11-05T00:01:00Z",
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(update)
    assert len(acc.package.objects) == 1
    assert "Updated" in acc.package.objects[0].content

    delete = SyncEvent(
        event_id="e3",
        source="local",
        kind="delete",
        cursor=None,
        payload={"object_id": "doc1"},
        occurred_at="2026-11-05T00:02:00Z",
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(delete)
    assert len(acc.package.objects) == 0

    # Reload confirms persistence
    acc2 = KnowledgeAccumulator(package_path=pkg_path)
    assert len(acc2.package.objects) == 0


def test_permission_change_read_false_excludes_from_retrieval(tmp_path):
    """permission_change with read=False is enforced fail-closed by KnowledgePackageRetriever."""
    pkg_path = str(tmp_path / "living.json")
    acc = KnowledgeAccumulator(package_path=pkg_path)

    create = SyncEvent(
        event_id="e1",
        source="local",
        kind="create",
        cursor=None,
        payload={"object_id": "doc1", "text": "Secret content."},
        occurred_at="2026-11-05T00:00:00Z",
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(create)

    revoke = SyncEvent(
        event_id="e2",
        source="local",
        kind="permission_change",
        cursor=None,
        payload={"object_id": "doc1", "read": False},
        occurred_at="2026-11-05T00:01:00Z",
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(revoke)

    retriever = KnowledgePackageRetriever(acc.package)
    results = retriever.retrieve("Secret", tenant_id="t1", silo_id="s1")
    assert len(results) == 0

    restore = SyncEvent(
        event_id="e3",
        source="local",
        kind="permission_change",
        cursor=None,
        payload={"object_id": "doc1", "read": True},
        occurred_at="2026-11-05T00:02:00Z",
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(restore)
    results = retriever.retrieve("Secret", tenant_id="t1", silo_id="s1")
    assert len(results) == 1


def test_persist_failure_rolls_back_in_memory_and_retry_succeeds(tmp_path, monkeypatch):
    pkg_path = str(tmp_path / "living.json")
    acc = KnowledgeAccumulator(package_path=pkg_path)

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(acc, "_persist", boom)

    event = SyncEvent(
        event_id="e1",
        source="local",
        kind="create",
        cursor=None,
        payload={"object_id": "doc1", "text": "content"},
        occurred_at="2026-11-05T00:00:00Z",
        tenant_id="t1",
        silo_id="s1",
    )
    try:
        acc.process(event)
        assert False, "should have raised"
    except OSError:
        pass

    # In-memory state rolled back
    assert len(acc.package.objects) == 0
    # File not written
    assert not Path(pkg_path).exists()

    # Retry succeeds
    monkeypatch.undo()
    acc.process(event)
    assert len(acc.package.objects) == 1


def test_permission_change_survives_package_reload(tmp_path):
    """P1 boundary: explicit permission_change (read=False) is persisted in package
    metadata and remains enforced by KnowledgePackageRetriever after package reload.
    """
    pkg_path = str(tmp_path / "living.json")
    acc = KnowledgeAccumulator(package_path=pkg_path)

    create = SyncEvent(
        event_id="e1",
        source="local",
        kind="create",
        cursor=None,
        payload={"object_id": "doc1", "text": "content"},
        occurred_at="2026-11-05T00:00:00Z",
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(create)

    revoke = SyncEvent(
        event_id="e2",
        source="local",
        kind="permission_change",
        cursor=None,
        payload={"object_id": "doc1", "read": False},
        occurred_at="2026-11-05T00:01:00Z",
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(revoke)

    # Reload
    acc2 = KnowledgeAccumulator(package_path=pkg_path)
    retriever = KnowledgePackageRetriever(acc2.package)
    results = retriever.retrieve("content", tenant_id="t1", silo_id="s1")
    assert len(results) == 0


def test_delete_removes_permission_metadata(tmp_path):
    """Delete event removes the corresponding permission metadata entry.
    Prevents stale permission records after object removal. Advances P1 provenance consistency.
    """
    pkg_path = str(tmp_path / "living.json")
    acc = KnowledgeAccumulator(package_path=pkg_path)

    create = SyncEvent(
        event_id="e1",
        source="local",
        kind="create",
        cursor=None,
        payload={"object_id": "doc1", "text": "content"},
        occurred_at="2026-11-05T00:00:00Z",
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(create)

    revoke = SyncEvent(
        event_id="e2",
        source="local",
        kind="permission_change",
        cursor=None,
        payload={"object_id": "doc1", "read": False},
        occurred_at="2026-11-05T00:01:00Z",
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(revoke)
    scoped = "local|t1|s1|doc1"
    assert scoped in acc.package.metadata.get("permissions", {})

    delete = SyncEvent(
        event_id="e3",
        source="local",
        kind="delete",
        cursor=None,
        payload={"object_id": "doc1"},
        occurred_at="2026-11-05T00:02:00Z",
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(delete)
    assert scoped not in acc.package.metadata.get("permissions", {})

    # Reload confirms
    acc2 = KnowledgeAccumulator(package_path=pkg_path)
    assert scoped not in acc2.package.metadata.get("permissions", {})


def test_permission_change_normalizes_non_dict_metadata(tmp_path):
    """permission_change normalizes a non-dict permissions entry to a dict before recording.
    Prevents KeyError or type errors if metadata was externally mutated.
    """
    pkg_path = str(tmp_path / "living.json")
    acc = KnowledgeAccumulator(package_path=pkg_path)
    # Simulate corrupted metadata
    acc.package.metadata["permissions"] = "not-a-dict"
    event = SyncEvent(
        event_id="perm-norm-1",
        source="local",
        kind="permission_change",
        cursor=None,
        payload={"object_id": "doc1", "read": False},
        occurred_at="2026-11-05T00:00:00Z",
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(event)
    scoped = "local|t1|s1|doc1"
    assert isinstance(acc.package.metadata["permissions"], dict)
    assert scoped in acc.package.metadata["permissions"]
    # Survives reload
    acc2 = KnowledgeAccumulator(package_path=pkg_path)
    assert scoped in acc2.package.metadata.get("permissions", {})

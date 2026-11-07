from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from okc.agent.models import AgentContextRequest
from okc.agent.retrievers import KnowledgePackageRetriever
from okc.connect.interfaces import SyncEvent
from okc.connect.knowledge_accumulator import KnowledgeAccumulator
from okc.models.knowledge_package import KnowledgePackage


def _request(task: str, tenant: str = "t", silo: str = "s") -> AgentContextRequest:
    return AgentContextRequest(
        request_id="r1",
        tenant_id=tenant,
        silo_id=silo,
        agent_id="a",
        task=task,
    )


def test_accumulator_create_update_delete_reflected_in_retrieval(tmp_path):
    pkg_path = str(tmp_path / "living.json")
    acc = KnowledgeAccumulator(package_path=pkg_path)

    create = SyncEvent(
        event_id="c1",
        source="folder",
        kind="create",
        cursor="1",
        payload={"object_id": "doc1", "text": "hello world knowledge"},
        tenant_id="t",
        silo_id="s",
    )
    acc.process(create)

    retriever = KnowledgePackageRetriever(acc.package)
    hits = retriever.retrieve(_request("hello world"))
    assert len(hits) == 1
    assert "hello world knowledge" in hits[0].content
    assert any(rid.startswith("src:folder|t|s|") for rid in hits[0].provenance.source_record_ids)

    update = SyncEvent(
        event_id="u1",
        source="folder",
        kind="update",
        cursor="2",
        payload={"object_id": "doc1", "text": "hello updated knowledge"},
        tenant_id="t",
        silo_id="s",
    )
    acc.process(update)
    hits2 = retriever.retrieve(_request("updated"))
    assert len(hits2) == 1
    assert "updated" in hits2[0].content

    delete = SyncEvent(
        event_id="d1",
        source="folder",
        kind="delete",
        cursor="3",
        payload={"object_id": "doc1"},
        tenant_id="t",
        silo_id="s",
    )
    acc.process(delete)
    hits3 = retriever.retrieve(_request("hello"))
    assert len(hits3) == 0


def test_permission_change_read_false_excludes_from_retrieval(tmp_path):
    """permission_change with read=False is enforced fail-closed by KnowledgePackageRetriever."""
    acc = KnowledgeAccumulator()

    create = SyncEvent(
        event_id="c1",
        source="folder",
        kind="create",
        payload={"object_id": "doc1", "text": "secret knowledge"},
        tenant_id="t",
        silo_id="s",
    )
    acc.process(create)

    retriever = KnowledgePackageRetriever(acc.package)
    hits = retriever.retrieve(_request("secret"))
    assert len(hits) == 1

    revoke = SyncEvent(
        event_id="p1",
        source="folder",
        kind="permission_change",
        payload={"object_id": "doc1", "read": False},
        tenant_id="t",
        silo_id="s",
    )
    acc.process(revoke)

    hits_after = retriever.retrieve(_request("secret"))
    assert len(hits_after) == 0

    # Explicit restore
    restore = SyncEvent(
        event_id="p2",
        source="folder",
        kind="permission_change",
        payload={"object_id": "doc1", "read": True},
        tenant_id="t",
        silo_id="s",
    )
    acc.process(restore)
    hits_restored = retriever.retrieve(_request("secret"))
    assert len(hits_restored) == 1


def test_persist_failure_rolls_back_in_memory_and_retry_succeeds(tmp_path):
    """Crash boundary: if _persist raises after mutation, in-memory package,
    source index and metadata are restored. Subsequent retry (same accumulator)
    succeeds and persists. Atomic write means no partial package file is left.
    """
    pkg_path = tmp_path / "living.json"
    acc = KnowledgeAccumulator(package_path=str(pkg_path))

    # Seed one object so we can observe rollback of a second mutation.
    seed = SyncEvent(
        event_id="seed",
        source="folder",
        kind="create",
        payload={"object_id": "doc0", "text": "seed knowledge"},
        tenant_id="t",
        silo_id="s",
    )
    acc.process(seed)
    assert len(acc.package.objects) == 1
    assert pkg_path.exists()

    failing = SyncEvent(
        event_id="fail",
        source="folder",
        kind="create",
        payload={"object_id": "doc1", "text": "should not stick"},
        tenant_id="t",
        silo_id="s",
    )

    with patch.object(KnowledgeAccumulator, "_persist", side_effect=RuntimeError("disk full")):
        with pytest.raises(RuntimeError, match="disk full"):
            acc.process(failing)

    # Rolled back: still only the seed object.
    assert len(acc.package.objects) == 1
    # Source index restored; the seed marker is still present.
    assert any("doc0" in rid or "folder|t|s|doc0" in rid for rid in acc.package.objects[0].provenance.source_record_ids)
    # No partial write: the on-disk package remains the previous good one.
    on_disk = KnowledgePackage.from_json(pkg_path.read_text(encoding="utf-8"))
    assert len(on_disk.objects) == 1

    # Retry without the patch succeeds and persists.
    acc.process(failing)
    assert len(acc.package.objects) == 2
    on_disk2 = KnowledgePackage.from_json(pkg_path.read_text(encoding="utf-8"))
    assert len(on_disk2.objects) == 2


def test_permission_change_survives_package_reload(tmp_path):
    """P1 boundary: explicit permission_change (read=False) is persisted in package
    metadata and remains enforced after process restart / package reload.
    """
    pkg_path = str(tmp_path / "living.json")
    acc = KnowledgeAccumulator(package_path=pkg_path)

    create = SyncEvent(
        event_id="c1",
        source="folder",
        kind="create",
        payload={"object_id": "doc1", "text": "secret knowledge"},
        tenant_id="t",
        silo_id="s",
    )
    acc.process(create)

    revoke = SyncEvent(
        event_id="p1",
        source="folder",
        kind="permission_change",
        payload={"object_id": "doc1", "read": False},
        tenant_id="t",
        silo_id="s",
    )
    acc.process(revoke)

    # Reload into a fresh accumulator (simulates restart).
    acc2 = KnowledgeAccumulator(package_path=pkg_path)
    retriever = KnowledgePackageRetriever(acc2.package)
    hits = retriever.retrieve(_request("secret"))
    assert len(hits) == 0

    # Explicit restore also survives reload.
    restore = SyncEvent(
        event_id="p2",
        source="folder",
        kind="permission_change",
        payload={"object_id": "doc1", "read": True},
        tenant_id="t",
        silo_id="s",
    )
    acc2.process(restore)
    acc3 = KnowledgeAccumulator(package_path=pkg_path)
    hits_restored = KnowledgePackageRetriever(acc3.package).retrieve(_request("secret"))
    assert len(hits_restored) == 1


def test_delete_removes_permission_metadata(tmp_path):
    """Delete event removes the corresponding permission metadata entry.
    Prevents stale permission records after object removal. Advances P1 provenance consistency.
    """
    pkg_path = str(tmp_path / "living.json")
    acc = KnowledgeAccumulator(package_path=pkg_path)
    # Create
    ev_c = SyncEvent(
        event_id="c1",
        source="lf",
        kind="create",
        cursor=None,
        payload={"object_id": "doc.txt", "text": "hello"},
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(ev_c)
    scoped = "lf|t1|s1|doc.txt"
    # Permission change
    ev_p = SyncEvent(
        event_id="p1",
        source="lf",
        kind="permission_change",
        cursor=None,
        payload={"object_id": "doc.txt", "read": False},
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(ev_p)
    assert scoped in acc.package.metadata.get("permissions", {})
    # Delete
    ev_d = SyncEvent(
        event_id="d1",
        source="lf",
        kind="delete",
        cursor=None,
        payload={"object_id": "doc.txt"},
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(ev_d)
    assert scoped not in acc.package.metadata.get("permissions", {})
    assert len(acc.package.objects) == 0
    # Reload confirms persistence
    acc2 = KnowledgeAccumulator(package_path=pkg_path)
    assert scoped not in acc2.package.metadata.get("permissions", {})


def test_reprocess_after_package_persist_is_idempotent(tmp_path):
    """Crash boundary: package persisted successfully, but engine failed to mark
    event processed (process killed after _persist, before SQLite UPDATE).
    On restart, the same event is re-delivered to a fresh accumulator loaded
    from the living package. Upsert must not duplicate objects or change count.
    """
    pkg_path = str(tmp_path / "living.json")
    acc = KnowledgeAccumulator(package_path=pkg_path)

    create = SyncEvent(
        event_id="c1",
        source="folder",
        kind="create",
        payload={"object_id": "doc1", "text": "stable content for idempotency"},
        tenant_id="t",
        silo_id="s",
    )
    acc.process(create)
    assert len(acc.package.objects) == 1
    original_obj_id = acc.package.objects[0].object_id
    assert pkg_path and Path(pkg_path).exists()

    # Simulate restart: fresh accumulator loads the persisted package.
    acc2 = KnowledgeAccumulator(package_path=pkg_path)
    assert len(acc2.package.objects) == 1

    # Re-deliver the identical event (engine retry after partial success).
    acc2.process(create)
    assert len(acc2.package.objects) == 1
    assert acc2.package.objects[0].object_id == original_obj_id
    assert "stable content for idempotency" in acc2.package.objects[0].content

    # On-disk package also remains single-object.
    on_disk = KnowledgePackage.from_json(Path(pkg_path).read_text(encoding="utf-8"))
    assert len(on_disk.objects) == 1
    assert on_disk.objects[0].object_id == original_obj_id


def test_missing_permission_entry_visible_by_default(tmp_path):
    """Documented compatibility: no permissions entry means object remains visible."""
    acc = KnowledgeAccumulator()
    create = SyncEvent(
        event_id="c1",
        source="folder",
        kind="create",
        payload={"object_id": "doc1", "text": "visible knowledge"},
        tenant_id="t",
        silo_id="s",
    )
    acc.process(create)
    retriever = KnowledgePackageRetriever(acc.package)  # strict_permissions=False
    hits = retriever.retrieve(_request("visible"))
    assert len(hits) == 1


def test_missing_permission_entry_denied_in_strict_mode(tmp_path):
    """Production mode: absence of permission entry is treated as denial."""
    acc = KnowledgeAccumulator()
    create = SyncEvent(
        event_id="c1",
        source="folder",
        kind="create",
        payload={"object_id": "doc1", "text": "restricted knowledge"},
        tenant_id="t",
        silo_id="s",
    )
    acc.process(create)
    retriever = KnowledgePackageRetriever(acc.package, strict_permissions=True)
    hits = retriever.retrieve(_request("restricted"))
    assert len(hits) == 0

    # Explicit allow restores visibility even in strict mode
    allow = SyncEvent(
        event_id="p1",
        source="folder",
        kind="permission_change",
        payload={"object_id": "doc1", "read": True},
        tenant_id="t",
        silo_id="s",
    )
    acc.process(allow)
    hits_allowed = retriever.retrieve(_request("restricted"))
    assert len(hits_allowed) == 1

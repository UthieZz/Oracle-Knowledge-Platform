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

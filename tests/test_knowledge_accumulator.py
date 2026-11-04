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

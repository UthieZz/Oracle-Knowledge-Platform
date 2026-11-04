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
        # reuse same object identity via path-like id; accumulator keys on scoped source
    )
    # Force same object_id by using consistent source/tenant/silo; the scoped id comes from event fields
    # In current implementation scoped is derived inside process from event.source etc + object identity in payload?
    # Looking at code, scoped is passed but how is object_id derived?
    # Re-inspect: process uses _scoped_source_id(event.source, event.tenant_id, event.silo_id, ???)
    # The code snippet showed scoped but not the derivation. Need to check full process.
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


def test_process_persist_failure_rolls_back_and_retry_succeeds(tmp_path):
    pkg_path = str(tmp_path / "living.json")
    acc = KnowledgeAccumulator(package_path=pkg_path)

    event = SyncEvent(
        event_id="fail1",
        source="folder",
        kind="create",
        cursor="1",
        payload={"object_id": "docfail", "text": "should rollback"},
        tenant_id="t",
        silo_id="s",
    )

    # First call: force persist to fail after mutation
    with patch.object(KnowledgeAccumulator, "_persist", side_effect=RuntimeError("disk full")):
        with pytest.raises(RuntimeError):
            acc.process(event)
        # In-memory state rolled back
        assert len(acc.package.objects) == 0
        assert acc._src_to_obj == {}

    # Retry succeeds
    acc.process(event)
    assert len(acc.package.objects) == 1
    assert Path(pkg_path).exists()
    data = json.loads(Path(pkg_path).read_text())
    assert len(data.get("objects", [])) == 1

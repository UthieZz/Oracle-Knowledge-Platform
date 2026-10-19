"""Tests that delete and update events update the living KnowledgePackage
so retrieval no longer sees deleted content.
"""
import tempfile
from pathlib import Path

from okc.connect.knowledge_accumulator import KnowledgeAccumulator
from okc.connect.local_folder_connector import LocalFolderConnector
from okc.connect.sync_engine import SyncEngine
from okc.agent.retrievers import KnowledgePackageRetriever
from okc.agent.models import AgentContextRequest


def test_accumulator_create_update_delete_reflected_in_retrieval(tmp_path):
    root = tmp_path / "docs"
    root.mkdir()
    (root / "keep.txt").write_text("Keep this knowledge.", encoding="utf-8")
    (root / "drop.txt").write_text("This will be deleted.", encoding="utf-8")

    conn = LocalFolderConnector(str(root))
    assert conn.authenticate({})

    acc = KnowledgeAccumulator()
    db = str(tmp_path / "acc.db")
    eng = SyncEngine(db)

    # Initial
    for ev in conn.initial_sync("t1", "s1"):
        eng.enqueue(ev)
    while eng.process_next(acc.process):
        pass

    assert len(acc.package.objects) == 2
    req = AgentContextRequest(request_id="r1", agent_id="test", task="knowledge", tenant_id="t1", silo_id="s1", max_context_items=10)
    retrieved = list(KnowledgePackageRetriever(acc.package).retrieve(req))
    contents = {o.content for o in retrieved}
    assert any("Keep this" in c for c in contents)
    assert any("deleted" in c for c in contents)

    # Delete drop.txt
    (root / "drop.txt").unlink()
    for ev in conn.incremental_sync("0", "t1", "s1"):
        eng.enqueue(ev)
    while eng.process_next(acc.process):
        pass

    assert len(acc.package.objects) == 1
    retrieved = list(KnowledgePackageRetriever(acc.package).retrieve(req))
    assert len(retrieved) == 1
    assert "Keep this" in retrieved[0].content
    assert "deleted" not in retrieved[0].content

    # Update keep.txt
    (root / "keep.txt").write_text("Keep this knowledge updated.", encoding="utf-8")
    for ev in conn.incremental_sync("0", "t1", "s1"):
        eng.enqueue(ev)
    while eng.process_next(acc.process):
        pass

    assert len(acc.package.objects) == 1
    retrieved = list(KnowledgePackageRetriever(acc.package).retrieve(req))
    assert "updated" in retrieved[0].content


def test_permission_change_recorded(tmp_path):
    from okc.connect.interfaces import SyncEvent
    acc = KnowledgeAccumulator()
    ev = SyncEvent(
        event_id="perm1",
        source="local_folder",
        kind="permission_change",
        payload={"object_id": "note.txt", "read": False},
        tenant_id="t",
        silo_id="s",
    )
    acc.process(ev)
    assert acc.package.metadata["permissions"]["note.txt"]["read"] is False


def test_permission_change_excludes_object_from_retrieval(tmp_path):
    """Fail-closed: permission_change with read=False removes object from retrieval."""
    from okc.connect.interfaces import SyncEvent

    acc = KnowledgeAccumulator()
    create = SyncEvent(
        event_id="c1",
        source="local_folder",
        kind="create",
        payload={"object_id": "secret.txt", "text": "Confidential source knowledge."},
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(create)
    assert len(acc.package.objects) == 1

    req = AgentContextRequest(
        request_id="r", agent_id="a", task="confidential", tenant_id="t1", silo_id="s1"
    )
    retrieved = list(KnowledgePackageRetriever(acc.package).retrieve(req))
    assert len(retrieved) == 1
    assert "Confidential" in retrieved[0].content

    # Deny read
    deny = SyncEvent(
        event_id="p1",
        source="local_folder",
        kind="permission_change",
        payload={"object_id": "secret.txt", "read": False},
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(deny)
    retrieved_after = list(KnowledgePackageRetriever(acc.package).retrieve(req))
    assert len(retrieved_after) == 0

    # Explicit allow restores it
    allow = SyncEvent(
        event_id="p2",
        source="local_folder",
        kind="permission_change",
        payload={"object_id": "secret.txt", "read": True},
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(allow)
    retrieved_allow = list(KnowledgePackageRetriever(acc.package).retrieve(req))
    assert len(retrieved_allow) == 1
    assert "Confidential" in retrieved_allow[0].content

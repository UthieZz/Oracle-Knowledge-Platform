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
from okc.connect.interfaces import SyncEvent


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
    scoped = "local_folder|t|s|note.txt"
    assert acc.package.metadata["permissions"][scoped]["read"] is False


def test_permission_change_excludes_object_from_retrieval(tmp_path):
    """Fail-closed: permission_change with read=False removes object from retrieval."""
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


def test_sync_worker_local_folder_accumulator_background_updates(tmp_path):
    """Background SyncWorker + LocalFolderConnector + KnowledgeAccumulator:
    initial sync, then file update and delete are reflected in retrieval
    without manual process_next calls.
    """
    import time
    from okc.connect.sync_worker import SyncWorker

    root = tmp_path / "watched"
    root.mkdir()
    (root / "alive.txt").write_text("Initial living knowledge.", encoding="utf-8")

    conn = LocalFolderConnector(str(root))
    assert conn.authenticate({})

    acc = KnowledgeAccumulator()
    db = str(tmp_path / "worker_acc.db")
    eng = SyncEngine(db)

    worker = SyncWorker(
        eng, conn, "tenant-w", "silo-w", acc.process, poll_interval=0.3
    )
    worker.start()
    time.sleep(0.8)  # allow initial poll + process
    worker.stop()

    assert len(acc.package.objects) == 1
    req = AgentContextRequest(
        request_id="rw", agent_id="test", task="living",
        tenant_id="tenant-w", silo_id="silo-w", max_context_items=5,
    )
    retrieved = list(KnowledgePackageRetriever(acc.package).retrieve(req))
    assert len(retrieved) == 1
    assert "Initial living" in retrieved[0].content

    # Background update
    (root / "alive.txt").write_text("Initial living knowledge — updated by worker.", encoding="utf-8")
    worker.start()
    time.sleep(0.8)
    worker.stop()

    retrieved = list(KnowledgePackageRetriever(acc.package).retrieve(req))
    assert len(retrieved) == 1
    assert "updated by worker" in retrieved[0].content

    # Background delete
    (root / "alive.txt").unlink()
    worker.start()
    time.sleep(0.8)
    worker.stop()

    retrieved = list(KnowledgePackageRetriever(acc.package).retrieve(req))
    assert len(retrieved) == 0
    assert len(acc.package.objects) == 0


def test_knowledge_accumulator_package_path_survives_restart(tmp_path):
    """Optional package_path makes the living package durable: process events,
    drop the accumulator, reload from the same path, retrieval reflects the state.
    """
    pkg_file = str(tmp_path / "living.json")
    acc = KnowledgeAccumulator(package_path=pkg_file)

    create = SyncEvent(
        event_id="e1",
        source="test",
        kind="create",
        payload={"object_id": "doc1", "text": "Durable living knowledge."},
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(create)
    assert Path(pkg_file).exists()
    assert len(acc.package.objects) == 1

    # Simulate process restart: new accumulator loads the file
    acc2 = KnowledgeAccumulator(package_path=pkg_file)
    assert len(acc2.package.objects) == 1
    req = AgentContextRequest(
        request_id="r", agent_id="test", task="durable",
        tenant_id="t1", silo_id="s1", max_context_items=5,
    )
    retrieved = list(KnowledgePackageRetriever(acc2.package).retrieve(req))
    assert len(retrieved) == 1
    assert "Durable living" in retrieved[0].content

    # Delete persists
    delete = SyncEvent(
        event_id="e2",
        source="test",
        kind="delete",
        payload={"object_id": "doc1"},
        tenant_id="t1",
        silo_id="s1",
    )
    acc2.process(delete)
    acc3 = KnowledgeAccumulator(package_path=pkg_file)
    assert len(acc3.package.objects) == 0
    retrieved = list(KnowledgePackageRetriever(acc3.package).retrieve(req))
    assert len(retrieved) == 0


def test_source_identity_namespaced_across_scopes(tmp_path):
    """Identical object_id (path) in different tenants/silos/sources must not collide.
    Each scoped identity keeps its own object.
    """
    acc = KnowledgeAccumulator()

    # Same path, different tenant
    e1 = SyncEvent(
        event_id="e1", source="local_folder", kind="create",
        payload={"object_id": "note.txt", "text": "Tenant A knowledge."},
        tenant_id="tenantA", silo_id="silo1",
    )
    e2 = SyncEvent(
        event_id="e2", source="local_folder", kind="create",
        payload={"object_id": "note.txt", "text": "Tenant B knowledge."},
        tenant_id="tenantB", silo_id="silo1",
    )
    # Same path, different silo
    e3 = SyncEvent(
        event_id="e3", source="local_folder", kind="create",
        payload={"object_id": "note.txt", "text": "Silo X knowledge."},
        tenant_id="tenantA", silo_id="siloX",
    )
    # Same path, different source
    e4 = SyncEvent(
        event_id="e4", source="other_source", kind="create",
        payload={"object_id": "note.txt", "text": "Other source knowledge."},
        tenant_id="tenantA", silo_id="silo1",
    )

    for e in (e1, e2, e3, e4):
        acc.process(e)

    assert len(acc.package.objects) == 4

    # Retrieval by tenant/silo sees only its own
    req_a = AgentContextRequest(request_id="ra", agent_id="t", task="a", tenant_id="tenantA", silo_id="silo1")
    got_a = list(KnowledgePackageRetriever(acc.package).retrieve(req_a))
    contents_a = {o.content for o in got_a}
    assert any("Tenant A" in c for c in contents_a)
    assert not any("Tenant B" in c for c in contents_a)
    assert any("Other source" in c for c in contents_a)  # different source, same tenant/silo

    req_b = AgentContextRequest(request_id="rb", agent_id="t", task="b", tenant_id="tenantB", silo_id="silo1")
    got_b = list(KnowledgePackageRetriever(acc.package).retrieve(req_b))
    assert len(got_b) == 1
    assert "Tenant B" in got_b[0].content

    # Delete only one scope
    del_a = SyncEvent(
        event_id="d1", source="local_folder", kind="delete",
        payload={"object_id": "note.txt"},
        tenant_id="tenantA", silo_id="silo1",
    )
    acc.process(del_a)
    assert len(acc.package.objects) == 3
    got_a_after = list(KnowledgePackageRetriever(acc.package).retrieve(req_a))
    assert not any("Tenant A knowledge" in o.content for o in got_a_after)
    # others remain
    assert len(list(KnowledgePackageRetriever(acc.package).retrieve(req_b))) == 1


def test_reprocess_after_simulated_crash_before_status_update_is_idempotent(tmp_path):
    """Reprocessing an already-applied event (crash after package persist,
    before SyncEngine marks processed) must not duplicate objects or leave
    inconsistent state. Package write is atomic.
    """
    pkg_file = str(tmp_path / "crash.json")
    acc = KnowledgeAccumulator(package_path=pkg_file)

    create = SyncEvent(
        event_id="crash-create",
        source="test",
        kind="create",
        payload={"object_id": "doc1", "text": "Knowledge that must not duplicate."},
        tenant_id="t1",
        silo_id="s1",
    )
    # First process (simulates success path up to persist)
    acc.process(create)
    assert len(acc.package.objects) == 1
    assert Path(pkg_file).exists()

    # Simulate crash: new process loads the persisted package, re-processes same event
    acc_re = KnowledgeAccumulator(package_path=pkg_file)
    acc_re.process(create)
    assert len(acc_re.package.objects) == 1
    contents = {o.content for o in acc_re.package.objects}
    assert "must not duplicate" in next(iter(contents))

    # Delete then reprocess delete
    delete = SyncEvent(
        event_id="crash-delete",
        source="test",
        kind="delete",
        payload={"object_id": "doc1"},
        tenant_id="t1",
        silo_id="s1",
    )
    acc_re.process(delete)
    assert len(acc_re.package.objects) == 0

    acc_re2 = KnowledgeAccumulator(package_path=pkg_file)
    acc_re2.process(delete)  # reprocess delete after persist
    assert len(acc_re2.package.objects) == 0

    # Atomicity smoke: package file is valid JSON after operations
    import json
    data = json.loads(Path(pkg_file).read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_process_exception_mid_mutation_rolls_back_and_retry_succeeds(tmp_path, monkeypatch):
    """If process raises after partial mutation (before persist), in-memory
    state is restored. Subsequent retry on the same accumulator succeeds
    cleanly without duplicates or lost objects.
    """
    pkg_file = str(tmp_path / "rollback.json")
    acc = KnowledgeAccumulator(package_path=pkg_file)

    # Seed one object so we can observe preservation on failure
    seed = SyncEvent(
        event_id="seed",
        source="test",
        kind="create",
        payload={"object_id": "seed", "text": "seed content"},
        tenant_id="t1",
        silo_id="s1",
    )
    acc.process(seed)
    assert len(acc.package.objects) == 1

    # Force exception inside _upsert_from_text after mutation would have started
    original_upsert = acc._upsert_from_text

    def boom(*args, **kwargs):
        # Mutate something visible then raise
        acc.package.objects.append(type(acc.package.objects[0])(**acc.package.objects[0].model_dump()))
        acc._src_to_obj["bad"] = "bad"
        raise RuntimeError("simulated mid-process failure")

    monkeypatch.setattr(acc, "_upsert_from_text", boom)

    failing = SyncEvent(
        event_id="fail",
        source="test",
        kind="create",
        payload={"object_id": "fail", "text": "should not stick"},
        tenant_id="t1",
        silo_id="s1",
    )
    try:
        acc.process(failing)
        assert False, "expected exception"
    except RuntimeError:
        pass

    # Rolled back: still only the seed
    assert len(acc.package.objects) == 1
    assert "bad" not in acc._src_to_obj
    assert not Path(pkg_file).exists() or "seed content" in Path(pkg_file).read_text()

    # Restore real method and retry successfully
    monkeypatch.setattr(acc, "_upsert_from_text", original_upsert)
    acc.process(failing)
    assert len(acc.package.objects) == 2
    contents = {o.content for o in acc.package.objects}
    assert any("should not stick" in c for c in contents)
    assert any("seed content" in c for c in contents)
    # Persisted and reloadable
    acc2 = KnowledgeAccumulator(package_path=pkg_file)
    assert len(acc2.package.objects) == 2

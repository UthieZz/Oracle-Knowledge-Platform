"""End-to-end: stub connector → SyncEngine → PlainTextImporter → KnowledgePackage.

Proves install→auth→initial sync→enqueue→process→permission-aware (tenant/silo) package
without a parallel IR or direct core mutation.
"""
import tempfile
from pathlib import Path

from okc.connect.stub_connector import StubConnector
from okc.connect.sync_engine import SyncEngine
from okc.importers.text_importer import PlainTextImporter


def test_stub_connector_to_knowledge_package(tmp_path):
    docs = [
        {"id": "doc1", "text": "Hello knowledge.\nThis is source evidence."},
        {"id": "doc2", "text": "Second document for isolation."},
    ]
    connector = StubConnector(docs)
    assert connector.authenticate({}) is True
    assert connector.health().value == "ok"

    events = connector.initial_sync("tenant-a", "silo-1")
    assert len(events) == 2

    db = str(tmp_path / "connect.db")
    engine = SyncEngine(db_path=db)
    for ev in events:
        assert engine.enqueue(ev) is True

    packages = []

    def processor(event):
        # Reuse exact PlainTextImporter path via temp file.
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(event.payload["text"])
            path = f.name
        try:
            pkg = PlainTextImporter().process(
                path,
                event.tenant_id,
                event.silo_id,
                source_platform=event.source,
            )
            packages.append(pkg)
        finally:
            Path(path).unlink(missing_ok=True)

    processed_ids = []
    while True:
        eid = engine.process_next(processor)
        if eid is None:
            break
        processed_ids.append(eid)

    assert processed_ids == ["stub-doc1", "stub-doc2"]
    assert len(packages) == 2

    p0 = packages[0]
    assert len(p0.objects) == 1
    obj = p0.objects[0]
    assert obj.provenance.tenant_id == "tenant-a"
    assert obj.provenance.silo_id == "silo-1"
    assert obj.provenance.source_platform == "stub"
    assert "Hello knowledge" in obj.content
    assert p0.metadata["tenant_id"] == "tenant-a"
    assert p0.metadata["silo_id"] == "silo-1"

    # Cursor advanced
    assert engine.get_cursor("stub", "tenant-a", "silo-1") == "2"
    health = engine.health()
    assert health["processed"] == 2
    assert health["queued"] == 0

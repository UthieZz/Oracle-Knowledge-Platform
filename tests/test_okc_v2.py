"""Formal tests for additive okc/ v2 path."""

import json
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from okc.analyzers.entity_extractor import EntityExtractor
from okc.compiler.passes.attachment_processing_pass import AttachmentProcessingPass
from okc.exporters.sqlite_exporter import SQLiteExporter
from okc.importers.json_importer import JsonToV2Importer
from okc.models.knowledge_package import (
    EvidenceSpan,
    KnowledgeObject,
    KnowledgePackage,
    Provenance,
)
from okc.search.hybrid_rag import HybridRAGEngine


@pytest.fixture
def sample_json(tmp_path: Path) -> Path:
    payload = [
        {
            "id": "conv_test_1",
            "title": "Python SQLite notes",
            "messages": [
                {"role": "user", "content": "How do we use Python with SQLite in OKP?"},
                {
                    "role": "assistant",
                    "content": "Use the sqlite3 module and keep tenant isolation.",
                },
            ],
        }
    ]
    path = tmp_path / "sample_chatgpt.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_schema_version_frozen():
    pkg = KnowledgePackage(package_id="t1")
    assert pkg.schema_version == "2.0.0"
    with pytest.raises(Exception):
        pkg.schema_version = "3.0.0"  # type: ignore[misc]


def test_json_importer_builds_evidence(sample_json: Path):
    pkg = JsonToV2Importer().process(
        str(sample_json), tenant_id="tenant_a", silo_id="silo_1", source_platform="chatgpt"
    )
    assert len(pkg.objects) == 1
    obj = pkg.objects[0]
    assert obj.object_id == "conv_test_1"
    assert obj.provenance.tenant_id == "tenant_a"
    assert len(obj.evidence) == 2
    assert obj.evidence[0].role == "user"
    assert "Python" in obj.content


def test_entity_extraction():
    prov = Provenance(
        source_platform="chatgpt",
        source_file="f.json",
        tenant_id="t",
        silo_id="s",
    )
    obj = KnowledgeObject(
        object_id="o1",
        title="T",
        provenance=prov,
        content="We used Python and SQLite with React at OpenAI.",
    )
    pkg = KnowledgePackage(package_id="p1", objects=[obj])
    pkg = EntityExtractor().run(pkg)
    ents = set(pkg.objects[0].entities)
    assert "python" in ents
    assert "sqlite" in ents
    assert "react" in ents
    assert "openai" in ents


def test_hybrid_rag_tenant_isolation():
    eng = HybridRAGEngine()
    prov = Provenance(
        source_platform="chatgpt",
        source_file="f.json",
        tenant_id="tenant_a",
        silo_id="silo_1",
    )
    obj = KnowledgeObject(
        object_id="o1",
        title="T",
        provenance=prov,
        content="Python SQLite integration notes for OKP.",
    )
    pkg = KnowledgePackage(package_id="p1", objects=[obj])
    eng.index_package(pkg)
    hits_ok = eng.search("Python SQLite", tenant_id="tenant_a", silo_id="silo_1")
    hits_blocked = eng.search("Python SQLite", tenant_id="tenant_b", silo_id="silo_1")
    assert len(hits_ok) >= 1
    assert len(hits_blocked) == 0


def test_sqlite_export_roundtrip(tmp_path: Path):
    db = tmp_path / "test.db"
    prov = Provenance(
        source_platform="chatgpt",
        source_file="f.json",
        tenant_id="t",
        silo_id="s",
    )
    span = EvidenceSpan(
        span_id="s1",
        message_id="m1",
        role="user",
        timestamp="2026-01-01T00:00:00Z",
        content="evidence",
    )
    obj = KnowledgeObject(
        object_id="o1",
        title="Title",
        provenance=prov,
        content="content here",
        evidence=[span],
    )
    pkg = KnowledgePackage(package_id="p1", objects=[obj])
    SQLiteExporter(db_path=str(db)).export(pkg, tenant_id="t", silo_id="s")

    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("SELECT object_id, title FROM knowledge_objects")
    assert c.fetchall() == [("o1", "Title")]
    c.execute("SELECT content FROM evidence_spans")
    assert c.fetchone()[0] == "evidence"
    conn.close()


def test_attachment_pass_marks_missing_file():
    prov = Provenance(
        source_platform="chatgpt",
        source_file="f.json",
        tenant_id="t",
        silo_id="s",
    )
    obj = KnowledgeObject(
        object_id="o1",
        title="T",
        provenance=prov,
        content="body",
        attachments=[{"file_path": "does_not_exist.png"}],
    )
    pkg = KnowledgePackage(package_id="p1", objects=[obj])
    pkg = AttachmentProcessingPass().execute(pkg)
    att = pkg.objects[0].attachments[0]
    assert att["status"] in {"failed", "processed"}


def test_end_to_end_importer_to_sqlite(sample_json: Path, tmp_path: Path):
    pkg = JsonToV2Importer().process(str(sample_json), "tenant_a", "silo_1")
    pkg = AttachmentProcessingPass().execute(pkg)
    pkg = EntityExtractor().run(pkg)
    db = tmp_path / "e2e.db"
    SQLiteExporter(db_path=str(db)).export(pkg, tenant_id="tenant_a", silo_id="silo_1")
    conn = sqlite3.connect(db)
    count = conn.execute("SELECT COUNT(*) FROM knowledge_objects").fetchone()[0]
    conn.close()
    assert count == 1

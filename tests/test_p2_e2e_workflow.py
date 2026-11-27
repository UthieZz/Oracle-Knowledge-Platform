"""P2 full-workflow verification (no excessive mocks).

Validates the supported local path:
  LocalFolderConnector → SyncEngine → KnowledgeAccumulator
  → KnowledgePackage IR v2 → SQLiteExporter → SQLiteKnowledgeReader
  → KnowledgePackageRetriever → ContextGateway

Also locks:
  - EvidenceSpan id continuity into ContextGateway items
  - source timestamp present on evidence
  - cross-tenant/silo isolation at retrieval
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from okc.agent.context_gateway import ContextAccessError, ContextGateway
from okc.agent.models import AgentContextRequest
from okc.agent.retrievers import KnowledgePackageRetriever
from okc.connect.knowledge_accumulator import KnowledgeAccumulator
from okc.connect.local_folder_connector import LocalFolderConnector
from okc.connect.sync_engine import SyncEngine
from okc.exporters.sqlite_exporter import SQLiteExporter
from okc.models.knowledge_package import KnowledgePackage
from okc.server.sqlite_reader import SQLiteKnowledgeReader


MARKER = "OKP_P2_E2E_WORKFLOW_MARKER_42"
TENANT = "p2-tenant"
SILO = "p2-silo"
OTHER_TENANT = "other-tenant"
OTHER_SILO = "other-silo"


def _run_folder_to_package(tmp_path: Path) -> tuple[KnowledgePackage, Path, Path]:
    """Drive real Connect local-folder path into a durable KnowledgePackage."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    pilot = source_dir / "p2_policy.md"
    pilot.write_text(
        f"# P2 Policy\n\nThis document contains {MARKER} for end-to-end verification.\n"
        f"International transfers require dual control.\n",
        encoding="utf-8",
    )

    snapshot_path = str(tmp_path / "snapshot.json")
    package_path = str(tmp_path / "living.json")
    queue_db = str(tmp_path / "sync.db")

    connector = LocalFolderConnector(str(source_dir), snapshot_path=snapshot_path)
    assert connector.authenticate({}) is True

    engine = SyncEngine(queue_db)
    accumulator = KnowledgeAccumulator(package_path=package_path)

    events = connector.stage_initial_sync(TENANT, SILO)
    assert events, "initial sync must emit at least one create event"
    for ev in events:
        assert ev.tenant_id == TENANT
        assert ev.silo_id == SILO
        engine.enqueue(ev)
    if connector.has_pending_journal():
        connector.commit_pending()

    processed = 0
    while True:
        eid = engine.process_next(accumulator.process)
        if eid is None:
            break
        processed += 1
    assert processed >= 1

    pkg = KnowledgePackage.from_json(Path(package_path).read_text(encoding="utf-8"))
    return pkg, Path(package_path), Path(tmp_path / "export.db")


def test_p2_ingest_to_ir_v2_package(tmp_path: Path):
    """Ingestion yields KnowledgePackage schema_version 2.0.0 with provenance + evidence."""
    pkg, _, _ = _run_folder_to_package(tmp_path)

    assert pkg.schema_version == "2.0.0"
    assert pkg.package_id
    assert len(pkg.objects) >= 1

    obj = next(o for o in pkg.objects if MARKER in o.content)
    assert obj.provenance.tenant_id == TENANT
    assert obj.provenance.silo_id == SILO
    assert obj.provenance.source_platform
    assert obj.provenance.source_file
    assert obj.evidence, "IR v2 object must carry EvidenceSpan source evidence"
    span = obj.evidence[0]
    assert span.span_id
    assert span.timestamp, "EvidenceSpan must retain source timestamp"
    assert MARKER in span.content or MARKER in obj.content


def test_p2_persistence_and_reader_isolation(tmp_path: Path):
    """SQLite export then reader returns scoped rows; other tenant sees empty."""
    pkg, _, export_db = _run_folder_to_package(tmp_path)
    SQLiteExporter(str(export_db)).export(pkg, TENANT, SILO)

    reader = SQLiteKnowledgeReader(str(export_db))
    assert reader.db_readable() is True

    rows = reader.list_knowledge_objects(TENANT, SILO, limit=50)
    assert len(rows) >= 1
    assert any(MARKER in (r.get("content") or "") for r in rows)

    assert reader.list_knowledge_objects(OTHER_TENANT, SILO) == []
    assert reader.list_knowledge_objects(TENANT, OTHER_SILO) == []
    assert reader.search(OTHER_TENANT, SILO, MARKER) == []

    hits = reader.search(TENANT, SILO, MARKER)
    assert len(hits) >= 1
    assert hits[0]["id"]

    stats = reader.get_dashboard_stats(TENANT, SILO)
    assert stats["knowledge_objects"] >= 1


def test_p2_context_gateway_retrieval_and_isolation(tmp_path: Path):
    """Retriever + ContextGateway return scoped items with evidence_ids; cross-scope empty."""
    pkg, _, _ = _run_folder_to_package(tmp_path)
    obj = next(o for o in pkg.objects if MARKER in o.content)
    expected_span_ids = [s.span_id for s in obj.evidence]
    assert expected_span_ids

    retriever = KnowledgePackageRetriever(pkg, strict_permissions=False)
    gateway = ContextGateway(retriever)

    request = AgentContextRequest(
        request_id="p2-req-1",
        tenant_id=TENANT,
        silo_id=SILO,
        agent_id="p2-agent",
        task=MARKER,
        max_context_items=10,
        include_provenance=True,
    )
    package = gateway.build(request)
    assert package.tenant_id == TENANT
    assert package.silo_id == SILO
    assert package.items, "gateway must return at least one context item for matching task"
    item = next(i for i in package.items if MARKER in i.content or i.object_id == obj.object_id)
    assert item.evidence_ids, "ContextItem must carry evidence_ids from IR EvidenceSpans"
    assert set(expected_span_ids).issubset(set(item.evidence_ids))
    assert item.provenance.get("tenant_id") == TENANT
    assert item.provenance.get("silo_id") == SILO

    # Cross-tenant request must not leak objects (retriever filters; gateway also guards)
    foreign = gateway.build(
        AgentContextRequest(
            request_id="p2-req-foreign",
            tenant_id=OTHER_TENANT,
            silo_id=SILO,
            agent_id="p2-agent",
            task=MARKER,
        )
    )
    assert foreign.items == []

    foreign_silo = gateway.build(
        AgentContextRequest(
            request_id="p2-req-silo",
            tenant_id=TENANT,
            silo_id=OTHER_SILO,
            agent_id="p2-agent",
            task=MARKER,
        )
    )
    assert foreign_silo.items == []


def test_p2_full_pipeline_single_path(tmp_path: Path):
    """Single coherent path: ingest → IR v2 → persist → read → gateway retrieve."""
    pkg, package_path, export_db = _run_folder_to_package(tmp_path)
    assert pkg.schema_version == "2.0.0"

    SQLiteExporter(str(export_db)).export(pkg, TENANT, SILO)

    # Persistence is real SQLite, not a mock
    with sqlite3.connect(str(export_db)) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT object_id, content FROM knowledge_objects WHERE tenant_id=? AND silo_id=?",
            (TENANT, SILO),
        )
        sql_rows = cur.fetchall()
    assert sql_rows
    assert any(MARKER in (row[1] or "") for row in sql_rows)

    # Reload living package (durability) and retrieve via gateway
    reloaded = KnowledgePackage.from_json(package_path.read_text(encoding="utf-8"))
    assert reloaded.schema_version == "2.0.0"
    gateway = ContextGateway(KnowledgePackageRetriever(reloaded))
    result = gateway.build(
        AgentContextRequest(
            request_id="p2-full",
            tenant_id=TENANT,
            silo_id=SILO,
            agent_id="p2-agent",
            task="dual control transfers",
        )
    )
    assert any(MARKER in i.content for i in result.items)

    reader = SQLiteKnowledgeReader(str(export_db))
    assert reader.search(TENANT, SILO, "dual control")

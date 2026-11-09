"""Regression: SQLiteExporter respects the permission model used by retrieval."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from okc.connect.interfaces import SyncEvent
from okc.connect.knowledge_accumulator import KnowledgeAccumulator
from okc.exporters.sqlite_exporter import SQLiteExporter
from okc.models.knowledge_package import KnowledgePackage


def test_sqlite_exporter_excludes_explicit_deny(tmp_path: Path):
    """Explicit read=False is excluded from export (default mode)."""
    pkg_path = str(tmp_path / "living.json")
    acc = KnowledgeAccumulator(package_path=pkg_path)

    acc.process(SyncEvent(
        event_id="c1",
        source="folder",
        kind="create",
        payload={"object_id": "doc1", "text": "secret knowledge"},
        tenant_id="t",
        silo_id="s",
    ))
    acc.process(SyncEvent(
        event_id="p1",
        source="folder",
        kind="permission_change",
        payload={"object_id": "doc1", "read": False},
        tenant_id="t",
        silo_id="s",
    ))

    db = str(tmp_path / "export.db")
    exporter = SQLiteExporter(db_path=db)
    exporter.export(acc.package, tenant_id="t", silo_id="s")  # default: not strict

    with sqlite3.connect(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM knowledge_objects").fetchone()[0]
    assert count == 0


def test_sqlite_exporter_includes_missing_permission_by_default(tmp_path: Path):
    """Objects without a permission entry are exported under default (pilot) mode."""
    acc = KnowledgeAccumulator()
    acc.process(SyncEvent(
        event_id="c1",
        source="folder",
        kind="create",
        payload={"object_id": "doc1", "text": "visible knowledge"},
        tenant_id="t",
        silo_id="s",
    ))

    db = str(tmp_path / "export.db")
    exporter = SQLiteExporter(db_path=db)
    exporter.export(acc.package, tenant_id="t", silo_id="s")

    with sqlite3.connect(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM knowledge_objects").fetchone()[0]
    assert count == 1


def test_sqlite_exporter_strict_mode_excludes_missing(tmp_path: Path):
    """strict_permissions=True excludes objects that have a source identity but no permission entry."""
    acc = KnowledgeAccumulator()
    acc.process(SyncEvent(
        event_id="c1",
        source="folder",
        kind="create",
        payload={"object_id": "doc1", "text": "restricted"},
        tenant_id="t",
        silo_id="s",
    ))

    db = str(tmp_path / "export.db")
    exporter = SQLiteExporter(db_path=db)
    exporter.export(acc.package, tenant_id="t", silo_id="s", strict_permissions=True)

    with sqlite3.connect(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM knowledge_objects").fetchone()[0]
    assert count == 0

    # Explicit allow restores export even in strict mode
    acc.process(SyncEvent(
        event_id="p1",
        source="folder",
        kind="permission_change",
        payload={"object_id": "doc1", "read": True},
        tenant_id="t",
        silo_id="s",
    ))
    exporter.export(acc.package, tenant_id="t", silo_id="s", strict_permissions=True)
    with sqlite3.connect(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM knowledge_objects").fetchone()[0]
    assert count == 1

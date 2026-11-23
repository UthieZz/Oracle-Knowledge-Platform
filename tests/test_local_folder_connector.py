"""Tests for LocalFolderConnector: initial/incremental, delete, e2e to KnowledgePackage."""
import json
import tempfile
import os
import sys
from pathlib import Path

import pytest

from okc.connect.local_folder_connector import LocalFolderConnector
from okc.connect.sync_engine import SyncEngine
from okc.connect.knowledge_accumulator import KnowledgeAccumulator
from okc.importers.text_importer import PlainTextImporter


def test_local_folder_initial_and_incremental(tmp_path):
    root = tmp_path / "docs"
    root.mkdir()
    (root / "a.txt").write_text("First document content.", encoding="utf-8")
    (root / "b.md").write_text("# Second\nMore text.", encoding="utf-8")

    conn = LocalFolderConnector(str(root))
    assert conn.authenticate({}) is True
    assert conn.health().value == "ok"

    events = conn.initial_sync("t1", "s1")
    assert len(events) == 2
    ids = {e.payload["object_id"] for e in events}
    assert ids == {"a.txt", "b.md"}
    assert all(e.kind == "create" for e in events)
    assert all(e.tenant_id == "t1" for e in events)

    # Incremental with no change
    more = conn.incremental_sync("0", "t1", "s1")
    assert more == []

    # Update one file
    (root / "a.txt").write_text("First document content updated.", encoding="utf-8")
    updates = conn.incremental_sync("0", "t1", "s1")
    assert len(updates) == 1
    assert updates[0].kind == "update"
    assert updates[0].payload["object_id"] == "a.txt"
    assert "updated" in updates[0].payload["text"]

    # Delete
    (root / "b.md").unlink()
    deletes = conn.incremental_sync("0", "t1", "s1")
    assert len(deletes) == 1
    assert deletes[0].kind == "delete"
    assert deletes[0].payload["object_id"] == "b.md"

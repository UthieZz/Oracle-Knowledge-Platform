#!/usr/bin/env python3
"""Single-command verification of the clean local-folder Connect pilot path.

Import (LocalFolderConnector) → Accumulate (KnowledgeAccumulator) → KnowledgePackage
→ SQLite export → lexical search. Uses only local filesystem and SQLite.
No cloud dependencies.

Usage:
  python scripts/verify_local_pilot.py
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

# Bootstrap project root
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from okc.connect.knowledge_accumulator import KnowledgeAccumulator
from okc.connect.local_folder_connector import LocalFolderConnector
from okc.connect.sync_engine import SyncEngine
from okc.exporters.sqlite_exporter import SQLiteExporter
from okc.models.knowledge_package import KnowledgePackage


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        marker = "OKP_LOCAL_PILOT_MARKER_42"
        (source_dir / "pilot.md").write_text(
            f"# Local pilot\n\nThis file contains the unique marker {marker} for verification.\n",
            encoding="utf-8",
        )

        db_path = str(tmp_path / "sync.db")
        package_path = str(tmp_path / "living.json")
        snapshot_path = str(tmp_path / "snapshot.json")
        export_db = str(tmp_path / "export.db")

        tenant, silo = "pilot", "verify"

        connector = LocalFolderConnector(str(source_dir), snapshot_path=snapshot_path)
        if not connector.authenticate({}):
            print("FAIL: connector authentication", file=sys.stderr)
            return 1

        engine = SyncEngine(db_path)
        accumulator = KnowledgeAccumulator(package_path=package_path)

        # Stage + enqueue + process + commit (simulates one worker cycle without thread)
        events = connector.stage_initial_sync(tenant, silo)
        if not events:
            print("FAIL: no events from initial sync", file=sys.stderr)
            return 1
        for ev in events:
            engine.enqueue(ev)
        if connector.has_pending_journal():
            connector.commit_pending()

        # Drain
        processed = 0
        while True:
            eid = engine.process_next(accumulator.process)
            if eid is None:
                break
            processed += 1

        if processed == 0:
            print("FAIL: no events processed", file=sys.stderr)
            return 1

        # Verify package
        pkg = KnowledgePackage.from_json(Path(package_path).read_text(encoding="utf-8"))
        if not pkg.objects:
            print("FAIL: package has no objects", file=sys.stderr)
            return 1
        contents = " ".join(o.content for o in pkg.objects)
        if marker not in contents:
            print("FAIL: marker not found in package content", file=sys.stderr)
            return 1

        # SQLite export
        exporter = SQLiteExporter(export_db)
        exporter.export(pkg, tenant, silo)

        # Lexical search
        with sqlite3.connect(export_db) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT object_id, title, content FROM knowledge_objects WHERE content LIKE ?",
                (f"%{marker}%",),
            )
            rows = cur.fetchall()

        if not rows:
            print("FAIL: lexical search returned no rows", file=sys.stderr)
            return 1

        print("OK: local pilot path verified")
        print(f"  objects: {len(pkg.objects)}")
        print(f"  processed events: {processed}")
        print(f"  search hits: {len(rows)}")
        print(f"  marker found: {marker}")
        return 0


if __name__ == "__main__":
    sys.exit(main())

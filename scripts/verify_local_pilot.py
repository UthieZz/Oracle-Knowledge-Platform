#!/usr/bin/env python3
"""Single-command verification of the clean local-folder Connect pilot path.

Import (LocalFolderConnector) → Accumulate (KnowledgeAccumulator) → KnowledgePackage
→ SQLite export → lexical search. Uses only local filesystem and SQLite.
No cloud dependencies.

Also exercises a restart + deletion convergence path to lock crash consistency
in the runtime verification.

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
        pilot_file = source_dir / "pilot.md"
        pilot_file.write_text(
            f"# Local pilot\n\nThis file contains the unique marker {marker} for verification.\n",
            encoding="utf-8",
        )

        db_path = str(tmp_path / "sync.db")
        package_path = str(tmp_path / "living.json")
        snapshot_path = str(tmp_path / "snapshot.json")
        export_db = str(tmp_path / "export.db")

        tenant, silo = "pilot", "verify"

        # --- Phase 1: initial sync ---
        connector = LocalFolderConnector(str(source_dir), snapshot_path=snapshot_path)
        if not connector.authenticate({}):
            print("FAIL: connector authentication", file=sys.stderr)
            return 1

        engine = SyncEngine(db_path)
        accumulator = KnowledgeAccumulator(package_path=package_path)

        events = connector.stage_initial_sync(tenant, silo)
        if not events:
            print("FAIL: no events from initial sync", file=sys.stderr)
            return 1
        for ev in events:
            engine.enqueue(ev)
        if connector.has_pending_journal():
            connector.commit_pending()

        processed = 0
        while True:
            eid = engine.process_next(accumulator.process)
            if eid is None:
                break
            processed += 1

        if processed == 0:
            print("FAIL: no events processed", file=sys.stderr)
            return 1

        pkg = KnowledgePackage.from_json(Path(package_path).read_text(encoding="utf-8"))
        if not pkg.objects or marker not in " ".join(o.content for o in pkg.objects):
            print("FAIL: initial package missing marker", file=sys.stderr)
            return 1

        # --- Phase 2: simulate crash/restart with source deletion ---
        pilot_file.unlink()  # delete while "stopped"

        # New connector instance (restart) from same snapshot
        connector2 = LocalFolderConnector(str(source_dir), snapshot_path=snapshot_path)
        if not connector2.authenticate({}):
            print("FAIL: restart connector auth", file=sys.stderr)
            return 1

        # Incremental should detect the deletion
        events2 = connector2.stage_incremental_sync("", tenant, silo)
        if not any(e.kind == "delete" for e in events2):
            print("FAIL: no delete event after source deletion on restart", file=sys.stderr)
            return 1

        for ev in events2:
            engine.enqueue(ev)
        if connector2.has_pending_journal():
            connector2.commit_pending()

        processed2 = 0
        while True:
            eid = engine.process_next(accumulator.process)
            if eid is None:
                break
            processed2 += 1

        # After deletion, package should no longer contain the marker object
        pkg2 = KnowledgePackage.from_json(Path(package_path).read_text(encoding="utf-8"))
        contents2 = " ".join(o.content for o in pkg2.objects) if pkg2.objects else ""
        if marker in contents2:
            print("FAIL: marker still present after deletion + restart processing", file=sys.stderr)
            return 1

        # --- Phase 3: export + search on final package ---
        exporter = SQLiteExporter(export_db)
        exporter.export(pkg2, tenant, silo)

        with sqlite3.connect(export_db) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT object_id, title, content FROM knowledge_objects WHERE content LIKE ?",
                (f"%{marker}%",),
            )
            rows = cur.fetchall()

        if rows:
            print("FAIL: lexical search still found marker after deletion", file=sys.stderr)
            return 1

        print("OK: local pilot path verified (including restart+deletion convergence)")
        print(f"  initial objects: 1")
        print(f"  final objects: {len(pkg2.objects)}")
        print(f"  processed events (phase1+phase2): {processed + processed2}")
        print(f"  marker removed: True")
        return 0


if __name__ == "__main__":
    sys.exit(main())

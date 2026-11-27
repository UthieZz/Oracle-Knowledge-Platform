"""Read path for local SQLite knowledge exported by SQLiteExporter.

Strictly filters by tenant_id and silo_id. Returns empty collections when the
DB or tables do not exist yet (pilot-safe; no hard failure on first run).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


class SQLiteKnowledgeReader:
    """Reads knowledge_objects and evidence_spans from the local pilot SQLite DB."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self) -> Optional[sqlite3.Connection]:
        path = Path(self.db_path)
        if not path.is_file():
            return None
        try:
            conn = sqlite3.connect(str(path))
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error:
            return None

    def _tables_exist(self, conn: sqlite3.Connection) -> bool:
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_objects'"
            )
            return cur.fetchone() is not None
        except sqlite3.Error:
            return False

    def list_knowledge_objects(
        self,
        tenant_id: str,
        silo_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return knowledge objects for the given tenant/silo only."""
        if not tenant_id or not silo_id:
            return []
        conn = self._connect()
        if conn is None:
            return []
        try:
            if not self._tables_exist(conn):
                return []
            cur = conn.cursor()
            cur.execute(
                """
                SELECT object_id, tenant_id, silo_id, source_platform, title, content,
                       raw_json, created_at
                FROM knowledge_objects
                WHERE tenant_id = ? AND silo_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (tenant_id, silo_id, max(1, int(limit))),
            )
            rows = cur.fetchall()
            results: List[Dict[str, Any]] = []
            for row in rows:
                results.append(
                    {
                        "id": row["object_id"],
                        "object_id": row["object_id"],
                        "tenant_id": row["tenant_id"],
                        "silo_id": row["silo_id"],
                        "title": row["title"] or row["object_id"],
                        "content": row["content"] or "",
                        "source_platform": row["source_platform"] or "",
                        "type": "knowledge_object",
                        "created_at": row["created_at"],
                        "raw_json": row["raw_json"],
                    }
                )
            return results
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def get_dashboard_stats(self, tenant_id: str, silo_id: str) -> Dict[str, Any]:
        """Aggregate counts for dashboard; empty when DB/tables missing."""
        objects = self.list_knowledge_objects(tenant_id, silo_id, limit=10000)
        platforms = set()
        for obj in objects:
            sp = (obj.get("source_platform") or "").strip()
            if sp:
                platforms.add(sp)
        return {
            "platforms": len(platforms),
            "conversations": 0,
            "knowledge_objects": len(objects),
            "updated_at": None,
        }

    def search(
        self,
        tenant_id: str,
        silo_id: str,
        query: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Lexical search over title and content, scoped to tenant/silo."""
        if not tenant_id or not silo_id or not (query or "").strip():
            return []
        conn = self._connect()
        if conn is None:
            return []
        try:
            if not self._tables_exist(conn):
                return []
            term = f"%{(query or '').strip()}%"
            cur = conn.cursor()
            cur.execute(
                """
                SELECT object_id, tenant_id, silo_id, source_platform, title, content,
                       created_at
                FROM knowledge_objects
                WHERE tenant_id = ? AND silo_id = ?
                  AND (title LIKE ? OR content LIKE ?)
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (tenant_id, silo_id, term, term, max(1, int(limit))),
            )
            rows = cur.fetchall()
            results: List[Dict[str, Any]] = []
            for row in rows:
                results.append(
                    {
                        "id": row["object_id"],
                        "type": "knowledge",
                        "title": row["title"] or row["object_id"],
                        "snippet": (row["content"] or "")[:240],
                        "content": row["content"] or "",
                        "source_platform": row["source_platform"] or "",
                        "created_at": row["created_at"],
                    }
                )
            return results
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def db_readable(self) -> bool:
        """True if the DB file exists and knowledge_objects is queryable."""
        conn = self._connect()
        if conn is None:
            return False
        try:
            return self._tables_exist(conn)
        finally:
            conn.close()

import sqlite3
import json
import logging
from typing import Optional
from okc.models.knowledge_package import KnowledgePackage

logger = logging.getLogger(__name__)


class SQLiteExporter:
    """Persists KnowledgePackages locally into an embedded SQLite database."""

    def __init__(self, db_path: str = "okp_local.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initializes relational tables for Knowledge Objects, provenance, and chunks."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_objects (
                    object_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    silo_id TEXT NOT NULL,
                    source_platform TEXT NOT NULL,
                    title TEXT,
                    content TEXT,
                    raw_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evidence_spans (
                    span_id TEXT PRIMARY KEY,
                    object_id TEXT,
                    message_id TEXT,
                    role TEXT,
                    content TEXT,
                    FOREIGN KEY(object_id) REFERENCES knowledge_objects(object_id)
                )
            """)
            conn.commit()

    def export(self, package: KnowledgePackage, tenant_id: str, silo_id: str) -> None:
        """Saves compiled knowledge package contents into SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for obj in package.objects:
                cursor.execute("""
                    INSERT OR REPLACE INTO knowledge_objects 
                    (object_id, tenant_id, silo_id, source_platform, title, content, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    obj.object_id,
                    tenant_id,
                    silo_id,
                    obj.provenance.source_platform,
                    obj.title,
                    obj.content,
                    obj.model_dump_json()
                ))
                for span in obj.evidence:
                    cursor.execute("""
                        INSERT OR REPLACE INTO evidence_spans
                        (span_id, object_id, message_id, role, content)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        span.span_id,
                        obj.object_id,
                        span.message_id,
                        span.role,
                        span.content
                    ))
            conn.commit()
        logger.info(f"Exported {len(package.objects)} objects to local SQLite DB: {self.db_path}")

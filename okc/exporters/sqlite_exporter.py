import sqlite3
import json
import logging
from typing import Optional
from okc.models.knowledge_package import KnowledgePackage

logger = logging.getLogger(__name__)


class SQLiteExportError(ValueError):
    """Export refused because tenant/silo identity does not match object provenance."""


class SQLiteExporter:
    """Persists KnowledgePackages locally into an embedded SQLite database.

    The export target must match each object's provenance tenant and silo.
    Caller-supplied identity is not allowed to relabel knowledge.
    """

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

    def export(
        self,
        package: KnowledgePackage,
        tenant_id: str,
        silo_id: str,
        strict_permissions: bool = False,
    ) -> None:
        """Saves compiled knowledge package contents into SQLite.

        Refuses the whole export if any object provenance does not match the
        target tenant/silo. Does not rewrite object content or provenance.

        Permission filtering (aligned with KnowledgePackageRetriever):
        - Explicit read=False entries are always excluded (fail-closed for recorded denials).
        - strict_permissions=False (default, pilot): objects without a permission entry are included.
        - strict_permissions=True: objects with a source identity but no permission entry are excluded.
        """
        self._require_isolated_target(package, tenant_id, silo_id)
        objects_to_export = [
            obj for obj in package.objects
            if not self._is_forbidden(obj, package, strict_permissions)
        ]
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for obj in objects_to_export:
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
        logger.info(
            f"Exported {len(objects_to_export)} of {len(package.objects)} objects "
            f"to local SQLite DB: {self.db_path} (strict_permissions={strict_permissions})"
        )

    def _is_forbidden(
        self, obj, package: KnowledgePackage, strict_permissions: bool
    ) -> bool:
        """Return True if the object should be excluded from export under the permission model."""
        raw_permissions = package.metadata.get("permissions", {})
        permissions = raw_permissions if isinstance(raw_permissions, dict) else {}
        src_ids = [
            rid[4:] for rid in obj.provenance.source_record_ids
            if rid.startswith("src:")
        ]
        if not src_ids:
            return False  # No source identity → no permission gate
        has_explicit = False
        for src_id in src_ids:
            perm = permissions.get(src_id)
            if perm is not None:
                has_explicit = True
                if perm.get("read") is False:
                    return True
        if strict_permissions and not has_explicit:
            return True
        return False

    def _require_isolated_target(
        self, package: KnowledgePackage, tenant_id: str, silo_id: str
    ) -> None:
        if not tenant_id or not silo_id:
            raise SQLiteExportError("tenant_id and silo_id are required.")
        if package is None:
            raise SQLiteExportError("KnowledgePackage is required.")
        for obj in package.objects:
            provenance = obj.provenance
            if provenance.tenant_id != tenant_id or provenance.silo_id != silo_id:
                raise SQLiteExportError(
                    f"Object {obj.object_id} provenance "
                    f"{provenance.tenant_id}/{provenance.silo_id} does not match "
                    f"export target {tenant_id}/{silo_id}."
                )

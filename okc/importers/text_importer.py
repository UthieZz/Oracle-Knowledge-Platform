"""Deterministic plain-text importer.

Source files become KnowledgeObjects. Extracted text is source evidence,
not inferred knowledge. This importer does not parse conversation JSON
and does not promote attachment or memory candidates.
"""
from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from okc.models.knowledge_package import (
    EvidenceSpan,
    KnowledgeObject,
    KnowledgePackage,
    Provenance,
)


class PlainTextImportError(ValueError):
    """Plain-text source could not be imported."""


class PlainTextImporter:
    """Import a UTF-8 .txt or .md file as one provenance-bearing object."""

    name = "plain_text_importer"
    version = "1.0.0"
    source_platform = "local_file"

    def process(self, source_filepath: str, tenant_id: str, silo_id: str, source_platform: str | None = None) -> KnowledgePackage:
        if not tenant_id or not silo_id:
            raise PlainTextImportError("tenant_id and silo_id are required.")
        if not os.path.isfile(source_filepath):
            raise FileNotFoundError(f"Source not found: {source_filepath}")

        suffix = Path(source_filepath).suffix.lower()
        if suffix not in {".txt", ".md"}:
            raise PlainTextImportError(
                f"plain_text_importer accepts .txt/.md only, got {suffix or 'no extension'}."
            )

        try:
            text = Path(source_filepath).read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise PlainTextImportError(f"UTF-8 decode failed: {source_filepath}") from exc
        if not text.strip():
            raise PlainTextImportError(f"Empty source: {source_filepath}")

        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        record_id = content_hash[:16]
        object_id = f"text_{record_id}"
        title = _title(source_filepath, text)
        platform = source_platform or self.source_platform
        now = datetime.now(timezone.utc).isoformat()

        obj = KnowledgeObject(
            object_id=object_id,
            title=title,
            provenance=Provenance(
                source_platform=platform,
                source_file=source_filepath,
                source_record_ids=[record_id],
                tenant_id=tenant_id,
                silo_id=silo_id,
            ),
            evidence=[
                EvidenceSpan(
                    span_id=f"{object_id}_span_0",
                    message_id=record_id,
                    role="source",
                    timestamp=now,
                    content=text,
                )
            ],
            content=text,
            entities=[],
            attachments=[],
            relationships=[],
            context_citations=[],
        )
        return KnowledgePackage(
            package_id=f"pkg_{uuid.uuid4().hex[:12]}",
            objects=[obj],
            metadata={
                "source_filepath": source_filepath,
                "source_platform": platform,
                "tenant_id": tenant_id,
                "silo_id": silo_id,
                "object_count": 1,
                "importer": self.name,
                "importer_version": self.version,
                "content_hash": content_hash,
                "transformation": "import_plain_text",
            },
        )


def _title(source_filepath: str, text: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip().lstrip("#").strip()
        if cleaned:
            return cleaned[:120]
    return Path(source_filepath).name

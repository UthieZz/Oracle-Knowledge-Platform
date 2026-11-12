"""Portable relationship index derived from existing package links.

Not a graph database. Writes output/relationships.json from already-present
conversation / message / attachment / knowledge-object identifiers.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from src.core.interfaces import Exporter
from src.models.knowledge_package import KnowledgePackage
from src.validators.knowledge_object_provenance import (
    ensure_knowledge_object_provenance,
)
from src.validators.knowledge_object_quality import annotate_knowledge_object_quality


class RelationshipIndexExporter(Exporter):
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir

    @property
    def name(self) -> str:
        return "Relationship Index Exporter"

    @property
    def version(self) -> str:
        return "1.0.1"

    @property
    def author(self) -> str:
        return "OKC Core Team"

    @property
    def description(self) -> str:
        return "Writes a portable sourced_from / attached_to index."

    @property
    def plugin_type(self) -> str:
        return "exporter"

    @property
    def supported_inputs(self) -> List[str]:
        return ["okc/package"]

    @property
    def supported_outputs(self) -> List[str]:
        return ["json"]

    def export(self, package: KnowledgePackage) -> KnowledgePackage:
        # Repair only. Hard reject belongs to ExportService / FirestoreExporter.
        ensure_knowledge_object_provenance(package)
        quality = annotate_knowledge_object_quality(package)
        edges: List[Dict[str, Any]] = []
        # Exclude knowledge_objects with explicit permission read=False (aligned with other delivery boundaries)
        raw_permissions = package.metadata.get("permissions", {}) if hasattr(package, "metadata") else {}
        permissions = raw_permissions if isinstance(raw_permissions, dict) else {}
        def _is_forbidden(ko) -> bool:
            oid = str(getattr(ko, "id", "") or "")
            if not oid:
                return False
            perm = permissions.get(oid)
            if perm is not None and isinstance(perm, dict) and perm.get("read") is False:
                return True
            return False
        for ko in package.knowledge_objects:
            if _is_forbidden(ko):
                continue
            prov = getattr(ko, "provenance", None) or {}
            cid = prov.get("conversation_id") or getattr(ko, "conversation_id", None)
            if cid:
                edges.append({
                    "type": "sourced_from",
                    "from": str(ko.id),
                    "from_kind": "knowledge_object",
                    "to": str(cid),
                    "to_kind": "conversation",
                    "source_platform": prov.get("source_platform") or getattr(ko, "source_platform", None),
                    "source_file": prov.get("source_file") or getattr(ko, "source_file", None),
                })
            for mid in prov.get("message_ids") or []:
                edges.append({
                    "type": "sourced_from",
                    "from": str(ko.id),
                    "from_kind": "knowledge_object",
                    "to": str(mid),
                    "to_kind": "message",
                })
            for aid in prov.get("attachment_ids") or []:
                edges.append({
                    "type": "attached_to",
                    "from": str(ko.id),
                    "from_kind": "knowledge_object",
                    "to": str(aid),
                    "to_kind": "attachment",
                })
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, "relationships.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "edge_count": len(edges),
                    "quality": {
                        "total": quality["total"],
                        "conversation_shaped_or_thin": quality["conversation_shaped_or_thin"],
                    },
                    "edges": edges,
                },
                fh,
                indent=2,
            )
        return package

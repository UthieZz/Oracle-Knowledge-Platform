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
        return "1.0.0"

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
        ensure_knowledge_object_provenance(package)
        quality = annotate_knowledge_object_quality(package)
        edges: List[Dict[str, Any]] = []
        for ko in package.knowledge_objects:
            prov = getattr(ko, "provenance", None) or {}
            cid = prov.get("conversation_id")
            if cid:
                edges.append({
                    "type": "sourced_from",
                    "from": str(ko.id),
                    "from_kind": "knowledge_object",
                    "to": str(cid),
                    "to_kind": "conversation",
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

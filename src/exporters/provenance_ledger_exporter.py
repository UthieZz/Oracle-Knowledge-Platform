"""Portable KnowledgeObject provenance ledger.

Does not change the compiler or KnowledgeObject dataclass. Reads lineage
already repaired by validators and writes output/provenance_ledger.json.

Contract per object:
    platform → source_file → conversation → message(s) → attachment(s) → KO
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from src.core.interfaces import Exporter
from src.models.knowledge_package import KnowledgePackage
from src.validators.knowledge_object_provenance import (
    REQUIRED_PROVENANCE_KEYS,
    ensure_knowledge_object_provenance,
    provenance_report,
)


class ProvenanceLedgerExporter(Exporter):
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir

    @property
    def name(self) -> str:
        return "Provenance Ledger Exporter"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def author(self) -> str:
        return "OKC Core Team"

    @property
    def description(self) -> str:
        return "Writes a portable per-object provenance ledger."

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
        repair = ensure_knowledge_object_provenance(package)
        check = provenance_report(package)
        entries: List[Dict[str, Any]] = []
        for ko in package.knowledge_objects:
            prov = dict(getattr(ko, "provenance", None) or {})
            missing = [key for key in REQUIRED_PROVENANCE_KEYS if not prov.get(key)]
            entries.append(
                {
                    "object_id": str(getattr(ko, "id", "") or ""),
                    "object_type": prov.get("object_type", "knowledge_object"),
                    "title": getattr(ko, "title", None),
                    "source_platform": prov.get("source_platform")
                    or getattr(ko, "source_platform", None),
                    "source_file": prov.get("source_file")
                    or getattr(ko, "source_file", None),
                    "conversation_id": prov.get("conversation_id"),
                    "message_ids": list(prov.get("message_ids") or []),
                    "attachment_ids": list(prov.get("attachment_ids") or []),
                    "evidence": list(getattr(ko, "evidence", None) or []),
                    "created_at": getattr(ko, "created_at", None),
                    "updated_at": getattr(ko, "updated_at", None),
                    "complete": not missing,
                    "missing": missing,
                    "quality": (prov.get("quality") or {}),
                }
            )
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, "provenance_ledger.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "total": len(entries),
                    "complete": sum(1 for item in entries if item["complete"]),
                    "incomplete": [item["object_id"] for item in entries if not item["complete"]],
                    "repair": {
                        "ok": repair.get("ok"),
                        "repaired": repair.get("repaired"),
                        "failed": repair.get("failed"),
                    },
                    "check": check,
                    "objects": entries,
                },
                fh,
                indent=2,
            )
        return package

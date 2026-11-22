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

    def export(self, package: KnowledgePackage, strict_permissions: bool = False) -> KnowledgePackage:
        repair = ensure_knowledge_object_provenance(package)
        check = provenance_report(package)
        entries: List[Dict[str, Any]] = []
        # Exclude knowledge_objects with explicit permission read=False (aligned with other delivery boundaries).
        # strict_permissions=True additionally excludes objects that have source identity but no explicit entry
        # (production-oriented fail-closed; default False preserves pilot compatibility).
        raw_permissions = package.metadata.get("permissions", {}) if hasattr(package, "metadata") else {}
        permissions = raw_permissions if isinstance(raw_permissions, dict) else {}
        def _is_forbidden(ko) -> bool:
            oid = str(getattr(ko, "id", "") or "")
            provenance = getattr(ko, "provenance", None) or {}
            src_ids = provenance.get("source_record_ids") or []
            if not isinstance(src_ids, list):
                src_ids = []
            keys = []
            if oid:
                keys.append(oid)
            for rid in src_ids:
                s = str(rid)
                keys.append(s[4:] if s.startswith("src:") else s)
            if not keys:
                return False
            has_explicit = False
            for key in keys:
                perm = permissions.get(key)
                if perm is not None and isinstance(perm, dict):
                    has_explicit = True
                    if perm.get("read") is False:
                        return True
            if strict_permissions and not has_explicit:
                return True
            return False
        for ko in package.knowledge_objects:
            if _is_forbidden(ko):
                continue
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
                    "conversation_id": prov.get("conversation_id")
                    or getattr(ko, "conversation_id", None),
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

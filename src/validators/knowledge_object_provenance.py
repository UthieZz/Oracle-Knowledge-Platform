"""Deterministic KnowledgeObject provenance normalization.

Does not change importers or the compiler. Mutates KO.provenance / evidence
in place so exporters and Studio receive a complete lineage contract:

    platform → conversation → message(s) → attachment(s) → knowledge object
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.models.knowledge_package import KnowledgePackage


REQUIRED_PROVENANCE_KEYS = (
    "source_platform",
    "source_file",
    "conversation_id",
)


def _conv_index(package: KnowledgePackage) -> Dict[str, Any]:
    index: Dict[str, Any] = {}
    for conv in package.conversations:
        cid = getattr(conv, "id", None)
        if cid is not None:
            index[str(cid)] = conv
    return index


def _message_ids(conv: Any) -> List[str]:
    ids: List[str] = []
    for msg in getattr(conv, "messages", []) or []:
        mid = getattr(msg, "id", None)
        if mid:
            ids.append(str(mid))
    return ids


def _attachment_ids(package: KnowledgePackage, conversation_id: Optional[str]) -> List[str]:
    if not conversation_id:
        return []
    ids: List[str] = []
    for att in package.attachment_knowledge:
        if str(getattr(att, "conversation_id", "") or "") != str(conversation_id):
            continue
        aid = getattr(att, "id", None) or getattr(att, "attachment_id", None)
        if aid:
            ids.append(str(aid))
    return ids


def _resolve_conversation_id(ko: Any, convs: Dict[str, Any]) -> Optional[str]:
    prov = ko.provenance or {}
    for key in ("conversation_id", "conversationId", "conversation"):
        value = prov.get(key)
        if value:
            return str(value)
    kid = str(getattr(ko, "id", "") or "")
    if kid in convs:
        return kid
    return None


def ensure_knowledge_object_provenance(
    package: KnowledgePackage,
    *,
    strict: bool = False,
) -> Dict[str, Any]:
    """Fill missing KO lineage from the package. Returns a repair report.

    If ``strict`` is True, raises ValueError when any KO still lacks
    REQUIRED_PROVENANCE_KEYS after repair.
    """
    convs = _conv_index(package)
    report: Dict[str, Any] = {
        "ok": 0,
        "repaired": 0,
        "failed": [],
        "total": len(package.knowledge_objects),
    }

    for ko in package.knowledge_objects:
        prov = dict(getattr(ko, "provenance", None) or {})
        repaired = False

        platform = prov.get("source_platform") or getattr(ko, "source_platform", None)
        if platform and prov.get("source_platform") != platform:
            prov["source_platform"] = platform
            repaired = True
        elif not prov.get("source_platform") and platform:
            prov["source_platform"] = platform
            repaired = True

        source_file = prov.get("source_file") or getattr(ko, "source_file", None)
        if source_file and prov.get("source_file") != source_file:
            prov["source_file"] = source_file
            repaired = True
        elif not prov.get("source_file") and source_file:
            prov["source_file"] = source_file
            repaired = True

        conversation_id = _resolve_conversation_id(ko, convs)
        if conversation_id and prov.get("conversation_id") != conversation_id:
            prov["conversation_id"] = conversation_id
            repaired = True

        conv = convs.get(str(prov.get("conversation_id") or ""))
        if conv:
            conv_prov = getattr(conv, "provenance", None) or {}
            if not prov.get("source_platform") and conv_prov.get("source_platform"):
                prov["source_platform"] = conv_prov["source_platform"]
                repaired = True
            if not prov.get("imported_at") and conv_prov.get("imported_at"):
                prov["imported_at"] = conv_prov["imported_at"]
                repaired = True
            if not prov.get("schema_version") and conv_prov.get("schema_version"):
                prov["schema_version"] = conv_prov["schema_version"]
                repaired = True

            msg_ids = _message_ids(conv)
            if msg_ids and not prov.get("message_ids"):
                prov["message_ids"] = msg_ids
                repaired = True
            evidence = list(getattr(ko, "evidence", None) or [])
            if not evidence and msg_ids:
                ko.evidence = list(msg_ids)
                repaired = True

        att_ids = _attachment_ids(package, prov.get("conversation_id"))
        if att_ids and not prov.get("attachment_ids"):
            prov["attachment_ids"] = att_ids
            repaired = True

        if "object_type" not in prov:
            prov["object_type"] = "knowledge_object"
            repaired = True

        ko.provenance = prov

        missing = [key for key in REQUIRED_PROVENANCE_KEYS if not prov.get(key)]
        if missing:
            report["failed"].append({"id": getattr(ko, "id", None), "missing": missing})
        elif repaired:
            report["repaired"] += 1
        else:
            report["ok"] += 1

    if strict and report["failed"]:
        raise ValueError(
            "KnowledgeObject provenance incomplete: "
            + ", ".join(
                f"{item['id']} missing {item['missing']}" for item in report["failed"]
            )
        )

    return report


def provenance_report(package: KnowledgePackage) -> Dict[str, Any]:
    """Read-only check. Does not mutate the package."""
    failed = []
    for ko in package.knowledge_objects:
        prov = getattr(ko, "provenance", None) or {}
        missing = [key for key in REQUIRED_PROVENANCE_KEYS if not prov.get(key)]
        if missing:
            failed.append({"id": getattr(ko, "id", None), "missing": missing})
    return {
        "total": len(package.knowledge_objects),
        "failed": failed,
        "ok": len(package.knowledge_objects) - len(failed),
    }

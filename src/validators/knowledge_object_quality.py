"""Deterministic quality flags for compiled Knowledge Objects.

Does not rewrite KO content or titles. Writes flags into provenance so
exporters and Studio can distinguish conversation-shaped artifacts from
reusable knowledge without changing the compiler.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.models.knowledge_package import KnowledgePackage

QUESTION_PREFIXES = (
    "how ",
    "what ",
    "why ",
    "when ",
    "where ",
    "who ",
    "can ",
    "could ",
    "would ",
    "should ",
    "is ",
    "are ",
    "do ",
    "does ",
    "did ",
    "hey ",
    "okay ",
    "ok ",
)


def _is_conversation_shaped(title: str) -> bool:
    t = (title or "").strip().lower()
    if not t:
        return True
    if t.endswith("?"):
        return True
    if any(t.startswith(p) for p in QUESTION_PREFIXES):
        return True
    if len(t.split()) > 12:
        return True
    return False


def annotate_knowledge_object_quality(package: KnowledgePackage) -> Dict[str, Any]:
    conversation_shaped = 0
    flagged: List[Dict[str, Any]] = []
    for ko in package.knowledge_objects:
        prov = dict(getattr(ko, "provenance", None) or {})
        shaped = _is_conversation_shaped(getattr(ko, "title", "") or "")
        thin = len((getattr(ko, "content", "") or "").strip()) < 80
        missing_evidence = not list(getattr(ko, "evidence", None) or [])
        quality = {
            "conversation_shaped": shaped,
            "thin_content": thin,
            "missing_evidence": missing_evidence,
            "reusable_candidate": not shaped and not thin and not missing_evidence,
        }
        if prov.get("quality") != quality:
            prov["quality"] = quality
            ko.provenance = prov
        if shaped or thin:
            conversation_shaped += 1
            flagged.append({"id": getattr(ko, "id", None), "quality": quality})
    return {
        "total": len(package.knowledge_objects),
        "conversation_shaped_or_thin": conversation_shaped,
        "flagged": flagged,
    }

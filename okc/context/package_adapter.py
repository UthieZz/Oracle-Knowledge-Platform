"""Pure adapter from KnowledgePackage to evidence spans for Context-Aware Reasoning.

Extracts existing evidence spans and any explicitly declared constraints from package metadata.
No inference, no domain interpretation, no promotion of unvalidated facts.
Preserves provenance.

Locked contracts: I-02 (package declarations never substitute for evidence), I-10.
"""

from __future__ import annotations

from typing import Any, Dict, List

from okc.models.knowledge_package import KnowledgePackage


def extract_evidence_spans(package: KnowledgePackage) -> List[Dict[str, Any]]:
    """Return evidence spans as dicts suitable for the compatibility engine.

    Includes span content, provenance, and any explicit 'constraints' dict
    present under object.metadata or package.metadata['context_constraints'].
    Does not invent constraints.
    """
    spans: List[Dict[str, Any]] = []
    pkg_constraints = package.metadata.get("context_constraints", {}) if package.metadata else {}

    for obj in package.objects:
        obj_constraints = {}
        if hasattr(obj, "metadata") and isinstance(getattr(obj, "metadata", None), dict):
            obj_constraints = obj.metadata.get("constraints") or obj.metadata.get("context_constraints", {})
        # Prefer object-level if present; else package-level keyed by object_id
        constraints = obj_constraints or pkg_constraints.get(obj.object_id, {})

        for span in obj.evidence:
            span_dict: Dict[str, Any] = {
                "span_id": span.span_id,
                "object_id": obj.object_id,
                "content": span.content,
                "provenance": obj.provenance.model_dump() if hasattr(obj.provenance, "model_dump") else {},
                "constraints": constraints,  # may be empty
            }
            spans.append(span_dict)
    return spans

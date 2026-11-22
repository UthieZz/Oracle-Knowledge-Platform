"""Pure adapter from KnowledgePackage to evidence spans for Context-Aware Reasoning.

Extracts existing evidence spans and any explicitly declared constraints from package metadata.
No inference, no domain interpretation, no promotion of unvalidated facts.
Preserves provenance.

Permission filtering (aligned with KnowledgePackageRetriever, HybridRAG, exporters):
- Explicit read=False entries are always excluded (fail-closed for recorded denials).
- strict_permissions=False (default, pilot): objects without a permission entry are included.
- strict_permissions=True: objects with a source identity but no permission entry are excluded.

Locked contracts: I-02 (package declarations never substitute for evidence), I-10.
"""

from __future__ import annotations

from typing import Any, Dict, List

from okc.models.knowledge_package import KnowledgePackage


def _is_forbidden(obj, package: KnowledgePackage, strict_permissions: bool) -> bool:
    """Return True if the object should be excluded under the permission model."""
    raw_permissions = package.metadata.get("permissions", {}) if package.metadata else {}
    permissions = raw_permissions if isinstance(raw_permissions, dict) else {}
    src_ids = [
        rid[4:] for rid in (obj.provenance.source_record_ids or [])
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


def extract_evidence_spans(
    package: KnowledgePackage, strict_permissions: bool = False
) -> List[Dict[str, Any]]:
    """Return evidence spans as dicts suitable for the compatibility engine.

    Includes span content, provenance, and any explicit 'constraints' dict
    present under object.metadata or package.metadata['context_constraints'].
    Does not invent constraints.
    Filters objects according to the permission model (see module docstring).
    """
    spans: List[Dict[str, Any]] = []
    pkg_constraints = package.metadata.get("context_constraints", {}) if package.metadata else {}

    for obj in package.objects:
        if _is_forbidden(obj, package, strict_permissions):
            continue
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

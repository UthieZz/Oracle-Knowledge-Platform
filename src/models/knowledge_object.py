"""Canonical, model-ready knowledge IR with mandatory evidence lineage."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class KnowledgeObject:
    # Existing core fields remain stable for importers and exporters.
    id: str
    title: str
    content: str
    source_platform: str
    source_file: str
    created_at: Optional[str]
    updated_at: Optional[str]
    provenance: Dict[str, Any]
    evidence: List[str]

    # Versioned evidence-first IR. Candidate data must cite evidence IDs.
    schema_version: str = "2.0"
    object_type: str = "conversation"
    conversation_id: Optional[str] = None
    source_record_ids: List[str] = field(default_factory=list)
    evidence_spans: List[Dict[str, Any]] = field(default_factory=list)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    topics: List[Dict[str, Any]] = field(default_factory=list)
    temporal_signals: List[Dict[str, Any]] = field(default_factory=list)
    claims: List[Dict[str, Any]] = field(default_factory=list)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    action_items: List[Dict[str, Any]] = field(default_factory=list)
    questions: List[Dict[str, Any]] = field(default_factory=list)
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    retrieval: Dict[str, Any] = field(default_factory=dict)
    quality: Dict[str, Any] = field(default_factory=dict)

    def add_evidence_span(self, text: str, source_id: str, kind: str = "message", **metadata: Any) -> str:
        """Add source-faithful evidence and return its local evidence id."""
        evidence_id = f"ev_{len(self.evidence_spans) + 1}"
        span = {
            "id": evidence_id,
            "kind": kind,
            "source_id": source_id,
            "text": text,
            **metadata,
        }
        self.evidence_spans.append(span)
        if evidence_id not in self.evidence:
            self.evidence.append(evidence_id)
        return evidence_id

    def validate_provenance(self) -> List[str]:
        """Return validation errors for missing source identity or broken evidence links."""
        errors: List[str] = []
        if not self.source_platform:
            errors.append("source_platform is required")
        if not self.source_file:
            errors.append("source_file is required")
        known = {span.get("id") for span in self.evidence_spans}
        for field_name in ("claims", "decisions", "action_items", "questions", "relationships"):
            for item in getattr(self, field_name, []) or []:
                evidence_ids = item.get("evidence_ids") or []
                if not evidence_ids:
                    errors.append(f"{field_name} item missing evidence_ids")
                for evidence_id in evidence_ids:
                    if evidence_id not in known:
                        errors.append(f"{field_name} references unknown evidence_id {evidence_id}")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

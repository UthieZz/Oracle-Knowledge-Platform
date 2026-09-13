import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class EvidenceSpan(BaseModel):
    """
    Maintains provenance by mapping normalized messages to stable local IDs.
    """
    span_id: str
    message_id: str
    role: str
    timestamp: str
    content: str


class Provenance(BaseModel):
    """
    Strictly preserves the origin of the knowledge object.
    """
    source_platform: str
    source_file: str
    source_record_ids: List[str] = Field(default_factory=list)
    tenant_id: str
    silo_id: str


class KnowledgeObject(BaseModel):
    """
    The upgraded KnowledgeObject intermediate representation (IR v2).
    """
    object_id: str
    title: str
    provenance: Provenance
    evidence: List[EvidenceSpan] = Field(default_factory=list)
    content: str
    entities: List[str] = Field(default_factory=list)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    context_citations: List[str] = Field(default_factory=list)


class KnowledgePackage(BaseModel):
    """
    A strictly versioned JSON/Protobuf-compatible schema serving as the
    system's single invariant Intermediate Representation.
    """
    schema_version: str = Field(default="2.0.0", frozen=True)
    package_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    objects: List[KnowledgeObject] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        """Outputs a standard JSON string payload for downstream exporters."""
        return self.model_dump_json(indent=2)

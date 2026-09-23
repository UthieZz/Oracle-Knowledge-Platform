from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List
from pydantic import BaseModel, Field

class AgentContextRequest(BaseModel):
    """A model or agent request for a governed slice of OKP context."""
    schema_version: str = Field(default="1.0.0", frozen=True)
    request_id: str
    tenant_id: str
    silo_id: str
    agent_id: str
    task: str
    session_id: str | None = None
    required_capabilities: List[str] = Field(default_factory=list)
    max_context_items: int = Field(default=12, ge=1, le=100)
    include_provenance: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ContextItem(BaseModel):
    """Model-facing representation of one governed KnowledgeObject."""
    object_id: str
    title: str
    content: str
    provenance: Dict[str, Any]
    evidence_ids: List[str] = Field(default_factory=list)
    relevance_score: float | None = None

class AgentContextPackage(BaseModel):
    """Portable context contract delivered to an agent runtime.

    This is deliberately distinct from KnowledgePackage. KnowledgePackage is
    OKP's canonical IR; AgentContextPackage is a filtered, model-facing view.
    """
    schema_version: str = Field(default="1.0.0", frozen=True)
    request_id: str
    tenant_id: str
    silo_id: str
    agent_id: str
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    task: str
    items: List[ContextItem] = Field(default_factory=list)
    instructions: List[str] = Field(default_factory=list)
    tool_names: List[str] = Field(default_factory=list)
    provenance_complete: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

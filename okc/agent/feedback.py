"""Inbound agent feedback contracts.

Feedback is process/audit data. It is not canonical knowledge.
Memory candidates and inferred claims must not be written into
KnowledgePackage until a compilation/validation contract exists.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


class CitationEvent(BaseModel):
    object_id: str
    evidence_ids: List[str] = Field(default_factory=list)
    quote: str | None = None


class ToolEvent(BaseModel):
    tool_name: str
    status: Literal["requested", "allowed", "denied", "succeeded", "failed"]
    arguments_digest: str | None = None
    result_digest: str | None = None
    error: str | None = None


class MemoryCandidate(BaseModel):
    """Proposed durable memory. Not a KnowledgeObject."""

    candidate_id: str
    text: str
    source_object_ids: List[str] = Field(default_factory=list)
    confidence: float | None = None
    accepted: bool = False


class AuditRecord(BaseModel):
    event_type: str
    detail: Dict[str, Any] = Field(default_factory=dict)


class AgentFeedbackPackage(BaseModel):
    """Model/agent output returned to OKP without becoming IR."""

    schema_version: str = Field(default="1.0.0", frozen=True)
    request_id: str
    tenant_id: str
    silo_id: str
    agent_id: str
    received_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    citations: List[CitationEvent] = Field(default_factory=list)
    tool_events: List[ToolEvent] = Field(default_factory=list)
    memory_candidates: List[MemoryCandidate] = Field(default_factory=list)
    audit: List[AuditRecord] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FeedbackAcceptanceError(ValueError):
    """Raised when feedback cannot be accepted at the OKP boundary."""


class FeedbackLedger:
    """In-memory acceptance log. Persistence is an adapter concern."""

    def __init__(self) -> None:
        self.records: list[AgentFeedbackPackage] = []

    def accept(self, feedback: AgentFeedbackPackage) -> AgentFeedbackPackage:
        if not feedback.request_id or not feedback.tenant_id or not feedback.silo_id:
            raise FeedbackAcceptanceError("Feedback is missing isolation identity.")
        for candidate in feedback.memory_candidates:
            if candidate.accepted:
                raise FeedbackAcceptanceError(
                    "Memory candidates cannot be marked accepted at the gateway. "
                    "Promotion requires a compilation/validation contract."
                )
        stored = feedback.model_copy(deep=True)
        self.records.append(stored)
        return stored

from __future__ import annotations
from typing import Sequence
from okc.models.knowledge_package import KnowledgeObject
from .interfaces import ContextPolicy, KnowledgeRetriever
from .models import AgentContextPackage, AgentContextRequest, ContextItem

class ContextAccessError(PermissionError):
    """Raised when context cannot safely cross the OKP/agent boundary."""

class AllowAllContextPolicy:
    """Development policy only. Production must enforce real authorization."""
    def filter(self, request: AgentContextRequest, objects: Sequence[KnowledgeObject]) -> Sequence[KnowledgeObject]:
        return objects

class ContextGateway:
    """Build a governed, model-facing context package from OKP knowledge."""
    def __init__(self, retriever: KnowledgeRetriever, policy: ContextPolicy | None = None) -> None:
        self.retriever = retriever
        self.policy = policy or AllowAllContextPolicy()

    def build(self, request: AgentContextRequest) -> AgentContextPackage:
        objects = list(self.retriever.retrieve(request))
        allowed = list(self.policy.filter(request, objects))
        items: list[ContextItem] = []

        for obj in allowed[: request.max_context_items]:
            if obj.provenance.tenant_id != request.tenant_id or obj.provenance.silo_id != request.silo_id:
                raise ContextAccessError("KnowledgeObject crossed a tenant/silo boundary.")

            provenance = obj.provenance.model_dump() if request.include_provenance else {}
            items.append(
                ContextItem(
                    object_id=obj.object_id,
                    title=obj.title,
                    content=obj.content,
                    provenance=provenance,
                    evidence_ids=[span.span_id for span in obj.evidence],
                )
            )

        complete = all(bool(item.provenance) for item in items) if request.include_provenance else False
        return AgentContextPackage(
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            silo_id=request.silo_id,
            agent_id=request.agent_id,
            task=request.task,
            items=items,
            provenance_complete=complete,
        )

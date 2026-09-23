from __future__ import annotations
from typing import Protocol, Sequence
from okc.models.knowledge_package import KnowledgeObject
from .models import AgentContextRequest

class KnowledgeRetriever(Protocol):
    """Retrieve KnowledgeObjects without exposing the retrieval implementation."""
    def retrieve(self, request: AgentContextRequest) -> Sequence[KnowledgeObject]:
        ...

class ContextPolicy(Protocol):
    """Apply enterprise policy before knowledge reaches an agent."""
    def filter(self, request: AgentContextRequest, objects: Sequence[KnowledgeObject]) -> Sequence[KnowledgeObject]:
        ...

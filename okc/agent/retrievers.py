"""Retrieval adapters over canonical KnowledgePackage objects.

These adapters do not invent a second IR. They select existing KnowledgeObjects
for the Agent Context Gateway. Ranking here is an index/process concern.
"""
from __future__ import annotations

import re
from typing import Sequence

from okc.models.knowledge_package import KnowledgeObject, KnowledgePackage

from .models import AgentContextRequest

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall((text or "").lower()))


def _score(request: AgentContextRequest, obj: KnowledgeObject) -> float:
    query = _tokens(request.task)
    if not query:
        return 0.0
    haystack = _tokens(" ".join([obj.title, obj.content, " ".join(obj.entities)]))
    if not haystack:
        return 0.0
    overlap = query & haystack
    return len(overlap) / len(query)


class KnowledgePackageRetriever:
    """Select tenant/silo-scoped objects from one KnowledgePackage.

    Isolation is enforced at retrieve time and again at the gateway.
    Unrelated objects stay in the package; they are not deleted.
    """

    def __init__(self, package: KnowledgePackage, min_score: float = 0.0) -> None:
        self.package = package
        self.min_score = min_score

    def retrieve(self, request: AgentContextRequest) -> Sequence[KnowledgeObject]:
        scoped: list[tuple[float, KnowledgeObject]] = []
        for obj in self.package.objects:
            if obj.provenance.tenant_id != request.tenant_id:
                continue
            if obj.provenance.silo_id != request.silo_id:
                continue
            score = _score(request, obj)
            if score < self.min_score:
                continue
            obj_copy = obj.model_copy(deep=True)
            scoped.append((score, obj_copy))
        scoped.sort(key=lambda pair: pair[0], reverse=True)
        return [obj for _, obj in scoped[: request.max_context_items]]

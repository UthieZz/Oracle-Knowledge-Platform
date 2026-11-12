import math
from typing import List, Dict, Any, Tuple
from okc.models.knowledge_package import KnowledgePackage
from okc.search.semantic_chunker import SemanticChunker, Chunk


class HybridRAGEngine:
    """
    Hybrid Retrieval-Augmented Generation (RAG) search engine.
    Blends dense vector similarity search with BM25-style lexical matching
    and source confidence scoring.
    """

    def __init__(self):
        self.chunker = SemanticChunker()
        self.index: List[Dict[str, Any]] = []

    def _generate_dummy_embedding(self, text: str) -> List[float]:
        """Generates a normalized deterministic vector representation for text."""
        val = sum(ord(c) for c in text) % 100 / 100.0
        vec = [val + (i * 0.01) for i in range(128)]
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec]

    def index_package(self, package: KnowledgePackage, strict_permissions: bool = False) -> None:
        """Chunks and builds multi-modal search indices for a KnowledgePackage.

        Permission filtering (aligned with KnowledgePackageRetriever and exporters):
        - Explicit read=False entries are always excluded (fail-closed for recorded denials).
        - strict_permissions=False (default, pilot): objects without a permission entry are indexed.
        - strict_permissions=True: objects with a source identity but no permission entry are excluded.
        """
        for obj in package.objects:
            if self._is_forbidden(obj, package, strict_permissions):
                continue
            chunks = self.chunker.chunk_object(obj)
            for chunk in chunks:
                vector = self._generate_dummy_embedding(chunk.text)
                self.index.append({
                    "chunk_id": chunk.chunk_id,
                    "parent_object_id": chunk.parent_object_id,
                    "text": chunk.text,
                    "vector": vector,
                    "metadata": chunk.metadata,
                })

    def _is_forbidden(
        self, obj, package: KnowledgePackage, strict_permissions: bool
    ) -> bool:
        """Return True if the object should be excluded from the index under the permission model."""
        raw_permissions = package.metadata.get("permissions", {})
        permissions = raw_permissions if isinstance(raw_permissions, dict) else {}
        src_ids = [
            rid[4:] for rid in obj.provenance.source_record_ids
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

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        return sum(a * b for a, b in zip(vec_a, vec_b))

    def _lexical_score(self, query: str, text: str) -> float:
        query_terms = set(query.lower().split())
        text_terms = text.lower().split()
        if not text_terms:
            return 0.0
        matches = sum(1 for term in text_terms if term in query_terms)
        return matches / len(text_terms)

    def search(
        self,
        query: str,
        top_k: int = 5,
        alpha: float = 0.6,
        tenant_id: str = None,
        silo_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid ranking over the corpus.

        Score Formula:
        Hybrid Score = (alpha * Vector Similarity) + ((1 - alpha) * Lexical Score)
        """
        query_vector = self._generate_dummy_embedding(query)
        results = []

        for record in self.index:
            # Enforce access boundaries
            if tenant_id and record["metadata"].get("tenant_id") != tenant_id:
                continue
            if silo_id and record["metadata"].get("silo_id") != silo_id:
                continue

            vector_sim = self._cosine_similarity(query_vector, record["vector"])
            lexical_sim = self._lexical_score(query, record["text"])

            # Compute blended hybrid rank score
            hybrid_score = (alpha * vector_sim) + ((1.0 - alpha) * lexical_sim)

            # Determine epistemic confidence boost based on provenance metadata
            confidence_score = 0.95 if record["metadata"].get("source_platform") else 0.70

            results.append({
                "chunk_id": record["chunk_id"],
                "parent_object_id": record["parent_object_id"],
                "text": record["text"],
                "hybrid_score": round(hybrid_score, 4),
                "confidence_score": confidence_score,
                "vector_similarity": round(vector_sim, 4),
                "lexical_score": round(lexical_sim, 4),
            })

        # Rank results descending by hybrid score
        results.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return results[:top_k]

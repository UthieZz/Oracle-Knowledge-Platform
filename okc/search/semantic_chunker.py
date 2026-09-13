from typing import List, Dict, Any
from okc.models.knowledge_package import KnowledgeObject


class Chunk:
    """Represents a bounded semantic chunk tied to parent source provenance."""

    def __init__(self, chunk_id: str, parent_object_id: str, text: str, metadata: Dict[str, Any]):
        self.chunk_id = chunk_id
        self.parent_object_id = parent_object_id
        self.text = text
        self.metadata = metadata


class SemanticChunker:
    """Splits KnowledgeObject contents into semantic contexts with sliding window overlap."""

    def __init__(self, chunk_size: int = 500, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_object(self, obj: KnowledgeObject) -> List[Chunk]:
        text = obj.content
        words = text.split()
        chunks = []

        if not words:
            return chunks

        idx = 0
        chunk_idx = 0
        while idx < len(words):
            end_idx = min(idx + self.chunk_size, len(words))
            chunk_text = " ".join(words[idx:end_idx])

            chunk_meta = {
                "source_platform": obj.provenance.source_platform,
                "tenant_id": obj.provenance.tenant_id,
                "silo_id": obj.provenance.silo_id,
                "entities": obj.entities,
            }

            chunk = Chunk(
                chunk_id=f"{obj.object_id}_chunk_{chunk_idx}",
                parent_object_id=obj.object_id,
                text=chunk_text,
                metadata=chunk_meta,
            )
            chunks.append(chunk)

            if end_idx == len(words):
                break

            idx += (self.chunk_size - self.overlap)
            chunk_idx += 1

        return chunks

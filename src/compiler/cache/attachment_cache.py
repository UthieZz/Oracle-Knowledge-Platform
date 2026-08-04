import hashlib
from typing import Dict, Optional
from src.models.attachment_knowledge import AttachmentKnowledge


class AttachmentCache:
    """Thread-safe, deterministic cache store for AttachmentKnowledge objects.

    Allows independent cacheability and resumability across multiple compiler runs.
    Keys are calculated based on attachment fingerprint, processor name, and processor version.
    """

    def __init__(self):
        self._store: Dict[str, AttachmentKnowledge] = {}
        self.hits: int = 0
        self.misses: int = 0

    @staticmethod
    def build_cache_key(fingerprint: str, processor_name: str, processor_version: str) -> str:
        raw = f"{fingerprint}:{processor_name}:{processor_version}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(
        self, fingerprint: str, processor_name: str, processor_version: str
    ) -> Optional[AttachmentKnowledge]:
        key = self.build_cache_key(fingerprint, processor_name, processor_version)
        if key in self._store:
            self.hits += 1
            return self._store[key]
        self.misses += 1
        return None

    def put(self, item: AttachmentKnowledge) -> None:
        key = self.build_cache_key(
            item.fingerprint, item.processor_name, item.processor_version
        )
        self._store[key] = item

    def has(self, fingerprint: str, processor_name: str, processor_version: str) -> bool:
        key = self.build_cache_key(fingerprint, processor_name, processor_version)
        return key in self._store

    def clear(self) -> None:
        self._store.clear()
        self.hits = 0
        self.misses = 0

    def size(self) -> int:
        return len(self._store)

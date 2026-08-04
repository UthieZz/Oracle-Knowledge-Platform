from abc import ABC, abstractmethod
import hashlib
from typing import Any, Dict, List, Optional, Type
from src.models.attachment_knowledge import AttachmentKnowledge


class AttachmentTask:
    """Self-contained processing context for a single attachment."""

    def __init__(
        self,
        attachment_id: str,
        conversation_id: str,
        file_name: str,
        message_id: Optional[str] = None,
        file_path_or_url: Optional[str] = None,
        media_type: str = "unknown",
        fingerprint: Optional[str] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ):
        self.attachment_id = attachment_id
        self.conversation_id = conversation_id
        self.message_id = message_id
        self.file_name = file_name
        self.file_path_or_url = file_path_or_url or file_name
        self.media_type = media_type
        self.provenance = provenance if provenance is not None else {}

        # Compute SHA-256 fingerprint if not provided
        self.fingerprint = fingerprint or self.compute_fingerprint(
            self.file_name, self.file_path_or_url, self.provenance
        )

    @staticmethod
    def compute_fingerprint(
        file_name: str, file_path_or_url: str, provenance: Dict[str, Any]
    ) -> str:
        """Generate SHA-256 fingerprint from attachment descriptor attributes."""
        source_url = provenance.get("url") or file_path_or_url or ""
        raw_key = f"{file_name}:{source_url}:{provenance.get('timestamp', '')}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


class BaseAttachmentProcessor(ABC):
    """Abstract base class for all attachment processors."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass

    @property
    @abstractmethod
    def media_type(self) -> str:
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        pass

    @abstractmethod
    def process(self, task: AttachmentTask) -> AttachmentKnowledge:
        """Process an AttachmentTask into an AttachmentKnowledge object."""
        pass


class AttachmentProcessorRegistry:
    """Central registry mapping attachments to media processors."""

    def __init__(self):
        self._processors: Dict[str, BaseAttachmentProcessor] = {}
        self._extension_map: Dict[str, BaseAttachmentProcessor] = {}

    def register(self, processor: BaseAttachmentProcessor) -> None:
        """Register a processor instance."""
        self._processors[processor.name] = processor
        for ext in processor.supported_extensions:
            clean_ext = ext.lower().lstrip(".")
            self._extension_map[clean_ext] = processor

    def find_processor(
        self, file_name: str, media_type: Optional[str] = None
    ) -> Optional[BaseAttachmentProcessor]:
        """Lookup matching processor by file extension or explicit media type."""
        ext = file_name.split(".")[-1].lower() if "." in file_name else ""
        if ext in self._extension_map:
            return self._extension_map[ext]

        if media_type:
            for proc in self._processors.values():
                if proc.media_type.lower() == media_type.lower():
                    return proc

        return None

    def get_supported_extensions(self) -> List[str]:
        return list(self._extension_map.keys())

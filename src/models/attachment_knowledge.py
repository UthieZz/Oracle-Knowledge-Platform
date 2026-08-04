import hashlib
from typing import Any, Dict, List, Optional


class AttachmentKnowledge:
    """A structured representation of knowledge extracted from an attachment.

    Attributes:
        id: Deterministic SHA-256 hash identifying this extraction.
        attachment_id: Identifier of the original attachment resource.
        conversation_id: Linked conversation ID.
        message_id: Linked message turn ID (if applicable).
        file_name: Original attachment filename.
        media_type: Standard media classification ('image', 'audio', 'pdf', etc.).
        fingerprint: SHA-256 digest of the attachment content/metadata.
        processor_name: Name of the processor used.
        processor_version: Version of the processor used.
        raw_extraction: Direct unstructured output (e.g. OCR text, transcript).
        structured_extraction: Structured features (headings, tables, UI components).
        summary: High-level summary of extracted attachment insights.
        keywords: Extracted tags and key phrases.
        entities: Extracted entity records.
        confidence: Normalized confidence score (0.0 to 1.0).
        metadata: Media-specific attributes (duration, dimensions, page count, etc.).
        provenance: Upstream lineage metadata (source platform, timestamps, etc.).
    """

    def __init__(
        self,
        attachment_id: str,
        conversation_id: str,
        file_name: str,
        media_type: str,
        fingerprint: str,
        processor_name: str,
        processor_version: str,
        message_id: Optional[str] = None,
        raw_extraction: str = "",
        structured_extraction: Optional[Dict[str, Any]] = None,
        summary: str = "",
        keywords: Optional[List[str]] = None,
        entities: Optional[List[Dict[str, Any]]] = None,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        provenance: Optional[Dict[str, Any]] = None,
        custom_id: Optional[str] = None,
    ):
        self.attachment_id = attachment_id
        self.conversation_id = conversation_id
        self.message_id = message_id
        self.file_name = file_name
        self.media_type = media_type
        self.fingerprint = fingerprint
        self.processor_name = processor_name
        self.processor_version = processor_version

        self.raw_extraction = raw_extraction
        self.structured_extraction = (
            structured_extraction if structured_extraction is not None else {}
        )
        self.summary = summary
        self.keywords = keywords if keywords is not None else []
        self.entities = entities if entities is not None else []
        self.confidence = confidence
        self.metadata = metadata if metadata is not None else {}
        self.provenance = provenance if provenance is not None else {}

        # Generate deterministic ID unless overridden
        self.id = custom_id or self.generate_deterministic_id(
            conversation_id=self.conversation_id,
            message_id=self.message_id,
            attachment_id=self.attachment_id,
            processor_version=self.processor_version,
        )

    @staticmethod
    def generate_deterministic_id(
        conversation_id: str,
        message_id: Optional[str],
        attachment_id: str,
        processor_version: str,
    ) -> str:
        """Compute a stable, deterministic ID from key lineage fields."""
        msg_part = message_id or "none"
        raw_key = f"{conversation_id}:{msg_part}:{attachment_id}:{processor_version}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def to_markdown(self) -> str:
        """Render extracted attachment knowledge into Markdown format."""
        lines = [
            f"## Attachment: {self.file_name} ({self.media_type.upper()})",
            f"**Attachment ID:** `{self.attachment_id}` | **Confidence:** {self.confidence:.2f}",
        ]
        if self.summary:
            lines.append(f"\n### Summary\n{self.summary}")
        if self.raw_extraction:
            lines.append(f"\n### Raw Content\n```\n{self.raw_extraction}\n```")
        if self.keywords:
            lines.append(f"\n**Keywords:** {', '.join(self.keywords)}")
        return "\n".join(lines)

    def to_knowledge_object(self) -> Dict[str, Any]:
        """Convert AttachmentKnowledge into a canonical dictionary representation."""
        return {
            "id": self.id,
            "attachment_id": self.attachment_id,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "file_name": self.file_name,
            "media_type": self.media_type,
            "fingerprint": self.fingerprint,
            "processor_name": self.processor_name,
            "processor_version": self.processor_version,
            "raw_extraction": self.raw_extraction,
            "structured_extraction": self.structured_extraction,
            "summary": self.summary,
            "keywords": self.keywords,
            "entities": self.entities,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "provenance": self.provenance,
        }

    def __repr__(self) -> str:
        return (
            f"<AttachmentKnowledge id={self.id[:8]!r} file={self.file_name!r} "
            f"type={self.media_type!r} conv={self.conversation_id[:8]!r}>"
        )

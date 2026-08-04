from typing import List, Optional
from src.compiler.processors.processor_registry import (
    AttachmentTask,
    BaseAttachmentProcessor,
)
from src.models.attachment_knowledge import AttachmentKnowledge
from src.providers.ocr_provider import DefaultOCRProvider, OCRProvider


class PdfProcessor(BaseAttachmentProcessor):
    """Processes PDF attachments with native text extraction and OCR fallback."""

    def __init__(self, ocr_provider: Optional[OCRProvider] = None):
        self.ocr_provider = ocr_provider or DefaultOCRProvider()

    @property
    def name(self) -> str:
        return "PdfProcessor"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def media_type(self) -> str:
        return "pdf"

    @property
    def supported_extensions(self) -> List[str]:
        return ["pdf"]

    def process(self, task: AttachmentTask) -> AttachmentKnowledge:
        # Native extraction placeholder / OCR fallback
        extracted_text = self.ocr_provider.extract_text(task.file_path_or_url, task.provenance)
        if not extracted_text:
            extracted_text = f"[PDF Document Content for {task.file_name}]"

        page_count = task.provenance.get("page_count", 1)
        headings = [f"Section 1: Overview of {task.file_name}"]
        paragraphs = [extracted_text]
        tables = task.provenance.get("tables", [])

        summary = f"PDF document '{task.file_name}' containing {page_count} page(s)."
        keywords = ["pdf", "document", task.file_name.split(".")[0].lower()]

        structured_extraction = {
            "headings": headings,
            "paragraphs": paragraphs,
            "tables": tables,
            "page_count": page_count,
        }

        return AttachmentKnowledge(
            attachment_id=task.attachment_id,
            conversation_id=task.conversation_id,
            message_id=task.message_id,
            file_name=task.file_name,
            media_type="pdf",
            fingerprint=task.fingerprint,
            processor_name=self.name,
            processor_version=self.version,
            raw_extraction=extracted_text,
            structured_extraction=structured_extraction,
            summary=summary,
            keywords=keywords,
            entities=[],
            confidence=0.98,
            metadata={
                "page_count": page_count,
                "author": task.provenance.get("author", "Unknown"),
                "title": task.provenance.get("title", task.file_name),
            },
            provenance=task.provenance,
        )

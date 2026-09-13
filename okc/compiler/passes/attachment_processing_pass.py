import logging
from typing import Dict, Type

from okc.models.knowledge_package import KnowledgePackage
from okc.compiler.processors.attachment_processor import (
    BaseAttachmentProcessor,
    ImageOCRProcessor,
    AudioTranscriptProcessor,
    PDFProcessor,
)

logger = logging.getLogger(__name__)


class AttachmentProcessingPass:
    """
    Compiler pass that dispatches attachments to specialized processors and enriches
    KnowledgeObjects with extracted transcripts, OCR text, and metadata.
    """

    def __init__(self):
        self.registry: Dict[str, BaseAttachmentProcessor] = {
            ".png": ImageOCRProcessor(),
            ".jpg": ImageOCRProcessor(),
            ".jpeg": ImageOCRProcessor(),
            ".mp3": AudioTranscriptProcessor(),
            ".wav": AudioTranscriptProcessor(),
            ".pdf": PDFProcessor(),
        }

    def execute(self, package: KnowledgePackage) -> KnowledgePackage:
        logger.info("Executing AttachmentProcessingPass across KnowledgeObjects...")

        for obj in package.objects:
            updated_attachments = []
            for attachment in obj.attachments:
                file_path = attachment.get("file_path", "")
                ext = "." + file_path.split(".")[-1].lower() if "." in file_path else ""

                if ext in self.registry:
                    processor = self.registry[ext]
                    result = processor.process(file_path)

                    # Enrich attachment record with extracted knowledge
                    attachment.update({
                        "status": result["status"],
                        "extracted_text": result.get("extracted_text", ""),
                        "keywords": result.get("keywords", []),
                        "confidence": result.get("confidence", 0.0),
                        "provenance": obj.provenance.model_dump(),
                    })
                else:
                    attachment["status"] = "unsupported_format"

                updated_attachments.append(attachment)

            obj.attachments = updated_attachments

        return package

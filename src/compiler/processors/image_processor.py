from typing import List, Optional
from src.compiler.processors.processor_registry import (
    AttachmentTask,
    BaseAttachmentProcessor,
)
from src.models.attachment_knowledge import AttachmentKnowledge
from src.providers.ocr_provider import DefaultOCRProvider, OCRProvider
from src.providers.vision_provider import DefaultVisionProvider, VisionProvider


class ImageProcessor(BaseAttachmentProcessor):
    """Processes image attachments using OCR and Vision providers."""

    def __init__(
        self,
        ocr_provider: Optional[OCRProvider] = None,
        vision_provider: Optional[VisionProvider] = None,
    ):
        self.ocr_provider = ocr_provider or DefaultOCRProvider()
        self.vision_provider = vision_provider or DefaultVisionProvider()

    @property
    def name(self) -> str:
        return "ImageProcessor"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def media_type(self) -> str:
        return "image"

    @property
    def supported_extensions(self) -> List[str]:
        return ["jpg", "jpeg", "png", "gif", "bmp", "webp", "svg"]

    def process(self, task: AttachmentTask) -> AttachmentKnowledge:
        ocr_text = self.ocr_provider.extract_text(task.file_path_or_url, task.provenance)
        vision_data = self.vision_provider.analyze_image(task.file_path_or_url, task.provenance)

        summary = vision_data.get("image_description", f"Image content for {task.file_name}")
        keywords = vision_data.get("keywords", ["image", "visual"])
        confidence = float(vision_data.get("confidence", 0.95))

        structured_extraction = {
            "ocr_text": ocr_text,
            "image_description": vision_data.get("image_description"),
            "ui_description": vision_data.get("ui_description"),
            "chart_detected": vision_data.get("chart_detected", False),
            "detected_objects": vision_data.get("detected_objects", []),
        }

        return AttachmentKnowledge(
            attachment_id=task.attachment_id,
            conversation_id=task.conversation_id,
            message_id=task.message_id,
            file_name=task.file_name,
            media_type="image",
            fingerprint=task.fingerprint,
            processor_name=self.name,
            processor_version=self.version,
            raw_extraction=ocr_text,
            structured_extraction=structured_extraction,
            summary=summary,
            keywords=keywords,
            entities=[],
            confidence=confidence,
            metadata={
                "dimensions": task.provenance.get("dimensions"),
                "format": task.file_name.split(".")[-1].lower(),
            },
            provenance=task.provenance,
        )

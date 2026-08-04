import unittest
from src.compiler.cache.attachment_cache import AttachmentCache
from src.compiler.passes.attachment_processing_pass import AttachmentProcessingPass
from src.compiler.processors.audio_processor import AudioProcessor
from src.compiler.processors.image_processor import ImageProcessor
from src.compiler.processors.pdf_processor import PdfProcessor
from src.compiler.processors.processor_registry import (
    AttachmentProcessorRegistry,
    AttachmentTask,
)
from src.models.attachment_knowledge import AttachmentKnowledge
from src.models.conversation import Conversation
from src.models.knowledge_package import KnowledgePackage
from src.models.message import Message
from src.providers.ocr_provider import OCRProvider
from src.providers.transcription_provider import TranscriptionProvider
from src.providers.vision_provider import VisionProvider


class CustomMockOCRProvider(OCRProvider):
    def extract_text(self, file_path_or_url: str, metadata=None) -> str:
        return "CUSTOM_OCR_TEXT: Invoice #12345"


class CustomMockVisionProvider(VisionProvider):
    def analyze_image(self, file_path_or_url: str, metadata=None):
        return {
            "image_description": "A screenshot of an invoice dashboard",
            "ui_description": "Dashboard with navbar and table",
            "chart_detected": True,
            "detected_objects": ["table", "logo"],
            "keywords": ["invoice", "finance"],
            "confidence": 0.99,
        }


class CustomMockTranscriptionProvider(TranscriptionProvider):
    def transcribe(self, file_path_or_url: str, metadata=None):
        return {
            "transcript": "CUSTOM_TRANSCRIPT: Welcome to the meeting.",
            "timestamps": [{"start": 0.0, "end": 2.5, "text": "Welcome to the meeting."}],
            "language": "en",
            "duration": 45.0,
            "summary": "Meeting intro",
            "keywords": ["meeting", "intro"],
            "confidence": 0.98,
        }


def create_sample_package() -> KnowledgePackage:
    package = KnowledgePackage()

    conv = Conversation(
        id="conv_100",
        title="Test Discussion with Attachments",
        source="/path/to/source.json",
        created="2026-03-01T10:00:00Z",
        updated="2026-03-01T11:00:00Z",
        messages=[
            Message(
                id="msg_101",
                role="user",
                content="Please review this image and audio file.",
                timestamp="2026-03-01T10:00:00Z",
                metadata={
                    "attachments": [
                        {"name": "diagram.png", "url": "http://example.com/diagram.png"},
                        {"name": "speech_notes.mp3", "url": "http://example.com/notes.mp3"},
                    ]
                },
            ),
            Message(
                id="msg_102",
                role="assistant",
                content="Here is the PDF summary.",
                timestamp="2026-03-01T10:05:00Z",
            ),
        ],
        provenance={
            "source_platform": "Gemini",
            "source_file": "conversations.json",
            "attachments": [
                {"name": "annual_report.pdf", "url": "http://example.com/report.pdf"}
            ],
        },
    )
    package.add_conversation(conv)
    return package


class TestAttachmentProcessingPass(unittest.TestCase):

    def test_image_processor(self):
        processor = ImageProcessor(
            ocr_provider=CustomMockOCRProvider(),
            vision_provider=CustomMockVisionProvider(),
        )
        task = AttachmentTask(
            attachment_id="att_img_1",
            conversation_id="conv_1",
            file_name="invoice.png",
            message_id="msg_1",
        )
        result = processor.process(task)

        self.assertIsInstance(result, AttachmentKnowledge)
        self.assertEqual(result.media_type, "image")
        self.assertIn("CUSTOM_OCR_TEXT", result.raw_extraction)
        self.assertTrue(result.structured_extraction["chart_detected"])
        self.assertEqual(result.confidence, 0.99)
        self.assertEqual(result.conversation_id, "conv_1")
        self.assertEqual(result.message_id, "msg_1")

    def test_audio_processor(self):
        processor = AudioProcessor(
            transcription_provider=CustomMockTranscriptionProvider()
        )
        task = AttachmentTask(
            attachment_id="att_aud_1",
            conversation_id="conv_1",
            file_name="voice.wav",
            message_id="msg_1",
        )
        result = processor.process(task)

        self.assertIsInstance(result, AttachmentKnowledge)
        self.assertEqual(result.media_type, "audio")
        self.assertIn("CUSTOM_TRANSCRIPT", result.raw_extraction)
        self.assertEqual(result.structured_extraction["duration"], 45.0)
        self.assertEqual(result.confidence, 0.98)

    def test_pdf_processor(self):
        processor = PdfProcessor(ocr_provider=CustomMockOCRProvider())
        task = AttachmentTask(
            attachment_id="att_pdf_1",
            conversation_id="conv_1",
            file_name="document.pdf",
        )
        result = processor.process(task)

        self.assertIsInstance(result, AttachmentKnowledge)
        self.assertEqual(result.media_type, "pdf")
        self.assertEqual(result.structured_extraction["page_count"], 1)
        self.assertTrue(len(result.structured_extraction["headings"]) > 0)

    def test_deterministic_id(self):
        id1 = AttachmentKnowledge.generate_deterministic_id(
            conversation_id="c1", message_id="m1", attachment_id="a1", processor_version="1.0.0"
        )
        id2 = AttachmentKnowledge.generate_deterministic_id(
            conversation_id="c1", message_id="m1", attachment_id="a1", processor_version="1.0.0"
        )
        id3 = AttachmentKnowledge.generate_deterministic_id(
            conversation_id="c1", message_id="m2", attachment_id="a1", processor_version="1.0.0"
        )

        self.assertEqual(id1, id2)
        self.assertNotEqual(id1, id3)

    def test_processor_registry(self):
        registry = AttachmentProcessorRegistry()
        registry.register(ImageProcessor())
        registry.register(AudioProcessor())
        registry.register(PdfProcessor())

        p_img = registry.find_processor("photo.jpeg")
        p_aud = registry.find_processor("recording.mp3")
        p_pdf = registry.find_processor("document.pdf")
        p_none = registry.find_processor("archive.zip")

        self.assertIsNotNone(p_img)
        self.assertEqual(p_img.media_type, "image")
        self.assertIsNotNone(p_aud)
        self.assertEqual(p_aud.media_type, "audio")
        self.assertIsNotNone(p_pdf)
        self.assertEqual(p_pdf.media_type, "pdf")
        self.assertIsNone(p_none)

    def test_attachment_processing_pass_full_run(self):
        package = create_sample_package()
        pass_instance = AttachmentProcessingPass()

        result_package = pass_instance.analyze(package)

        self.assertEqual(len(result_package.attachment_knowledge), 3)
        self.assertEqual(len(result_package.attachmentKnowledge), 3)

        types = {item.media_type for item in result_package.attachment_knowledge}
        self.assertEqual(types, {"image", "audio", "pdf"})

        # Verify links
        for item in result_package.attachment_knowledge:
            self.assertEqual(item.conversation_id, "conv_100")
            self.assertIsNotNone(item.fingerprint)
            self.assertIsNotNone(item.id)
            self.assertNotEqual(item.to_markdown(), "")
            self.assertEqual(item.to_knowledge_object()["id"], item.id)

    def test_cache_hits_and_resumability(self):
        package = create_sample_package()
        cache = AttachmentCache()
        pass_instance = AttachmentProcessingPass(cache=cache)

        # First run: uncached
        pass_instance.process_pass(package)
        meta1 = package.metadata["attachment_processing"]
        self.assertEqual(meta1["processed_count"], 3)
        self.assertEqual(meta1["cache_hits"], 0)

        # Second run on new package with same data: cache hit
        package2 = create_sample_package()
        pass_instance.process_pass(package2)
        meta2 = package2.metadata["attachment_processing"]
        self.assertEqual(meta2["processed_count"], 3)
        self.assertEqual(meta2["cache_hits"], 3)


if __name__ == "__main__":
    unittest.main()

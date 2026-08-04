from typing import List, Optional
from src.compiler.processors.processor_registry import (
    AttachmentTask,
    BaseAttachmentProcessor,
)
from src.models.attachment_knowledge import AttachmentKnowledge
from src.providers.transcription_provider import (
    DefaultTranscriptionProvider,
    TranscriptionProvider,
)


class AudioProcessor(BaseAttachmentProcessor):
    """Processes audio attachments using Transcription providers."""

    def __init__(self, transcription_provider: Optional[TranscriptionProvider] = None):
        self.transcription_provider = (
            transcription_provider or DefaultTranscriptionProvider()
        )

    @property
    def name(self) -> str:
        return "AudioProcessor"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def media_type(self) -> str:
        return "audio"

    @property
    def supported_extensions(self) -> List[str]:
        return ["mp3", "wav", "m4a", "ogg", "flac", "aac", "opus"]

    def process(self, task: AttachmentTask) -> AttachmentKnowledge:
        tx_data = self.transcription_provider.transcribe(
            task.file_path_or_url, task.provenance
        )

        transcript = tx_data.get("transcript", "")
        summary = tx_data.get("summary", f"Audio transcript for {task.file_name}")
        keywords = tx_data.get("keywords", ["audio", "speech", "transcript"])
        confidence = float(tx_data.get("confidence", 0.90))

        structured_extraction = {
            "transcript": transcript,
            "timestamps": tx_data.get("timestamps", []),
            "language": tx_data.get("language", "en"),
            "duration": tx_data.get("duration", 0.0),
        }

        return AttachmentKnowledge(
            attachment_id=task.attachment_id,
            conversation_id=task.conversation_id,
            message_id=task.message_id,
            file_name=task.file_name,
            media_type="audio",
            fingerprint=task.fingerprint,
            processor_name=self.name,
            processor_version=self.version,
            raw_extraction=transcript,
            structured_extraction=structured_extraction,
            summary=summary,
            keywords=keywords,
            entities=[],
            confidence=confidence,
            metadata={
                "duration_seconds": tx_data.get("duration", 0.0),
                "language": tx_data.get("language", "en"),
                "format": task.file_name.split(".")[-1].lower(),
            },
            provenance=task.provenance,
        )

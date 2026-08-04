from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class TranscriptionProvider(ABC):
    """Abstract interface for Speech-to-Text / Audio Transcription backends."""

    @abstractmethod
    def transcribe(
        self, file_path_or_url: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Transcribe audio into text and return speech metrics."""
        pass


class DefaultTranscriptionProvider(TranscriptionProvider):
    """Default deterministic Transcription provider."""

    def transcribe(
        self, file_path_or_url: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        name = file_path_or_url.split("/")[-1].split("\\")[-1]
        return {
            "transcript": f"Audio recording transcript for {name}. Discussion on key technical concepts.",
            "timestamps": [
                {"start": 0.0, "end": 5.0, "text": f"Audio recording transcript for {name}."},
                {"start": 5.0, "end": 12.0, "text": "Discussion on key technical concepts."},
            ],
            "language": "en",
            "duration": 12.0,
            "summary": f"Voice recording discussing technical details from {name}.",
            "keywords": ["audio", "recording", "voice", "transcript"],
            "confidence": 0.92,
        }

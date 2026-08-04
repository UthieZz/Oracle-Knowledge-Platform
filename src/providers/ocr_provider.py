from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class OCRProvider(ABC):
    """Abstract interface for Optical Character Recognition (OCR) backends."""

    @abstractmethod
    def extract_text(self, file_path_or_url: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Extract plain text from an image or document file/URL."""
        pass


class DefaultOCRProvider(OCRProvider):
    """Default deterministic OCR provider."""

    def extract_text(self, file_path_or_url: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        name = file_path_or_url.split("/")[-1].split("\\")[-1]
        return f"[OCR Extracted Text from {name}]"

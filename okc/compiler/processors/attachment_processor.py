from abc import ABC, abstractmethod
from typing import Dict, Any
import os
import logging

logger = logging.getLogger(__name__)


class BaseAttachmentProcessor(ABC):
    """Abstract base class for all OKC media attachment processors."""

    @abstractmethod
    def process(self, file_path: str) -> Dict[str, Any]:
        """Processes raw media files and extracts search-ready text and metadata."""
        pass


def _basic_text_probe(file_path: str, max_bytes: int = 64_000) -> str:
    """Best-effort text extraction without heavy native deps."""
    try:
        with open(file_path, "rb") as fh:
            raw = fh.read(max_bytes)
        # Prefer utf-8; fall back to latin-1 for partial recovery
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1", errors="ignore")
    except OSError as exc:
        logger.warning("Failed reading %s: %s", file_path, exc)
        return ""


class ImageOCRProcessor(BaseAttachmentProcessor):
    """OCR path. Uses pytesseract when available; otherwise metadata-only stub."""

    def process(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            logger.warning("Image file not found: %s", file_path)
            return {"status": "failed", "error": "File not found"}

        extracted_text = ""
        engine = "stub"
        try:
            from PIL import Image  # type: ignore
            import pytesseract  # type: ignore

            extracted_text = pytesseract.image_to_string(Image.open(file_path)) or ""
            engine = "pytesseract"
        except Exception:
            extracted_text = f"[OCR unavailable — install pillow+pytesseract for {os.path.basename(file_path)}]"

        return {
            "status": "processed",
            "extracted_text": extracted_text.strip(),
            "keywords": ["image", "ocr"],
            "confidence": 0.9 if engine == "pytesseract" else 0.2,
            "media_type": "image",
            "engine": engine,
        }


class AudioTranscriptProcessor(BaseAttachmentProcessor):
    """Speech-to-text path. Placeholder until a local STT backend is configured."""

    def process(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            logger.warning("Audio file not found: %s", file_path)
            return {"status": "failed", "error": "File not found"}

        size = os.path.getsize(file_path)
        return {
            "status": "processed",
            "extracted_text": f"[Audio transcript pending — {os.path.basename(file_path)} ({size} bytes)]",
            "keywords": ["audio", "transcript"],
            "confidence": 0.15,
            "media_type": "audio",
            "engine": "stub",
        }


class PDFProcessor(BaseAttachmentProcessor):
    """PDF text extraction. Uses pypdf when available; binary probe otherwise."""

    def process(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            logger.warning("PDF file not found: %s", file_path)
            return {"status": "failed", "error": "File not found"}

        extracted_text = ""
        engine = "stub"
        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(file_path)
            parts = []
            for page in reader.pages:
                parts.append(page.extract_text() or "")
            extracted_text = "\n".join(parts).strip()
            engine = "pypdf"
        except Exception:
            # Last-resort probe (often noisy for binary PDFs)
            probe = _basic_text_probe(file_path)
            extracted_text = probe if probe.strip() else f"[PDF text unavailable — install pypdf for {os.path.basename(file_path)}]"

        return {
            "status": "processed",
            "extracted_text": extracted_text,
            "keywords": ["pdf", "document"],
            "confidence": 0.95 if engine == "pypdf" else 0.25,
            "media_type": "pdf",
            "engine": engine,
        }

import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class BaseAttachmentProcessor(ABC):
    """Abstract base class for all OKC media attachment processors."""

    name: str = "base"
    version: str = "1.0.0"
    transformation: str = "extract"

    @abstractmethod
    def process(self, file_path: str) -> Dict[str, Any]:
        """Processes raw media files and extracts search-ready text and metadata."""
        pass


def _basic_text_probe(file_path: str, max_bytes: int = 64_000) -> str:
    """Best-effort text extraction without heavy native deps."""
    try:
        with open(file_path, "rb") as fh:
            raw = fh.read(max_bytes)
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1", errors="ignore")
    except OSError as exc:
        logger.warning("Failed reading %s: %s", file_path, exc)
        return ""


class ImageOCRProcessor(BaseAttachmentProcessor):
    """OCR path. Uses pytesseract when available; otherwise metadata-only stub."""

    name = "image_ocr"
    version = "1.0.0"
    transformation = "ocr"

    def process(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            logger.warning("Image file not found: %s", file_path)
            return {"status": "failed", "error": "File not found"}

        extracted_text = ""
        engine = "stub"
        image_parser = "stub"
        width = None
        height = None
        mode = None
        image_format = None
        try:
            from PIL import Image  # type: ignore

            with Image.open(file_path) as img:
                width, height = img.size
                mode = img.mode
                image_format = img.format
            image_parser = "pillow"
            try:
                import pytesseract  # type: ignore

                extracted_text = pytesseract.image_to_string(Image.open(file_path)) or ""
                engine = "pytesseract"
            except Exception:
                extracted_text = (
                    f"[OCR unavailable — install pytesseract for {os.path.basename(file_path)}]"
                )
        except Exception:
            extracted_text = (
                f"[OCR unavailable — install pillow+pytesseract for {os.path.basename(file_path)}]"
            )

        structure = {
            "format": "image",
            "engine": engine,
            "image_parser": image_parser,
            "width": width,
            "height": height,
            "mode": mode,
            "image_format": image_format,
        }
        return {
            "status": "processed",
            "extracted_text": extracted_text.strip(),
            "keywords": ["image", "ocr"],
            "confidence": 0.9 if engine == "pytesseract" else 0.2,
            "media_type": "image",
            "engine": engine,
            "metadata": {
                "width": width,
                "height": height,
                "mode": mode,
                "image_format": image_format,
            },
            "structured_extraction": structure,
        }


class AudioTranscriptProcessor(BaseAttachmentProcessor):
    """Speech-to-text path. Placeholder until a local STT backend is configured."""

    name = "audio_transcript"
    version = "1.0.0"
    transformation = "transcribe"

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

    name = "pdf_parse"
    version = "1.0.0"
    transformation = "parse"

    def process(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            logger.warning("PDF file not found: %s", file_path)
            return {"status": "failed", "error": "File not found"}

        extracted_text = ""
        engine = "stub"
        page_count = None
        page_char_counts = []
        title = None
        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(file_path)
            parts = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                parts.append(page_text)
                page_char_counts.append(len(page_text))
            extracted_text = "\n".join(parts).strip()
            page_count = len(reader.pages)
            engine = "pypdf"
            meta = reader.metadata
            if meta is not None:
                title = getattr(meta, "title", None)
        except Exception:
            probe = _basic_text_probe(file_path)
            extracted_text = probe if probe.strip() else f"[PDF text unavailable — install pypdf for {os.path.basename(file_path)}]"

        metadata = {"page_count": page_count, "title": title}
        return {
            "status": "processed",
            "extracted_text": extracted_text,
            "keywords": ["pdf", "document"],
            "confidence": 0.95 if engine == "pypdf" else 0.25,
            "media_type": "pdf",
            "engine": engine,
            "metadata": metadata,
            "structured_extraction": {
                "format": "pdf",
                "engine": engine,
                "page_count": page_count,
                "page_char_counts": page_char_counts,
            },
        }


class TextParseProcessor(BaseAttachmentProcessor):
    """Parse text-like attachments without promoting them to KnowledgeObjects."""

    name = "text_parse"
    version = "1.0.0"
    transformation = "parse"

    def process(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            logger.warning("Text file not found: %s", file_path)
            return {"status": "failed", "error": "File not found"}

        extracted_text = _basic_text_probe(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        structured = None
        if ext == ".csv":
            structured = _csv_structure(extracted_text)
        result = {
            "status": "processed",
            "extracted_text": extracted_text,
            "keywords": ["text", "parse"] if structured is None else ["text", "csv", "structured"],
            "confidence": 0.8 if extracted_text.strip() else 0.2,
            "media_type": "text" if structured is None else "structured",
            "engine": "text_probe" if structured is None else "csv_structure",
        }
        if structured is not None:
            result["structured_extraction"] = structured
        return result


def _csv_structure(text: str) -> Dict[str, Any]:
    """Deterministic header/row summary. Not a KnowledgeObject promotion."""
    import csv
    from io import StringIO

    rows = list(csv.reader(StringIO(text or "")))
    headers = rows[0] if rows else []
    data_rows = rows[1:] if len(rows) > 1 else []
    return {
        "format": "csv",
        "headers": headers,
        "row_count": len(data_rows),
        "column_count": len(headers),
    }


def content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()


def structured_extraction_hash(value: Any) -> str:
    """Stable hash of processor-returned structure. Not a knowledge identity."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def source_file_hash(file_path: str) -> str:
    """SHA-256 of source bytes. Empty string if the file cannot be read."""
    digest = hashlib.sha256()
    try:
        with open(file_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError as exc:
        logger.warning("Failed hashing %s: %s", file_path, exc)
        return ""


def source_file_size(file_path: str):
    try:
        return os.path.getsize(file_path)
    except OSError:
        return None

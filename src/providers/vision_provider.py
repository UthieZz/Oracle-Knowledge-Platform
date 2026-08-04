from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class VisionProvider(ABC):
    """Abstract interface for Computer Vision backends."""

    @abstractmethod
    def analyze_image(
        self, file_path_or_url: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze image content and return structured visual features."""
        pass


class DefaultVisionProvider(VisionProvider):
    """Default deterministic Vision provider."""

    def analyze_image(
        self, file_path_or_url: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        name = file_path_or_url.split("/")[-1].split("\\")[-1]
        return {
            "image_description": f"Visual analysis of image '{name}'",
            "ui_description": "Standard UI screenshot layout with header and body" if "screen" in name.lower() or "ui" in name.lower() else "General graphic illustration",
            "chart_detected": "chart" in name.lower() or "graph" in name.lower(),
            "detected_objects": ["graphic", "text_block"],
            "keywords": ["visual", "image", "attachment"],
            "confidence": 0.95,
        }

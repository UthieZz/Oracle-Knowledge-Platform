from typing import Dict, List, Optional
from src.core.interfaces import Exporter


class ExportRegistry:
    """Registry for managing pluggable Exporter plugins."""

    def __init__(self):
        self._exporters: Dict[str, Exporter] = {}

    def register(self, exporter: Exporter) -> None:
        """Register an exporter plugin instance."""
        self._exporters[exporter.name] = exporter

    def get_exporter(self, name: str) -> Optional[Exporter]:
        """Retrieve an exporter plugin by name."""
        return self._exporters.get(name)

    def get_available_exporters(self) -> List[Dict[str, str]]:
        """Return metadata for all registered exporters."""
        result = []
        for exp in self._exporters.values():
            result.append({
                "name": exp.name,
                "version": getattr(exp, "version", "1.0.0"),
                "author": getattr(exp, "author", "OKC Core"),
                "description": getattr(exp, "description", ""),
                "status": "Ready",
            })
        return result

    def list_names(self) -> List[str]:
        return list(self._exporters.keys())

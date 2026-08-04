from typing import Any, Dict, Optional
from src.exporters.exporter_registry import ExportRegistry
from src.exporters.multi_source_exporter import MultiSourceExporter
from src.models.knowledge_package import KnowledgePackage


class ExportService:
    """Service governing export execution and exporter plugins."""

    def __init__(self, mode: str = "Both"):
        self.mode = mode
        self.registry = ExportRegistry()
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.registry.register(MultiSourceExporter(mode=self.mode))

    def set_export_mode(self, mode: str) -> None:
        """Update the export configuration mode ('Unified', 'Separate by Source', 'Both')."""
        self.mode = mode

    def get_available_exporters(self) -> list[dict[str, str]]:
        return self.registry.get_available_exporters()

    def export_knowledge(
        self, package: KnowledgePackage, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute knowledge export across all registered exporters."""
        cfg = config or {}
        mode = cfg.get("mode", self.mode)
        output_dir = cfg.get("output_dir", "output")

        exporter_name = cfg.get("exporter_name", "Multi-Source Exporter")
        exporter = self.registry.get_exporter(exporter_name)

        if not exporter:
            exporter = MultiSourceExporter(output_dir=output_dir, mode=mode)

        if hasattr(exporter, "mode"):
            setattr(exporter, "mode", mode)
        if hasattr(exporter, "output_dir"):
            setattr(exporter, "output_dir", output_dir)

        exporter.export(package)

        return {
            "status": "Success",
            "message": f"Successfully exported knowledge graph using '{exporter_name}' (mode: {mode}).",
            "mode": mode,
            "output_dir": output_dir,
        }

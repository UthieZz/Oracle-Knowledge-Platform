from typing import Any, Dict, Optional
from src.exporters.exporter_registry import ExportRegistry
from src.exporters.multi_source_exporter import MultiSourceExporter
from src.exporters.firestore_exporter import FirestoreExporter
from src.models.knowledge_package import KnowledgePackage


class ExportService:
    """Service governing export execution and exporter plugins."""

    def __init__(self, mode: str = "Both"):
        self.mode = mode
        self.registry = ExportRegistry()
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.registry.register(MultiSourceExporter(mode=self.mode))
        self.registry.register(FirestoreExporter())

    def set_export_mode(self, mode: str) -> None:
        """Update the export configuration mode ('Unified', 'Separate by Source', 'Both')."""
        self.mode = mode

    def get_available_exporters(self) -> list[dict[str, str]]:
        return self.registry.get_available_exporters()

    def export_knowledge(
        self, package: KnowledgePackage, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute knowledge export.

        By default, publish to all registered exporters. An explicit
        ``exporter_name`` can still be supplied for single-exporter operation.
        """
        cfg = config or {}
        mode = cfg.get("mode", self.mode)
        output_dir = cfg.get("output_dir", "output")
        exporter_name = cfg.get("exporter_name")

        if exporter_name:
            exporters = [self.registry.get_exporter(exporter_name)]
            exporters = [exporter for exporter in exporters if exporter]
        else:
            exporters = list(self.registry._exporters.values())

        if not exporters:
            raise RuntimeError("No exporters are registered.")

        results = []

        for exporter in exporters:
            if hasattr(exporter, "mode"):
                setattr(exporter, "mode", mode)

            if hasattr(exporter, "output_dir"):
                setattr(exporter, "output_dir", output_dir)

            exporter.export(package)
            results.append(exporter.name)

        return {
            "status": "Success",
            "message": f"Successfully exported knowledge using: {', '.join(results)}.",
            "exporters": results,
            "mode": mode,
            "output_dir": output_dir,
        }

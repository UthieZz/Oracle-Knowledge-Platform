import os
from typing import Any, Dict, Optional
from src.exporters.exporter_registry import ExportRegistry
from src.exporters.multi_source_exporter import MultiSourceExporter
from src.exporters.firestore_exporter import FirestoreExporter
from src.exporters.relationship_index_exporter import RelationshipIndexExporter
from src.models.knowledge_package import KnowledgePackage
from src.validators.knowledge_object_provenance import (
    ensure_knowledge_object_provenance,
)
from src.validators.knowledge_object_quality import (
    annotate_knowledge_object_quality,
)


def _is_firestore_exporter(exporter: Any) -> bool:
    name = str(getattr(exporter, "name", "") or exporter.__class__.__name__)
    return "firestore" in name.lower()


class ExportService:
    """Service governing export execution and exporter plugins."""

    def __init__(self, mode: str = "Both"):
        self.mode = mode
        self.registry = ExportRegistry()
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.registry.register(MultiSourceExporter(mode=self.mode))
        self.registry.register(RelationshipIndexExporter())
        tenant = os.getenv("OKP_TENANT_ID")
        silo = os.getenv("OKP_SILO_ID")
        if tenant and silo:
            self.registry.register(FirestoreExporter(tenant_id=tenant, silo_id=silo))

    def set_export_mode(self, mode: str) -> None:
        self.mode = mode

    def get_available_exporters(self) -> list[dict[str, str]]:
        return self.registry.get_available_exporters()

    def export_knowledge(
        self, package: KnowledgePackage, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
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

        publishing_firestore = any(_is_firestore_exporter(exp) for exp in exporters)
        if "strict_provenance" in cfg:
            strict = bool(cfg.get("strict_provenance"))
        else:
            # Portable and published KnowledgeObjects share the same lineage contract.
            strict = True

        provenance = ensure_knowledge_object_provenance(package, strict=strict)
        quality = annotate_knowledge_object_quality(package)

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
            "strict_provenance": strict,
            "publishing_firestore": publishing_firestore,
            "provenance": provenance,
            "quality": {
                "total": quality["total"],
                "conversation_shaped_or_thin": quality["conversation_shaped_or_thin"],
            },
        }

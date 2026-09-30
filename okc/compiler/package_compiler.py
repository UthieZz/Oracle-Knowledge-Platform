"""Deterministic KnowledgePackage compiler for the okc runtime.

This is orchestration over the canonical IR, not a second IR.
Pipeline: import (optional) → attachment process → enrich → validate.
Derived indexes (RAG, clusters, conversation archives) stay outside this compiler.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from okc.compiler.passes.attachment_processing_pass import AttachmentProcessingPass
from okc.models.knowledge_package import KnowledgePackage
from okc.plugins.registry import PluginRegistry


class PackageCompileError(ValueError):
    """Raised when a package cannot be compiled without violating contracts."""


@dataclass
class CompileResult:
    package: KnowledgePackage
    stages: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class PackageCompiler:
    """Compile a KnowledgePackage through registered okc processors/analyzers."""

    name = "package_compiler"
    version = "1.0.0"

    def __init__(self, registry: Optional[PluginRegistry] = None) -> None:
        if registry is None:
            from okc.plugins.registry import default_okc_registry

            registry = default_okc_registry()
        self.registry = registry

    def compile_file(
        self,
        source_filepath: str,
        *,
        tenant_id: str,
        silo_id: str,
        source_platform: Optional[str] = None,
        importer_name: str = "json_v2_importer",
    ) -> CompileResult:
        importer = self.registry.get("importer", importer_name).plugin
        package = importer.process(
            source_filepath,
            tenant_id=tenant_id,
            silo_id=silo_id,
            source_platform=source_platform,
        )
        result = self.compile_package(package)
        result.stages.insert(0, "import")
        return result

    def compile_package(self, package: KnowledgePackage) -> CompileResult:
        if not isinstance(package, KnowledgePackage):
            raise PackageCompileError("PackageCompiler only accepts okc KnowledgePackage.")

        stages: List[str] = []
        warnings: List[str] = []

        package = AttachmentProcessingPass(registry=self.registry).execute(package)
        stages.append("process_attachments")

        analyzer = self.registry.get("analyzer", "entity_extractor").plugin
        package = analyzer.run(package)
        stages.append("enrich")

        self._validate(package)
        stages.append("validate")

        meta: Dict[str, Any] = dict(package.metadata or {})
        pipeline = dict(meta.get("pipeline") or {})
        pipeline.update(
            {
                "compiler": self.name,
                "compiler_version": self.version,
                "stages": list(stages),
            }
        )
        meta["pipeline"] = pipeline
        package.metadata = meta

        return CompileResult(package=package, stages=stages, warnings=warnings)

    def _validate(self, package: KnowledgePackage) -> None:
        if not package.package_id:
            raise PackageCompileError("KnowledgePackage.package_id is required.")
        if not package.objects:
            raise PackageCompileError("KnowledgePackage contains no objects.")
        for obj in package.objects:
            prov = obj.provenance
            missing = [
                field
                for field, value in (
                    ("source_platform", prov.source_platform),
                    ("source_file", prov.source_file),
                    ("tenant_id", prov.tenant_id),
                    ("silo_id", prov.silo_id),
                )
                if not value
            ]
            if missing:
                raise PackageCompileError(
                    f"Object {obj.object_id} missing required provenance: {', '.join(missing)}"
                )
            if not obj.object_id:
                raise PackageCompileError("KnowledgeObject.object_id is required.")

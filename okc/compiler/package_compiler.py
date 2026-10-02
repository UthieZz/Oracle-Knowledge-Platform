"""Structural KnowledgePackage compiler for the okc runtime.

This compiler validates durable identity and provenance. It does not invent
knowledge objects, promote memory candidates, or import the legacy src tree.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from okc.models.knowledge_package import KnowledgeObject, KnowledgePackage


class PackageCompileError(ValueError):
    """Package failed the structural compilation contract."""


class PackageCompiler:
    """Validate and stamp a KnowledgePackage without changing object content."""

    name = "package_compiler"
    version = "1.0.0"

    def compile(self, package: KnowledgePackage) -> KnowledgePackage:
        if package is None:
            raise PackageCompileError("KnowledgePackage is required.")
        if not package.package_id:
            raise PackageCompileError("package_id is required.")

        self._validate_objects(package.objects)
        compiled = package.model_copy(deep=True)
        metadata = dict(compiled.metadata)
        metadata["compilation"] = {
            "compiler": self.name,
            "version": self.version,
            "status": "validated",
            "object_count": len(compiled.objects),
            "compiled_at": datetime.now(timezone.utc).isoformat(),
            "transformations": ["validate_identity", "validate_provenance", "stamp_compilation"],
        }
        compiled.metadata = metadata
        return compiled

    def _validate_objects(self, objects: List[KnowledgeObject]) -> None:
        seen_ids = set()
        tenant_id = None
        silo_id = None
        for obj in objects:
            if not obj.object_id:
                raise PackageCompileError("object_id is required.")
            if obj.object_id in seen_ids:
                raise PackageCompileError(f"Duplicate object_id: {obj.object_id}")
            seen_ids.add(obj.object_id)
            provenance = obj.provenance
            missing = [
                field
                for field in ("source_platform", "source_file", "tenant_id", "silo_id")
                if not getattr(provenance, field, None)
            ]
            if missing:
                raise PackageCompileError(
                    f"Object {obj.object_id} missing provenance fields: {', '.join(missing)}"
                )
            if tenant_id is None:
                tenant_id = provenance.tenant_id
                silo_id = provenance.silo_id
            elif provenance.tenant_id != tenant_id or provenance.silo_id != silo_id:
                raise PackageCompileError(
                    "Package mixes tenant/silo identity; compile one silo at a time."
                )

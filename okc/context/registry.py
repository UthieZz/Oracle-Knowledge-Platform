"""Minimal Context Registry enforcing ownership rules from locked design.

KnowledgePackage may declare support only; it cannot own or redefine dimensions.
"""

from __future__ import annotations

from typing import Dict, Optional

from okc.context.models import ContextDimension


class ContextRegistry:
    """Global / domain-owned dimension registry.

    Version isolation: resolution is against the version the package was compiled against.
    """

    def __init__(self) -> None:
        self._dimensions: Dict[str, Dict[str, ContextDimension]] = {}

    def register(self, dimension: ContextDimension) -> None:
        versions = self._dimensions.setdefault(dimension.dimension_id, {})
        if dimension.version in versions:
            raise ValueError(
                f"Dimension {dimension.dimension_id}@{dimension.version} already registered"
            )
        versions[dimension.version] = dimension

    def get(self, dimension_id: str, version: Optional[str] = None) -> Optional[ContextDimension]:
        versions = self._dimensions.get(dimension_id)
        if not versions:
            return None
        if version:
            return versions.get(version)
        # latest by version string (simple; production would use semver)
        latest = max(versions.keys())
        return versions[latest]

    def reject_package_ownership(self, package_metadata: dict) -> None:
        """A1: package-level redefinition of a dimension_id is rejected."""
        if "context_dimensions" in package_metadata:
            raise ValueError(
                "KnowledgePackage may declare support only; it may not own or redefine dimensions"
            )

    def soft_deprecate(self, dimension_id: str, version: str) -> None:
        """A4: old versions remain resolvable; warning on new compilation (caller responsibility)."""
        if not self.get(dimension_id, version):
            raise ValueError(f"Cannot deprecate unknown {dimension_id}@{version}")
        # Marking is external; resolution still succeeds.

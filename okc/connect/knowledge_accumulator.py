"""KnowledgeAccumulator: applies SyncEvents to a living KnowledgePackage.

Connectors and SyncEngine never write KnowledgePackage. This processor
feeds the existing PlainTextImporter path for create/update, then upserts
or removes objects so that retrieval reflects deletions and updates.

Source object identity is preserved in provenance.source_record_ids as
"src:<scoped_id>" where scoped_id = source|tenant_id|silo_id|object_id
so deletes can locate the corresponding KnowledgeObject without inventing
a parallel IR, and identical paths cannot collide across scopes.

Optional package_path makes the living package durable across process restarts.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from okc.connect.interfaces import SyncEvent
from okc.importers.text_importer import PlainTextImporter
from okc.models.knowledge_package import KnowledgePackage


def _scoped_source_id(source: str, tenant_id: str, silo_id: str, object_id: str) -> str:
    """Composite key that isolates the same object_id across source/tenant/silo."""
    return f"{source}|{tenant_id}|{silo_id}|{object_id}"


class KnowledgeAccumulator:
    """Maintains one KnowledgePackage by processing SyncEvents.

    Create/update: import via PlainTextImporter, inject scoped source identity,
    replace any prior object with the same scoped source id.
    Delete: remove the object whose source_record_ids contain the scoped id.
    Permission_change: recorded in package.metadata["permissions"] keyed by scoped id;
    retrieval can consult it later. Does not alter object content.

    If package_path is provided, the package is loaded on init (if the file
    exists) and written after every successful process. This makes the
    living knowledge durable without changing the IR or Connect contract.
    """

    def __init__(
        self,
        package: Optional[KnowledgePackage] = None,
        package_path: Optional[str] = None,
    ) -> None:
        self.package_path = package_path
        if package is not None:
            self.package = package
        elif package_path and Path(package_path).exists():
            self.package = KnowledgePackage.from_json(Path(package_path).read_text(encoding="utf-8"))
        else:
            self.package = KnowledgePackage(
                package_id="accumulator",
                objects=[],
                metadata={"accumulator": "okp_connect"},
            )
        self._src_to_obj: dict[str, str] = {}
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        self._src_to_obj = {}
        for obj in self.package.objects:
            for rid in obj.provenance.source_record_ids:
                if rid.startswith("src:"):
                    # Prefer scoped markers; legacy unscoped "src:object_id" still indexed for compatibility.
                    key = rid[4:]
                    self._src_to_obj[key] = obj.object_id

    def _persist(self) -> None:
        if not self.package_path:
            return
        path = Path(self.package_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.package.to_json(), encoding="utf-8")

    def process(self, event: SyncEvent) -> None:
        src_id = event.payload.get("object_id")
        if not src_id:
            return
        scoped = _scoped_source_id(event.source, event.tenant_id, event.silo_id, src_id)
        if event.kind in ("create", "update"):
            text = event.payload.get("text")
            if not text:
                return
            self._upsert_from_text(event, text, scoped)
        elif event.kind == "delete":
            self._remove(scoped)
        elif event.kind == "permission_change":
            perms = self.package.metadata.setdefault("permissions", {})
            perms[scoped] = event.payload
        self._persist()

    def _upsert_from_text(self, event: SyncEvent, text: str, scoped_id: str) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(text)
            path = f.name
        try:
            imported = PlainTextImporter().process(
                path,
                event.tenant_id,
                event.silo_id,
                source_platform=event.source,
            )
        finally:
            Path(path).unlink(missing_ok=True)

        obj = imported.objects[0]
        # Inject stable scoped source identity so delete can find it later.
        marker = f"src:{scoped_id}"
        if marker not in obj.provenance.source_record_ids:
            obj.provenance.source_record_ids.append(marker)

        # Remove prior version of the same scoped source object, if any.
        prior_obj_id = self._src_to_obj.get(scoped_id)
        if prior_obj_id:
            self.package.objects = [
                o for o in self.package.objects if o.object_id != prior_obj_id
            ]

        self.package.objects.append(obj)
        self._src_to_obj[scoped_id] = obj.object_id

        # Keep package metadata aligned with last event.
        self.package.metadata["tenant_id"] = event.tenant_id
        self.package.metadata["silo_id"] = event.silo_id
        self.package.metadata["last_source"] = event.source
        self.package.metadata["object_count"] = len(self.package.objects)

    def _remove(self, scoped_id: str) -> None:
        obj_id = self._src_to_obj.pop(scoped_id, None)
        if obj_id:
            self.package.objects = [
                o for o in self.package.objects if o.object_id != obj_id
            ]
            self.package.metadata["object_count"] = len(self.package.objects)

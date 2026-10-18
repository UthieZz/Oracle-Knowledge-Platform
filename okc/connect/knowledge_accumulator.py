"""KnowledgeAccumulator: applies SyncEvents to a living KnowledgePackage.

Connectors and SyncEngine never write KnowledgePackage. This processor
feeds the existing PlainTextImporter path for create/update, then upserts
or removes objects so that retrieval reflects deletions and updates.

Source object identity is preserved in provenance.source_record_ids as
"src:<object_id>" so deletes can locate the corresponding KnowledgeObject
without inventing a parallel IR.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from okc.connect.interfaces import SyncEvent
from okc.importers.text_importer import PlainTextImporter
from okc.models.knowledge_package import KnowledgePackage


class KnowledgeAccumulator:
    """Maintains one KnowledgePackage by processing SyncEvents.

    Create/update: import via PlainTextImporter, inject source object_id,
    replace any prior object with the same source id.
    Delete: remove the object whose source_record_ids contain the source id.
    Permission_change: recorded in package.metadata["permissions"] for now;
    retrieval can consult it later. Does not alter object content.
    """

    def __init__(self, package: Optional[KnowledgePackage] = None) -> None:
        self.package = package or KnowledgePackage(
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
                    self._src_to_obj[rid[4:]] = obj.object_id

    def process(self, event: SyncEvent) -> None:
        src_id = event.payload.get("object_id")
        if event.kind in ("create", "update"):
            text = event.payload.get("text")
            if not text or not src_id:
                return
            self._upsert_from_text(event, text, src_id)
        elif event.kind == "delete":
            if src_id:
                self._remove(src_id)
        elif event.kind == "permission_change":
            if src_id:
                perms = self.package.metadata.setdefault("permissions", {})
                perms[src_id] = event.payload

    def _upsert_from_text(self, event: SyncEvent, text: str, src_id: str) -> None:
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
        # Inject stable source identity so delete can find it later.
        marker = f"src:{src_id}"
        if marker not in obj.provenance.source_record_ids:
            obj.provenance.source_record_ids.append(marker)

        # Remove prior version of the same source object, if any.
        prior_obj_id = self._src_to_obj.get(src_id)
        if prior_obj_id:
            self.package.objects = [
                o for o in self.package.objects if o.object_id != prior_obj_id
            ]

        self.package.objects.append(obj)
        self._src_to_obj[src_id] = obj.object_id

        # Keep package metadata aligned with last event.
        self.package.metadata["tenant_id"] = event.tenant_id
        self.package.metadata["silo_id"] = event.silo_id
        self.package.metadata["last_source"] = event.source
        self.package.metadata["object_count"] = len(self.package.objects)

    def _remove(self, src_id: str) -> None:
        obj_id = self._src_to_obj.pop(src_id, None)
        if obj_id:
            self.package.objects = [
                o for o in self.package.objects if o.object_id != obj_id
            ]
            self.package.metadata["object_count"] = len(self.package.objects)

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional

from src.models.knowledge_package import KnowledgePackage


class ImportService:
    """Service layer for all import operations.

    Maintains a list of files queued for import (used by the UI) and provides
    high-level runner methods that delegate to the appropriate importer plugin.
    """

    def __init__(self):
        self.imported_files: List[Dict[str, Any]] = []
        self._package: Optional[KnowledgePackage] = None

    def get_imported_files(self) -> List[Dict[str, Any]]:
        return self.imported_files

    def add_import_files(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        from src.services.import_dispatcher import detect_source_type

        for path in file_paths:
            source_type = detect_source_type(path)
            self.imported_files.append(
                {"path": path, "status": "Pending", "type": source_type.value}
            )
        return self.imported_files

    def run_import_dispatcher(self, file_path: str) -> Dict[str, Any]:
        from src.services.import_dispatcher import detect_source_type, SourceType

        source_type = detect_source_type(file_path)

        if source_type == SourceType.GROK:
            return self.run_grok_import(file_path)
        if source_type == SourceType.GEMINI:
            return self.run_gemini_import(file_path)
        if source_type == SourceType.CHATGPT:
            from src.importers.chatgpt_importer import ChatGPTImporter

            if self._package is None:
                self._package = KnowledgePackage()
            importer = ChatGPTImporter()
            self._package = importer.import_data(self._package, file_path=file_path)
            return {
                "status": "Done",
                "conversations": len(self._package.conversations),
                "messages": importer.total_messages,
                "source_type": source_type.value,
            }

        raise ValueError(f"Unknown or unsupported source format: {file_path}")

    def remove_import_file(self, file_path: str) -> List[Dict[str, Any]]:
        self.imported_files = [f for f in self.imported_files if f["path"] != file_path]
        return self.imported_files

    def _mark_file_status(self, path: str, status: str) -> None:
        for f in self.imported_files:
            if f["path"] == path:
                f["status"] = status
                break

    def run_gemini_import(
        self,
        file_path: str,
        grouping_window_minutes: int = 30,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Dict[str, Any]:
        """Import a Gemini MyActivity JSON file into a KnowledgePackage."""
        from src.importers.gemini_importer import GeminiImporter, GeminiImportError
        from src.services.import_dispatcher import detect_source_type, SourceType

        detected = detect_source_type(file_path)
        if detected == SourceType.GROK:
            raise ValueError(
                f"Refusing GeminiImporter for Grok-classified file: {file_path}. "
                "Use run_grok_import or run_import_dispatcher."
            )
        if detected == SourceType.CHATGPT:
            raise ValueError(
                f"Refusing GeminiImporter for ChatGPT-classified file: {file_path}."
            )

        if self._package is None:
            self._package = KnowledgePackage()

        abs_path = os.path.abspath(file_path)
        self._mark_file_status(abs_path, "Importing")

        importer = GeminiImporter(
            input_dir=abs_path,
            grouping_window_minutes=grouping_window_minutes,
            progress_callback=progress_callback,
        )

        try:
            self._package = importer.import_data(self._package)
            manifest: Dict[str, Any] = self._package.metadata.get("import_manifest", {})
            errors: List[str] = manifest.get("errors", [])
            status = "Error" if errors else "Done"
            self._mark_file_status(abs_path, status)
            return {
                "status": status,
                "conversations": manifest.get("conversations_created", 0),
                "messages": manifest.get("messages_created", 0),
                "schema_version": manifest.get("schema_version", "unknown"),
                "errors": errors,
                "warnings": manifest.get("warnings", []),
                "manifest": manifest,
                "source_type": "gemini",
            }
        except GeminiImportError as exc:
            self._mark_file_status(abs_path, "Error")
            return {
                "status": "Error",
                "conversations": 0,
                "messages": 0,
                "schema_version": "unknown",
                "errors": [str(exc)],
                "warnings": [],
                "manifest": {},
                "source_type": "gemini",
            }

    def run_grok_import(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Dict[str, Any]:
        """Import a Grok JSON file into a KnowledgePackage (single-file)."""
        from src.importers.grok_importer import GrokImporter
        from src.services.import_dispatcher import detect_source_type, SourceType

        detected = detect_source_type(file_path)
        if detected == SourceType.GEMINI:
            raise ValueError(
                f"Refusing GrokImporter for Gemini-classified file: {file_path}. "
                "Use run_gemini_import or run_import_dispatcher."
            )

        if self._package is None:
            self._package = KnowledgePackage()

        abs_path = os.path.abspath(file_path)
        self._mark_file_status(abs_path, "Importing")

        importer = GrokImporter(
            input_dir=os.path.dirname(abs_path) or ".",
            progress_callback=progress_callback,
        )

        try:
            # Single-file mode so prod-grok-backend.json is not lost to glob patterns
            self._package = importer.import_data(self._package, file_path=abs_path)
            self._mark_file_status(abs_path, "Done")

            kos = [
                ko
                for ko in self._package.knowledge_objects
                if getattr(ko, "source_file", None) == abs_path
                or os.path.basename(getattr(ko, "source_file", "") or "")
                == os.path.basename(abs_path)
            ]
            platforms = {getattr(ko, "source_platform", None) for ko in kos}
            if kos and platforms - {None, "Grok"}:
                raise ValueError(
                    f"Provenance failure: expected source_platform=Grok, got {platforms}"
                )

            return {
                "status": "Done",
                "conversations": len(self._package.conversations),
                "messages": importer.total_messages,
                "knowledge_objects": len(self._package.knowledge_objects),
                "errors": [],
                "warnings": [],
                "source_type": "grok",
            }
        except Exception as exc:
            self._mark_file_status(abs_path, "Error")
            return {
                "status": "Error",
                "conversations": 0,
                "messages": 0,
                "knowledge_objects": 0,
                "errors": [str(exc)],
                "warnings": [],
                "source_type": "grok",
            }

    def get_package(self) -> Optional[KnowledgePackage]:
        return self._package

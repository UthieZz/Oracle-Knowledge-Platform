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
        # Shared KnowledgePackage — populated by run_* methods and made
        # available to downstream services (pipeline, knowledge, etc.).
        self._package: Optional[KnowledgePackage] = None

    # ------------------------------------------------------------------
    # File queue (used by Import Wizard UI)
    # ------------------------------------------------------------------

    def get_imported_files(self) -> List[Dict[str, Any]]:
        return self.imported_files

    def add_import_files(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        from src.services.import_dispatcher import detect_source_type
        for path in file_paths:
            source_type = detect_source_type(path)
            self.imported_files.append({"path": path, "status": "Pending", "type": source_type.value})
        return self.imported_files

    def run_import_dispatcher(self, file_path: str) -> Dict[str, Any]:
        from src.services.import_dispatcher import detect_source_type, SourceType
        source_type = detect_source_type(file_path)
        
        if source_type == SourceType.GROK:
            return self.run_grok_import(file_path)
        elif source_type == SourceType.GEMINI:
            return self.run_gemini_import(file_path)
        elif source_type == SourceType.CHATGPT:
            from src.importers.chatgpt_importer import ChatGPTImporter
            if self._package is None:
                self._package = KnowledgePackage()
            importer = ChatGPTImporter()
            self._package = importer.import_data(self._package, file_path=file_path)
            # Need to get conversations count
            return {"status": "Done", "conversations": len(self._package.conversations), "messages": importer.total_messages}
        else:
            raise ValueError(f"Unknown or unsupported source format: {file_path}")

    def remove_import_file(self, file_path: str) -> List[Dict[str, Any]]:
        self.imported_files = [f for f in self.imported_files if f["path"] != file_path]
        return self.imported_files

    def _mark_file_status(self, path: str, status: str) -> None:
        for f in self.imported_files:
            if f["path"] == path:
                f["status"] = status
                break

    # ------------------------------------------------------------------
    # Gemini import runner
    # ------------------------------------------------------------------

    def run_gemini_import(
        self,
        file_path: str,
        grouping_window_minutes: int = 30,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Dict[str, Any]:
        """Import a Gemini MyActivity JSON file into a :class:`~src.models.knowledge_package.KnowledgePackage`."""
        from src.importers.gemini_importer import GeminiImporter, GeminiImportError

        if self._package is None:
            self._package = KnowledgePackage()

        abs_path = os.path.abspath(file_path)
        self._mark_file_status(abs_path, "Importing")

        # Point the importer at the specific file, not a directory
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
            }

    # ------------------------------------------------------------------
    # Grok import runner
    # ------------------------------------------------------------------

    def run_grok_import(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Dict[str, Any]:
        """Import a Grok JSON file into a KnowledgePackage."""
        from src.importers.grok_importer import GrokImporter

        if self._package is None:
            self._package = KnowledgePackage()

        abs_path = os.path.abspath(file_path)
        self._mark_file_status(abs_path, "Importing")

        importer = GrokImporter(
            input_dir=os.path.dirname(abs_path),
            progress_callback=progress_callback,
        )

        try:
            self._package = importer.import_data(self._package)
            self._mark_file_status(abs_path, "Done")
            return {
                "status": "Done",
                "conversations": len(self._package.conversations),
                "messages": importer.total_messages,
                "errors": [],
                "warnings": [],
            }
        except Exception as exc:
            self._mark_file_status(abs_path, "Error")
            return {
                "status": "Error",
                "conversations": 0,
                "messages": 0,
                "errors": [str(exc)],
                "warnings": [],
            }

    # ------------------------------------------------------------------
    # Package accessor
    # ------------------------------------------------------------------

    def get_package(self) -> Optional[KnowledgePackage]:
        """Return the currently loaded KnowledgePackage (may be None)."""
        return self._package

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
        for path in file_paths:
            self.imported_files.append({"path": path, "status": "Pending", "type": "Unknown"})
        return self.imported_files

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
        """Import a Gemini MyActivity JSON file into a :class:`~src.models.knowledge_package.KnowledgePackage`.

        This is the canonical *Import Pass* for Gemini data. It:

        1. Creates (or reuses) the shared :attr:`_package`.
        2. Instantiates :class:`~src.importers.gemini_importer.GeminiImporter`
           with ``input_dir`` pointed at the file's parent directory so that
           ``discover_files()`` picks up the single file.
        3. Runs ``import_data(package)`` and captures the import manifest.
        4. Updates the UI file-queue entry status.
        5. Returns a serialised summary dict suitable for display or logging.

        Parameters
        ----------
        file_path:
            Absolute path to the Gemini MyActivity JSON file.
        grouping_window_minutes:
            Passed through to the importer (default: 30).
        progress_callback:
            Optional ``Callable[[float, str], None]`` forwarded to the importer
            so Qt progress bars can be updated without coupling service↔UI.

        Returns
        -------
        Dict[str, Any]
            ``{ "status", "conversations", "messages", "schema_version",
               "errors", "warnings", "manifest" }``
        """
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
    # Package accessor
    # ------------------------------------------------------------------

    def get_package(self) -> Optional[KnowledgePackage]:
        """Return the currently loaded KnowledgePackage (may be None)."""
        return self._package

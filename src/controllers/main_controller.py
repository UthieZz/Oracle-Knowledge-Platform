from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from src.services.export_service import ExportService
from src.services.import_service import ImportService
from src.services.knowledge_service import KnowledgeService
from src.services.pipeline_service import PipelineService
from src.services.plugin_service import PluginService
from src.services.project_service import ProjectService
from src.studio.controllers.studio_controller import StudioController


class MainController:
    """Central coordinator between the UI layer and all service objects.

    The UI should never import service classes directly — it calls methods on
    this controller so that services remain independently testable.
    """

    def __init__(self):
        # Initialize Services
        self.project_service = ProjectService()
        self.import_service = ImportService()
        self.pipeline_service = PipelineService()
        self.knowledge_service = KnowledgeService()
        self.export_service = ExportService()
        self.plugin_service = PluginService()

        # Initialize Workbench
        self.studio_controller = StudioController(self)

        self.main_window = None

    def set_main_window(self, main_window):
        self.main_window = main_window

    def navigate_to(self, view_name: str):
        if self.main_window:
            self.main_window.switch_view(view_name)

    # ------------------------------------------------------------------
    # Import operations
    # ------------------------------------------------------------------

    def import_grok_file(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Dict[str, Any]:
        """Import a Grok JSON file via the ImportService."""
        import os
        abs_path = os.path.abspath(file_path)
        existing_paths = [f["path"] for f in self.import_service.get_imported_files()]
        if abs_path not in existing_paths:
            self.import_service.add_import_files([abs_path])

        return self.import_service.run_grok_import(
            file_path=abs_path,
            progress_callback=progress_callback,
        )

    # ------------------------------------------------------------------
    # Export operations
    # ------------------------------------------------------------------

    def set_export_mode(self, mode: str) -> None:
        """Set the export configuration mode ('Unified', 'Separate by Source', 'Both')."""
        self.export_service.set_export_mode(mode)

    def export_knowledge(self, package: Any, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Export the knowledge package using the ExportService."""
        return self.export_service.export_knowledge(package, config)


import time
from typing import List

from .interfaces import ICompilerAdapter, IProgressReporter
from .dtos import (
    CompilerSession,
    ProjectStatus,
    PipelineProgress,
    PipelineResult,
    ImportSummary,
    CompilationSummary
)
from .exceptions import (
    SessionInvalidException,
    ImportFailedException,
    CompilationFailedException
)

# Note: In a fully wired state, we would import the core compiler engine classes here:
# from src.models.knowledge_package import KnowledgePackage
# from src.core.plugin_registry import PluginRegistry

class CompilerAdapter(ICompilerAdapter):
    """
    Concrete implementation of the Compiler Adapter.
    This class orchestrates the Oracle Knowledge Compiler engine.
    It remains entirely stateless, relying on the CompilerSession object.
    """

    def initialize_project(self, project_path: str) -> CompilerSession:
        # Create a new session. In the future, this is where we instantiate
        # a fresh KnowledgePackage for the project path.
        session = CompilerSession(project_path=project_path)
        # session.knowledge_package = KnowledgePackage()
        return session

    def get_status(self, session: CompilerSession) -> ProjectStatus:
        if not session or not session.is_active:
            raise SessionInvalidException("Session is null or inactive.")
            
        return ProjectStatus(
            name=session.project_path.split("/")[-1] if "/" in session.project_path else session.project_path,
            path=session.project_path,
            is_loaded=True
        )

    def import_sources(self, session: CompilerSession, import_paths: List[str], reporter: IProgressReporter) -> ImportSummary:
        if not session or not session.is_active:
            raise SessionInvalidException("Cannot import into an inactive session.")

        reporter.log_message("INFO", f"Starting import of {len(import_paths)} sources...")
        reporter.report_progress(PipelineProgress(stage_name="Import", percentage=10.0, message="Parsing files..."))
        
        try:
            # TODO: Invoke core Importer plugins here and mutate session.knowledge_package
            
            reporter.report_progress(PipelineProgress(stage_name="Import", percentage=100.0, message="Import complete."))
            
            # Return an immutable DTO representing the result
            return ImportSummary(
                total_files=len(import_paths),
                successful_imports=len(import_paths),
                failed_imports=0,
                errors=[]
            )
        except Exception as e:
            reporter.log_message("ERROR", f"Import failed: {str(e)}")
            raise ImportFailedException(f"Failed to import sources: {str(e)}") from e

    def run_analysis(self, session: CompilerSession, reporter: IProgressReporter) -> PipelineResult:
        if not session or not session.is_active:
            raise SessionInvalidException("Cannot analyze an inactive session.")

        start_time = time.time()
        reporter.log_message("INFO", "Starting analysis pipeline...")
        reporter.report_progress(PipelineProgress(stage_name="Analysis", percentage=0.0, message="Discovering analyzers..."))

        try:
            # TODO: Fetch Analyzers from PluginRegistry and execute them sequentially
            # passing session.knowledge_package through the pipeline.
            
            reporter.report_progress(PipelineProgress(stage_name="Analysis", percentage=100.0, message="Analysis complete."))
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            return PipelineResult(
                success=True,
                total_time_ms=elapsed_ms,
                error_message=None
            )
        except Exception as e:
            reporter.log_message("ERROR", f"Analysis failed: {str(e)}")
            return PipelineResult(
                success=False,
                total_time_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            )

    def compile(self, session: CompilerSession, reporter: IProgressReporter) -> CompilationSummary:
        if not session or not session.is_active:
            raise SessionInvalidException("Cannot compile an inactive session.")

        reporter.log_message("INFO", "Starting compilation phase...")
        reporter.report_progress(PipelineProgress(stage_name="Compile", percentage=50.0, message="Generating markdown..."))
        
        try:
            # TODO: Invoke MarkdownCompiler plugin
            
            reporter.report_progress(PipelineProgress(stage_name="Compile", percentage=100.0, message="Compilation complete."))
            
            return CompilationSummary(
                topics_generated=0, # Retrieve from knowledge_package metrics
                entities_extracted=0,
                total_conversations_processed=0
            )
        except Exception as e:
            reporter.log_message("ERROR", f"Compilation failed: {str(e)}")
            raise CompilationFailedException(f"Failed to compile knowledge base: {str(e)}") from e

    def export(self, session: CompilerSession, exporter_name: str, reporter: IProgressReporter) -> PipelineResult:
        if not session or not session.is_active:
            raise SessionInvalidException("Cannot export an inactive session.")
            
        start_time = time.time()
        reporter.log_message("INFO", f"Starting export using {exporter_name}...")
        
        try:
            # TODO: Invoke Exporter plugin
            
            return PipelineResult(
                success=True,
                total_time_ms=int((time.time() - start_time) * 1000),
                error_message=None
            )
        except Exception as e:
            reporter.log_message("ERROR", f"Export failed: {str(e)}")
            return PipelineResult(
                success=False,
                total_time_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            )

    def cancel(self, session: CompilerSession) -> None:
        if session:
            session.is_active = False
            # In a real threading scenario, this would set a threading.Event
            # that the plugin execution loop checks periodically.

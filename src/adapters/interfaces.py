import abc
from typing import List
from .dtos import (
    CompilerSession,
    ProjectStatus,
    PipelineProgress,
    PipelineResult,
    ImportSummary,
    CompilationSummary
)

class IProgressReporter(abc.ABC):
    """
    Interface for infrastructure to inject logging and progress callbacks into the adapter.
    """
    @abc.abstractmethod
    def report_progress(self, progress: PipelineProgress) -> None:
        pass

    @abc.abstractmethod
    def log_message(self, level: str, message: str) -> None:
        pass


class ICompilerAdapter(abc.ABC):
    """
    Abstract interface for the CompilerAdapter.
    Services must depend on this interface, never the concrete adapter.
    """
    
    @abc.abstractmethod
    def initialize_project(self, project_path: str) -> CompilerSession:
        pass

    @abc.abstractmethod
    def get_status(self, session: CompilerSession) -> ProjectStatus:
        pass

    @abc.abstractmethod
    def import_sources(self, session: CompilerSession, import_paths: List[str], reporter: IProgressReporter) -> ImportSummary:
        pass

    @abc.abstractmethod
    def run_analysis(self, session: CompilerSession, reporter: IProgressReporter) -> PipelineResult:
        pass

    @abc.abstractmethod
    def compile(self, session: CompilerSession, reporter: IProgressReporter) -> CompilationSummary:
        pass

    @abc.abstractmethod
    def export(self, session: CompilerSession, exporter_name: str, reporter: IProgressReporter) -> PipelineResult:
        pass

    @abc.abstractmethod
    def cancel(self, session: CompilerSession) -> None:
        pass

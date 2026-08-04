from dataclasses import dataclass
from typing import List, Dict, Optional, Any

@dataclass(frozen=True)
class ProjectStatus:
    name: str
    path: str
    is_loaded: bool

@dataclass(frozen=True)
class PipelineProgress:
    stage_name: str
    percentage: float
    message: str

@dataclass(frozen=True)
class PipelineResult:
    success: bool
    total_time_ms: int
    error_message: Optional[str] = None

@dataclass(frozen=True)
class KnowledgeObjectSummary:
    id: str
    name: str
    type: str
    reference_count: int

@dataclass(frozen=True)
class ImportSummary:
    total_files: int
    successful_imports: int
    failed_imports: int
    errors: List[str]

@dataclass(frozen=True)
class CompilationSummary:
    topics_generated: int
    entities_extracted: int
    total_conversations_processed: int

class CompilerSession:
    """
    State object passed to the adapter to manage a specific compilation run.
    This ensures the adapter itself remains stateless.
    """
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.knowledge_package = None # In a real scenario, this holds the src.models.KnowledgePackage
        self.is_active = True

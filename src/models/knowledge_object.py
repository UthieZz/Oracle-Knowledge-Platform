from dataclasses import dataclass
from typing import Dict, Any, List, Optional

@dataclass
class KnowledgeObject:
    id: str
    title: str
    content: str
    source_platform: str
    source_file: str
    created_at: Optional[str]
    updated_at: Optional[str]
    provenance: Dict[str, Any]
    evidence: List[str]

from typing import List, Dict, Any
from src.studio.services.studio_knowledge_service import StudioKnowledgeService

class SearchService:
    """Service for performing semantic and lexical search over knowledge."""
    
    def __init__(self, knowledge_service: StudioKnowledgeService):
        self.knowledge_service = knowledge_service
        
    def search(self, query: str) -> List[Dict[str, Any]]:
        """Performs search across conversations, entities, and knowledge objects."""
        # For Phase 1, we delegate to the knowledge service's basic search
        # Future phases will implement vector-based semantic search
        return self.knowledge_service.search_knowledge(query)

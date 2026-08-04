from typing import List, Dict, Any, Optional
from src.studio.services.studio_knowledge_service import StudioKnowledgeService
from src.studio.services.search_service import SearchService
from src.studio.services.voice_service import VoiceService

class StudioController:
    """Controller for the Studio module.
    
    Coordinates between the Studio UI and various services (Knowledge, Search, Voice).
    """
    
    def __init__(self, main_controller: Any):
        self.main_controller = main_controller
        self.knowledge_service = StudioKnowledgeService()
        self.knowledge_service.load_workspace()
        
        self.search_service = SearchService(self.knowledge_service)
        self.voice_service = VoiceService()
        
    def get_platforms(self) -> List[str]:
        return self.knowledge_service.get_platforms()
        
    def get_conversations(self, platform_name: str) -> List[Dict[str, Any]]:
        return self.knowledge_service.get_conversations(platform_name)
        
    def get_knowledge_object(self, platform_name: str, title: str) -> Optional[str]:
        return self.knowledge_service.get_knowledge_object_markdown(platform_name, title)
        
    def search(self, query: str) -> List[Dict[str, Any]]:
        return self.search_service.search(query)
        
    def get_conversation_details(self, platform_name: str, conv_id: str) -> Optional[Dict[str, Any]]:
        return self.knowledge_service.get_conversation_details(platform_name, conv_id)

    def push_to_talk(self, audio_data: bytes) -> str:
        return self.voice_service.transcribe(audio_data)

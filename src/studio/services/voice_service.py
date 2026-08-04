from abc import ABC, abstractmethod
from typing import Optional

class VoiceProvider(ABC):
    """Abstract base class for voice providers (STT/TTS)."""
    
    @abstractmethod
    def speech_to_text(self, audio_data: bytes) -> str:
        pass
        
    @abstractmethod
    def text_to_speech(self, text: str) -> bytes:
        pass

class MockVoiceProvider(VoiceProvider):
    """A mock voice provider for initial development."""
    
    def speech_to_text(self, audio_data: bytes) -> str:
        return "This is mock transcribed text."
        
    def text_to_speech(self, text: str) -> bytes:
        return b"mock_audio_data"

class VoiceService:
    """Service for handling voice interactions in the Workbench."""
    
    def __init__(self, provider: Optional[VoiceProvider] = None):
        self.provider = provider or MockVoiceProvider()
        
    def set_provider(self, provider: VoiceProvider):
        self.provider = provider
        
    def transcribe(self, audio_data: bytes) -> str:
        return self.provider.speech_to_text(audio_data)
        
    def synthesize(self, text: str) -> bytes:
        return self.provider.text_to_speech(text)

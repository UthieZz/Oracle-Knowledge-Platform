class VoiceService:
    """Service for handling voice interactions in the Workbench."""
    
    def __init__(self):
        pass
        
    def transcribe(self, audio_data: bytes) -> str:
        return "Voice transcription not implemented."
        
    def synthesize(self, text: str) -> bytes:
        return b""

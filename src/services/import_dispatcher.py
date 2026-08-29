import json
import os
from enum import Enum
from typing import Any, Dict, Optional

class SourceType(Enum):
    GROK = "grok"
    CHATGPT = "chatgpt"
    GEMINI = "gemini"
    UNKNOWN = "unknown"

def detect_source_type(file_path: str) -> SourceType:
    try:
        filename = os.path.basename(file_path).lower()
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(1024 * 5)
            
            if '"header": "Gemini Apps"' in content or 'myactivity' in filename:
                return SourceType.GEMINI

            if '"conversations"' in content[:1000] or 'grok' in filename:
                return SourceType.GROK
            
            if '"conversation_id"' in content or 'conversations-' in filename:
                return SourceType.CHATGPT
                
    except (IOError, UnicodeDecodeError):
        pass # Fallthrough to UNKNOWN
        
    return SourceType.UNKNOWN

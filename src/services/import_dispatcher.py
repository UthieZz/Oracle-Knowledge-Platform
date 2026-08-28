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
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read first few KB to avoid loading massive files
            # For Gemini, the structure is [{ "header": "Gemini Apps", ... }, ... ]
            content = f.read(1024 * 5)
            # Make sure it's valid JSON up to the point we read.
            # If the file is huge, the truncated content might be invalid JSON.
            # Let's try to parse it, if it fails, maybe we need to read more or 
            # try to parse just the first object.
            
            # Simple heuristic: look for substrings in the raw content
            if '"conversations"' in content[:1000]:
                return SourceType.GROK
            
            if '"conversation_id"' in content:
                return SourceType.CHATGPT
                
            if '"header": "Gemini Apps"' in content:
                return SourceType.GEMINI
                
    except (IOError, UnicodeDecodeError):
        pass # Fallthrough to UNKNOWN
        
    return SourceType.UNKNOWN

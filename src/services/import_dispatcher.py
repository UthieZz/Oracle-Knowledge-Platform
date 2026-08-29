"""Source-type detection for OKC importers.

Priority (highest first):
1. Explicit filename signals (myactivity → Gemini, grok → Grok, conversations- → ChatGPT)
2. Content markers unique to each platform
3. UNKNOWN

Grok files must never be classified as Gemini. Filename containing "grok"
always wins over weak content heuristics.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Optional


class SourceType(Enum):
    GROK = "grok"
    CHATGPT = "chatgpt"
    GEMINI = "gemini"
    UNKNOWN = "unknown"


def detect_source_type(file_path: str) -> SourceType:
    """Detect platform for a single JSON export path.

    Never raises; returns UNKNOWN on I/O or decode failure.
    """
    filename = os.path.basename(file_path).lower()

    # --- Filename-first rules (cheap, decisive) ---
    if "myactivity" in filename:
        return SourceType.GEMINI
    if "grok" in filename:
        return SourceType.GROK
    if filename.startswith("conversations-") or "conversations-" in filename:
        return SourceType.CHATGPT

    content: Optional[str] = None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read(1024 * 8)
    except (OSError, UnicodeDecodeError):
        return SourceType.UNKNOWN

    if not content:
        return SourceType.UNKNOWN

    head = content[:2000]

    # Gemini Apps Takeout marker
    if '"header": "Gemini Apps"' in content or '"header":"Gemini Apps"' in content:
        return SourceType.GEMINI

    # ChatGPT export shape
    if '"conversation_id"' in head or '"mapping"' in head:
        return SourceType.CHATGPT

    # Grok-style list/object with conversations key (after stronger rules)
    if '"conversations"' in head:
        return SourceType.GROK

    # Weak fallback: assistant content mentioning Grok is not reliable enough alone
    return SourceType.UNKNOWN

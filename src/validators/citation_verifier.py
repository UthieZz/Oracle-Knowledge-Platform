"""Verify model citations against retrieved Knowledge Objects.

Does not call models. Filters citations to those actually referenced
in the answer via [Source N] markers. Distinguishes retrieved evidence
from cited evidence.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence

SOURCE_RE = re.compile(r"\[Source\s+(\d+)\]", re.IGNORECASE)


def referenced_source_indexes(answer: str) -> List[int]:
    found = []
    for match in SOURCE_RE.finditer(answer or ""):
        idx = int(match.group(1))
        if idx not in found:
            found.append(idx)
    return found


def verify_citations(
    answer: str,
    citations: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Return only citations whose source_index appears in the answer.

    Citations without a source_index stay unverified and are dropped.
    """
    indexes = set(referenced_source_indexes(answer))
    cited = []
    unverified = []
    for citation in citations:
        source_index = citation.get("source_index")
        try:
            source_index = int(source_index)
        except (TypeError, ValueError):
            unverified.append(citation)
            continue
        if source_index in indexes:
            cited.append(citation)
        else:
            unverified.append(citation)
    return {
        "citations": cited,
        "unverified": unverified,
        "referenced_indexes": sorted(indexes),
        "sufficient": bool(cited) or not (answer or "").strip(),
    }

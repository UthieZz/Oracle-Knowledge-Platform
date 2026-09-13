"""Detect repeated source content while preserving every provenance record."""

import hashlib
import re
from collections import defaultdict
from typing import Any, Dict, List

from src.core.interfaces import Analyzer
from src.models.knowledge_package import KnowledgePackage


class SourceIdentityAnalyzer(Analyzer):
    """Assign deterministic content identities to imported conversations.

    This detects exact normalized source evidence, not semantic similarity.
    Near-duplicate or paraphrase matching must be a separate, reviewable stage.
    """

    @property
    def name(self) -> str: return "Source Identity Analyzer"
    @property
    def version(self) -> str: return "1.0.0"
    @property
    def author(self) -> str: return "OKC Core Team"
    @property
    def description(self) -> str: return "Finds repeated normalized source evidence across imports."
    @property
    def plugin_type(self) -> str: return "analyzer"
    @property
    def supported_inputs(self) -> List[str]: return ["okc/conversations"]
    @property
    def supported_outputs(self) -> List[str]: return ["okc/conversations"]

    def analyze(self, package: KnowledgePackage) -> KnowledgePackage:
        fingerprint_map: Dict[str, List[Any]] = defaultdict(list)
        for conversation in package.conversations:
            fingerprint = self._content_fingerprint(conversation)
            if not fingerprint:
                continue
            provenance = dict(getattr(conversation, "provenance", None) or {})
            provenance["content_fingerprint"] = fingerprint
            conversation.provenance = provenance
            fingerprint_map[fingerprint].append(conversation)

        for fingerprint, conversations in fingerprint_map.items():
            canonical = conversations[0]
            canonical_id = str(getattr(canonical, "id", fingerprint))
            aliases = []
            for conversation in conversations:
                provenance = dict(getattr(conversation, "provenance", None) or {})
                provenance["canonical_conversation_id"] = canonical_id
                provenance["duplicate_status"] = (
                    "canonical" if str(getattr(conversation, "id", "")) == canonical_id else "duplicate_same_content"
                )
                source_ref = {
                    "conversation_id": str(getattr(conversation, "id", "")),
                    "source_platform": provenance.get("source_platform") or getattr(conversation, "source", None),
                    "source_file": getattr(conversation, "source", None),
                }
                aliases.append(source_ref)
                provenance["source_aliases"] = aliases
                conversation.provenance = provenance

            package.metadata.setdefault("source_fingerprints", {})[fingerprint] = {
                "canonical_conversation_id": canonical_id,
                "source_aliases": aliases,
                "occurrence_count": len(conversations),
            }
        return package

    def _content_fingerprint(self, conversation: Any) -> str:
        parts: List[str] = []
        for message in getattr(conversation, "messages", []) or []:
            role = str(getattr(message, "role", "") or "").strip().lower()
            content = self._normalize_text(getattr(message, "content", "") or "")
            if not content:
                continue
            parts.append(f"{role}:{content}")
        if not parts:
            return ""
        payload = "\n".join(parts).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _normalize_text(self, text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip().lower()

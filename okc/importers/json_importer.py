"""Bridge common conversation JSON exports into okc v2 KnowledgePackage IR."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from okc.models.knowledge_package import (
    EvidenceSpan,
    KnowledgeObject,
    KnowledgePackage,
    Provenance,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_as_text(v) for v in value if v is not None)
    if isinstance(value, dict):
        if "parts" in value and isinstance(value["parts"], list):
            return " ".join(str(p) for p in value["parts"] if isinstance(p, str))
        return json.dumps(value, ensure_ascii=False)
    return str(value)


class JsonToV2Importer:
    """
    Deterministic importer that maps ChatGPT/Grok-style JSON exports
    into okc v2 KnowledgePackage objects with evidence spans.
    """

    def process(
        self,
        source_filepath: str,
        tenant_id: str,
        silo_id: str,
        source_platform: Optional[str] = None,
    ) -> KnowledgePackage:
        if not os.path.isfile(source_filepath):
            raise FileNotFoundError(f"Source not found: {source_filepath}")

        with open(source_filepath, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        platform = source_platform or self._detect_platform(data, source_filepath)
        conversations = self._extract_conversations(data)

        objects: List[KnowledgeObject] = []
        for raw in conversations:
            obj = self._conversation_to_object(
                raw,
                source_file=source_filepath,
                platform=platform,
                tenant_id=tenant_id,
                silo_id=silo_id,
            )
            if obj:
                objects.append(obj)

        return KnowledgePackage(
            package_id=f"pkg_{uuid.uuid4().hex[:12]}",
            objects=objects,
            metadata={
                "source_filepath": source_filepath,
                "source_platform": platform,
                "tenant_id": tenant_id,
                "silo_id": silo_id,
                "object_count": len(objects),
            },
        )

    def _detect_platform(self, data: Any, path: str) -> str:
        name = os.path.basename(path).lower()
        if "grok" in name:
            return "grok"
        if "chatgpt" in name or "conversations-" in name:
            return "chatgpt"
        if isinstance(data, dict) and data.get("client") == "grok":
            return "grok"
        return "json"

    def _extract_conversations(self, data: Any) -> List[Dict[str, Any]]:
        if isinstance(data, list):
            return [c for c in data if isinstance(c, dict)]
        if isinstance(data, dict):
            if isinstance(data.get("conversations"), list):
                return [c for c in data["conversations"] if isinstance(c, dict)]
            return [data]
        return []

    def _conversation_to_object(
        self,
        raw: Dict[str, Any],
        source_file: str,
        platform: str,
        tenant_id: str,
        silo_id: str,
    ) -> Optional[KnowledgeObject]:
        conv_id = str(
            raw.get("conversation_id")
            or raw.get("id")
            or raw.get("uuid")
            or uuid.uuid4().hex[:12]
        )
        title = str(raw.get("title") or "Untitled Conversation")

        messages = self._extract_messages(raw)
        if not messages and not raw.get("content"):
            return None

        evidence: List[EvidenceSpan] = []
        content_parts: List[str] = []
        for idx, msg in enumerate(messages):
            role = str(msg.get("role") or "unknown")
            text = _as_text(msg.get("content"))
            if not text.strip():
                continue
            span_id = f"{conv_id}_span_{idx}"
            msg_id = str(msg.get("id") or f"{conv_id}_msg_{idx}")
            ts = str(msg.get("timestamp") or msg.get("create_time") or _utc_now())
            evidence.append(
                EvidenceSpan(
                    span_id=span_id,
                    message_id=msg_id,
                    role=role,
                    timestamp=str(ts),
                    content=text,
                )
            )
            content_parts.append(f"{role}: {text}")

        if not content_parts and raw.get("content"):
            content_parts.append(_as_text(raw.get("content")))

        attachments: List[Dict[str, Any]] = []
        for att in raw.get("attachments") or []:
            if isinstance(att, dict):
                attachments.append(dict(att))
            elif isinstance(att, str):
                attachments.append({"file_path": att})

        return KnowledgeObject(
            object_id=conv_id,
            title=title,
            provenance=Provenance(
                source_platform=platform,
                source_file=source_file,
                source_record_ids=[conv_id],
                tenant_id=tenant_id,
                silo_id=silo_id,
            ),
            evidence=evidence,
            content="\n\n".join(content_parts),
            entities=[],
            attachments=attachments,
            relationships=[],
            context_citations=[],
        )

    def _extract_messages(self, raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        if isinstance(raw.get("messages"), list):
            return [m for m in raw["messages"] if isinstance(m, dict)]

        mapping = raw.get("mapping")
        if isinstance(mapping, dict):
            msgs: List[Dict[str, Any]] = []
            for node in mapping.values():
                if not isinstance(node, dict):
                    continue
                message = node.get("message")
                if not isinstance(message, dict):
                    continue
                author = message.get("author") or {}
                role = author.get("role", "unknown") if isinstance(author, dict) else "unknown"
                content = message.get("content")
                msgs.append(
                    {
                        "id": message.get("id"),
                        "role": role,
                        "content": content,
                        "timestamp": message.get("create_time"),
                    }
                )
            msgs.sort(key=lambda m: m.get("timestamp") or 0)
            return msgs

        return []

"""Build a richer, evidence-linked KnowledgeObject IR from imported records."""

import re
from typing import Any, Dict, List

from src.core.interfaces import Analyzer
from src.models.knowledge_object import KnowledgeObject
from src.models.knowledge_package import KnowledgePackage


class KnowledgeObjectEnricher(Analyzer):
    @property
    def name(self) -> str: return "Knowledge Object Enricher"
    @property
    def version(self) -> str: return "2.0.0"
    @property
    def author(self) -> str: return "OKC Core Team"
    @property
    def description(self) -> str: return "Builds evidence-linked, model-ready KnowledgeObject IR."
    @property
    def plugin_type(self) -> str: return "analyzer"
    @property
    def supported_inputs(self) -> List[str]: return ["okc/package"]
    @property
    def supported_outputs(self) -> List[str]: return ["okc/knowledge_objects/v2"]

    def analyze(self, package: KnowledgePackage) -> KnowledgePackage:
        existing = {getattr(obj, "conversation_id", None) or obj.id: obj for obj in package.knowledge_objects}
        for conversation in package.conversations:
            conversation_id = str(getattr(conversation, "id", "unknown"))
            obj = existing.get(conversation_id)
            if obj is None:
                provenance = dict(getattr(conversation, "provenance", {}) or {})
                obj = KnowledgeObject(
                    id=conversation_id, title=getattr(conversation, "title", conversation_id) or conversation_id,
                    content="", source_platform=provenance.get("source_platform", "Unmapped"),
                    source_file=getattr(conversation, "source", ""), created_at=getattr(conversation, "created", None),
                    updated_at=getattr(conversation, "updated", None), provenance=provenance, evidence=[],
                    conversation_id=conversation_id,
                )
                package.add_knowledge_object(obj)
            self._enrich(obj, conversation, package)
        package.update_metadata("knowledge_object_schema", "2.0")
        return package

    def _enrich(self, obj: KnowledgeObject, conversation: Any, package: KnowledgePackage) -> None:
        obj.schema_version, obj.object_type = "2.0", "conversation"
        obj.conversation_id = str(getattr(conversation, "id", obj.id))
        obj.source_record_ids = [obj.conversation_id]
        obj.provenance = {**dict(getattr(conversation, "provenance", {}) or {}), **obj.provenance}
        obj.provenance.setdefault("source_platform", obj.source_platform)
        obj.provenance.setdefault("source_file", obj.source_file)
        obj.evidence_spans, obj.messages = [], []
        for index, message in enumerate(getattr(conversation, "messages", [])):
            text = str(getattr(message, "content", "") or "").strip()
            if not text: continue
            message_id = str(getattr(message, "id", None) or f"message_{index}")
            evidence_id = obj.add_evidence_span(text, message_id, role=getattr(message, "role", "unknown"), timestamp=getattr(message, "timestamp", None))
            obj.messages.append({"id": message_id, "role": getattr(message, "role", "unknown"), "timestamp": getattr(message, "timestamp", None), "evidence_id": evidence_id})
        obj.evidence = [span["text"] for span in obj.evidence_spans]
        obj.content = "\n\n".join(obj.evidence)
        obj.entities = [self._entity(entity) for entity in package.entities if getattr(entity, "conversation_id", None) == obj.conversation_id]
        obj.attachments = [self._attachment(attachment) for attachment in package.attachment_knowledge if getattr(attachment, "conversation_id", None) == obj.conversation_id]
        obj.temporal_signals = [{"value": value, "kind": "date", "evidence": value} for value in sorted(set(re.findall(r"\b(?:\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})\b", obj.content)))]
        obj.questions = self._candidates(obj, r"\?\s*$", "question")
        obj.decisions = self._candidates(obj, r"\b(?:decided|decision|will use|we will|approved)\b", "decision")
        obj.action_items = self._candidates(obj, r"\b(?:todo|action item|next step|need to|should)\b", "action")
        obj.claims = self._candidates(obj, r"\b(?:is|are|was|were|has|have)\b", "claim")
        obj.chunks = self._chunks(obj)
        obj.retrieval = {"search_text": " ".join([obj.title, obj.content] + [a.get("raw_extraction", "") for a in obj.attachments]).strip(), "embedding_status": "pending_server_index", "lexical_fields": ["title", "content", "attachments.raw_extraction", "entities.value"]}
        obj.quality = {"evidence_span_count": len(obj.evidence_spans), "attachment_count": len(obj.attachments), "provenance_errors": obj.validate_provenance(), "candidate_fields_are_inferred": True}

    @staticmethod
    def _entity(entity: Any) -> Dict[str, Any]:
        return {"id": getattr(entity, "id", None), "value": getattr(entity, "value", ""), "type": getattr(entity, "type", "entity"), "confidence": getattr(entity, "confidence", None)}
    @staticmethod
    def _attachment(attachment: Any) -> Dict[str, Any]:
        return {"id": getattr(attachment, "id", None), "file_name": getattr(attachment, "file_name", ""), "media_type": getattr(attachment, "media_type", "unknown"), "summary": getattr(attachment, "summary", ""), "raw_extraction": getattr(attachment, "raw_extraction", ""), "confidence": getattr(attachment, "confidence", 0.0), "provenance": getattr(attachment, "provenance", {})}
    @staticmethod
    def _candidates(obj: KnowledgeObject, pattern: str, kind: str) -> List[Dict[str, Any]]:
        return [{"text": span["text"], "evidence_ids": [span["id"]], "kind": kind, "status": "candidate"} for span in obj.evidence_spans if re.search(pattern, span["text"], re.IGNORECASE)][:50]
    @staticmethod
    def _chunks(obj: KnowledgeObject, size: int = 1200) -> List[Dict[str, Any]]:
        chunks = []
        for span in obj.evidence_spans:
            for offset in range(0, len(span["text"]), size):
                text = span["text"][offset:offset + size]
                chunks.append({"id": f"{span['id']}_{offset // size}", "text": text, "evidence_ids": [span["id"]], "char_start": offset, "char_end": offset + len(text)})
        return chunks

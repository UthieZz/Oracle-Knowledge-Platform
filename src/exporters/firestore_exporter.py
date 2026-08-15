import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from google.cloud import firestore

from src.core.interfaces import Exporter
from src.models.knowledge_package import KnowledgePackage


class FirestoreExporter(Exporter):
    """Publishes a KnowledgePackage projection to Google Cloud Firestore."""

    def __init__(self, project_id: str | None = None):
        self.project_id = project_id or os.getenv(
            "GOOGLE_CLOUD_PROJECT",
            "oracle-knowledge-platform",
        )
        self.db = firestore.Client(project=self.project_id)

    @property
    def name(self) -> str:
        return "Firestore Exporter"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def author(self) -> str:
        return "OKC Core Team"

    @property
    def description(self) -> str:
        return "Publishes the KnowledgePackage operational projection to Firestore."

    @property
    def plugin_type(self) -> str:
        return "exporter"

    @property
    def supported_inputs(self) -> List[str]:
        return ["okc/package"]

    @property
    def supported_outputs(self) -> List[str]:
        return ["firestore"]

    def export(self, package: KnowledgePackage) -> KnowledgePackage:
        """Publish the current KnowledgePackage to Firestore."""

        timestamp = datetime.now(timezone.utc).isoformat()

        platform_map = self._group_platforms(package)

        self.db.collection("meta").document("dashboard").set(
            {
                "updated_at": timestamp,
                "conversations": len(package.conversations),
                "messages": sum(
                    len(getattr(conv, "messages", []))
                    for conv in package.conversations
                ),
                "entities": len(package.entities),
                "attachments": len(package.attachment_knowledge),
                "platforms": len(platform_map),
            }
        )

        self._write_platforms(package, platform_map, timestamp)
        self._write_conversations(package, timestamp)
        self._write_knowledge_objects(package, timestamp)
        self._write_entities(package, timestamp)
        self._write_attachments(package, timestamp)

        return package

    def _group_platforms(
        self, package: KnowledgePackage
    ) -> Dict[str, List[Any]]:
        platforms: Dict[str, List[Any]] = {}

        for conversation in package.conversations:
            provenance = getattr(conversation, "provenance", {}) or {}
            platform = (
                provenance.get("source_platform")
                or self._derive_platform(
                    getattr(conversation, "source", "")
                )
            )

            platforms.setdefault(platform, []).append(conversation)

        return platforms

    @staticmethod
    def _derive_platform(source: str) -> str:
        source = (source or "").lower()

        if "gemini" in source:
            return "Gemini"
        if "chatgpt" in source or "openai" in source:
            return "ChatGPT"
        if "claude" in source or "anthropic" in source:
            return "Claude"
        if "grok" in source:
            return "Grok"
        if "perplexity" in source:
            return "Perplexity"
        if "copilot" in source:
            return "Copilot"

        return "Unknown"

    def _write_platforms(
        self,
        package: KnowledgePackage,
        platform_map: Dict[str, List[Any]],
        timestamp: str,
    ) -> None:
        platforms_ref = self.db.collection("platforms")

        for platform, conversations in platform_map.items():
            conversation_ids = {
                getattr(conv, "id", None)
                for conv in conversations
            }

            entities = [
                entity
                for entity in package.entities
                if getattr(entity, "conversation_id", None)
                in conversation_ids
            ]

            attachments = [
                attachment
                for attachment in package.attachment_knowledge
                if getattr(attachment, "conversation_id", None)
                in conversation_ids
            ]

            platforms_ref.document(platform).set(
                {
                    "name": platform,
                    "conversation_count": len(conversations),
                    "message_count": sum(
                        len(getattr(conv, "messages", []))
                        for conv in conversations
                    ),
                    "entity_count": len(entities),
                    "attachment_count": len(attachments),
                    "updated_at": timestamp,
                }
            )

    def _write_conversations(
        self,
        package: KnowledgePackage,
        timestamp: str,
    ) -> None:
        conversations_ref = self.db.collection("conversations")

        for conversation in package.conversations:
            data = {
                "id": conversation.id,
                "title": conversation.title,
                "source": conversation.source,
                "created": conversation.created,
                "updated": conversation.updated,
                "message_count": len(
                    getattr(conversation, "messages", [])
                ),
                "provenance": self._safe_value(
                    getattr(conversation, "provenance", {})
                ),
                "published_at": timestamp,
            }

            conversations_ref.document(str(conversation.id)).set(data)

    def _write_knowledge_objects(
        self,
        package: KnowledgePackage,
        timestamp: str,
    ) -> None:
        objects_ref = self.db.collection("knowledgeObjects")

        for conversation in package.conversations:
            object_id = str(conversation.id)

            objects_ref.document(object_id).set(
                {
                    "id": object_id,
                    "type": "conversation",
                    "title": conversation.title,
                    "conversation_id": object_id,
                    "source": conversation.source,
                    "message_count": len(
                        getattr(conversation, "messages", [])
                    ),
                    "published_at": timestamp,
                }
            )

    def _write_entities(
        self,
        package: KnowledgePackage,
        timestamp: str,
    ) -> None:
        entities_ref = self.db.collection("entities")

        for index, entity in enumerate(package.entities):
            entity_id = getattr(entity, "id", None)

            if not entity_id:
                entity_id = (
                    f"{getattr(entity, 'conversation_id', 'unknown')}"
                    f"_{index}"
                )

            entities_ref.document(str(entity_id)).set(
                {
                    "id": str(entity_id),
                    "value": self._safe_value(
                        getattr(entity, "value", None)
                    ),
                    "type": self._safe_value(
                        getattr(entity, "type", "entity")
                    ),
                    "conversation_id": self._safe_value(
                        getattr(entity, "conversation_id", None)
                    ),
                    "published_at": timestamp,
                }
            )

    def _write_attachments(
        self,
        package: KnowledgePackage,
        timestamp: str,
    ) -> None:
        attachments_ref = self.db.collection("attachments")

        for index, attachment in enumerate(
            package.attachment_knowledge
        ):
            attachment_id = (
                getattr(attachment, "id", None)
                or getattr(attachment, "attachment_id", None)
                or f"attachment_{index}"
            )

            attachments_ref.document(str(attachment_id)).set(
                {
                    "id": str(attachment_id),
                    "conversation_id": self._safe_value(
                        getattr(attachment, "conversation_id", None)
                    ),
                    "file_name": self._safe_value(
                        getattr(attachment, "file_name", None)
                    ),
                    "media_type": self._safe_value(
                        getattr(attachment, "media_type", None)
                    ),
                    "summary": self._safe_value(
                        getattr(attachment, "summary", None)
                    ),
                    "published_at": timestamp,
                }
            )

    @staticmethod
    def _safe_value(value: Any) -> Any:
        """Convert simple model values into Firestore-safe values."""

        if value is None or isinstance(
            value,
            (str, int, float, bool),
        ):
            return value

        if isinstance(value, dict):
            return {
                str(key): FirestoreExporter._safe_value(item)
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [
                FirestoreExporter._safe_value(item)
                for item in value
            ]

        return str(value)

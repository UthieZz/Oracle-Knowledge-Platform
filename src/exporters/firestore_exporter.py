import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from google.cloud import firestore

from src.core.interfaces import Exporter
from src.models.conversation import Conversation
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

    def _process_batches(self, operations: List[Dict[str, Any]], collection_name: str) -> None:
        """Helper to process operations in batches of 500."""
        batch_size = 500
        total_batches = (len(operations) + batch_size - 1) // batch_size
        for i in range(0, len(operations), batch_size):
            batch = self.db.batch()
            chunk = operations[i:i + batch_size]
            for op in chunk:
                doc_ref = self.db.collection(collection_name).document(op["id"])
                batch.set(doc_ref, op["data"])
            batch.commit()
            print(f"Batch {i//batch_size + 1}/{total_batches} committed for {collection_name}")

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
                "knowledge_objects": len(package.conversations),
            }
        )

        self._write_platforms(package, platform_map, timestamp)
        self._write_conversations(package, timestamp)
        self._write_knowledge_objects(package, timestamp)
        self._write_entities(package, timestamp)
        self._write_attachments(package, timestamp)

        return package

    def _write_messages_batched(self, conversation: Conversation, timestamp: str) -> None:
        """Batch export all messages of a conversation."""
        messages_ref = self.db.collection("conversations").document(str(conversation.id)).collection("messages")
        
        batch_size = 500
        messages = conversation.messages
        total_batches = (len(messages) + batch_size - 1) // batch_size
        
        for i in range(0, len(messages), batch_size):
            batch = self.db.batch()
            chunk = messages[i:i + batch_size]
            for index, message in enumerate(chunk, start=i):
                message_id = getattr(message, "id", None) or f"msg_{index}"
                doc_ref = messages_ref.document(str(message_id))
                batch.set(doc_ref, {
                    "id": str(message_id),
                    "role": self._safe_value(message.role),
                    "content": self._safe_value(message.content),
                    "timestamp": self._safe_value(message.timestamp),
                    "index": index,
                    "metadata": self._safe_value(getattr(message, "metadata", {})),
                    "published_at": timestamp
                })
            batch.commit()
            print(f"Batch {i//batch_size + 1}/{total_batches} committed for messages in conv {conversation.id}")

    def _group_platforms(
        self, package: KnowledgePackage
    ) -> Dict[str, List[Any]]:
        platforms: Dict[str, List[Any]] = {}

        for conversation in package.conversations:
            provenance = getattr(conversation, "provenance", {}) or {}
            platform = provenance.get("source_platform")
            if not platform:
                # Force derivation but log a warning if it fails
                platform = self._derive_platform(getattr(conversation, "source", ""))

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

        return "Unmapped"


    def _write_platforms(
        self,
        package: KnowledgePackage,
        platform_map: Dict[str, List[Any]],
        timestamp: str,
    ) -> None:
        operations = []
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

            operations.append({
                "id": platform,
                "data": {
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
            })
        self._process_batches(operations, "platforms")

    def _write_conversations(
        self,
        package: KnowledgePackage,
        timestamp: str,
    ) -> None:
        operations = []
        for conversation in package.conversations:
            provenance = getattr(conversation, "provenance", {})
            if "source_platform" not in provenance:
                provenance["source_platform"] = self._derive_platform(getattr(conversation, "source", ""))
            
            operations.append({
                "id": str(conversation.id),
                "data": {
                    "id": conversation.id,
                    "title": conversation.title,
                    "source": conversation.source,
                    "created": conversation.created,
                    "updated": conversation.updated,
                    "message_count": len(
                        getattr(conversation, "messages", [])
                    ),
                    "provenance": self._safe_value(provenance),
                    "published_at": timestamp,
                }
            })
            self._write_messages_batched(conversation, timestamp)
            
        self._process_batches(operations, "conversations")

    def _write_knowledge_objects(
        self,
        package: KnowledgePackage,
        timestamp: str,
    ) -> None:
        operations = []
        for ko in package.knowledge_objects:
            object_id = str(ko.id)
            # Use source_platform from KnowledgeObject, fallback to derivation if needed
            platform = ko.source_platform
            if platform == "Other" or not platform:
                platform = self._derive_platform(ko.source_file)
            
            operations.append({
                "id": object_id,
                "data": {
                    "id": object_id,
                    "type": "conversation",
                    "title": ko.title,
                    "content": ko.content,
                    "conversation_id": object_id,
                    "source_platform": platform,
                    "source_file": ko.source_file,
                    "provenance": self._safe_value(ko.provenance),
                    "created_at": ko.created_at,
                    "updated_at": ko.updated_at,
                    "published_at": timestamp,
                }
            })
        self._process_batches(operations, "knowledgeObjects")

    def _write_entities(
        self,
        package: KnowledgePackage,
        timestamp: str,
    ) -> None:
        operations = []
        for index, entity in enumerate(package.entities):
            entity_id = getattr(entity, "id", None) or f"{getattr(entity, 'conversation_id', 'unknown')}_{index}"
            operations.append({
                "id": str(entity_id),
                "data": {
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
            })
        self._process_batches(operations, "entities")

    def _write_attachments(
        self,
        package: KnowledgePackage,
        timestamp: str,
    ) -> None:
        operations = []
        for index, attachment in enumerate(
            package.attachment_knowledge
        ):
            attachment_id = (
                getattr(attachment, "id", None)
                or getattr(attachment, "attachment_id", None)
                or f"attachment_{index}"
            )

            operations.append({
                "id": str(attachment_id),
                "data": {
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
            })
        self._process_batches(operations, "attachments")

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

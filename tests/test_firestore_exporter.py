import unittest
from unittest.mock import MagicMock, patch
from src.exporters.firestore_exporter import FirestoreExporter
from src.models.knowledge_package import KnowledgePackage
from src.models.knowledge_object import KnowledgeObject
from src.models.conversation import Conversation
from src.models.message import Message
from src.models.entity import Entity


class TestFirestoreExporter(unittest.TestCase):
    def _exporter(self, mock_db):
        return FirestoreExporter(
            project_id="test-project",
            tenant_id="acme",
            silo_id="default",
            client=mock_db,
        )

    def _complete_package(self):
        package = KnowledgePackage()
        conv = Conversation(
            id="conv1",
            title="Test Conversation",
            source="gemini_export.json",
            created="2026-08-15T00:00:00Z",
            updated="2026-08-15T00:00:00Z",
            messages=[Message(id="msg1", role="user", content="hello", timestamp="2026-08-15T00:00:00Z")],
            provenance={"source_platform": "Gemini"}
        )
        package.add_conversation(conv)
        package.add_knowledge_object(KnowledgeObject(
            id="ko1",
            title="Test Conversation",
            content="hello",
            source_platform="Gemini",
            source_file="gemini_export.json",
            created_at="2026-08-15T00:00:00Z",
            updated_at="2026-08-15T00:00:00Z",
            provenance={
                "source_platform": "Gemini",
                "source_file": "gemini_export.json",
                "conversation_id": "conv1",
            },
            evidence=["msg1"]
        ))
        package.add_entity(Entity(
            id="ent1",
            type="person",
            value="Ada",
            confidence=0.9,
            source="msg1",
            conversation_id="conv1",
            message_id="msg1",
        ))
        return package

    @patch("src.exporters.firestore_exporter.firestore.Client")
    def test_export(self, mock_client):
        mock_db = MagicMock()
        mock_client.return_value = mock_db

        exporter = self._exporter(mock_db)
        package = self._complete_package()
        exporter.export(package)

        self.assertTrue(mock_db.collection.called)
        self.assertEqual(mock_db.collection.call_args_list[0][0][0], "tenants")

        batch_mock = mock_db.batch.return_value
        found_data = None
        found_entity = None
        for args, kwargs in batch_mock.set.call_args_list:
            doc_ref, data = args
            if data.get("id") == "conv1" and "message_count" in data:
                found_data = data
            if data.get("id") == "ent1":
                found_entity = data

        self.assertIsNotNone(found_data, "Could not find batch set for conv1 data")
        self.assertEqual(found_data["id"], "conv1")
        self.assertEqual(found_data["title"], "Test Conversation")
        self.assertEqual(found_data["message_count"], 1)
        self.assertIsNotNone(found_entity)
        self.assertEqual(found_entity["source_platform"], "Gemini")
        self.assertEqual(found_entity["source_file"], "gemini_export.json")
        self.assertEqual(found_entity["provenance"]["conversation_id"], "conv1")

    @patch("src.exporters.firestore_exporter.firestore.Client")
    def test_export_rejects_incomplete_ko_provenance(self, mock_client):
        mock_db = MagicMock()
        exporter = self._exporter(mock_db)
        package = KnowledgePackage()
        package.add_knowledge_object(KnowledgeObject(
            id="orphan",
            title="Orphan",
            content="no lineage",
            source_platform="",
            source_file="",
            created_at=None,
            updated_at=None,
            provenance={},
            evidence=[],
        ))
        with self.assertRaises(ValueError):
            exporter.export(package)

    def test_requires_tenant_and_silo(self):
        with self.assertRaises(ValueError):
            FirestoreExporter(project_id="test-project", client=MagicMock())


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import MagicMock, patch
from src.exporters.firestore_exporter import FirestoreExporter
from src.models.knowledge_package import KnowledgePackage
from src.models.knowledge_object import KnowledgeObject
from src.models.conversation import Conversation
from src.models.message import Message

class TestFirestoreExporter(unittest.TestCase):
    @patch("src.exporters.firestore_exporter.firestore.Client")
    def test_export(self, mock_client):
        mock_db = MagicMock()
        mock_client.return_value = mock_db

        exporter = FirestoreExporter(
            project_id="test-project",
            tenant_id="acme",
            silo_id="default",
            client=mock_db,
        )
        package = KnowledgePackage()

        conv = Conversation(
            id="conv1",
            title="Test Conversation",
            source="test",
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
            source_file="test",
            created_at="2026-08-15T00:00:00Z",
            updated_at="2026-08-15T00:00:00Z",
            provenance={"source_platform": "Gemini"},
            evidence=["msg1"]
        ))

        exporter.export(package)

        # Tenant/silo path: tenants/{id}/silos/{id}/collection
        self.assertTrue(mock_db.collection.called)
        self.assertEqual(mock_db.collection.call_args_list[0][0][0], "tenants")

        batch_mock = mock_db.batch.return_value
        found_data = None
        for args, kwargs in batch_mock.set.call_args_list:
            doc_ref, data = args
            if "title" in data and data["title"] == "Test Conversation":
                found_data = data
                break

        self.assertIsNotNone(found_data, "Could not find batch set for conv1 data")
        self.assertEqual(found_data["id"], "conv1")
        self.assertEqual(found_data["title"], "Test Conversation")
        self.assertEqual(found_data["message_count"], 1)

    def test_requires_tenant_and_silo(self):
        with self.assertRaises(ValueError):
            FirestoreExporter(project_id="test-project", client=MagicMock())

if __name__ == "__main__":
    unittest.main()

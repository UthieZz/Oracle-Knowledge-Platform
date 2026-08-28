import unittest
from unittest.mock import MagicMock, patch
from src.exporters.firestore_exporter import FirestoreExporter
from src.models.knowledge_package import KnowledgePackage
from src.models.conversation import Conversation
from src.models.message import Message

class TestFirestoreExporter(unittest.TestCase):
    @patch("src.exporters.firestore_exporter.firestore.Client")
    def test_export(self, mock_client):
        # Setup
        mock_db = MagicMock()
        mock_client.return_value = mock_db
        
        exporter = FirestoreExporter(project_id="test-project")
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
        
        # Execute
        exporter.export(package)
        
        # Look for the dashboard set call
        dashboard_set_call = None
        for args, kwargs in mock_db.collection.return_value.document.return_value.set.call_args_list:
            if args[0].get("conversations") == 1:
                dashboard_set_call = args[0]
                break
        
        self.assertIsNotNone(dashboard_set_call, "Could not find dashboard set call")
        self.assertEqual(dashboard_set_call["knowledge_objects"], 1)

        # Look for the batch set call (for conversation data)
        batch_mock = mock_db.batch.return_value
        
        # Get data from the set call
        found_data = None
        for args, kwargs in batch_mock.set.call_args_list:
            doc_ref, data = args
            # Look for the conversation data specifically (it will have 'title')
            if "title" in data and data["title"] == "Test Conversation":
                found_data = data
                break
        
        self.assertIsNotNone(found_data, "Could not find batch set for conv1 data")
        self.assertEqual(found_data["id"], "conv1")
        self.assertEqual(found_data["title"], "Test Conversation")
        self.assertEqual(found_data["message_count"], 1)

if __name__ == "__main__":
    unittest.main()

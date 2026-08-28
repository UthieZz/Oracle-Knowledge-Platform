import unittest
from unittest.mock import MagicMock, patch
from src.exporters.firestore_exporter import FirestoreExporter
from src.models.knowledge_package import KnowledgePackage
from src.models.conversation import Conversation
from src.models.message import Message

class TestFirestoreExporterBatching(unittest.TestCase):
    def setUp(self):
        self.package = KnowledgePackage()
        # Add a conversation with 501 messages to force 2 batches (500 + 1)
        conv = Conversation(
            id="conv1", 
            title="Test Conv", 
            source="test", 
            created="2026-01-01", 
            updated="2026-01-01", 
            messages=[Message(role="user", content="msg") for _ in range(501)]
        )
        self.package.add_conversation(conv)
        self.exporter = FirestoreExporter(project_id="test-project")
        self.exporter.db = MagicMock()
        self.exporter.db.batch.return_value = MagicMock()

    def test_message_batching(self):
        self.exporter._write_messages_batched(self.package.conversations[0], "2026-01-01T00:00:00Z")
        
        # Verify batch.commit() called 2 times
        self.assertEqual(self.exporter.db.batch.return_value.commit.call_count, 2)
        self.assertEqual(self.exporter.db.batch.call_count, 2)

    @patch('src.exporters.firestore_exporter.FirestoreExporter._process_batches')
    def test_process_batches_call(self, mock_process_batches):
        self.package.add_conversation(Conversation(
            id="conv2", 
            title="Conv2",
            source="test",
            created="2026-01-01",
            updated="2026-01-01"
        ))
        self.exporter._write_conversations(self.package, "2026-01-01T00:00:00Z")
        self.assertTrue(mock_process_batches.called)

if __name__ == '__main__':
    unittest.main()

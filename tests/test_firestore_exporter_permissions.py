import unittest
from unittest.mock import MagicMock, patch
from src.exporters.firestore_exporter import FirestoreExporter
from src.models.knowledge_package import KnowledgePackage
from src.models.knowledge_object import KnowledgeObject


class TestFirestoreExporterPermissions(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.exporter = FirestoreExporter(
            project_id="test",
            tenant_id="acme",
            silo_id="default",
            client=self.mock_db,
        )

    def _ko(self, ko_id: str, src_id: str | None = None):
        prov = {"source_platform": "test", "conversation_id": "conv1"}
        if src_id:
            prov["source_record_ids"] = [f"src:{src_id}"]
        return KnowledgeObject(
            id=ko_id,
            title=ko_id,
            content="content",
            source_platform="test",
            source_file="file.txt",
            created_at=None,
            updated_at=None,
            provenance=prov,
            evidence=[],
        )

    def test_explicit_deny_excludes_object(self):
        package = KnowledgePackage()
        package.add_knowledge_object(self._ko("ko1", "obj1"))
        package.metadata["permissions"] = {"obj1": {"read": False}}
        # Mock the write path to capture what would be written
        with patch.object(self.exporter, "_process_batches") as mock_batches:
            with patch.object(self.exporter, "_write_platforms"):
                with patch.object(self.exporter, "_write_conversations"):
                    with patch.object(self.exporter, "_write_entities"):
                        with patch.object(self.exporter, "_write_attachments"):
                            with patch.object(self.exporter, "_write_source_fingerprints"):
                                with patch.object(self.exporter, "_collection"):
                                    self.exporter.export(package)
        # Dashboard or knowledgeObjects collection should reflect exclusion
        # Inspect the last call to _process_batches for knowledgeObjects
        calls = [c for c in mock_batches.call_args_list if c[0][1] == "knowledgeObjects"]
        self.assertTrue(calls)
        ops = calls[0][0][0]
        self.assertEqual(len(ops), 0)

    def test_missing_permission_included_by_default(self):
        package = KnowledgePackage()
        package.add_knowledge_object(self._ko("ko1", "obj1"))
        # no permissions key
        with patch.object(self.exporter, "_process_batches") as mock_batches:
            with patch.object(self.exporter, "_write_platforms"):
                with patch.object(self.exporter, "_write_conversations"):
                    with patch.object(self.exporter, "_write_entities"):
                        with patch.object(self.exporter, "_write_attachments"):
                            with patch.object(self.exporter, "_write_source_fingerprints"):
                                with patch.object(self.exporter, "_collection"):
                                    self.exporter.export(package, strict_permissions=False)
        calls = [c for c in mock_batches.call_args_list if c[0][1] == "knowledgeObjects"]
        self.assertTrue(calls)
        ops = calls[0][0][0]
        self.assertEqual(len(ops), 1)

    def test_strict_mode_excludes_missing(self):
        package = KnowledgePackage()
        package.add_knowledge_object(self._ko("ko1", "obj1"))
        with patch.object(self.exporter, "_process_batches") as mock_batches:
            with patch.object(self.exporter, "_write_platforms"):
                with patch.object(self.exporter, "_write_conversations"):
                    with patch.object(self.exporter, "_write_entities"):
                        with patch.object(self.exporter, "_write_attachments"):
                            with patch.object(self.exporter, "_write_source_fingerprints"):
                                with patch.object(self.exporter, "_collection"):
                                    self.exporter.export(package, strict_permissions=True)
        calls = [c for c in mock_batches.call_args_list if c[0][1] == "knowledgeObjects"]
        self.assertTrue(calls)
        ops = calls[0][0][0]
        self.assertEqual(len(ops), 0)


if __name__ == "__main__":
    unittest.main()

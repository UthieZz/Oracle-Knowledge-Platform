import json
import os
import tempfile
import unittest

from src.exporters.relationship_index_exporter import RelationshipIndexExporter
from src.models.knowledge_package import KnowledgePackage
from src.models.knowledge_object import KnowledgeObject


class TestRelationshipIndexPermissions(unittest.TestCase):
    def test_excludes_explicit_deny(self):
        package = KnowledgePackage()
        package.metadata["permissions"] = {
            "denied": {"read": False},
            "allowed": {"read": True},
        }
        package.add_knowledge_object(
            KnowledgeObject(
                id="denied",
                title="Secret",
                content="hidden",
                source_platform="Test",
                source_file="test.json",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
                provenance={"conversation_id": "denied", "message_ids": ["m1"]},
                evidence=[],
            )
        )
        package.add_knowledge_object(
            KnowledgeObject(
                id="allowed",
                title="Public",
                content="visible",
                source_platform="Test",
                source_file="test.json",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
                provenance={"conversation_id": "allowed", "message_ids": ["m2"]},
                evidence=[],
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            RelationshipIndexExporter(output_dir=tmp).export(package)
            with open(os.path.join(tmp, "relationships.json"), encoding="utf-8") as fh:
                payload = json.load(fh)
        from_ids = {e["from"] for e in payload["edges"]}
        self.assertNotIn("denied", from_ids)
        self.assertIn("allowed", from_ids)


if __name__ == "__main__":
    unittest.main()

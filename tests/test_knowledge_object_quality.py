import json
import os
import tempfile
import unittest

from src.exporters.relationship_index_exporter import RelationshipIndexExporter
from src.models.conversation import Conversation
from src.models.knowledge_object import KnowledgeObject
from src.models.knowledge_package import KnowledgePackage
from src.models.message import Message
from src.validators.knowledge_object_quality import annotate_knowledge_object_quality


class TestKnowledgeObjectQuality(unittest.TestCase):
    def test_flags_question_title(self):
        package = KnowledgePackage()
        package.add_knowledge_object(
            KnowledgeObject(
                id="q1",
                title="Hey Gemini give me some examples of what you can do",
                content="short",
                source_platform="Gemini",
                source_file="in.json",
                created_at=None,
                updated_at=None,
                provenance={"source_platform": "Gemini", "source_file": "in.json", "conversation_id": "c1"},
                evidence=["m1"],
            )
        )
        report = annotate_knowledge_object_quality(package)
        self.assertEqual(report["conversation_shaped_or_thin"], 1)
        self.assertTrue(package.knowledge_objects[0].provenance["quality"]["conversation_shaped"])
        self.assertFalse(package.knowledge_objects[0].provenance["quality"]["reusable_candidate"])

    def test_relationship_index_writes_edges(self):
        package = KnowledgePackage()
        package.add_conversation(
            Conversation(
                id="c1",
                title="t",
                source="grok.json",
                created=None,
                updated=None,
                messages=[Message(id="m1", role="user", content="x")],
                provenance={"source_platform": "Grok"},
            )
        )
        package.add_knowledge_object(
            KnowledgeObject(
                id="ko1",
                title="Decision record",
                content="A reusable compiled decision with enough body text to pass thin check.",
                source_platform="Grok",
                source_file="grok.json",
                created_at=None,
                updated_at=None,
                provenance={
                    "source_platform": "Grok",
                    "source_file": "grok.json",
                    "conversation_id": "c1",
                    "message_ids": ["m1"],
                    "object_type": "knowledge_object",
                },
                evidence=["m1"],
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            RelationshipIndexExporter(output_dir=tmp).export(package)
            path = os.path.join(tmp, "relationships.json")
            data = json.load(open(path, encoding="utf-8"))
            self.assertGreaterEqual(data["edge_count"], 2)
            types = {e["type"] for e in data["edges"]}
            self.assertIn("sourced_from", types)


if __name__ == "__main__":
    unittest.main()

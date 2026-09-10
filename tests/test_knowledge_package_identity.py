import unittest

from src.models.knowledge_object import KnowledgeObject
from src.models.knowledge_package import KnowledgePackage
from src.models.conversation import Conversation


class TestKnowledgePackageIdentity(unittest.TestCase):
    def test_dedup_knowledge_objects_by_id(self):
        package = KnowledgePackage()
        ko = KnowledgeObject(
            id="ko1",
            title="A",
            content="x",
            source_platform="Grok",
            source_file="f.json",
            created_at=None,
            updated_at=None,
            provenance={"source_platform": "Grok", "source_file": "f.json", "conversation_id": "c1"},
            evidence=[],
        )
        package.add_knowledge_object(ko)
        package.add_knowledge_object(ko)
        self.assertEqual(len(package.knowledge_objects), 1)
        self.assertIs(package.get_knowledge_object("ko1"), ko)

    def test_dedup_conversations_by_id(self):
        package = KnowledgePackage()
        conv = Conversation(
            id="c1",
            title="T",
            source="s",
            created=None,
            updated=None,
            messages=[],
            provenance={"source_platform": "Grok"},
        )
        package.add_conversation(conv)
        package.add_conversation(conv)
        self.assertEqual(len(package.conversations), 1)
        self.assertIs(package.get_conversation("c1"), conv)

import unittest

from src.models.attachment_knowledge import AttachmentKnowledge
from src.models.conversation import Conversation
from src.models.knowledge_object import KnowledgeObject
from src.models.knowledge_package import KnowledgePackage
from src.models.message import Message
from src.validators.knowledge_object_provenance import (
    ensure_knowledge_object_provenance,
    provenance_report,
)


class TestKnowledgeObjectProvenance(unittest.TestCase):
    def _package(self) -> KnowledgePackage:
        package = KnowledgePackage()
        conv = Conversation(
            id="conv1",
            title="Lineage",
            source="/input/grok-export.json",
            created="2026-08-16T10:00:00Z",
            updated="2026-08-16T10:05:00Z",
            messages=[
                Message(id="msg1", role="user", content="hi"),
                Message(id="msg2", role="assistant", content="hello"),
            ],
            provenance={
                "source_platform": "Grok",
                "imported_at": "2026-08-16T10:06:00Z",
            },
        )
        package.add_conversation(conv)
        package.add_attachment_knowledge(
            AttachmentKnowledge(
                attachment_id="att1",
                conversation_id="conv1",
                file_name="shot.png",
                media_type="image",
                fingerprint="abc",
                processor_name="image",
                processor_version="1",
                message_id="msg1",
            )
        )
        package.add_knowledge_object(
            KnowledgeObject(
                id="conv1",
                title="Lineage",
                content="hi",
                source_platform="Grok",
                source_file="/input/grok-export.json",
                created_at="2026-08-16T10:00:00Z",
                updated_at="2026-08-16T10:05:00Z",
                provenance={},
                evidence=[],
            )
        )
        return package

    def test_repairs_missing_lineage(self):
        package = self._package()
        before = provenance_report(package)
        self.assertEqual(before["ok"], 0)

        report = ensure_knowledge_object_provenance(package)
        self.assertEqual(report["failed"], [])
        self.assertEqual(report["repaired"], 1)

        ko = package.knowledge_objects[0]
        self.assertEqual(ko.provenance["source_platform"], "Grok")
        self.assertEqual(ko.provenance["source_file"], "/input/grok-export.json")
        self.assertEqual(ko.provenance["conversation_id"], "conv1")
        self.assertEqual(ko.provenance["message_ids"], ["msg1", "msg2"])
        self.assertEqual(ko.evidence, ["msg1", "msg2"])
        self.assertTrue(ko.provenance["attachment_ids"])
        self.assertEqual(ko.provenance["object_type"], "knowledge_object")

        after = provenance_report(package)
        self.assertEqual(after["failed"], [])

    def test_strict_raises_when_unrecoverable(self):
        package = KnowledgePackage()
        package.add_knowledge_object(
            KnowledgeObject(
                id="orphan",
                title="No source",
                content="",
                source_platform="",
                source_file="",
                created_at=None,
                updated_at=None,
                provenance={},
                evidence=[],
            )
        )
        with self.assertRaises(ValueError):
            ensure_knowledge_object_provenance(package, strict=True)


if __name__ == "__main__":
    unittest.main()

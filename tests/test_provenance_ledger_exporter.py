import json
import os
import tempfile
import unittest

from src.exporters.provenance_ledger_exporter import ProvenanceLedgerExporter
from src.models.conversation import Conversation
from src.models.knowledge_object import KnowledgeObject
from src.models.knowledge_package import KnowledgePackage
from src.models.message import Message


class TestProvenanceLedgerExporter(unittest.TestCase):
    def test_writes_complete_lineage(self):
        package = KnowledgePackage()
        package.add_conversation(
            Conversation(
                id="conv1",
                title="Lineage",
                source="/input/grok-export.json",
                created="2026-08-16T10:00:00Z",
                updated="2026-08-16T10:05:00Z",
                messages=[
                    Message(id="msg1", role="user", content="hi"),
                    Message(id="msg2", role="assistant", content="hello"),
                ],
                provenance={"source_platform": "Grok"},
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
        with tempfile.TemporaryDirectory() as tmp:
            exporter = ProvenanceLedgerExporter(output_dir=tmp)
            exporter.export(package)
            path = os.path.join(tmp, "provenance_ledger.json")
            self.assertTrue(os.path.exists(path))
            with open(path, encoding="utf-8") as fh:
                payload = json.load(fh)
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["complete"], 1)
        self.assertEqual(payload["incomplete"], [])
        obj = payload["objects"][0]
        self.assertEqual(obj["conversation_id"], "conv1")
        self.assertEqual(obj["message_ids"], ["msg1", "msg2"])
        self.assertEqual(obj["source_platform"], "Grok")
        self.assertTrue(obj["complete"])

    def test_flags_orphan_object(self):
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
        with tempfile.TemporaryDirectory() as tmp:
            ProvenanceLedgerExporter(output_dir=tmp).export(package)
            with open(os.path.join(tmp, "provenance_ledger.json"), encoding="utf-8") as fh:
                payload = json.load(fh)
        self.assertEqual(payload["complete"], 0)
        self.assertEqual(payload["incomplete"], ["orphan"])


if __name__ == "__main__":
    unittest.main()

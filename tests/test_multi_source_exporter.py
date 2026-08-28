import json
import os
import tempfile
import unittest
from src.exporters.exporter_registry import ExportRegistry
from src.exporters.multi_source_exporter import MultiSourceExporter
from src.models.attachment_knowledge import AttachmentKnowledge
from src.models.conversation import Conversation
from src.models.entity import Entity
from src.models.knowledge_package import KnowledgePackage
from src.models.message import Message
from src.services.export_service import ExportService


def create_multi_source_package() -> KnowledgePackage:
    package = KnowledgePackage()

    # Gemini conversation
    conv_gemini = Conversation(
        id="conv_gemini_1",
        title="Gemini Quantum Computing Notes",
        source="/inputs/gemini.json",
        created="2026-03-01T10:00:00Z",
        updated="2026-03-01T10:30:00Z",
        messages=[
            Message(id="msg_g1", role="user", content="Explain qubit superposition."),
            Message(id="msg_g2", role="assistant", content="Superposition allows qubits to exist in combined states."),
        ],
        provenance={"source_platform": "Gemini", "source_file": "gemini.json"},
    )

    # ChatGPT conversation
    conv_chatgpt = Conversation(
        id="conv_chatgpt_1",
        title="ChatGPT Python Best Practices",
        source="/inputs/chatgpt.json",
        created="2026-03-02T12:00:00Z",
        updated="2026-03-02T12:45:00Z",
        messages=[
            Message(id="msg_c1", role="user", content="What is PEP 8?"),
            Message(id="msg_c2", role="assistant", content="PEP 8 is the Python style guide."),
        ],
        provenance={"source_platform": "ChatGPT", "source_file": "chatgpt.json"},
    )

    # Claude conversation (future importer platform test)
    conv_claude = Conversation(
        id="conv_claude_1",
        title="Claude System Architecture",
        source="/inputs/claude.json",
        created="2026-03-03T15:00:00Z",
        updated="2026-03-03T16:00:00Z",
        messages=[
            Message(id="msg_cl1", role="user", content="Design a modular microservice."),
            Message(id="msg_cl2", role="assistant", content="A modular microservice architecture uses clean APIs."),
        ],
        provenance={"source_platform": "Claude", "source_file": "claude.json"},
    )

    package.add_conversation(conv_gemini)
    package.add_conversation(conv_chatgpt)
    package.add_conversation(conv_claude)

    package.add_entity(Entity(id="e1", type="concept", value="Qubit", confidence=1.0, source="test", conversation_id="conv_gemini_1", message_id="msg_g1"))
    package.add_entity(Entity(id="e2", type="standard", value="PEP 8", confidence=1.0, source="test", conversation_id="conv_chatgpt_1", message_id="msg_c1"))
    package.add_entity(Entity(id="e3", type="architecture", value="Microservice", confidence=1.0, source="test", conversation_id="conv_claude_1", message_id="msg_cl1"))

    package.add_attachment_knowledge(
        AttachmentKnowledge(
            attachment_id="att_g1",
            conversation_id="conv_gemini_1",
            message_id="msg_g1",
            file_name="qubit_diagram.png",
            media_type="image",
            fingerprint="fp_12345",
            processor_name="ImageProcessor",
            processor_version="1.0.0",
            summary="Quantum circuit diagram",
            provenance={"source_platform": "Gemini"},
        )
    )

    return package


class TestMultiSourceExporter(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = os.path.join(self.temp_dir.name, "output")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_export_mode_both(self):
        package = create_multi_source_package()
        exporter = MultiSourceExporter(output_dir=self.output_dir, mode="Both")
        exporter.export(package)

        # 1. Check Root Manifest
        root_manifest_path = os.path.join(self.output_dir, "manifest.json")
        self.assertTrue(os.path.exists(root_manifest_path))
        with open(root_manifest_path, "r", encoding="utf-8") as f:
            root_manifest = json.load(f)
        self.assertEqual(root_manifest["compilation_run"]["total_conversations"], 3)
        self.assertEqual(root_manifest["compilation_run"]["total_platforms"], 3)
        self.assertIn("Gemini", root_manifest["platforms"])
        self.assertIn("ChatGPT", root_manifest["platforms"])
        self.assertIn("Claude", root_manifest["platforms"])

        # 2. Check Unified Output Folder
        unified_dir = os.path.join(self.output_dir, "unified")
        self.assertTrue(os.path.exists(unified_dir))
        self.assertTrue(os.path.exists(os.path.join(unified_dir, "INDEX.md")))
        self.assertTrue(os.path.exists(os.path.join(unified_dir, "manifest.json")))
        self.assertTrue(os.path.isdir(os.path.join(unified_dir, "knowledge_objects")))
        self.assertTrue(os.path.isdir(os.path.join(unified_dir, "sources_archive")))

        # 3. Check Platforms Folders
        platforms_dir = os.path.join(self.output_dir, "Platforms")
        self.assertTrue(os.path.exists(platforms_dir))

        for plat_name in ["Gemini", "ChatGPT", "Claude"]:
            plat_path = os.path.join(platforms_dir, plat_name)
            self.assertTrue(os.path.exists(plat_path), f"Missing platform dir: {plat_path}")
            self.assertTrue(os.path.exists(os.path.join(plat_path, "INDEX.md")))
            self.assertTrue(os.path.exists(os.path.join(plat_path, "platform.json")))
            self.assertTrue(os.path.exists(os.path.join(plat_path, "manifest.json")))
            self.assertTrue(os.path.isdir(os.path.join(plat_path, "knowledge_objects")))
            self.assertTrue(os.path.isdir(os.path.join(plat_path, "sources_archive")))

            with open(os.path.join(plat_path, "platform.json"), "r", encoding="utf-8") as f:
                plat_json = json.load(f)
            self.assertEqual(plat_json["platform_name"], plat_name)
            self.assertEqual(plat_json["conversation_count"], 1)

    def test_export_mode_separate_by_source(self):
        package = create_multi_source_package()
        exporter = MultiSourceExporter(output_dir=self.output_dir, mode="Separate by Source")
        exporter.export(package)

        # Platforms directory exists
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "Platforms")))
        # Unified directory should not exist in Separate mode
        self.assertFalse(os.path.exists(os.path.join(self.output_dir, "unified")))

    def test_export_mode_unified_only(self):
        package = create_multi_source_package()
        exporter = MultiSourceExporter(output_dir=self.output_dir, mode="Unified")
        exporter.export(package)

        # Unified directory exists
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "unified")))
        # Platforms directory should not exist in Unified mode
        self.assertFalse(os.path.exists(os.path.join(self.output_dir, "Platforms")))

    def test_export_registry_and_service(self):
        service = ExportService(mode="Both")
        available = service.get_available_exporters()
        self.assertTrue(len(available) > 0)
        self.assertEqual(available[0]["name"], "Multi-Source Exporter")

        package = create_multi_source_package()
        res = service.export_knowledge(package, {"output_dir": self.output_dir, "mode": "Both", "exporter_name": "Multi-Source Exporter"})
        self.assertEqual(res["status"], "Success")
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "manifest.json")))


if __name__ == "__main__":
    unittest.main()

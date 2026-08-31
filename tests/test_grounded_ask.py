import os
import tempfile
import unittest
from unittest.mock import MagicMock

from src.studio.services.studio_knowledge_service import StudioKnowledgeService
from src.studio.services.search_service import SearchService
from src.studio.services.chat_service import ChatService, INSUFFICIENT_EVIDENCE


class TestGroundedAsk(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._output = os.path.join(self._tmpdir, "output")
        os.makedirs(self._output, exist_ok=True)

        # Minimal portable workspace with one knowledge object
        with open(os.path.join(self._output, "manifest.json"), "w", encoding="utf-8") as f:
            f.write("{}")

        plat_dir = os.path.join(self._output, "Platforms", "Grok")
        ko_dir = os.path.join(plat_dir, "knowledge_objects")
        os.makedirs(ko_dir, exist_ok=True)
        with open(os.path.join(plat_dir, "manifest.json"), "w", encoding="utf-8") as f:
            f.write("{}")

        with open(
            os.path.join(ko_dir, "Dispatcher_Rules.md"), "w", encoding="utf-8"
        ) as f:
            f.write(
                "# Dispatcher Rules\n\n"
                "Grok files must never compile via GeminiImporter.\n"
                "Provenance must retain source_platform.\n"
            )

        self.ks = StudioKnowledgeService(output_dir=self._output)
        self.assertTrue(self.ks.load_workspace())
        self.search = SearchService(self.ks)
        self.chat = ChatService(self.search)
        # Force offline path: no live Gemini
        self.chat.genai_client = None

    def tearDown(self):
        for root, dirs, files in os.walk(self._tmpdir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self._tmpdir)

    def test_empty_evidence_refuses_without_model(self):
        result = self.chat.chat("totally unrelated quantum banana casserole")
        self.assertEqual(result["answer"], INSUFFICIENT_EVIDENCE)
        self.assertEqual(result["citations"], [])

    def test_knowledge_object_hit_produces_citations(self):
        # With a matching KO, retrieval should produce citations even if Gemini is offline
        result = self.chat.chat("Grok dispatcher GeminiImporter")
        self.assertTrue(len(result["citations"]) >= 1)
        cite = result["citations"][0]
        self.assertIn("source_index", cite)
        self.assertEqual(cite["platform"], "Grok")
        self.assertEqual(cite.get("type"), "knowledge")
        # Offline Gemini still returns structured response with citations attached
        self.assertTrue(result.get("hasError") or "Gemini" in result["answer"] or result["citations"])

    def test_search_prefers_knowledge_type(self):
        hits = self.search.search("Dispatcher")
        self.assertTrue(len(hits) >= 1)
        self.assertEqual(hits[0]["type"], "knowledge")
        self.assertEqual(hits[0]["source_platform"], "Grok")

    def test_blank_query(self):
        result = self.chat.chat("   ")
        self.assertIn("Please enter", result["answer"])
        self.assertEqual(result["citations"], [])


if __name__ == "__main__":
    unittest.main()

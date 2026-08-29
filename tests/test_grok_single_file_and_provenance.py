"""Regression: single-file Grok import + provenance + KO mapping."""

import os
import tempfile
import json
import unittest

from src.services.import_service import ImportService
from src.services.import_dispatcher import detect_source_type, SourceType


class TestGrokSingleFileAndProvenance(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        for root, _, files in os.walk(self._tmpdir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            os.rmdir(root)

    def test_prod_named_file_detects_grok(self):
        path = os.path.join(self._tmpdir, "prod-grok-backend.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                [
                    {
                        "id": "g1",
                        "title": "Hello",
                        "messages": [
                            {"role": "user", "content": "hi"},
                            {"role": "assistant", "content": "hello"},
                        ],
                    }
                ],
                f,
            )
        self.assertEqual(detect_source_type(path), SourceType.GROK)

    def test_single_file_import_creates_ko_with_grok_platform(self):
        path = os.path.join(self._tmpdir, "prod-grok-backend.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                [
                    {
                        "id": "g1",
                        "title": "Hello",
                        "created_at": "2026-08-16T10:00:00Z",
                        "updated_at": "2026-08-16T10:05:00Z",
                        "messages": [
                            {"role": "user", "content": "hi", "timestamp": "2026-08-16T10:00:00Z"},
                            {
                                "role": "assistant",
                                "content": "hello",
                                "timestamp": "2026-08-16T10:00:05Z",
                            },
                        ],
                    }
                ],
                f,
            )

        service = ImportService()
        result = service.run_grok_import(file_path=path)
        self.assertEqual(result["status"], "Done", result)
        self.assertGreaterEqual(result["conversations"], 1)

        package = service.get_package()
        self.assertIsNotNone(package)
        assert package is not None

        self.assertGreaterEqual(len(package.conversations), 1)
        self.assertGreaterEqual(len(package.knowledge_objects), 1)

        for conv in package.conversations:
            self.assertEqual(conv.provenance.get("source_platform"), "Grok")

        for ko in package.knowledge_objects:
            self.assertEqual(ko.source_platform, "Grok")
            self.assertEqual(ko.id, next(c.id for c in package.conversations if c.id == ko.id).id)

        # Mapping invariant: KO count tracks conversations added in this package
        self.assertEqual(len(package.knowledge_objects), len(package.conversations))

    def test_gemini_importer_refuses_grok_file(self):
        path = os.path.join(self._tmpdir, "prod-grok-backend.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump([{"id": "g1", "messages": []}], f)

        service = ImportService()
        with self.assertRaises(ValueError) as ctx:
            service.run_gemini_import(file_path=path)
        self.assertIn("Refusing GeminiImporter", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

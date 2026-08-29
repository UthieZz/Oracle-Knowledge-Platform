import unittest
import os
import json
import tempfile

from src.services.import_dispatcher import detect_source_type, SourceType


class TestImportDispatcher(unittest.TestCase):
    def _write(self, name: str, payload) -> str:
        path = os.path.join(self._tmpdir, name)
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(payload, str):
                f.write(payload)
            else:
                json.dump(payload, f)
        return path

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        for root, _, files in os.walk(self._tmpdir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            os.rmdir(root)

    def test_filename_grok_wins(self):
        path = self._write(
            "prod-grok-backend.json",
            {"conversations": [{"id": "1", "messages": []}]},
        )
        self.assertEqual(detect_source_type(path), SourceType.GROK)

    def test_filename_grok_test(self):
        path = self._write("grok-test.json", [{"id": "grok_conv_1", "messages": []}])
        self.assertEqual(detect_source_type(path), SourceType.GROK)

    def test_filename_myactivity_is_gemini(self):
        path = self._write(
            "MyActivity-081f794118b580a5.json",
            [{"header": "Gemini Apps", "title": "Prompted hi"}],
        )
        self.assertEqual(detect_source_type(path), SourceType.GEMINI)

    def test_content_gemini_header(self):
        path = self._write(
            "export.json",
            [{"header": "Gemini Apps", "title": "Prompted test", "time": "2026-01-01T00:00:00Z"}],
        )
        self.assertEqual(detect_source_type(path), SourceType.GEMINI)

    def test_chatgpt_conversation_id(self):
        path = self._write(
            "slice.json",
            [{"conversation_id": "abc", "title": "t", "mapping": {}}],
        )
        self.assertEqual(detect_source_type(path), SourceType.CHATGPT)

    def test_chatgpt_filename_prefix(self):
        path = self._write("conversations-000.json", [{"id": "x"}])
        self.assertEqual(detect_source_type(path), SourceType.CHATGPT)

    def test_grok_never_classified_as_gemini_by_name(self):
        # Even if content looked vaguely list-like, filename rules Grok
        path = self._write("prod-grok-backend.json", [{"header": "not gemini"}])
        self.assertEqual(detect_source_type(path), SourceType.GROK)

    def test_unknown(self):
        path = self._write("random.json", {"foo": "bar"})
        self.assertEqual(detect_source_type(path), SourceType.UNKNOWN)

    def test_malformed_json_unknown(self):
        path = self._write("broken.json", "{not json")
        self.assertEqual(detect_source_type(path), SourceType.UNKNOWN)


if __name__ == "__main__":
    unittest.main()

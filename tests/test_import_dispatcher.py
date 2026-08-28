import unittest
import os
import json
from src.services.import_dispatcher import detect_source_type, SourceType

class TestImportDispatcher(unittest.TestCase):

    def test_grok_detection(self):
        # Create dummy Grok file
        with open('temp_grok.json', 'w') as f:
            json.dump({"conversations": []}, f)
        self.assertEqual(detect_source_type('temp_grok.json'), SourceType.GROK)
        os.remove('temp_grok.json')

    def test_chatgpt_detection(self):
        # Create dummy ChatGPT file
        with open('temp_chatgpt.json', 'w') as f:
            json.dump([{"conversation_id": "123"}], f)
        self.assertEqual(detect_source_type('temp_chatgpt.json'), SourceType.CHATGPT)
        os.remove('temp_chatgpt.json')

    def test_gemini_detection(self):
        # Create dummy Gemini file
        with open('temp_gemini.json', 'w') as f:
            json.dump([{"header": "Gemini Apps"}], f)
        self.assertEqual(detect_source_type('temp_gemini.json'), SourceType.GEMINI)
        os.remove('temp_gemini.json')

    def test_unknown_detection(self):
        with open('temp_unknown.json', 'w') as f:
            json.dump({"random": "data"}, f)
        self.assertEqual(detect_source_type('temp_unknown.json'), SourceType.UNKNOWN)
        os.remove('temp_unknown.json')

    def test_malformed_json(self):
        with open('temp_malformed.json', 'w') as f:
            f.write("{invalid: json}")
        self.assertEqual(detect_source_type('temp_malformed.json'), SourceType.UNKNOWN)
        os.remove('temp_malformed.json')

if __name__ == '__main__':
    unittest.main()

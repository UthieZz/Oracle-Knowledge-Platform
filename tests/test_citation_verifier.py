import unittest

from src.validators.citation_verifier import (
    referenced_source_indexes,
    verify_citations,
)


class TestCitationVerifier(unittest.TestCase):
    def test_extracts_unique_indexes(self):
        text = "Fact [Source 1] and again [Source 1] plus [Source 3]."
        self.assertEqual(referenced_source_indexes(text), [1, 3])

    def test_keeps_only_referenced_citations(self):
        answer = "The dispatcher rule is explicit [Source 2]."
        citations = [
            {"id": "a", "source_index": 1, "title": "A"},
            {"id": "b", "source_index": 2, "title": "B"},
        ]
        result = verify_citations(answer, citations)
        self.assertEqual([c["id"] for c in result["citations"]], ["b"])
        self.assertEqual([c["id"] for c in result["unverified"]], ["a"])
        self.assertTrue(result["sufficient"])

    def test_empty_answer_is_sufficient_with_no_claims(self):
        result = verify_citations("", [{"id": "a", "source_index": 1}])
        self.assertEqual(result["citations"], [])
        self.assertTrue(result["sufficient"])


if __name__ == "__main__":
    unittest.main()

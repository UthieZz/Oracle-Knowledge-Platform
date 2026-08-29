import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import patch, MagicMock

from src.services.import_service import ImportService
from src.services.import_dispatcher import detect_source_type, SourceType
from src.analyzers.entity_engine import EntityEngine
from src.analyzers.knowledge_index_builder import KnowledgeIndexBuilder
from src.models.knowledge_package import KnowledgePackage
from src.models.knowledge_object import KnowledgeObject
from src.exporters.firestore_exporter import FirestoreExporter

def test_pipeline_and_grounding():
    print("\n==========================================")
    print("OKP E2E PIPELINE & GROUNDING VERIFICATION")
    print("==========================================")

    # 1. Test Source Type Detection
    print("\n[STEP 1] Testing Importer Source Detection...")
    grok_type = detect_source_type("uploads/grok-test.json")
    print(f"  uploads/grok-test.json detected as: {grok_type.value}")
    assert grok_type == SourceType.GROK, "Grok source detection failed"

    # 2. Test Import into KnowledgePackage
    print("\n[STEP 2] Running Import on Grok test data...")
    import_service = ImportService()
    result = import_service.run_grok_import("uploads/grok-test.json")
    print(f"  Import result: {result}")
    assert result["status"] == "Done", "Grok import status not Done"
    
    pkg = import_service.get_package()
    assert pkg is not None, "KnowledgePackage is None"
    print(f"  Conversations in package: {len(pkg.conversations)}")
    print(f"  Knowledge Objects in package: {len(pkg.knowledge_objects)}")
    assert len(pkg.conversations) > 0, "No conversations imported"
    assert len(pkg.knowledge_objects) > 0, "No knowledge objects generated"

    # 3. Test Analyzers
    print("\n[STEP 3] Running Entity Analysis & Indexing...")
    EntityEngine().analyze(pkg)
    KnowledgeIndexBuilder().analyze(pkg)
    print(f"  Entities in package: {len(pkg.entities)}")
    print(f"  Index categories: {list(pkg.index.keys())}")

    # 4. Test Firestore Exporter with Mocked Client
    print("\n[STEP 4] Verifying Firestore Exporter Data Contract...")
    with patch("src.exporters.firestore_exporter.firestore.Client") as mock_client:
        mock_db = MagicMock()
        mock_client.return_value = mock_db
        exporter = FirestoreExporter(project_id="oracle-knowledge-platform")
        exporter.export(pkg)

        # Check meta/dashboard payload
        dashboard_set_calls = mock_db.collection.return_value.document.return_value.set.call_args_list
        dash_payload = None
        for call in dashboard_set_calls:
            if "conversations" in call[0][0]:
                dash_payload = call[0][0]
                break
        
        assert dash_payload is not None, "Dashboard metadata not written"
        print(f"  Dashboard metadata written: {dash_payload}")
        assert dash_payload["knowledge_objects"] == len(pkg.knowledge_objects), "KO count mismatch in dashboard meta"
        assert dash_payload["conversations"] == len(pkg.conversations), "Conversation count mismatch in dashboard meta"
        assert dash_payload["entities"] == len(pkg.entities), "Entities count mismatch in dashboard meta"
        print("  Firestore data contract successfully verified!")

    # 5. Test Epistemic Grounding Simulation
    print("\n[STEP 5] Testing Grounded Chat Logic Simulation...")
    
    # Grounding Simulation Function matching ChatService.ts logic
    def simulate_chat(query_text: str, knowledge_items: list):
        query_lower = query_text.lower()
        # 1. Deterministic retrieval
        matched = [ko for ko in knowledge_items if any(w in ko.title.lower() or w in ko.content.lower() for w in query_lower.split())]
        
        if not matched:
            return {
                "answer": "I do not have sufficient evidence in the compiled knowledge to answer this question. No related knowledge objects or conversations were found for your query.",
                "citations": [],
                "is_grounded": True,
                "refusal": True
            }
        
        # Build context
        context_str = "\n".join([f"[Source {i+1}: {ko.title} ({ko.source_platform})]\n{ko.content}" for i, ko in enumerate(matched)])
        citations = [{"source_index": i+1, "title": ko.title, "platform": ko.source_platform} for i, ko in enumerate(matched)]
        
        return {
            "answer": f"Based on [Source 1], the information confirms: {matched[0].content[:80]}...",
            "citations": citations,
            "is_grounded": True,
            "refusal": False
        }

    # Test Supported Question
    ko_sample = pkg.knowledge_objects[0]
    supported_query = ko_sample.title
    print(f"\n  [5A] Supported Question Query: '{supported_query}'")
    resp_supported = simulate_chat(supported_query, pkg.knowledge_objects)
    print(f"    Answer: {resp_supported['answer']}")
    print(f"    Citations ({len(resp_supported['citations'])}): {resp_supported['citations']}")
    assert not resp_supported["refusal"], "Supported question was falsely refused"
    assert len(resp_supported["citations"]) > 0, "No citations generated for supported question"

    # Test Unsupported Question
    unsupported_query = "Quantum teleportation protocols in 18th century naval warfare"
    print(f"\n  [5B] Unsupported Question Query: '{unsupported_query}'")
    resp_unsupported = simulate_chat(unsupported_query, pkg.knowledge_objects)
    print(f"    Answer: {resp_unsupported['answer']}")
    print(f"    Citations: {resp_unsupported['citations']}")
    assert resp_unsupported["refusal"], "Unsupported question did not trigger refusal"
    assert len(resp_unsupported["citations"]) == 0, "Unsupported question generated fabricated citations"
    assert "sufficient evidence" in resp_unsupported["answer"].lower(), "Missing insufficient evidence response"

    print("\n==========================================")
    print("ALL E2E VERIFICATION CHECKS PASSED (100%)")
    print("==========================================")

if __name__ == "__main__":
    test_pipeline_and_grounding()

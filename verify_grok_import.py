from src.services.import_service import ImportService
from src.models.knowledge_package import KnowledgePackage
import os

# Initialize
service = ImportService()

# Run import
test_file = os.path.abspath("input/grok-test.json")
result = service.run_grok_import(file_path=test_file)

print(f"Import result: {result}")

# Verify
package = service.get_package()
conversations = package.conversations

if len(conversations) == 1:
    conv = conversations[0]
    print(f"Conversation ID: {conv.id}")
    print(f"Title: {conv.title}")
    print(f"Provenance: {conv.provenance}")
    if conv.provenance.get("source_platform") == "Grok":
        print("Success! Provenance is correct.")
    else:
        print(f"Failure! Provenance is {conv.provenance.get('source_platform')}")
else:
    print(f"Failure! Expected 1 conversation, found {len(conversations)}")

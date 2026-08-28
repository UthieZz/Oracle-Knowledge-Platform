from src.exporters.firestore_exporter import FirestoreExporter
from src.models.knowledge_package import KnowledgePackage
from src.models.conversation import Conversation
from src.models.message import Message
from google.cloud import firestore

# Setup
exporter = FirestoreExporter(project_id="oracle-knowledge-platform")
package = KnowledgePackage()

# Dummy Data
TEST_CONV_ID = "test_conv_99999"
conv = Conversation(
    id=TEST_CONV_ID,
    title="Test Conversation for Verification",
    source="test_source",
    created="2026-08-16T12:00:00Z",
    updated="2026-08-16T12:00:00Z",
    messages=[
        Message(id="test_msg_1", role="user", content="hello test", timestamp="2026-08-16T12:00:00Z"),
        Message(id="test_msg_2", role="assistant", content="hi test", timestamp="2026-08-16T12:00:01Z")
    ],
    provenance={"source_platform": "Gemini"}
)
package.add_conversation(conv)

# Execute
print(f"Exporting conversation {TEST_CONV_ID}...")
exporter.export(package)
print("Export complete.")

# Verify
db = firestore.Client(project="oracle-knowledge-platform")
doc = db.collection("conversations").document(TEST_CONV_ID).get()

if doc.exists:
    print(f"Success! Found document {TEST_CONV_ID} in 'conversations'.")
    data = doc.to_dict()
    print(f"Document data: {data}")
else:
    print(f"Failure! Document {TEST_CONV_ID} not found in 'conversations'.")

from google.cloud import firestore

db = firestore.Client(project="oracle-knowledge-platform")

collections = [col.id for col in db.collections()]
print(f"Collections in Firestore: {collections}")

for col_id in ["conversations", "entities", "attachments"]:
    docs = list(db.collection(col_id).stream())
    print(f"Collection '{col_id}' has {len(docs)} documents.")

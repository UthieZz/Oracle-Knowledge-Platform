from src.services.import_service import ImportService
from src.exporters.firestore_exporter import FirestoreExporter
import os

# Define the dataset
files_to_import = [
    'uploads/MyActivity(2)-4f440db610fea3cc.json',
    'uploads/prod-grok-backend.json',
    'uploads/MyActivity(1)-081f794118b580a5.json',
    'uploads/conversations-006.json',
    'uploads/conversations-005.json',
    'uploads/MyActivity(3)-081f794118b580a5.json',
    'uploads/test_data.json',
    'uploads/conversations-001.json',
    'uploads/conversations-000.json',
    'uploads/conversations-004.json',
    'uploads/conversations-003.json',
    'uploads/conversations-002.json'
]

# Run compilation
import_service = ImportService()
for file_path in files_to_import:
    try:
        print(f"Importing {file_path}...")
        import_service.run_import_dispatcher(file_path)
    except Exception as e:
        print(f"Error importing {file_path}: {e}")

# Export
print("Exporting to Firestore...")
pkg = import_service.get_package()
exporter = FirestoreExporter(project_id="oracle-knowledge-platform")
exporter.export(pkg)
print("Export completed.")

"""Import local uploads and export to tenant/silo Firestore.

Requires:
  OKP_TENANT_ID
  OKP_SILO_ID
  GOOGLE_APPLICATION_CREDENTIALS (or ADC)
"""

import os
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from src.services.import_service import ImportService
from src.exporters.firestore_exporter import FirestoreExporter


def require_env(*keys: str) -> None:
    missing = [key for key in keys if not os.getenv(key)]
    if missing:
        raise SystemExit(
            "Missing required environment variables: "
            + ", ".join(missing)
            + ". Copy .env.example to .env and set OKP_TENANT_ID / OKP_SILO_ID."
        )


require_env("OKP_TENANT_ID", "OKP_SILO_ID")

files_to_import = [
    "uploads/MyActivity(2)-4f440db610fea3cc.json",
    "uploads/prod-grok-backend.json",
    "uploads/MyActivity(1)-081f794118b580a5.json",
    "uploads/conversations-006.json",
    "uploads/conversations-005.json",
    "uploads/MyActivity(3)-081f794118b580a5.json",
    "uploads/test_data.json",
    "uploads/conversations-001.json",
    "uploads/conversations-000.json",
    "uploads/conversations-004.json",
    "uploads/conversations-003.json",
    "uploads/conversations-002.json",
]

import_service = ImportService()
for file_path in files_to_import:
    if not os.path.exists(file_path):
        print(f"Skip missing {file_path}")
        continue
    try:
        print(f"Importing {file_path}...")
        import_service.run_import_dispatcher(file_path)
    except Exception as e:
        print(f"Error importing {file_path}: {e}")

print(
    f"Exporting to Firestore tenants/{os.environ['OKP_TENANT_ID']}/silos/{os.environ['OKP_SILO_ID']}..."
)
pkg = import_service.get_package()
exporter = FirestoreExporter(project_id=os.getenv("GOOGLE_CLOUD_PROJECT", "oracle-knowledge-platform"))
exporter.export(pkg)
print("Export completed.")

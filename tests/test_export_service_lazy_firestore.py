import os
import unittest
from unittest.mock import patch

from src.services.export_service import ExportService


class TestExportServiceLazyFirestore(unittest.TestCase):
    def test_portable_export_registers_without_tenant_env(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OKP_TENANT_ID", None)
            os.environ.pop("OKP_SILO_ID", None)
            service = ExportService()
            names = [item["name"] for item in service.get_available_exporters()]
            self.assertTrue(any("Multi" in n or "Source" in n for n in names) or names)
            self.assertFalse(any("Firestore" in n for n in names))

    def test_firestore_registers_when_tenant_set(self):
        with patch.dict(os.environ, {"OKP_TENANT_ID": "acme", "OKP_SILO_ID": "default"}):
            service = ExportService()
            names = [item["name"] for item in service.get_available_exporters()]
            self.assertTrue(any("Firestore" in n for n in names))


if __name__ == "__main__":
    unittest.main()

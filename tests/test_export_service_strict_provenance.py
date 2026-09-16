import os
import unittest
from unittest.mock import patch

from src.models.knowledge_object import KnowledgeObject
from src.models.knowledge_package import KnowledgePackage
from src.services.export_service import ExportService


def _orphan_package() -> KnowledgePackage:
    package = KnowledgePackage()
    package.add_knowledge_object(
        KnowledgeObject(
            id="orphan",
            title="orphan",
            content="x",
            source_platform="",
            source_file="",
            created_at=None,
            updated_at=None,
            provenance={},
            evidence=[],
        )
    )
    return package


class TestExportServiceStrictProvenance(unittest.TestCase):
    def test_portable_export_does_not_raise_on_incomplete_lineage(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OKP_TENANT_ID", None)
            os.environ.pop("OKP_SILO_ID", None)
            service = ExportService()
            result = service.export_knowledge(_orphan_package(), {"mode": "JSON", "output_dir": "/tmp/okp-audit"})
            self.assertEqual(result["strict_provenance"], False)
            self.assertTrue(result["provenance"]["failed"])

    def test_explicit_strict_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            service = ExportService()
            with self.assertRaises(ValueError):
                service.export_knowledge(
                    _orphan_package(),
                    {"mode": "JSON", "output_dir": "/tmp/okp-audit", "strict_provenance": True},
                )


if __name__ == "__main__":
    unittest.main()

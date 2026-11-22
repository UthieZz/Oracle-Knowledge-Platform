import os
from unittest.mock import MagicMock, patch
from src.services.export_service import ExportService
from src.models.knowledge_package import KnowledgePackage


def test_export_knowledge_forwards_strict_permissions_from_env():
    service = ExportService()
    mock_exporter = MagicMock()
    mock_exporter.name = "MockExporter"
    service.registry._exporters = {"MockExporter": mock_exporter}

    dummy_package = KnowledgePackage()

    with patch.dict(os.environ, {"OKP_STRICT_PERMISSIONS": "true"}, clear=False):
        result = service.export_knowledge(dummy_package)

    mock_exporter.export.assert_called_once()
    call_kwargs = mock_exporter.export.call_args.kwargs
    assert call_kwargs.get("strict_permissions") is True
    assert result["status"] == "Success"


def test_export_knowledge_pilot_default_when_env_unset():
    service = ExportService()
    mock_exporter = MagicMock()
    mock_exporter.name = "MockExporter"
    service.registry._exporters = {"MockExporter": mock_exporter}

    dummy_package = KnowledgePackage()

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OKP_STRICT_PERMISSIONS", None)
        result = service.export_knowledge(dummy_package)

    call_kwargs = mock_exporter.export.call_args.kwargs
    assert call_kwargs.get("strict_permissions") is False
    assert result["status"] == "Success"

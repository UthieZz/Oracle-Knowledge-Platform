import os
from unittest.mock import MagicMock, patch
from okc.adapters.compiler_adapter import CompilerAdapter
from okc.models.knowledge_package import KnowledgePackage

def test_execute_pipeline_forwards_strict_permissions_from_env():
    mock_importer = MagicMock()
    mock_analyzer = MagicMock()
    mock_compiler = MagicMock()
    mock_exporter = MagicMock()

    # Minimal package that survives the pipeline stubs
    dummy_package = KnowledgePackage(package_id="pkg-test", objects=[], metadata={})
    mock_importer.process.return_value = dummy_package
    mock_analyzer.run_all.return_value = dummy_package
    mock_compiler.compile.return_value = dummy_package

    adapter = CompilerAdapter(mock_importer, mock_analyzer, mock_compiler, mock_exporter)

    with patch.dict(os.environ, {"OKP_TENANT_ID": "t1", "OKP_SILO_ID": "s1", "OKP_STRICT_PERMISSIONS": "true"}):
        adapter.execute_pipeline("dummy.txt")

    mock_exporter.export.assert_called_once()
    call_kwargs = mock_exporter.export.call_args.kwargs
    assert call_kwargs.get("tenant_id") == "t1"
    assert call_kwargs.get("silo_id") == "s1"
    assert call_kwargs.get("strict_permissions") is True

def test_execute_pipeline_pilot_default_when_env_unset():
    mock_importer = MagicMock()
    mock_analyzer = MagicMock()
    mock_compiler = MagicMock()
    mock_exporter = MagicMock()

    dummy_package = KnowledgePackage(package_id="pkg-test", objects=[], metadata={})
    mock_importer.process.return_value = dummy_package
    mock_analyzer.run_all.return_value = dummy_package
    mock_compiler.compile.return_value = dummy_package

    adapter = CompilerAdapter(mock_importer, mock_analyzer, mock_compiler, mock_exporter)

    with patch.dict(os.environ, {"OKP_TENANT_ID": "t1", "OKP_SILO_ID": "s1"}, clear=False):
        # Ensure the key is absent
        os.environ.pop("OKP_STRICT_PERMISSIONS", None)
        adapter.execute_pipeline("dummy.txt")

    call_kwargs = mock_exporter.export.call_args.kwargs
    assert call_kwargs.get("strict_permissions") is False

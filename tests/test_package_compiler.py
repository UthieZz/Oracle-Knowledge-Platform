"""PackageCompiler owns process → enrich → validate over KnowledgePackage."""

import json
from pathlib import Path

import pytest

from okc.compiler.package_compiler import PackageCompileError, PackageCompiler
from okc.models.knowledge_package import KnowledgeObject, KnowledgePackage, Provenance


def test_compile_package_records_stages_and_entities():
    pkg = KnowledgePackage(
        package_id="p1",
        objects=[
            KnowledgeObject(
                object_id="o1",
                title="Notes",
                provenance=Provenance(
                    source_platform="chatgpt",
                    source_file="f.json",
                    tenant_id="t",
                    silo_id="s",
                ),
                content="Python and SQLite stay local.",
            )
        ],
    )
    result = PackageCompiler().compile_package(pkg)
    assert result.stages == ["process_attachments", "enrich", "validate"]
    assert "python" in result.package.objects[0].entities
    assert result.package.metadata["pipeline"]["compiler"] == "package_compiler"


def test_compile_file_imports_then_compiles(tmp_path: Path):
    payload = [
        {
            "id": "conv_1",
            "title": "Notes",
            "messages": [
                {"role": "user", "content": "Use Python with SQLite."},
            ],
        }
    ]
    path = tmp_path / "export.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    result = PackageCompiler().compile_file(
        str(path), tenant_id="tenant_a", silo_id="silo_1", source_platform="chatgpt"
    )
    assert result.stages[0] == "import"
    assert result.package.objects[0].provenance.tenant_id == "tenant_a"
    assert "python" in result.package.objects[0].entities


def test_validate_rejects_missing_provenance():
    pkg = KnowledgePackage(
        package_id="p1",
        objects=[
            KnowledgeObject(
                object_id="o1",
                title="Bad",
                provenance=Provenance(
                    source_platform="",
                    source_file="f.json",
                    tenant_id="t",
                    silo_id="s",
                ),
                content="x",
            )
        ],
    )
    with pytest.raises(PackageCompileError):
        PackageCompiler().compile_package(pkg)

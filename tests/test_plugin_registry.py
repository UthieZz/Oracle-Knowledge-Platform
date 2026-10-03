"""PluginRegistry and attachment-pass provenance enrichment."""

from pathlib import Path

import pytest

from okc.compiler.package_compiler import PackageCompileError, PackageCompiler
from okc.compiler.passes.attachment_processing_pass import AttachmentProcessingPass
from okc.compiler.processors.attachment_processor import TextParseProcessor
from okc.importers.text_importer import PlainTextImportError, PlainTextImporter
from okc.models.knowledge_package import KnowledgeObject, KnowledgePackage, Provenance
from okc.plugins.registry import (
    PluginRegistry,
    PluginRegistryError,
    default_attachment_registry,
    default_okc_registry,
)


def test_register_and_lookup_by_kind():
    reg = PluginRegistry()
    reg.register(object(), name="json", kind="importer", version="1.0.0")
    spec = reg.get("importer", "json")
    assert spec.kind == "importer"
    assert spec.version == "1.0.0"
    assert [s.name for s in reg.list("importer")] == ["json"]


def test_unknown_kind_rejected():
    reg = PluginRegistry()
    with pytest.raises(PluginRegistryError):
        reg.register(object(), name="x", kind="vector_index")  # type: ignore[arg-type]


def test_duplicate_registration_rejected_unless_replace():
    reg = PluginRegistry()
    reg.register(object(), name="json", kind="exporter")
    with pytest.raises(PluginRegistryError):
        reg.register(object(), name="json", kind="exporter")
    reg.register(object(), name="json", kind="exporter", replace=True)


def test_default_attachment_registry_resolves_extensions():
    reg = default_attachment_registry()
    assert reg.attachment_processor_for("a.PNG").name == "image_ocr"
    assert reg.attachment_processor_for("/tmp/notes.mp3").name == "audio_transcript"
    assert reg.attachment_processor_for("doc.pdf").name == "pdf_parse"
    assert reg.attachment_processor_for("readme.md").name == "text_parse"
    assert reg.attachment_processor_for("bin.xyz") is None


def test_attachment_pass_records_processor_and_hash(tmp_path: Path):
    path = tmp_path / "note.txt"
    path.write_text("tenant isolation matters", encoding="utf-8")
    prov = Provenance(
        source_platform="chatgpt",
        source_file="f.json",
        tenant_id="t",
        silo_id="s",
    )
    obj = KnowledgeObject(
        object_id="o1",
        title="T",
        provenance=prov,
        content="body",
        attachments=[{"file_path": str(path)}],
    )
    pkg = KnowledgePackage(package_id="p1", objects=[obj])
    pkg = AttachmentProcessingPass().execute(pkg)
    att = pkg.objects[0].attachments[0]
    assert att["status"] == "processed"
    assert "tenant isolation" in att["extracted_text"]
    assert att["processor"] == "text_parse"
    assert att["processor_version"] == TextParseProcessor.version
    assert att["transformation"] == "parse"
    assert len(att["content_hash"]) == 64
    assert att["provenance"]["tenant_id"] == "t"
    assert att["provenance"]["silo_id"] == "s"


def test_custom_processor_can_be_registered(tmp_path: Path):
    class Fake:
        transformation = "structured_extract"

        def process(self, file_path: str):
            return {
                "status": "processed",
                "extracted_text": "TABLE:1",
                "keywords": ["table"],
                "confidence": 0.7,
                "media_type": "structured",
                "engine": "fake",
            }

    reg = PluginRegistry()
    reg.register(
        Fake(),
        name="csv_table",
        kind="attachment_processor",
        version="0.1.0",
        extensions=(".csv",),
    )
    path = tmp_path / "rows.csv"
    path.write_text("a,b\n1,2\n", encoding="utf-8")
    prov = Provenance(
        source_platform="chatgpt",
        source_file="f.json",
        tenant_id="t",
        silo_id="s",
    )
    obj = KnowledgeObject(
        object_id="o1",
        title="T",
        provenance=prov,
        content="body",
        attachments=[{"file_path": str(path)}],
    )
    pkg = KnowledgePackage(package_id="p1", objects=[obj])
    pkg = AttachmentProcessingPass(registry=reg).execute(pkg)
    att = pkg.objects[0].attachments[0]
    assert att["processor"] == "csv_table"
    assert att["extracted_text"] == "TABLE:1"
    assert att["transformation"] == "structured_extract"


def test_default_okc_registry_contains_runtime_components():
    reg = default_okc_registry()

    assert reg.get("importer", "json_v2_importer").plugin.__class__.__name__ == "JsonToV2Importer"
    assert reg.get("importer", "plain_text_importer").plugin.__class__.__name__ == "PlainTextImporter"
    assert reg.importer_for("export.json").name == "json_v2_importer"
    assert reg.importer_for("notes.md").name == "plain_text_importer"
    assert reg.importer_for("scan.pdf") is None
    assert reg.get("analyzer", "entity_extractor").plugin.__class__.__name__ == "EntityExtractor"
    assert reg.get("compiler", "package_compiler").plugin.__class__.__name__ == "PackageCompiler"
    assert reg.get("exporter", "sqlite_exporter").plugin.__name__ == "SQLiteExporter"
    assert reg.get("context_provider", "context_gateway").plugin.__name__ == "ContextGateway"
    assert reg.get("attachment_processor", "text_parse").plugin.__class__.__name__ == "TextParseProcessor"


def _plugin_module(plugin):
    return getattr(plugin, "__module__", plugin.__class__.__module__)


def test_default_okc_registry_does_not_register_legacy_src_components():
    reg = default_okc_registry()
    # Classes and instances both expose their defining module on __module__.
    # Using plugin.__class__.__module__ is wrong for registered classes
    # (SQLiteExporter, ContextGateway) because that is builtins.type.
    assert all(_plugin_module(spec.plugin).startswith("okc.") for spec in reg.list())
    compilers = [spec for spec in reg.list() if spec.kind == "compiler"]
    assert [spec.name for spec in compilers] == ["package_compiler"]
    assert _plugin_module(compilers[0].plugin) == "okc.compiler.package_compiler"


def _package():
    prov = Provenance(
        source_platform="chatgpt",
        source_file="f.json",
        tenant_id="t",
        silo_id="s",
    )
    return KnowledgePackage(
        package_id="p1",
        metadata={"source": "kept"},
        objects=[
            KnowledgeObject(object_id="o1", title="T", provenance=prov, content="body"),
        ],
    )


def test_package_compiler_stamps_without_rewriting_content():
    package = _package()
    compiled = PackageCompiler().compile(package)
    assert compiled.objects[0].content == "body"
    assert compiled.metadata["source"] == "kept"
    stamp = compiled.metadata["compilation"]
    assert stamp["compiler"] == "package_compiler"
    assert stamp["status"] == "validated"
    assert stamp["object_count"] == 1
    assert package.metadata.get("compilation") is None


def test_package_compiler_rejects_mixed_silo():
    package = _package()
    other = package.objects[0].model_copy(deep=True)
    other.object_id = "o2"
    other.provenance.silo_id = "other"
    package.objects.append(other)
    with pytest.raises(PackageCompileError):
        PackageCompiler().compile(package)


def test_plain_text_importer_preserves_source_and_provenance(tmp_path: Path):
    path = tmp_path / "decision.md"
    path.write_text("# Keep provenance\n\nSource text stays source text.\n", encoding="utf-8")
    package = PlainTextImporter().process(str(path), tenant_id="acme", silo_id="default")
    obj = package.objects[0]
    assert obj.title == "Keep provenance"
    assert obj.content.startswith("# Keep provenance")
    assert obj.provenance.source_platform == "local_file"
    assert obj.provenance.source_file == str(path)
    assert obj.provenance.tenant_id == "acme"
    assert obj.provenance.silo_id == "default"
    assert obj.evidence[0].role == "source"
    assert obj.evidence[0].content == obj.content
    assert package.metadata["importer"] == "plain_text_importer"
    assert package.metadata["transformation"] == "import_plain_text"
    compiled = PackageCompiler().compile(package)
    assert compiled.objects[0].content == obj.content
    assert compiled.metadata["compilation"]["status"] == "validated"


def test_plain_text_importer_rejects_empty_and_non_utf8(tmp_path: Path):
    empty = tmp_path / "empty.txt"
    empty.write_text("   \n", encoding="utf-8")
    with pytest.raises(PlainTextImportError):
        PlainTextImporter().process(str(empty), tenant_id="acme", silo_id="default")
    binary = tmp_path / "bad.txt"
    binary.write_bytes(b"\xff\xfe not utf-8")
    with pytest.raises(PlainTextImportError):
        PlainTextImporter().process(str(binary), tenant_id="acme", silo_id="default")


def test_importer_extension_conflict_is_rejected():
    reg = PluginRegistry()
    reg.register(object(), name="a", kind="importer", extensions=(".txt",))
    with pytest.raises(PluginRegistryError):
        reg.register(object(), name="b", kind="importer", extensions=(".txt",))

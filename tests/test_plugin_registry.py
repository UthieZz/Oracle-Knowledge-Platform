"""PluginRegistry and attachment-pass provenance enrichment."""

from pathlib import Path

import pytest

from okc.compiler.package_compiler import PackageCompileError, PackageCompiler
from okc.compiler.passes.attachment_processing_pass import AttachmentProcessingPass
import hashlib

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
    assert reg.attachment_processor_for("book.xlsx").name == "office_container"
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
    assert att["source_hash"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert att["source_size"] == path.stat().st_size
    assert att["provenance"]["tenant_id"] == "t"
    assert att["provenance"]["silo_id"] == "s"
    lineage = att["provenance"]["attachment_lineage"]
    assert lineage["processor"] == "text_parse"
    assert lineage["source_hash"] == att["source_hash"]
    assert lineage["content_hash"] == att["content_hash"]
    assert lineage["transformation"] == "parse"


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
                "structured_extraction": {"format": "table", "row_count": 1},
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
    assert att["structured_extraction"] == {"format": "table", "row_count": 1}
    assert att["source_hash"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_csv_structured_extraction_stays_on_attachment(tmp_path: Path):
    path = tmp_path / "rows.csv"
    path.write_text("name,qty\nalpha,2\nbeta,3\n", encoding="utf-8")
    prov = Provenance(
        source_platform="local_file",
        source_file="rows.csv",
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
    assert att["processor"] == "text_parse"
    assert att["media_type"] == "structured"
    assert att["structured_extraction"] == {
        "format": "csv",
        "headers": ["name", "qty"],
        "row_count": 2,
        "column_count": 2,
    }
    assert pkg.objects[0].content == "body"
    assert len(pkg.objects) == 1
    assert att["structured_extraction_hash"] == lineage_hash(att["structured_extraction"])
    assert att["provenance"]["attachment_lineage"]["structured_extraction_hash"] == att["structured_extraction_hash"]


def test_pdf_structured_extraction_stays_on_attachment(tmp_path: Path):
    path = tmp_path / "note.pdf"
    path.write_bytes(b"%PDF-1.1\nnot a parseable pdf")
    prov = Provenance(
        source_platform="local_file",
        source_file="note.pdf",
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
    assert att["processor"] == "pdf_parse"
    assert att["media_type"] == "pdf"
    assert att["structured_extraction"]["format"] == "pdf"
    assert att["structured_extraction"]["engine"] in {"stub", "pypdf"}
    assert "page_count" in att["structured_extraction"]
    assert att["structured_extraction_hash"]
    assert att["provenance"]["attachment_lineage"]["structured_extraction_hash"] == att["structured_extraction_hash"]
    assert "headings" not in att["structured_extraction"]
    assert pkg.objects[0].content == "body"
    assert len(pkg.objects) == 1


def test_image_structured_extraction_stays_on_attachment(tmp_path: Path):
    path = tmp_path / "pixel.png"
    try:
        from PIL import Image

        Image.new("RGB", (2, 3), color=(1, 2, 3)).save(path)
    except Exception:
        path.write_bytes(b"\x89PNG\r\nnot a parseable image")
    prov = Provenance(
        source_platform="local_file",
        source_file="pixel.png",
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
    structure = att["structured_extraction"]
    assert att["processor"] == "image_ocr"
    assert att["media_type"] == "image"
    assert structure["format"] == "image"
    assert structure["engine"] in {"stub", "pytesseract"}
    assert structure["image_parser"] in {"stub", "pillow"}
    assert "width" in structure and "height" in structure
    assert att["structured_extraction_hash"]
    assert att["provenance"]["attachment_lineage"]["structured_extraction_hash"] == att["structured_extraction_hash"]
    assert "labels" not in structure
    assert "claims" not in structure
    assert pkg.objects[0].content == "body"
    assert len(pkg.objects) == 1
    if structure["image_parser"] == "pillow":
        assert structure["width"] == 2
        assert structure["height"] == 3
        assert structure["mode"] == "RGB"
        assert att["metadata"]["width"] == 2


def test_audio_structured_extraction_stays_on_attachment(tmp_path: Path):
    path = tmp_path / "clip.mp3"
    path.write_bytes(b"ID3not-a-real-frame")
    prov = Provenance(
        source_platform="local_file",
        source_file="clip.mp3",
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
    structure = att["structured_extraction"]
    assert att["processor"] == "audio_transcript"
    assert att["processor_version"] == "1.1.0"
    assert att["transformation"] == "transcribe"
    assert att["media_type"] == "audio"
    assert att["engine"] == "stub"
    assert structure == {
        "format": "audio",
        "engine": "stub",
        "container": "mp3",
        "byte_size": path.stat().st_size,
        "transcript_state": "pending",
    }
    assert att["metadata"]["transcript_state"] == "pending"
    assert att["source_hash"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert att["source_size"] == path.stat().st_size
    assert att["structured_extraction_hash"] == lineage_hash(structure)
    assert att["provenance"]["attachment_lineage"]["structured_extraction_hash"] == att["structured_extraction_hash"]
    assert att["provenance"]["tenant_id"] == "t"
    assert att["provenance"]["silo_id"] == "s"
    assert "duration" not in structure
    assert "language" not in structure
    assert "transcript" not in structure
    assert pkg.objects[0].content == "body"
    assert len(pkg.objects) == 1


def _minimal_ooxml(path: Path, parts: dict) -> None:
    import zipfile

    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        for name, payload in parts.items():
            zf.writestr(name, payload)


def test_office_structured_extraction_stays_on_attachment(tmp_path: Path):
    path = tmp_path / "book.xlsx"
    workbook = (
        '<?xml version="1.0"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheets><sheet name="Facts" sheetId="1"/>'
        '<sheet name="Sources" sheetId="2"/></sheets></workbook>'
    )
    _minimal_ooxml(path, {"xl/workbook.xml": workbook})
    prov = Provenance(
        source_platform="local_file",
        source_file="book.xlsx",
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
    structure = att["structured_extraction"]
    assert att["processor"] == "office_container"
    assert att["processor_version"] == "1.0.0"
    assert att["transformation"] == "structured_extract"
    assert att["media_type"] == "office"
    assert att["engine"] == "zip_container"
    assert structure["format"] == "office"
    assert structure["container"] == "xlsx"
    assert structure["parser_state"] == "parsed"
    assert structure["sheet_names"] == ["Facts", "Sources"]
    assert structure["sheet_count"] == 2
    assert structure["has_content_types"] is True
    assert "cell_values" not in structure
    assert "claims" not in structure
    assert att["source_hash"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert att["structured_extraction_hash"] == lineage_hash(structure)
    assert att["provenance"]["tenant_id"] == "t"
    assert att["provenance"]["silo_id"] == "s"
    assert pkg.objects[0].content == "body"
    assert len(pkg.objects) == 1

    broken = tmp_path / "notes.docx"
    broken.write_bytes(b"not-a-zip")
    obj.attachments = [{"file_path": str(broken)}]
    pkg = AttachmentProcessingPass().execute(pkg)
    bad = pkg.objects[0].attachments[0]
    assert bad["structured_extraction"]["parser_state"] == "unavailable"
    assert bad["structured_extraction"]["engine"] == "stub"
    assert "sheet_names" not in bad["structured_extraction"]
    assert pkg.objects[0].content == "body"


def test_pptx_slide_count_does_not_extract_narrative(tmp_path: Path):
    path = tmp_path / "deck.pptx"
    _minimal_ooxml(
        path,
        {
            "ppt/slides/slide1.xml": "<p:sld>secret narrative</p:sld>",
            "ppt/slides/slide2.xml": "<p:sld/>",
        },
    )
    prov = Provenance(
        source_platform="local_file",
        source_file="deck.pptx",
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
    structure = att["structured_extraction"]
    assert structure["slide_count"] == 2
    assert "secret narrative" not in att["extracted_text"]
    assert "narrative" not in structure
    assert len(pkg.objects) == 1


def lineage_hash(value):
    import json
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


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

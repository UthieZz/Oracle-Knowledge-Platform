"""Plugin registry for OKC v2.

This is a discovery/dispatch table, not an IR. Registered plugins operate on
KnowledgePackage or attachments; they do not replace KnowledgePackage.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Literal, Optional

PluginKind = Literal[
    "importer",
    "processor",
    "analyzer",
    "attachment_processor",
    "compiler",
    "exporter",
    "context_provider",
]

VALID_KINDS = frozenset(
    {
        "importer",
        "processor",
        "analyzer",
        "attachment_processor",
        "compiler",
        "exporter",
        "context_provider",
    }
)


@dataclass(frozen=True)
class PluginSpec:
    name: str
    kind: str
    version: str
    plugin: Any
    extensions: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""


class PluginRegistryError(ValueError):
    """Invalid registration or lookup."""


class PluginRegistry:
    """Register importers, processors, compilers, exporters, context providers."""

    def __init__(self) -> None:
        self._by_name: Dict[tuple[str, str], PluginSpec] = {}
        self._by_extension: Dict[str, PluginSpec] = {}

    def register(
        self,
        plugin: Any,
        *,
        name: str,
        kind: PluginKind,
        version: str = "1.0.0",
        extensions: Optional[Iterable[str]] = None,
        description: str = "",
        replace: bool = False,
    ) -> PluginSpec:
        if kind not in VALID_KINDS:
            raise PluginRegistryError(f"Unknown plugin kind: {kind}")
        if not name:
            raise PluginRegistryError("Plugin name is required.")
        key = (kind, name)
        if key in self._by_name and not replace:
            raise PluginRegistryError(f"Plugin already registered: {kind}/{name}")
        ext_tuple = tuple(self._normalize_ext(e) for e in (extensions or ()))
        spec = PluginSpec(
            name=name,
            kind=kind,
            version=version,
            plugin=plugin,
            extensions=ext_tuple,
            description=description,
        )
        self._by_name[key] = spec
        if kind == "attachment_processor":
            for ext in ext_tuple:
                self._by_extension[ext] = spec
        return spec

    def get(self, kind: PluginKind, name: str) -> PluginSpec:
        try:
            return self._by_name[(kind, name)]
        except KeyError as exc:
            raise PluginRegistryError(f"No plugin registered: {kind}/{name}") from exc

    def list(self, kind: Optional[PluginKind] = None) -> List[PluginSpec]:
        specs = list(self._by_name.values())
        if kind is not None:
            specs = [s for s in specs if s.kind == kind]
        return sorted(specs, key=lambda s: (s.kind, s.name))

    def attachment_processor_for(self, file_path: str) -> Optional[PluginSpec]:
        ext = ""
        if "." in file_path:
            ext = self._normalize_ext(file_path.rsplit(".", 1)[-1])
        return self._by_extension.get(ext)

    @staticmethod
    def _normalize_ext(ext: str) -> str:
        e = (ext or "").strip().lower()
        if not e:
            return ""
        return e if e.startswith(".") else f".{e}"


def default_attachment_registry(
    factory: Optional[Callable[[], PluginRegistry]] = None,
) -> PluginRegistry:
    """Build a registry preloaded with built-in attachment processors."""
    from okc.compiler.processors.attachment_processor import (
        AudioTranscriptProcessor,
        ImageOCRProcessor,
        PDFProcessor,
        TextParseProcessor,
    )

    registry = factory() if factory else PluginRegistry()
    registry.register(
        ImageOCRProcessor(),
        name="image_ocr",
        kind="attachment_processor",
        version=ImageOCRProcessor.version,
        extensions=(".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"),
        description="OCR / image text extraction",
    )
    registry.register(
        AudioTranscriptProcessor(),
        name="audio_transcript",
        kind="attachment_processor",
        version=AudioTranscriptProcessor.version,
        extensions=(".mp3", ".wav", ".m4a", ".ogg", ".flac"),
        description="Audio transcription",
    )
    registry.register(
        PDFProcessor(),
        name="pdf_parse",
        kind="attachment_processor",
        version=PDFProcessor.version,
        extensions=(".pdf",),
        description="PDF text extraction",
    )
    registry.register(
        TextParseProcessor(),
        name="text_parse",
        kind="attachment_processor",
        version=TextParseProcessor.version,
        extensions=(".txt", ".md", ".csv", ".json", ".xml", ".html"),
        description="Plain/structured text parse",
    )
    return registry


def default_okc_registry() -> PluginRegistry:
    """Build the runtime registry from concrete OKC components only.

    This intentionally does not import the legacy src/ plugin tree. The
    registry describes components that actually exist in the okc runtime.
    """
    from okc.agent.context_gateway import ContextGateway
    from okc.analyzers.entity_extractor import EntityExtractor
    from okc.compiler.package_compiler import PackageCompiler
    from okc.compiler.passes.attachment_processing_pass import AttachmentProcessingPass
    from okc.exporters.sqlite_exporter import SQLiteExporter
    from okc.importers.json_importer import JsonToV2Importer

    registry = default_attachment_registry()
    registry.register(
        JsonToV2Importer(),
        name="json_v2_importer",
        kind="importer",
        version="2.0.0",
        extensions=(".json",),
        description="Deterministic ChatGPT/Grok JSON to KnowledgePackage v2 importer",
    )
    registry.register(
        EntityExtractor(),
        name="entity_extractor",
        kind="analyzer",
        version="1.0.0",
        description="Deterministic entity extraction over KnowledgePackage objects",
    )
    registry.register(
        AttachmentProcessingPass,
        name="attachment_processing_pass",
        kind="processor",
        version="1.0.0",
        description="Dispatch attachments through registered attachment processors",
    )
    registry.register(
        PackageCompiler,
        name="package_compiler",
        kind="compiler",
        version=PackageCompiler.version,
        description="Deterministic KnowledgePackage compile: process → enrich → validate",
    )
    registry.register(
        SQLiteExporter,
        name="sqlite_exporter",
        kind="exporter",
        version="1.0.0",
        description="Local SQLite persistence for KnowledgePackage objects",
    )
    # ContextGateway requires a retriever at construction time, so the class is
    # registered as the context-provider factory rather than as a fake instance.
    registry.register(
        ContextGateway,
        name="context_gateway",
        kind="context_provider",
        version="1.0.0",
        description="Governed KnowledgePackage -> AgentContextPackage boundary",
    )
    return registry

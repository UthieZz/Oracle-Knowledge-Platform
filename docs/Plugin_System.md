# OKC Plugin System

Status: implemented in `okc/plugins` (2026-09-28). Not a second IR.

## Role

`PluginRegistry` is a discovery and dispatch table for:

- importer
- processor
- analyzer
- attachment_processor
- compiler
- exporter
- context_provider

Plugins transform or publish `KnowledgePackage`. They do not replace it.

`src/services/plugin_service.py` remains a Studio-facing stub list. Do not treat it as the compiler registry.

## Attachment processors

`AttachmentProcessingPass` resolves processors through `PluginRegistry`.

Each processed attachment record receives:

- status, extracted_text, keywords, confidence, media_type, engine
- processor name and version
- transformation (`ocr`, `transcribe`, `parse`, `structured_extract`, or custom)
- SHA-256 `content_hash` of extracted text
- SHA-256 `source_hash` of the source file bytes (empty if unreadable) and `source_size`
- provenance copied from the parent KnowledgeObject, plus `attachment_lineage` (processor, version, transformation, both hashes, engine)
- `structured_extraction` and `metadata` when the processor returns them
- SHA-256 `structured_extraction_hash` when structured extraction is present, also copied into `attachment_lineage`

Extracted attachment text and structured extraction stay on the attachment record. Promotion into a KnowledgeObject requires a later compilation/validation contract. CSV text attachments receive a deterministic header/row summary in `structured_extraction`; that summary is not a knowledge object. PDF attachments receive `format`, `engine`, `page_count`, and `page_char_counts` only. Page count is null when the parser is unavailable. Image attachments receive `format`, `engine`, `image_parser`, `width`, `height`, `mode`, and `image_format` only. Dimensions are null when Pillow cannot open the file. Audio attachments receive `format`, `engine`, `container`, `byte_size`, and `transcript_state` only. Transcript state stays `pending` until a local STT backend is configured; duration, language, and transcript claims are not invented. No headings, labels, or claims are invented.

## Extension

```python
from okc.plugins import PluginRegistry
from okc.compiler.passes.attachment_processing_pass import AttachmentProcessingPass

registry = PluginRegistry()
registry.register(
    my_processor,
    name="docx_parse",
    kind="attachment_processor",
    version="1.0.0",
    extensions=(".docx",),
)
AttachmentProcessingPass(registry=registry).execute(package)
```

Built-in attachment processors are loaded by `default_attachment_registry()`.


## Runtime registry

`default_okc_registry()` registers the concrete components that are actually implemented in the `okc/` runtime:

- `json_v2_importer` — importer (`.json`)
- `plain_text_importer` — importer (`.txt`, `.md`)
- `entity_extractor` — analyzer
- `package_compiler` — compiler
- `sqlite_exporter` — exporter
- `context_gateway` — context provider factory/class
- all built-in attachment processors

The registry is used by the local compiler driver and local API pipeline for runtime construction. The legacy `src/` plugin registry is not imported.

`package_compiler` validates object identity, required provenance fields, and single tenant/silo membership, then stamps `package.metadata["compilation"]`. It does not create objects, rewrite content, or promote memory candidates or attachment text.

The local API resolves an importer by extension via `PluginRegistry.importer_for`. It does not send PDF, image, or audio uploads through `json_v2_importer`. Those media types remain attachment processors. A source file of that type is not a KnowledgePackage until an explicit attachment-as-source import contract exists.

`plain_text_importer` copies UTF-8 source text into one KnowledgeObject with `source_platform=local_file`, source file path, content hash, and a `source` evidence span. That is source import, not inference promotion.

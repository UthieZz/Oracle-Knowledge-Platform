# OKC Plugin System

Status: implemented in `okc/plugins` (2026-09-28). Not a second IR.

## Role

`PluginRegistry` is a discovery and dispatch table for:

- importer
- processor
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
- transformation (`ocr`, `transcribe`, `parse`, or custom)
- SHA-256 `content_hash` of extracted text
- provenance copied from the parent KnowledgeObject (tenant/silo/source)

Extracted attachment text stays on the attachment record. Promotion into a KnowledgeObject requires a later compilation/validation contract.

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

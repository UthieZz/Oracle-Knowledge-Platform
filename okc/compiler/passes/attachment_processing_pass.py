import logging
from typing import Any, Dict, Optional

from okc.models.knowledge_package import KnowledgePackage
from okc.compiler.processors.attachment_processor import (
    content_hash,
    source_file_hash,
    source_file_size,
    structured_extraction_hash,
)
from okc.plugins.registry import PluginRegistry, default_attachment_registry

logger = logging.getLogger(__name__)


class AttachmentProcessingPass:
    """
    Compiler pass that dispatches attachments to specialized processors and enriches
    attachment records with extracted text, hashes, processor identity, and provenance.

    Extracted attachment content stays on the attachment record. It is not promoted
    to a KnowledgeObject by this pass.
    """

    def __init__(self, registry: Optional[PluginRegistry] = None):
        self.registry = registry or default_attachment_registry()

    def execute(self, package: KnowledgePackage) -> KnowledgePackage:
        logger.info("Executing AttachmentProcessingPass across KnowledgeObjects...")

        for obj in package.objects:
            updated_attachments = []
            for attachment in obj.attachments:
                file_path = attachment.get("file_path") or attachment.get("url") or ""
                spec = self.registry.attachment_processor_for(file_path) if file_path else None

                if spec is None:
                    attachment["status"] = "unsupported_format"
                    attachment.setdefault("provenance", obj.provenance.model_dump())
                    updated_attachments.append(attachment)
                    continue

                processor = spec.plugin
                result: Dict[str, Any] = processor.process(file_path)
                extracted = result.get("extracted_text", "") or ""
                source_hash = source_file_hash(file_path)
                extracted_hash = content_hash(extracted)
                provenance = obj.provenance.model_dump()
                provenance["attachment_lineage"] = {
                    "processor": spec.name,
                    "processor_version": spec.version,
                    "transformation": getattr(processor, "transformation", spec.kind),
                    "source_hash": source_hash,
                    "content_hash": extracted_hash,
                    "engine": result.get("engine"),
                }
                attachment.update({
                    "status": result.get("status", "processed"),
                    "extracted_text": extracted,
                    "keywords": result.get("keywords", []),
                    "confidence": result.get("confidence", 0.0),
                    "media_type": result.get("media_type"),
                    "engine": result.get("engine"),
                    "processor": spec.name,
                    "processor_version": spec.version,
                    "transformation": getattr(processor, "transformation", spec.kind),
                    "content_hash": extracted_hash,
                    "source_hash": source_hash,
                    "source_size": source_file_size(file_path),
                    "provenance": provenance,
                })
                if "error" in result:
                    attachment["error"] = result["error"]
                if "structured_extraction" in result:
                    attachment["structured_extraction"] = result["structured_extraction"]
                    structure_hash = structured_extraction_hash(result["structured_extraction"])
                    attachment["structured_extraction_hash"] = structure_hash
                    provenance["attachment_lineage"]["structured_extraction_hash"] = structure_hash
                if "metadata" in result:
                    attachment["metadata"] = result["metadata"]
                updated_attachments.append(attachment)

            obj.attachments = updated_attachments

        return package

from typing import Any, Dict, List, Optional
from src.compiler.cache.attachment_cache import AttachmentCache
from src.compiler.processors.audio_processor import AudioProcessor
from src.compiler.processors.image_processor import ImageProcessor
from src.compiler.processors.pdf_processor import PdfProcessor
from src.compiler.processors.processor_registry import (
    AttachmentProcessorRegistry,
    AttachmentTask,
)
from src.core.interfaces import Analyzer
from src.models.attachment_knowledge import AttachmentKnowledge
from src.models.knowledge_package import KnowledgePackage


class AttachmentProcessingPass(Analyzer):
    """Compiler pass that transforms conversation attachments into AttachmentKnowledge.

    Executes immediately after the Import Pass and before the Discovery Pass.
    Orchestrates registered processors and utilizes an AttachmentCache for
    independent processability, cacheability, and resumability.
    """

    @property
    def name(self) -> str:
        return "Attachment Processing Pass"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def author(self) -> str:
        return "OKC Core Team"

    @property
    def description(self) -> str:
        return "Converts image, audio, and PDF attachments into structured AttachmentKnowledge records."

    @property
    def plugin_type(self) -> str:
        return "analyzer"

    @property
    def supported_inputs(self) -> List[str]:
        return ["okc/package"]

    @property
    def supported_outputs(self) -> List[str]:
        return ["okc/package"]

    def __init__(
        self,
        registry: Optional[AttachmentProcessorRegistry] = None,
        cache: Optional[AttachmentCache] = None,
    ):
        self.cache = cache or AttachmentCache()
        if registry is not None:
            self.registry = registry
        else:
            self.registry = AttachmentProcessorRegistry()
            self.registry.register(ImageProcessor())
            self.registry.register(AudioProcessor())
            self.registry.register(PdfProcessor())

    def analyze(self, package: KnowledgePackage) -> KnowledgePackage:
        """Execute the pass on the provided KnowledgePackage."""
        return self.process_pass(package)

    def process_pass(self, package: KnowledgePackage) -> KnowledgePackage:
        """Iterate conversations and messages to discover and process attachments."""
        processed_count = 0
        cache_hits = 0

        for conv in package.conversations:
            conv_id = getattr(conv, "id", "unknown_conv")

            # 1. Process conversation-level attachments in provenance
            conv_provenance = getattr(conv, "provenance", {}) or {}
            attachments = conv_provenance.get("attachments", [])

            for idx, att_item in enumerate(attachments):
                task = self._build_task(
                    att_item=att_item,
                    conv_id=conv_id,
                    msg_id=None,
                    index=idx,
                    conv_provenance=conv_provenance,
                )
                knowledge, from_cache = self._process_task(task)
                if knowledge:
                    package.add_attachment_knowledge(knowledge)
                    processed_count += 1
                    if from_cache:
                        cache_hits += 1

            # 2. Process message-level attachments
            for msg in getattr(conv, "messages", []):
                msg_id = getattr(msg, "id", None)
                msg_meta = getattr(msg, "metadata", {}) or {}
                msg_attachments = msg_meta.get("attachments", [])

                for idx, att_item in enumerate(msg_attachments):
                    task = self._build_task(
                        att_item=att_item,
                        conv_id=conv_id,
                        msg_id=msg_id,
                        index=idx,
                        conv_provenance=conv_provenance,
                    )
                    knowledge, from_cache = self._process_task(task)
                    if knowledge:
                        package.add_attachment_knowledge(knowledge)
                        processed_count += 1
                        if from_cache:
                            cache_hits += 1

        package.update_metadata("attachment_processing", {
            "processed_count": processed_count,
            "cache_hits": cache_hits,
            "total_in_package": len(package.attachment_knowledge),
        })

        return package

    def _build_task(
        self,
        att_item: Any,
        conv_id: str,
        msg_id: Optional[str],
        index: int,
        conv_provenance: Dict[str, Any],
    ) -> AttachmentTask:
        """Construct a self-contained AttachmentTask from raw attachment data."""
        if isinstance(att_item, dict):
            file_name = att_item.get("name") or att_item.get("file_name") or f"attachment_{index}"
            att_id = att_item.get("id") or att_item.get("url") or f"{conv_id}_att_{index}"
            file_path_or_url = att_item.get("url") or att_item.get("path") or file_name
            media_type = att_item.get("media_type") or "unknown"
            fingerprint = att_item.get("fingerprint")
        else:
            file_name = str(att_item)
            att_id = f"{conv_id}_att_{index}"
            file_path_or_url = file_name
            media_type = "unknown"
            fingerprint = None

        provenance = {
            "source_platform": conv_provenance.get("source_platform", "Unknown"),
            "source_file": conv_provenance.get("source_file", ""),
            "imported_at": conv_provenance.get("imported_at", ""),
            "raw_attachment": att_item,
        }

        return AttachmentTask(
            attachment_id=att_id,
            conversation_id=conv_id,
            message_id=msg_id,
            file_name=file_name,
            file_path_or_url=file_path_or_url,
            media_type=media_type,
            fingerprint=fingerprint,
            provenance=provenance,
        )

    def _process_task(self, task: AttachmentTask) -> tuple[Optional[AttachmentKnowledge], bool]:
        """Lookup processor, check cache, execute processor, and update cache."""
        processor = self.registry.find_processor(task.file_name, task.media_type)
        if not processor:
            # Unsupported media type - generate deterministic placeholder record
            placeholder = AttachmentKnowledge(
                attachment_id=task.attachment_id,
                conversation_id=task.conversation_id,
                message_id=task.message_id,
                file_name=task.file_name,
                media_type="unknown",
                fingerprint=task.fingerprint,
                processor_name="UnsupportedMediaProcessor",
                processor_version="1.0.0",
                raw_extraction="",
                summary=f"Unsupported attachment format for {task.file_name}",
                confidence=0.0,
                provenance=task.provenance,
            )
            return placeholder, False

        # Check Cache
        cached_item = self.cache.get(task.fingerprint, processor.name, processor.version)
        if cached_item:
            return cached_item, True

        # Process uncached task
        knowledge = processor.process(task)
        self.cache.put(knowledge)
        return knowledge, False

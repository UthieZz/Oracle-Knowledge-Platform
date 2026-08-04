import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Set
from collections import defaultdict

from src.core.interfaces import Exporter
from src.models.knowledge_package import KnowledgePackage


class MultiSourceExporter(Exporter):
    """Generic exporter that supports Unified, Separate by Source, or Both modes.

    Writes per-platform output packages under output/Platforms/{Platform}/ and
    a unified package under output/unified/. Every platform directory contains:
      - INDEX.md
      - platform.json
      - manifest.json
      - knowledge_objects/
      - sources_archive/
    """

    @property
    def name(self) -> str:
        return "Multi-Source Exporter"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def author(self) -> str:
        return "OKC Core Team"

    @property
    def description(self) -> str:
        return "Exports unified and per-platform knowledge packages with manifests."

    @property
    def plugin_type(self) -> str:
        return "exporter"

    @property
    def supported_inputs(self) -> List[str]:
        return ["okc/package"]

    @property
    def supported_outputs(self) -> List[str]:
        return ["markdown", "json", "okc/platform_package"]

    def __init__(self, output_dir: str = "output", mode: str = "Both"):
        self.output_dir = output_dir
        self.mode = self._normalize_mode(mode)

    @staticmethod
    def _normalize_mode(mode: str) -> str:
        clean = (mode or "Both").strip().lower()
        if "unified" in clean and "source" not in clean and "both" not in clean:
            return "Unified"
        elif "separate" in clean or "source" in clean:
            return "Separate by Source"
        return "Both"

    def export(self, package: KnowledgePackage) -> KnowledgePackage:
        """Execute export based on configured mode."""
        os.makedirs(self.output_dir, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat()

        # Group data by platform dynamically
        platform_map = self._group_by_platform(package)

        # 1. Export Unified if mode is Unified or Both
        if self.mode in ("Unified", "Both"):
            unified_dir = os.path.join(self.output_dir, "unified")
            self._export_package_unit(
                target_dir=unified_dir,
                package_title="Unified Knowledge Base",
                conversations=package.conversations,
                package=package,
                platform_name="Unified",
                is_unified=True,
            )
            # Root output directory fallback for backwards compatibility
            self._export_package_unit(
                target_dir=self.output_dir,
                package_title="Unified Knowledge Base",
                conversations=package.conversations,
                package=package,
                platform_name="Unified",
                is_unified=True,
                skip_platform_json=True,
            )

        # 2. Export Separate by Source if mode is Separate by Source or Both
        if self.mode in ("Separate by Source", "Both"):
            platforms_dir = os.path.join(self.output_dir, "Platforms")
            os.makedirs(platforms_dir, exist_ok=True)

            for platform_name, convs in platform_map.items():
                plat_dir = os.path.join(platforms_dir, self._sanitize_name(platform_name))
                self._export_package_unit(
                    target_dir=plat_dir,
                    package_title=f"{platform_name} Knowledge Package",
                    conversations=convs,
                    package=package,
                    platform_name=platform_name,
                    is_unified=False,
                )

        # 3. Generate Top-Level Root Manifest
        self._write_root_manifest(package, platform_map, timestamp)

        return package

    def _group_by_platform(self, package: KnowledgePackage) -> Dict[str, List[Any]]:
        """Group conversations by their provenance source_platform."""
        groups: Dict[str, List[Any]] = defaultdict(list)
        for conv in package.conversations:
            provenance = getattr(conv, "provenance", {}) or {}
            platform = provenance.get("source_platform") or self._derive_platform_from_source(getattr(conv, "source", ""))
            groups[platform].append(conv)
        return groups

    @staticmethod
    def _derive_platform_from_source(source: str) -> str:
        lower = source.lower()
        if "gemini" in lower:
            return "Gemini"
        elif "chatgpt" in lower or "openai" in lower:
            return "ChatGPT"
        elif "claude" in lower or "anthropic" in lower:
            return "Claude"
        elif "grok" in lower:
            return "Grok"
        elif "perplexity" in lower:
            return "Perplexity"
        elif "copilot" in lower:
            return "Copilot"
        return "Unknown"

    @staticmethod
    def _sanitize_name(name: str) -> str:
        return re.sub(r'[^a-zA-Z0-9_\-]+', '_', name).strip('_') or "Platform"

    def _export_package_unit(
        self,
        target_dir: str,
        package_title: str,
        conversations: List[Any],
        package: KnowledgePackage,
        platform_name: str,
        is_unified: bool,
        skip_platform_json: bool = False,
    ) -> None:
        """Render a self-contained knowledge package folder."""
        os.makedirs(target_dir, exist_ok=True)
        ko_dir = os.path.join(target_dir, "knowledge_objects")
        sa_dir = os.path.join(target_dir, "sources_archive")
        os.makedirs(ko_dir, exist_ok=True)
        os.makedirs(sa_dir, exist_ok=True)

        conv_ids = {conv.id for conv in conversations if hasattr(conv, "id")}

        # Filter entities, topics, and attachments for this platform
        platform_entities = [
            e for e in package.entities if getattr(e, "conversation_id", None) in conv_ids
        ]
        platform_attachments = [
            a for a in package.attachment_knowledge if getattr(a, "conversation_id", None) in conv_ids
        ]

        # Write topic/knowledge object markdown files
        self._write_knowledge_objects(ko_dir, conversations, platform_entities, platform_attachments)

        # Write sources archive
        source_files = self._write_sources_archive(sa_dir, conversations)

        # Write INDEX.md
        self._write_index_md(
            filepath=os.path.join(target_dir, "INDEX.md"),
            package_title=package_title,
            conversations=conversations,
            entities=platform_entities,
            attachments=platform_attachments,
        )

        # Write platform.json (unless root level fallback)
        if not skip_platform_json:
            self._write_platform_json(
                filepath=os.path.join(target_dir, "platform.json"),
                platform_name=platform_name,
                conversations=conversations,
                entities=platform_entities,
                attachments=platform_attachments,
            )

        # Write package manifest.json
        self._write_package_manifest(
            filepath=os.path.join(target_dir, "manifest.json"),
            platform_name=platform_name,
            conversations=conversations,
            entities=platform_entities,
            attachments=platform_attachments,
            source_files=source_files,
            is_unified=is_unified,
        )

    def _write_knowledge_objects(
        self,
        ko_dir: str,
        conversations: List[Any],
        entities: List[Any],
        attachments: List[Any],
    ) -> None:
        """Write conversation and entity knowledge objects to markdown files."""
        for conv in conversations:
            filename = f"{self._sanitize_name(conv.title or conv.id)}.md"
            filepath = os.path.join(ko_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {conv.title}\n\n")
                f.write(f"**ID:** `{conv.id}` | **Source:** `{conv.source}`\n\n")

                # Entities in this conversation
                conv_ents = [e for e in entities if getattr(e, "conversation_id", None) == conv.id]
                if conv_ents:
                    f.write("## Entities\n\n")
                    for e in conv_ents:
                        val = getattr(e, "value", str(e))
                        etype = getattr(e, "type", "entity")
                        f.write(f"- **{val}** ({etype})\n")
                    f.write("\n")

                # Messages
                f.write("## Messages\n\n")
                for msg in conv.messages:
                    role = getattr(msg, "role", "user").capitalize()
                    content = getattr(msg, "content", "")
                    f.write(f"### {role}\n\n{content}\n\n")

    def _write_sources_archive(
        self, sa_dir: str, conversations: List[Any]
    ) -> List[str]:
        """Write source reference records into sources_archive."""
        source_files = []
        for conv in conversations:
            filename = f"{self._sanitize_name(conv.id)}.json"
            filepath = os.path.join(sa_dir, filename)
            source_files.append(filename)

            record = {
                "id": conv.id,
                "title": conv.title,
                "source": conv.source,
                "created": conv.created,
                "updated": conv.updated,
                "message_count": len(conv.messages),
                "provenance": conv.provenance,
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2)

        return sorted(source_files)

    def _write_index_md(
        self,
        filepath: str,
        package_title: str,
        conversations: List[Any],
        entities: List[Any],
        attachments: List[Any],
    ) -> None:
        """Write deterministically ordered INDEX.md."""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {package_title}\n\n")
            f.write(f"**Conversations:** {len(conversations)} | ")
            f.write(f"**Entities:** {len(entities)} | ")
            f.write(f"**Attachments:** {len(attachments)}\n\n")

            f.write("## Index of Conversations\n\n")
            for conv in sorted(conversations, key=lambda c: c.title or c.id):
                f.write(f"- **{conv.title}** (`{conv.id}`) - {len(conv.messages)} messages\n")

            if entities:
                f.write("\n## Index of Extracted Entities\n\n")
                for ent in sorted(entities, key=lambda e: getattr(e, "value", "")):
                    val = getattr(ent, "value", str(ent))
                    etype = getattr(ent, "type", "entity")
                    f.write(f"- `{val}` ({etype})\n")

            if attachments:
                f.write("\n## Index of Attachment Knowledge\n\n")
                for att in sorted(attachments, key=lambda a: getattr(a, "file_name", "")):
                    fname = getattr(att, "file_name", "attachment")
                    mtype = getattr(att, "media_type", "unknown")
                    f.write(f"- `{fname}` ({mtype}) - Summary: {getattr(att, 'summary', '')}\n")

    def _write_platform_json(
        self,
        filepath: str,
        platform_name: str,
        conversations: List[Any],
        entities: List[Any],
        attachments: List[Any],
    ) -> None:
        """Write platform.json descriptor."""
        created_dates = [c.created for c in conversations if getattr(c, "created", None)]
        data = {
            "platform_name": platform_name,
            "conversation_count": len(conversations),
            "message_count": sum(len(c.messages) for c in conversations),
            "entity_count": len(entities),
            "attachment_count": len(attachments),
            "first_imported": min(created_dates) if created_dates else None,
            "last_imported": max(created_dates) if created_dates else None,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _write_package_manifest(
        self,
        filepath: str,
        platform_name: str,
        conversations: List[Any],
        entities: List[Any],
        attachments: List[Any],
        source_files: List[str],
        is_unified: bool,
    ) -> None:
        """Write package manifest.json."""
        manifest = {
            "package_type": "unified" if is_unified else "platform_package",
            "platform_name": platform_name,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "conversations": len(conversations),
                "messages": sum(len(c.messages) for c in conversations),
                "entities": len(entities),
                "attachments": len(attachments),
            },
            "source_files": source_files,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    def _write_root_manifest(
        self,
        package: KnowledgePackage,
        platform_map: Dict[str, List[Any]],
        timestamp: str,
    ) -> None:
        """Write top-level root manifest.json under output_dir."""
        filepath = os.path.join(self.output_dir, "manifest.json")

        platforms_summary = {}
        for plat_name, convs in platform_map.items():
            conv_ids = {c.id for c in convs if hasattr(c, "id")}
            platforms_summary[plat_name] = {
                "conversations": len(convs),
                "messages": sum(len(c.messages) for c in convs),
                "entities": len([e for e in package.entities if getattr(e, "conversation_id", None) in conv_ids]),
                "attachments": len([a for a in package.attachment_knowledge if getattr(a, "conversation_id", None) in conv_ids]),
            }

        root_manifest = {
            "compilation_run": {
                "exported_at": timestamp,
                "export_mode": self.mode,
                "total_conversations": len(package.conversations),
                "total_messages": sum(len(c.messages) for c in package.conversations),
                "total_entities": len(package.entities),
                "total_attachments": len(package.attachment_knowledge),
                "total_platforms": len(platform_map),
            },
            "platforms": platforms_summary,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(root_manifest, f, indent=2)

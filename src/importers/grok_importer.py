import glob
import os
import json
from typing import List, Any, Optional, Callable

from src.models.conversation import Conversation
from src.models.message import Message
from src.models.knowledge_object import KnowledgeObject
from src.core.interfaces import Importer
from src.models.knowledge_package import KnowledgePackage


class GrokImporter(Importer):
    @property
    def name(self) -> str:
        return "Grok Importer"

    @property
    def version(self) -> str:
        return "1.1.0"

    @property
    def author(self) -> str:
        return "OKC Core Team"

    @property
    def description(self) -> str:
        return "Imports Grok conversation data from JSON files."

    @property
    def plugin_type(self) -> str:
        return "importer"

    @property
    def supported_inputs(self) -> List[str]:
        return ["application/json", "grok-export"]

    @property
    def supported_outputs(self) -> List[str]:
        return ["okc/conversations"]

    def __init__(
        self,
        input_dir: str = "input",
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ):
        self.input_dir = input_dir
        self.total_messages = 0
        self._progress_cb = progress_callback

    def import_data(
        self,
        package: KnowledgePackage,
        file_path: Optional[str] = None,
    ) -> KnowledgePackage:
        """Import Grok JSON into *package*.

        If *file_path* is set, only that file is processed (single-file mode).
        Otherwise discover files under *input_dir*.
        """
        if file_path:
            files = [file_path]
        else:
            files = self.discover_files()

        for f in files:
            if not os.path.isfile(f):
                continue

            try:
                with open(f, "r", encoding="utf-8") as file:
                    data = json.load(file)

                    raw_conversations: List[Any] = []
                    if isinstance(data, list):
                        raw_conversations.extend(data)
                    elif isinstance(data, dict):
                        if isinstance(data.get("conversations"), list):
                            raw_conversations.extend(data["conversations"])
                        else:
                            raw_conversations.append(data)
                    else:
                        continue

                    for raw_conv in raw_conversations:
                        if not isinstance(raw_conv, dict):
                            continue
                        conv_obj = self._parse_raw_conversation(raw_conv, f)
                        package.add_conversation(conv_obj)
                        package.add_knowledge_object(
                            KnowledgeObject(
                                id=conv_obj.id,
                                title=conv_obj.title,
                                content="\n\n".join(
                                    f"{msg.role}: {msg.content}" for msg in conv_obj.messages
                                ),
                                source_platform="Grok",
                                source_file=conv_obj.source,
                                created_at=conv_obj.created,
                                updated_at=conv_obj.updated,
                                provenance=dict(conv_obj.provenance),
                                evidence=[],
                            )
                        )
                        self.total_messages += len(conv_obj.messages)

            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Failed to read or parse '{f}': {e}")

        return package

    def discover_files(self) -> List[str]:
        """Discover candidate Grok JSON files under input_dir."""
        if os.path.isfile(self.input_dir) and self.input_dir.lower().endswith(".json"):
            return [os.path.abspath(self.input_dir)]

        patterns = [
            os.path.join(self.input_dir, "grok-*.json"),
            os.path.join(self.input_dir, "*grok*.json"),
        ]
        found: List[str] = []
        seen = set()
        for pattern in patterns:
            for path in glob.glob(os.path.abspath(pattern)):
                if path not in seen:
                    seen.add(path)
                    found.append(path)
        return sorted(found)

    def _parse_raw_conversation(self, raw_conv: dict, source_file: str) -> Conversation:
        conv_id = str(raw_conv.get("id") or raw_conv.get("conversation_id") or "unknown")
        title = raw_conv.get("title") or "Untitled Grok Conversation"
        created = raw_conv.get("created_at") or raw_conv.get("create_time")
        updated = raw_conv.get("updated_at") or raw_conv.get("update_time")

        messages: List[Message] = []
        for msg in raw_conv.get("messages") or []:
            if not isinstance(msg, dict):
                continue
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(str(p) for p in content if p is not None)
            timestamp = msg.get("timestamp") or msg.get("create_time")
            messages.append(Message(role=role, content=str(content), timestamp=timestamp))

        return Conversation(
            id=conv_id,
            title=title,
            source=source_file,
            created=created,
            updated=updated,
            messages=messages,
            provenance={
                "source_platform": "Grok",
                "source_file": source_file,
            },
        )

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
        return "1.0.0"
        
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

    def __init__(self, input_dir="input", progress_callback: Optional[Callable[[float, str], None]] = None):
        self.input_dir = input_dir
        self.total_messages = 0
        self._progress_cb = progress_callback

    def import_data(self, package: KnowledgePackage) -> KnowledgePackage:
        files = self.discover_files()
        
        for idx, f in enumerate(files):
            if not os.path.isfile(f):
                continue
                
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    
                    # Assuming a structure similar to chatgpt for now: list of conversations
                    raw_conversations = []
                    if isinstance(data, list):
                        raw_conversations.extend(data)
                    else:
                        raw_conversations.append(data)
                        
                    for raw_conv in raw_conversations:
                        conv_obj = self._parse_raw_conversation(raw_conv, f)
                        package.add_conversation(conv_obj)
                        package.add_knowledge_object(KnowledgeObject(
                            id=conv_obj.id,
                            title=conv_obj.title,
                            content="\n\n".join([f"{msg.role}: {msg.content}" for msg in conv_obj.messages]),
                            source_platform=conv_obj.provenance.get("source_platform", "Grok"),
                            source_file=conv_obj.source,
                            created_at=conv_obj.created,
                            updated_at=conv_obj.updated,
                            provenance=conv_obj.provenance,
                            evidence=[]
                        ))
                        self.total_messages += len(conv_obj.messages)
                        
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Failed to read or parse '{f}': {e}")
                
        return package

    def discover_files(self) -> List[str]:
        # Assume files are named like grok-*.json
        pattern = os.path.join(self.input_dir, "grok-*.json")
        search_pattern = os.path.abspath(pattern)
        files = glob.glob(search_pattern)
        return files

    def _parse_raw_conversation(self, raw_conv: dict, source_file: str) -> Conversation:
        # Assuming similar fields to ChatGPT
        conv_id = raw_conv.get("id", "unknown")
        title = raw_conv.get("title", "Untitled Grok Conversation")
        created = raw_conv.get("created_at")
        updated = raw_conv.get("updated_at")
        
        messages = []
        for msg in raw_conv.get("messages", []):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp")
            messages.append(Message(role=role, content=content, timestamp=timestamp))
                
        return Conversation(
            id=conv_id,
            title=title,
            source=source_file,
            created=created,
            updated=updated,
            messages=messages,
            provenance={"source_platform": "Grok"}
        )

import glob
import os
import json
from typing import List, Any

from src.models.conversation import Conversation
from src.models.message import Message
from src.core.interfaces import Importer
from src.models.knowledge_package import KnowledgePackage

class ChatGPTImporter(Importer):
    @property
    def name(self) -> str:
        return "ChatGPT Importer"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    @property
    def author(self) -> str:
        return "OKC Core Team"
        
    @property
    def description(self) -> str:
        return "Imports ChatGPT conversation data from JSON files."
        
    @property
    def plugin_type(self) -> str:
        return "importer"
        
    @property
    def supported_inputs(self) -> List[str]:
        return ["application/json", "chatgpt-export"]
        
    @property
    def supported_outputs(self) -> List[str]:
        return ["okc/conversations"]

    def __init__(self, input_dir="input"):
        self.input_dir = input_dir
        self.total_messages = 0

    def import_data(self, package: KnowledgePackage) -> KnowledgePackage:
        files = self.discover_files()
        
        for f in files:
            if not os.path.isfile(f):
                continue
                
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    
                    raw_conversations = []
                    if isinstance(data, list):
                        raw_conversations.extend(data)
                    else:
                        raw_conversations.append(data)
                        
                    for raw_conv in raw_conversations:
                        conv_obj = self._parse_raw_conversation(raw_conv, f)
                        package.add_conversation(conv_obj)
                        self.total_messages += len(conv_obj.messages)
                        
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Failed to read or parse '{f}': {e}")
                
        print(f"Total conversations (ChatGPT): {len(package.conversations)}")
        print(f"Total messages (ChatGPT): {self.total_messages}")
        return package

    def discover_files(self):
        pattern = os.path.join(self.input_dir, "conversations-*.json")
        search_pattern = os.path.abspath(pattern)
        files = glob.glob(search_pattern)
        return files

    def _extract_messages_from_mapping(self, mapping):
        messages = []
        if not mapping:
            return messages
            
        for key, node in mapping.items():
            if not isinstance(node, dict):
                continue
                
            message_data = node.get("message")
            if not message_data:
                continue
                
            author = message_data.get("author", {})
            role = author.get("role", "unknown")
            
            content_data = message_data.get("content", {})
            parts = content_data.get("parts", [])
            
            content = ""
            if parts:
                content = " ".join([str(p) for p in parts if isinstance(p, str)])
            
            create_time = message_data.get("create_time")
            
            messages.append(Message(role=role, content=content, timestamp=create_time))
            
        # Optional: Sort messages by timestamp if available
        messages.sort(key=lambda x: x.timestamp if x.timestamp is not None else 0)
        return messages

    def _parse_raw_conversation(self, raw_conv, source_file):
        conv_id = raw_conv.get("conversation_id", raw_conv.get("id", "unknown"))
        title = raw_conv.get("title", "Untitled")
        created = raw_conv.get("create_time")
        updated = raw_conv.get("update_time")
        
        messages = []
        if "mapping" in raw_conv:
            messages = self._extract_messages_from_mapping(raw_conv["mapping"])
        elif "messages" in raw_conv and isinstance(raw_conv["messages"], list):
            for msg in raw_conv["messages"]:
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
            messages=messages
        )

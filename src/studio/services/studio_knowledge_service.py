import os
import json
from typing import List, Dict, Any, Optional

class StudioKnowledgeService:
    """Service for consuming and querying compiled/exported knowledge.
    
    This service is the primary read/query layer for the Studio.
    It loads exported data from the 'output' directory and provides
    structured access to platforms, conversations, knowledge objects,
    entities, and attachments.
    """
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        self.root_manifest: Dict[str, Any] = {}
        self.platforms: Dict[str, Dict[str, Any]] = {}
        self._loaded = False

    def load_workspace(self) -> bool:
        """Loads the root manifest and discovers available platform packages."""
        manifest_path = os.path.join(self.output_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            return False
            
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                self.root_manifest = json.load(f)
            
            # Discover platforms
            platforms_dir = os.path.join(self.output_dir, "Platforms")
            if os.path.exists(platforms_dir):
                for platform_name in os.listdir(platforms_dir):
                    plat_dir = os.path.join(platforms_dir, platform_name)
                    if os.path.isdir(plat_dir):
                        plat_manifest_path = os.path.join(plat_dir, "manifest.json")
                        if os.path.exists(plat_manifest_path):
                            with open(plat_manifest_path, "r", encoding="utf-8") as f:
                                self.platforms[platform_name] = json.load(f)
                                self.platforms[platform_name]["path"] = plat_dir
            
            self._loaded = True
            return True
        except Exception as e:
            print(f"Error loading workbench workspace: {e}")
            return False

    def get_platforms(self) -> List[str]:
        return list(self.platforms.keys())

    def get_conversations(self, platform_name: str) -> List[Dict[str, Any]]:
        """Returns metadata for all conversations in a platform."""
        if platform_name not in self.platforms:
            return []
            
        plat_dir = self.platforms[platform_name]["path"]
        sa_dir = os.path.join(plat_dir, "sources_archive")
        
        conversations = []
        if os.path.exists(sa_dir):
            for filename in os.listdir(sa_dir):
                if filename.endswith(".json"):
                    with open(os.path.join(sa_dir, filename), "r", encoding="utf-8") as f:
                        conversations.append(json.load(f))
        return sorted(conversations, key=lambda c: c.get("title") or c.get("id"))

    def get_conversation_details(self, platform_name: str, conv_id: str) -> Optional[Dict[str, Any]]:
        """Loads full conversation details from the source archive."""
        if platform_name not in self.platforms:
            return None
            
        plat_dir = self.platforms[platform_name]["path"]
        conv_path = os.path.join(plat_dir, "sources_archive", f"{conv_id}.json")
        
        if os.path.exists(conv_path):
            with open(conv_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def get_knowledge_object_markdown(self, platform_name: str, title: str) -> Optional[str]:
        """Reads the markdown representation of a knowledge object."""
        if platform_name not in self.platforms:
            return None
            
        # Sanitize title as per MultiSourceExporter
        import re
        sanitized = re.sub(r'[^a-zA-Z0-9_\-]+', '_', title).strip('_') or "Platform"
        md_path = os.path.join(self.platforms[platform_name]["path"], "knowledge_objects", f"{sanitized}.md")
        
        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def search_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Stub for semantic search. Currently returns matches from titles/summaries."""
        # TODO: Implement semantic search integration
        results = []
        query_lower = query.lower()
        
        for plat_name in self.platforms:
            convs = self.get_conversations(plat_name)
            for conv in convs:
                if query_lower in (conv.get("title") or "").lower():
                    results.append({
                        "type": "conversation",
                        "id": conv["id"],
                        "title": conv["title"],
                        "platform": plat_name,
                        "relevance": 1.0
                    })
        return results

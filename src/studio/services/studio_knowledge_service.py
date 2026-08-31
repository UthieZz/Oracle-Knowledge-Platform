import os
import json
import re
from typing import List, Dict, Any, Optional


class StudioKnowledgeService:
    """Service for consuming and querying compiled/exported knowledge.

    Primary read/query layer for Studio portable output under `output/`.
    Stage 3: search prefers knowledge objects over raw conversations.
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
        if platform_name not in self.platforms:
            return None

        plat_dir = self.platforms[platform_name]["path"]
        conv_path = os.path.join(plat_dir, "sources_archive", f"{conv_id}.json")

        if os.path.exists(conv_path):
            with open(conv_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def get_knowledge_object_markdown(self, platform_name: str, title: str) -> Optional[str]:
        if platform_name not in self.platforms:
            return None

        sanitized = re.sub(r"[^a-zA-Z0-9_\-]+", "_", title).strip("_") or "Platform"
        md_path = os.path.join(
            self.platforms[platform_name]["path"], "knowledge_objects", f"{sanitized}.md"
        )

        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def get_knowledge_objects(self) -> List[Dict[str, Any]]:
        """Returns metadata + content path for all knowledge objects."""
        objects = []
        for plat_name, plat_info in self.platforms.items():
            ko_dir = os.path.join(plat_info["path"], "knowledge_objects")
            if os.path.exists(ko_dir):
                for filename in os.listdir(ko_dir):
                    if filename.endswith(".md"):
                        title = filename.replace(".md", "")
                        path = os.path.join(ko_dir, filename)
                        content = ""
                        try:
                            with open(path, "r", encoding="utf-8") as f:
                                content = f.read()
                        except OSError:
                            content = ""
                        objects.append(
                            {
                                "id": f"{plat_name}/{title}",
                                "title": title,
                                "platform": plat_name,
                                "source_platform": plat_name,
                                "path": path,
                                "content": content,
                                "type": "knowledge",
                            }
                        )
        return objects

    def get_entities(self) -> List[Dict[str, Any]]:
        entities_path = os.path.join(self.output_dir, "entities.json")
        if os.path.exists(entities_path):
            with open(entities_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def get_attachments(self) -> List[Dict[str, Any]]:
        attachments = []
        for p in self.get_platforms():
            conversations = self.get_conversations(p)
            for conv in conversations:
                prov = conv.get("provenance", {})
                if "attachments" in prov:
                    for att in prov["attachments"]:
                        attachments.append(
                            {
                                "name": att.get("name"),
                                "url": att.get("url"),
                                "conversation_id": conv.get("id"),
                                "conversation_title": conv.get("title"),
                                "platform": p,
                                "source_platform": p,
                            }
                        )
        return attachments

    def search_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Stage 3 search: knowledge objects first, conversations secondary.

        Returns ranked results with type, score, source_platform, and content
        when available. Does not invent hits.
        """
        if not query or not str(query).strip():
            return []

        if not self._loaded:
            self.load_workspace()

        term = query.strip().lower()
        tokens = [t for t in re.split(r"\s+", term) if t]
        results: List[Dict[str, Any]] = []

        # 1. Knowledge objects (primary evidence)
        for ko in self.get_knowledge_objects():
            title = (ko.get("title") or "").lower()
            content = (ko.get("content") or "").lower()
            score = 0
            if term in title:
                score += 10
            if term in content:
                score += 5
            for tok in tokens:
                if tok in title:
                    score += 3
                if tok in content:
                    score += 1
            if score > 0:
                results.append(
                    {
                        "id": ko["id"],
                        "title": ko["title"],
                        "type": "knowledge",
                        "source_platform": ko.get("source_platform") or ko.get("platform"),
                        "platform": ko.get("platform"),
                        "content": ko.get("content") or "",
                        "score": score,
                    }
                )

        # 2. Conversations (secondary; title / first message only)
        for p in self.get_platforms():
            for conv in self.get_conversations(p):
                title = (conv.get("title") or conv.get("id") or "").lower()
                first = ""
                # Prefer explicit preview fields if present
                first = (
                    conv.get("first_user_message")
                    or conv.get("preview")
                    or ""
                )
                if not first and isinstance(conv.get("messages"), list):
                    for m in conv["messages"]:
                        if m.get("role") in ("user", "human"):
                            first = m.get("content") or ""
                            break
                first_l = first.lower() if isinstance(first, str) else ""

                score = 0
                if term in title:
                    score += 8
                if term in first_l:
                    score += 4
                for tok in tokens:
                    if tok in title:
                        score += 2
                    if tok in first_l:
                        score += 1

                if score > 0:
                    results.append(
                        {
                            "id": conv.get("id"),
                            "title": conv.get("title") or conv.get("id"),
                            "type": "conversation",
                            "source_platform": conv.get("source_platform")
                            or conv.get("provenance", {}).get("source_platform")
                            or p,
                            "platform": p,
                            "content": first[:2000] if first else "",
                            "score": score,
                        }
                    )

        results.sort(key=lambda r: r.get("score") or 0, reverse=True)
        return results

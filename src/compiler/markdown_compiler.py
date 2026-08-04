import os
import re
from typing import List, Dict, Set
from collections import defaultdict
from src.core.interfaces import Compiler
from src.models.knowledge_package import KnowledgePackage

# Display names for known topics (index stores lowercase)
DISPLAY_NAMES = {
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "react": "React",
    "angular": "Angular",
    "vue": "Vue",
    "django": "Django",
    "flask": "Flask",
    "spring": "Spring",
    "express": "Express",
    "node": "Node.js",
    "next.js": "Next.js",
    "nestjs": "NestJS",
    "laravel": "Laravel",
    "fastapi": "FastAPI",
    "firebase": "Firebase",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "mysql": "MySQL",
    "postgres": "PostgreSQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "sql": "SQL",
    "nosql": "NoSQL",
    "graphql": "GraphQL",
    "html": "HTML",
    "css": "CSS",
    "bash": "Bash",
    "shell": "Shell",
    "rust": "Rust",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "java": "Java",
    "ruby": "Ruby",
    "php": "PHP",
    "chatgpt": "ChatGPT",
    "figma": "Figma",
    "notion": "Notion",
    "google": "Google",
    "microsoft": "Microsoft",
    "apple": "Apple",
    "amazon": "Amazon",
    "meta": "Meta",
    "facebook": "Facebook",
    "netflix": "Netflix",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "oracle": "Oracle",
    "github": "GitHub",
    "gitlab": "GitLab",
    "vercel": "Vercel",
    "heroku": "Heroku",
    "stripe": "Stripe",
    "oracle compiler": "Oracle Compiler",
}

# Index categories that produce meaningful topics
TOPIC_CATEGORIES = [
    "technologies",
    "programming_languages",
    "frameworks",
    "products",
    "companies",
    "projects",
]

# Minimum conversations required for a topic to get its own document
MIN_CONVERSATIONS_PER_TOPIC = 2


class MarkdownCompiler(Compiler):
    @property
    def name(self) -> str:
        return "Markdown Compiler"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def author(self) -> str:
        return "OKC Core Team"

    @property
    def description(self) -> str:
        return "Compiles KnowledgePackage into topic-centric Markdown files suitable for NotebookLM."

    @property
    def plugin_type(self) -> str:
        return "compiler"

    @property
    def supported_inputs(self) -> List[str]:
        return ["okc/package"]

    @property
    def supported_outputs(self) -> List[str]:
        return ["markdown"]

    def __init__(self, output_dir="output/markdown"):
        self.output_dir = output_dir

    def _display_name(self, token: str) -> str:
        """Return a properly cased display name for a topic token."""
        if token.lower() in DISPLAY_NAMES:
            return DISPLAY_NAMES[token.lower()]
        return token.capitalize()

    def _sanitize_filename(self, title: str) -> str:
        safe = re.sub(r'[^a-zA-Z0-9]+', '-', title)
        return safe.strip('-') or "Untitled"

    def _build_topic_map(self, package: KnowledgePackage) -> Dict[str, Set[str]]:
        """
        Build a mapping of topic_display_name -> set of conversation IDs
        by scanning the relevant index categories.
        """
        topic_map: Dict[str, Set[str]] = defaultdict(set)

        for category in TOPIC_CATEGORIES:
            if category not in package.index:
                continue
            mappings = package.index[category]
            for token, conv_ids in mappings.items():
                display = self._display_name(token)
                for cid in conv_ids:
                    topic_map[display].add(cid)

        return topic_map

    def _build_conv_lookup(self, package: KnowledgePackage) -> Dict[str, object]:
        """Build a dict of conv_id -> Conversation for fast lookups."""
        return {conv.id: conv for conv in package.conversations}

    def _build_entity_lookup(self, package: KnowledgePackage) -> Dict[str, Set[str]]:
        """Build a dict of conv_id -> set of entity display strings."""
        conv_entities: Dict[str, Set[str]] = defaultdict(set)
        for entity in package.entities:
            conv_entities[entity.conversation_id].add(
                f"{entity.value} ({entity.type})"
            )
        return conv_entities

    def _write_topic_file(
        self,
        topic_name: str,
        conv_ids: Set[str],
        conv_lookup: Dict[str, object],
        conv_entities: Dict[str, Set[str]],
    ) -> str:
        """Write a single topic Markdown file. Returns the filepath written."""
        filename = f"{self._sanitize_filename(topic_name)}.md"
        filepath = os.path.join(self.output_dir, filename)

        # Collect the actual conversation objects (skip missing IDs)
        conversations = []
        for cid in conv_ids:
            conv = conv_lookup.get(cid)
            if conv:
                conversations.append(conv)

        # Sort by creation date (newest first).
        # ChatGPT and Gemini importers may populate `created`
        # using different data types (float, int, str, None).
        # Convert everything to a string so Python never tries
        # to compare floats with strings.

        def conversation_sort_key(conv):
            created = getattr(conv, "created", None)

            if created is None:
                return ""

            return str(created)

        conversations.sort(
            key=conversation_sort_key,
            reverse=True
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {topic_name}\n\n")
            f.write(f"**Conversations:** {len(conversations)}\n\n")

            # Table of contents
            f.write("## Contents\n\n")
            for i, conv in enumerate(conversations, 1):
                anchor = re.sub(r'[^a-zA-Z0-9 ]', '', conv.title).strip().replace(' ', '-').lower()
                f.write(f"{i}. [{conv.title}](#{anchor})\n")
            f.write("\n---\n\n")

            # Each conversation as a section
            for conv in conversations:
                f.write(f"## {conv.title}\n\n")
                f.write(f"*Source: {conv.source} | Date: {conv.created}*\n\n")

                # Referenced entities for this conversation
                if conv.id in conv_entities and conv_entities[conv.id]:
                    f.write("**Entities:** ")
                    f.write(", ".join(sorted(conv_entities[conv.id])))
                    f.write("\n\n")

                # Messages – preserve original wording
                for msg in conv.messages:
                    role = getattr(msg, "role", "unknown").capitalize()
                    content = msg.content
                    if not content or not content.strip():
                        continue
                    f.write(f"### {role}\n\n")
                    f.write(f"{content}\n\n")

                f.write("---\n\n")

        return filepath

    def compile(self, package: KnowledgePackage) -> KnowledgePackage:
        print(f"Compiling topic-centric Markdown knowledge base to {self.output_dir}...")

        # Clean previous output
        os.makedirs(self.output_dir, exist_ok=True)

        # Build lookups
        topic_map = self._build_topic_map(package)
        conv_lookup = self._build_conv_lookup(package)
        conv_entities = self._build_entity_lookup(package)

        # Track which conversations are assigned to at least one topic
        assigned_conv_ids: Set[str] = set()
        compiled_files = 0
        skipped_topics = 0

        # Sort topics by number of conversations (largest first)
        sorted_topics = sorted(topic_map.items(), key=lambda x: len(x[1]), reverse=True)

        for topic_name, conv_ids in sorted_topics:
            if len(conv_ids) < MIN_CONVERSATIONS_PER_TOPIC:
                skipped_topics += 1
                continue

            self._write_topic_file(topic_name, conv_ids, conv_lookup, conv_entities)
            assigned_conv_ids.update(conv_ids)
            compiled_files += 1

        # Collect unassigned conversations into General.md
        all_conv_ids = set(conv_lookup.keys())
        unassigned = all_conv_ids - assigned_conv_ids

        if unassigned:
            self._write_topic_file("General", unassigned, conv_lookup, conv_entities)
            compiled_files += 1

        print(f"Successfully compiled {compiled_files} topic documents.")
        print(f"  Topics with enough conversations: {compiled_files}")
        print(f"  Topics skipped (< {MIN_CONVERSATIONS_PER_TOPIC} conversations): {skipped_topics}")
        print(f"  Conversations assigned to topics: {len(assigned_conv_ids)}")
        print(f"  Unassigned conversations (-> General.md): {len(unassigned)}")

        return package

import re
from typing import List, Set
from okc.models.knowledge_package import KnowledgePackage


class EntityExtractor:
    """Extracts technologies, companies, emails, URLs, and dates using gazetteers and regex."""

    def __init__(self):
        self.tech_gazetteer = {
            "python", "javascript", "react", "docker", "sqlite",
            "chatgpt", "gemini", "grok", "pydantic", "fastapi"
        }
        self.company_gazetteer = {"google", "microsoft", "openai", "oracle", "anthropic"}
        self.email_regex = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
        self.url_regex = re.compile(r"https?://[^\s/$.?#].[^\s]*")

    def run(self, package: KnowledgePackage) -> KnowledgePackage:
        for obj in package.objects:
            found_entities: Set[str] = set(obj.entities)
            text_lower = obj.content.lower()

            # Gazetteer matching
            for term in self.tech_gazetteer.union(self.company_gazetteer):
                if re.search(r"\b" + re.escape(term) + r"\b", text_lower):
                    found_entities.add(term)

            # Regex matching
            emails = self.email_regex.findall(obj.content)
            urls = self.url_regex.findall(obj.content)

            found_entities.update(emails)
            found_entities.update(urls)

            obj.entities = list(found_entities)
        return package

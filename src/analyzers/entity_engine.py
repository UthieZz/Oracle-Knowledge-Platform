import json
import re
import os
import uuid
import sys
from typing import List, Set, Any
from collections import Counter

# To allow relative imports if run directly
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.conversation import Conversation
from src.models.message import Message
from src.models.entity import Entity
from src.core.interfaces import Analyzer
from src.models.knowledge_package import KnowledgePackage

class EntityEngine(Analyzer):
    @property
    def name(self) -> str:
        return "Entity Engine"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    @property
    def author(self) -> str:
        return "OKC Core Team"
        
    @property
    def description(self) -> str:
        return "Deterministically extracts entities from conversations."
        
    @property
    def plugin_type(self) -> str:
        return "analyzer"
        
    @property
    def supported_inputs(self) -> List[str]:
        return ["okc/conversations"]
        
    @property
    def supported_outputs(self) -> List[str]:
        return ["okc/entities"]

    def __init__(self):
        # Deterministic extraction via Regular Expressions
        self.url_pattern = re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+')
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        self.date_pattern = re.compile(r'\b(?:\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})\b')
        self.file_pattern = re.compile(r'\b[\w\-\.]+\.(?:py|md|txt|json|csv|yml|yaml|html|js|ts|cpp|c|java|go|rs)\b', re.IGNORECASE)

        # Deterministic extraction via Gazetteers (Knowledge Lists)
        self.programming_languages = {"Python", "JavaScript", "Java", "C++", "C#", "Go", "Rust", "TypeScript", "Ruby", "PHP", "Swift", "Kotlin"}
        self.frameworks = {"React", "Angular", "Vue", "Django", "Flask", "Spring", "Express", "Ruby on Rails", "Next.js", "FastAPI"}
        self.technologies = {"Docker", "Kubernetes", "AWS", "Azure", "GCP", "SQL", "NoSQL", "GraphQL", "REST", "Linux", "Git", "Kafka"}
        self.companies = {"Google", "Microsoft", "Apple", "Amazon", "Meta", "OpenAI", "Oracle", "IBM", "Intel", "Nvidia", "Anthropic"}
        self.products = {"ChatGPT", "Gemini", "Claude", "Grok", "Copilot", "Windows", "macOS", "Linux", "iPhone"}
        self.people = {"Alan Turing", "Linus Torvalds", "Grace Hopper", "Ada Lovelace", "Tim Berners-Lee", "Bill Gates", "Steve Jobs", "Elon Musk"}

    def _extract_regex(self, text: str, pattern: re.Pattern, entity_type: str, conv_id: str) -> List[Entity]:
        entities = []
        for match in pattern.finditer(text):
            entities.append(Entity(
                id=str(uuid.uuid4()),
                type=entity_type,
                value=match.group(0),
                confidence=1.0,  # Exact pattern match
                source="regex",
                conversation_id=conv_id,
                message_id=None,
                metadata={}
            ))
        return entities

    def _extract_gazetteer(self, text: str, gazetteer: Set[str], entity_type: str, conv_id: str) -> List[Entity]:
        entities = []
        for item in gazetteer:
            # Word boundary search to prevent partial matches (e.g., "Go" in "Good")
            pattern = r'\b' + re.escape(item) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                entities.append(Entity(
                    id=str(uuid.uuid4()),
                    type=entity_type,
                    value=item,
                    confidence=1.0,  # Exact list match
                    source="gazetteer",
                    conversation_id=conv_id,
                    message_id=None,
                    metadata={}
                ))
        return entities

    def process_conversation(self, conversation: Conversation) -> List[Entity]:
        all_entities = []
        for message in conversation.messages:
            text = message.content
            
            # 1. Regex Extractions
            all_entities.extend(self._extract_regex(text, self.url_pattern, "URL", conversation.id))
            all_entities.extend(self._extract_regex(text, self.email_pattern, "Email Address", conversation.id))
            all_entities.extend(self._extract_regex(text, self.date_pattern, "Date", conversation.id))
            all_entities.extend(self._extract_regex(text, self.file_pattern, "File Name", conversation.id))
            
            # 2. Gazetteer Extractions
            all_entities.extend(self._extract_gazetteer(text, self.programming_languages, "Programming Language", conversation.id))
            all_entities.extend(self._extract_gazetteer(text, self.frameworks, "Framework", conversation.id))
            all_entities.extend(self._extract_gazetteer(text, self.technologies, "Technology", conversation.id))
            all_entities.extend(self._extract_gazetteer(text, self.companies, "Company", conversation.id))
            all_entities.extend(self._extract_gazetteer(text, self.products, "Product", conversation.id))
            all_entities.extend(self._extract_gazetteer(text, self.people, "Person", conversation.id))
            
        return all_entities

    def analyze(self, package: KnowledgePackage) -> KnowledgePackage:
        """Implement the Analyzer interface."""
        all_entities = []
        for conv in package.conversations:
            all_entities.extend(self.process_conversation(conv))
            
        for entity in all_entities:
            package.add_entity(entity)
            
        self.save_and_report(package.entities, "output/entities.json")
        return package

    def save_and_report(self, entities: List[Entity], output_path: str):
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save to JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump([e.__dict__ for e in entities], f, indent=2)
            
        # Compile analytics
        total_entities = len(entities)
        tech_types = {'Technology', 'Programming Language', 'Framework', 'Product'}
        
        tech_counter = Counter([e.value for e in entities if e.type in tech_types])
        people_counter = Counter([e.value for e in entities if e.type == 'Person'])
        company_counter = Counter([e.value for e in entities if e.type == 'Company'])
        
        # Print report to standard output
        print(f"Total entities extracted: {total_entities}\n")
        
        print("Top 25 Technologies:")
        for name, count in tech_counter.most_common(25):
            print(f"- {name}: {count}")
        print("\n", end="")
            
        print("Top 25 People:")
        for name, count in people_counter.most_common(25):
            print(f"- {name}: {count}")
        print("\n", end="")
            
        print("Top 25 Companies:")
        for name, count in company_counter.most_common(25):
            print(f"- {name}: {count}")
        print()

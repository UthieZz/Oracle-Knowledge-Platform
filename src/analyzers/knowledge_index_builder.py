import re
import json
import os
from collections import defaultdict, Counter
from src.core.interfaces import Analyzer
from src.models.knowledge_package import KnowledgePackage

STOP_WORDS = {
    "the", "and", "a", "to", "of", "in", "i", "is", "that", "it", "on", "you", 
    "this", "for", "but", "with", "are", "have", "be", "at", "or", "as", "was", 
    "so", "if", "out", "not", "we", "my", "can", "they", "from", "do", "what",
    "about", "which", "when", "one", "their", "there", "all", "would", "how",
    "me", "will", "up", "an", "your", "by", "just", "like", "know", "get", "no",
    "some", "them", "then", "now", "into", "has", "more",
    "also", "any", "could", "should", "very", "much", "these", "those", "than",
    "use", "using", "used", "make", "want", "need", "way", "see", "think",
    "time", "good", "well", "where", "who", "why", "been", "had", "does",
    "our", "were", "don", "did", "didn", "only", "other"
}

LANGUAGES = {"python", "javascript", "java", "ruby", "php", "swift", "kotlin", "rust", "typescript", "html", "css", "sql", "c++", "c#", "go", "bash", "shell"}
FRAMEWORKS = {"react", "angular", "vue", "django", "flask", "spring", "node", "express", "next.js", "nestjs", "laravel"}
PRODUCTS = {"firebase", "aws", "azure", "gcp", "mysql", "postgres", "mongodb", "redis", "docker", "kubernetes", "figma", "notion", "chatgpt"}
COMPANIES = {"google", "microsoft", "apple", "amazon", "facebook", "meta", "netflix", "openai", "anthropic", "oracle", "github", "gitlab", "vercel", "heroku", "stripe"}

class KnowledgeIndexBuilder(Analyzer):
    @property
    def name(self) -> str:
        return "Knowledge Index Builder"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    @property
    def author(self) -> str:
        return "OKC Core Team"
        
    @property
    def description(self) -> str:
        return "Builds search indices over the conversations."
        
    @property
    def plugin_type(self) -> str:
        return "analyzer"
        
    @property
    def supported_inputs(self) -> list:
        return ["okc/conversations"]
        
    @property
    def supported_outputs(self) -> list:
        return ["okc/index"]

    def __init__(self, output_dir="output"):
        self.output_dir = output_dir

    def _extract_from_text(self, text, conv_id, local_index):
        # URLs
        urls = set(re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', text))
        for url in urls:
            local_index["urls"][url].append(conv_id)
            
        # File names
        files = set(re.findall(r'\b[\w\-\.]+\.(?:py|js|ts|json|txt|md|csv|html|css|yml|yaml|xml|sh)\b', text.lower()))
        for f in files:
            local_index["file_names"][f].append(conv_id)
            
        # Dates
        dates = set(re.findall(r'\b(?:\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})\b', text))
        for d in dates:
            local_index["dates"][d].append(conv_id)
            
        # Words for keywords and known entities
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
        freq = Counter(words)
        
        for word, count in freq.items():
            categorized = False
            if word in LANGUAGES:
                local_index["programming_languages"][word].append(conv_id)
                local_index["technologies"][word].append(conv_id)
                categorized = True
            if word in FRAMEWORKS:
                local_index["frameworks"][word].append(conv_id)
                local_index["technologies"][word].append(conv_id)
                categorized = True
            if word in PRODUCTS:
                local_index["products"][word].append(conv_id)
                local_index["technologies"][word].append(conv_id)
                categorized = True
            if word in COMPANIES:
                local_index["companies"][word].append(conv_id)
                local_index["projects"][word].append(conv_id)
                categorized = True
                
            if not categorized and word not in STOP_WORDS and len(word) > 2 and count >= 2:
                local_index["keywords"][word].append(conv_id)
                
        # Specific multi-word extractions
        if "oracle compiler" in text.lower():
            local_index["projects"]["oracle compiler"].append(conv_id)

    def analyze(self, package: KnowledgePackage) -> KnowledgePackage:
        local_index = {
            "keywords": defaultdict(list),
            "technologies": defaultdict(list),
            "programming_languages": defaultdict(list),
            "frameworks": defaultdict(list),
            "products": defaultdict(list),
            "companies": defaultdict(list),
            "file_names": defaultdict(list),
            "urls": defaultdict(list),
            "dates": defaultdict(list),
            "projects": defaultdict(list)
        }
        
        for conv in package.conversations:
            text = " ".join([msg.content for msg in conv.messages if msg.content])
            self._extract_from_text(text, conv.id, local_index)
            
        # Save to package using helper
        for category, mappings in local_index.items():
            cleaned_category = {}
            for k, v in mappings.items():
                cleaned_category[k] = list(set(v))
            package.update_index(category, cleaned_category)
            
        self.save_index(package.index)
        self.print_summary(package.index)
        return package

    def save_index(self, package_index):
        os.makedirs(self.output_dir, exist_ok=True)
        output_file = os.path.join(self.output_dir, "knowledge_index.json")
                
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(package_index, f, indent=2, ensure_ascii=False)
            
        print(f"\nKnowledge index saved to: {output_file}")
        
    def _print_top(self, package_index, category, limit=25):
        if category not in package_index:
            return
            
        items = []
        for k, v_list in package_index[category].items():
            items.append((k, len(set(v_list))))
        items.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\n--- Top {limit} {category.capitalize()} ---")
        if not items:
            print("None found.")
        for k, v in items[:limit]:
            print(f"  {k}: {v} conversation(s)")
            
    def print_summary(self, package_index):
        self._print_top(package_index, "keywords", 25)
        self._print_top(package_index, "technologies", 25)
        self._print_top(package_index, "projects", 25)

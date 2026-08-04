import json
import os
from src.core.interfaces import Analyzer
from src.models.knowledge_package import KnowledgePackage

class KnowledgeRecord:
    def __init__(self, conversation_id, title, source, created_date, updated_date, 
                 num_messages, total_chars, est_tokens, first_user_message, last_updated_timestamp):
        self.conversation_id = conversation_id
        self.title = title
        self.source = source
        self.created_date = created_date
        self.updated_date = updated_date
        self.num_messages = num_messages
        self.total_chars = total_chars
        self.est_tokens = est_tokens
        self.first_user_message = first_user_message
        self.last_updated_timestamp = last_updated_timestamp
        
    def to_dict(self):
        return {
            "conversation_id": self.conversation_id,
            "title": self.title,
            "source": self.source,
            "created_date": self.created_date,
            "updated_date": self.updated_date,
            "num_messages": self.num_messages,
            "total_chars": self.total_chars,
            "est_tokens": self.est_tokens,
            "first_user_message": self.first_user_message,
            "last_updated_timestamp": self.last_updated_timestamp
        }

class InventoryBuilder(Analyzer):
    @property
    def name(self) -> str:
        return "Inventory Builder"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    @property
    def author(self) -> str:
        return "OKC Core Team"
        
    @property
    def description(self) -> str:
        return "Builds a knowledge inventory from conversations."
        
    @property
    def plugin_type(self) -> str:
        return "analyzer"
        
    @property
    def supported_inputs(self) -> list:
        return ["okc/conversations"]
        
    @property
    def supported_outputs(self) -> list:
        return ["okc/inventory"]

    def __init__(self, output_dir="output"):
        self.output_dir = output_dir

    def analyze(self, package: KnowledgePackage) -> KnowledgePackage:
        for conv in package.conversations:
            total_chars = sum(len(msg.content) for msg in conv.messages if msg.content)
            est_tokens = total_chars // 4
            
            first_user_msg = ""
            for msg in conv.messages:
                if getattr(msg, "role", "unknown").lower() == "user" and msg.content:
                    first_user_msg = msg.content[:200]
                    break
                    
            record = KnowledgeRecord(
                conversation_id=conv.id,
                title=conv.title,
                source=conv.source,
                created_date=conv.created,
                updated_date=conv.updated,
                num_messages=len(conv.messages),
                total_chars=total_chars,
                est_tokens=est_tokens,
                first_user_message=first_user_msg,
                last_updated_timestamp=conv.updated
            )
            package.add_inventory_record(record)
            
        self.save_inventory(package.inventory)
        self.print_summary(package.conversations, package.inventory)
        return package
        
    def print_summary(self, conversations, records):
        total_convs = len(conversations)
        total_messages = sum(r.num_messages for r in records)
        
        print(f"\n--- Knowledge Inventory Summary ---")
        print(f"Total conversations: {total_convs}")
        print(f"Total messages: {total_messages}")
        
        sorted_records = sorted(records, key=lambda x: x.est_tokens, reverse=True)
        print("\nTop 10 largest conversations by estimated token count:")
        for i, r in enumerate(sorted_records[:10]):
            print(f"  {i+1}. {r.title} ({r.est_tokens} tokens)")
            
    def save_inventory(self, records):
        os.makedirs(self.output_dir, exist_ok=True)
        output_file = os.path.join(self.output_dir, "knowledge_inventory.json")
        
        data = [r.to_dict() for r in records]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"\nKnowledge inventory saved to: {output_file}")

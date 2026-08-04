from typing import List, Dict, Any, Optional

class KnowledgePackage:
    def __init__(self):
        # Internal fields, access through helper methods
        self._conversations: List[Any] = []
        self._entities: List[Any] = []
        self._relationships: List[Any] = []
        self._topics: List[Any] = []
        self._clusters: List[Any] = []
        self._timeline: List[Any] = []
        self._inventory: List[Any] = []
        self._attachment_knowledge: List[Any] = []
        self._index: Dict[str, Any] = {}
        self._statistics: Dict[str, Any] = {}
        self._metadata: Dict[str, Any] = {}

    # Getters that return references to the collections for read access
    @property
    def conversations(self): return self._conversations
    @property
    def entities(self): return self._entities
    @property
    def relationships(self): return self._relationships
    @property
    def topics(self): return self._topics
    @property
    def clusters(self): return self._clusters
    @property
    def timeline(self): return self._timeline
    @property
    def inventory(self): return self._inventory
    @property
    def attachment_knowledge(self): return self._attachment_knowledge
    @property
    def attachmentKnowledge(self): return self._attachment_knowledge
    @property
    def index(self): return self._index
    @property
    def statistics(self): return self._statistics
    @property
    def metadata(self): return self._metadata

    # Mutator helper methods
    def add_conversation(self, conversation: Any) -> None:
        self._conversations.append(conversation)

    def add_entity(self, entity: Any) -> None:
        self._entities.append(entity)

    def add_relationship(self, relationship: Any) -> None:
        self._relationships.append(relationship)

    def add_topic(self, topic: Any) -> None:
        self._topics.append(topic)

    def add_cluster(self, cluster: Any) -> None:
        self._clusters.append(cluster)
        
    def add_inventory_record(self, record: Any) -> None:
        self._inventory.append(record)

    def add_attachment_knowledge(self, record: Any) -> None:
        self._attachment_knowledge.append(record)

    def get_attachment_knowledge(self, att_id: str) -> Optional[Any]:
        for att in self._attachment_knowledge:
            if getattr(att, "id", None) == att_id or getattr(att, "attachment_id", None) == att_id:
                return att
        return None
        
    def update_index(self, key: str, value: Any) -> None:
        if key not in self._index:
            self._index[key] = []
        # Support for passing a dictionary to merge or just storing the whole thing
        if isinstance(value, dict):
             self._index[key] = value
        else:
             self._index[key].append(value)

    def get_conversation(self, conv_id: str) -> Optional[Any]:
        for conv in self._conversations:
            if conv.id == conv_id:
                return conv
        return None

    def get_message(self, message_id: str) -> Optional[Any]:
        for conv in self._conversations:
            for msg in conv.messages:
                # Need to use getattr because Message objects didn't have an ID in previous stages
                if getattr(msg, "id", None) == message_id:
                    return msg
        return None

    def update_statistics(self, key: str, value: Any) -> None:
        self._statistics[key] = value
        
    def update_metadata(self, key: str, value: Any) -> None:
        self._metadata[key] = value

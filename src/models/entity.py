class Entity:
    def __init__(self, id, type, value, confidence, source, conversation_id, message_id, metadata=None):
        self.id = id
        self.type = type
        self.value = value
        self.confidence = confidence
        self.source = source
        self.conversation_id = conversation_id
        self.message_id = message_id
        self.metadata = metadata if metadata is not None else {}

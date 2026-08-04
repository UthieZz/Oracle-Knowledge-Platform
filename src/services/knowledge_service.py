class KnowledgeService:
    def __init__(self):
        pass

    def get_topics(self):
        return [
            {"name": "React", "conversations": 51, "size": "3.8 MB"},
            {"name": "Python", "conversations": 26, "size": "1.6 MB"},
            {"name": "Oracle", "conversations": 113, "size": "5.1 MB"}
        ]

    def get_entities(self):
        return [
            {"type": "Technology", "value": "Go", "count": 835},
            {"type": "Company", "value": "Meta", "count": 182}
        ]

    def load_object(self, object_id: str):
        return {"id": object_id, "content": "# Placeholder Content\nThis is placeholder markdown content for the object."}

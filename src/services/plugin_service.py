class PluginService:
    def __init__(self):
        self.plugins = [
            {"name": "ChatGPT Importer", "type": "Importer", "active": True, "version": "1.0.0"},
            {"name": "Gemini Importer",  "type": "Importer", "active": True, "version": "1.0.0"},
            {"name": "Entity Engine",    "type": "Analyzer", "active": True, "version": "1.0.0"},
            {"name": "Markdown Compiler","type": "Compiler", "active": True, "version": "2.0.0"},
        ]

    def get_all_plugins(self):
        return self.plugins

    def toggle_plugin(self, plugin_name: str, active: bool):
        for p in self.plugins:
            if p["name"] == plugin_name:
                p["active"] = active
                break
        return self.plugins

class ProjectService:
    def __init__(self):
        self.current_project = None

    def create_project(self, name: str, path: str):
        self.current_project = {"name": name, "path": path}
        return self.current_project

    def load_project(self, path: str):
        self.current_project = {"name": "Loaded Project", "path": path}
        return self.current_project

    def get_current_project_info(self):
        return self.current_project

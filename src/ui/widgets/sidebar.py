from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import Signal

class Sidebar(QWidget):
    navigate = Signal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.buttons = {}
        
        self.add_nav_button("Dashboard", "dashboard")
        self.add_nav_button("Project Manager", "project_manager")
        self.add_nav_button("Import Wizard", "import_wizard")
        self.add_nav_button("Pipeline Runner", "pipeline_runner")
        self.add_nav_button("Knowledge Explorer", "knowledge_explorer")
        self.add_nav_button("Oracle Studio", "studio")
        self.add_nav_button("Settings", "settings")

        layout.addStretch()
        self.setLayout(layout)
        self.setFixedWidth(200)

    def add_nav_button(self, label: str, view_name: str):
        btn = QPushButton(label)
        btn.clicked.connect(lambda: self.navigate.emit(view_name))
        self.layout().addWidget(btn)
        self.buttons[view_name] = btn

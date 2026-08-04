from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

class ProjectManagerView(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Project Manager")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        
        self.info_label = QLabel("Create or Load a Knowledge Project")
        layout.addWidget(self.info_label)
        
        btn_layout = QHBoxLayout()
        self.create_btn = QPushButton("Create New Project")
        self.create_btn.clicked.connect(self.on_create)
        
        self.load_btn = QPushButton("Load Existing Project")
        self.load_btn.clicked.connect(self.on_load)
        
        btn_layout.addWidget(self.create_btn)
        btn_layout.addWidget(self.load_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        self.setLayout(layout)

    def on_create(self):
        res = self.controller.project_service.create_project("New Project", "/mock/path")
        self.info_label.setText(f"Created Project: {res['name']}")

    def on_load(self):
        res = self.controller.project_service.load_project("/mock/path")
        self.info_label.setText(f"Loaded Project: {res['name']}")

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Qt

class DashboardView(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        
        self.status_label = QLabel("Loading project data...")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        self.setLayout(layout)

    def showEvent(self, event):
        super().showEvent(event)
        # Fetch mock data
        proj = self.controller.project_service.get_current_project_info()
        if proj:
            self.status_label.setText(f"Active Project: {proj['name']} at {proj['path']}")
        else:
            self.status_label.setText("No project loaded.")

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class StudioView(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Oracle Studio View (Stub)"))
        self.setLayout(layout)
        
    def refresh_data(self):
        pass

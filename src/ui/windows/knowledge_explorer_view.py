from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem

class KnowledgeExplorerView(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Knowledge Explorer")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Item", "Details"])
        layout.addWidget(self.tree)
        
        self.setLayout(layout)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_data()

    def refresh_data(self):
        self.tree.clear()
        
        # Load Mock Topics
        topics = self.controller.knowledge_service.get_topics()
        topics_root = QTreeWidgetItem(self.tree, ["Topics", f"Total: {len(topics)}"])
        for t in topics:
            QTreeWidgetItem(topics_root, [t['name'], f"{t['conversations']} convs, {t['size']}"])
            
        # Load Mock Entities
        entities = self.controller.knowledge_service.get_entities()
        entities_root = QTreeWidgetItem(self.tree, ["Entities", f"Total: {len(entities)}"])
        for e in entities:
            QTreeWidgetItem(entities_root, [e['value'], f"{e['type']} ({e['count']})"])
            
        self.tree.expandAll()

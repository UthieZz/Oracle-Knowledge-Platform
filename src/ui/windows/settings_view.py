from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox, QHBoxLayout

class SettingsView(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Settings & Plugins")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        
        self.plugin_layout = QVBoxLayout()
        layout.addLayout(self.plugin_layout)
        
        layout.addStretch()
        self.setLayout(layout)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_plugins()

    def refresh_plugins(self):
        # Clear existing
        for i in reversed(range(self.plugin_layout.count())): 
            widget = self.plugin_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                
        plugins = self.controller.plugin_service.get_all_plugins()
        for p in plugins:
            cb = QCheckBox(f"{p['name']} ({p['type']} v{p['version']})")
            cb.setChecked(p['active'])
            
            # Use default arguments in lambda to capture current value of 'p'
            cb.toggled.connect(lambda checked, plugin=p: self.controller.plugin_service.toggle_plugin(plugin['name'], checked))
            self.plugin_layout.addWidget(cb)

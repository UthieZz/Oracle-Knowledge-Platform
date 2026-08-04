from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget
from src.ui.widgets.sidebar import Sidebar
from src.ui.windows.dashboard_view import DashboardView
from src.ui.windows.project_manager_view import ProjectManagerView
from src.ui.windows.import_wizard_view import ImportWizardView
from src.ui.windows.pipeline_runner_view import PipelineRunnerView
from src.ui.windows.knowledge_explorer_view import KnowledgeExplorerView
from src.ui.windows.settings_view import SettingsView
from src.studio.ui.studio_view import StudioView

class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Oracle Knowledge Compiler")
        self.resize(1024, 768)
        
        # Main Layout (Sidebar + Stacked Content)
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.navigate.connect(self.switch_view)
        
        # Stacked Widget for Views
        self.stacked_widget = QStackedWidget()
        
        # Initialize Views
        self.views = {
            "dashboard": DashboardView(self.controller),
            "project_manager": ProjectManagerView(self.controller),
            "import_wizard": ImportWizardView(self.controller),
            "pipeline_runner": PipelineRunnerView(self.controller),
            "knowledge_explorer": KnowledgeExplorerView(self.controller),
            "studio": StudioView(self.controller.studio_controller),
            "settings": SettingsView(self.controller)
        }
        
        # Add Views to Stack
        for view in self.views.values():
            self.stacked_widget.addWidget(view)
            
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stacked_widget)
        
        self.setCentralWidget(central_widget)
        
        # Default view
        self.switch_view("studio")

    def switch_view(self, view_name: str):
        if view_name in self.views:
            self.stacked_widget.setCurrentWidget(self.views[view_name])
            if hasattr(self.views[view_name], "refresh_data"):
                self.views[view_name].refresh_data()

import sys
import os

# Add the project root to sys.path so we can import src modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from src.controllers.main_controller import MainController
from src.ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Initialize the main controller (which initializes the services)
    controller = MainController()
    
    # Initialize the main window and inject the controller
    window = MainWindow(controller)
    controller.set_main_window(window)
    
    # Show the UI
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

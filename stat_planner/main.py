import sys
from PyQt6.QtWidgets import QApplication
from .main_gui import StatPlannerGUI

def main():
    app = QApplication(sys.argv)
    window = StatPlannerGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

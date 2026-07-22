import sys

from PySide6.QtWidgets import QApplication

from mingo_assistant.ui.main_window import MainWindow
from mingo_assistant.ui.styles import APP_STYLESHEET


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Mingo Assistant")
    app.setStyleSheet(APP_STYLESHEET)

    window = MainWindow()
    window.show()

    return app.exec()

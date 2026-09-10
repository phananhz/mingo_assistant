from __future__ import annotations

import sys
import unittest

from PySide6.QtWidgets import QApplication, QWidget

from mingo_assistant.ui.main_window import MainWindow


class NavigationVisibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_sidebar_is_restored_when_stack_returns_from_a_fullscreen_workflow(self) -> None:
        window = MainWindow()
        try:
            window._apply_layout_structure("default")
            self.assertFalse(window.sidebar.isHidden())

            workspace = QWidget()
            window.current_workspace = workspace
            window.stack.addWidget(workspace)
            window.stack.setCurrentWidget(workspace)
            self.assertTrue(window.sidebar.isHidden())

            window.stack.setCurrentWidget(window.business_page)
            self.assertFalse(window.sidebar.isHidden())

            documents = QWidget()
            window.current_documents_view = documents
            window.stack.addWidget(documents)
            window.stack.setCurrentWidget(documents)
            self.assertTrue(window.sidebar.isHidden())

            window.stack.setCurrentWidget(window.dependent_units_page)
            self.assertFalse(window.sidebar.isHidden())
        finally:
            window.close()
            window.deleteLater()


if __name__ == "__main__":
    unittest.main()
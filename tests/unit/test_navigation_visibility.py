from __future__ import annotations

import sys
import unittest

from PySide6.QtWidgets import QApplication, QLabel, QWidget

from mingo_assistant.models.case import CaseSummary
from mingo_assistant.ui.main_window import MainWindow
from mingo_assistant.ui.views.location_business_workspace import LOCATION_CASE_TYPE


class NavigationVisibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_dependent_cases_are_shown_only_in_section_four(self) -> None:
        window = MainWindow()
        try:
            company_case = CaseSummary(
                id="company-test", company_name="Company A", case_type="TNHH một thành viên",
                owner="Owner", updated_at="10/09/2026", status="Bản nháp",
                condition="Đủ dữ liệu", members=1, capital="100",
            )
            location_case = CaseSummary(
                id="location-test", company_name="Địa điểm A", case_type=LOCATION_CASE_TYPE,
                owner="Owner", updated_at="10/09/2026", status="Bản nháp",
                condition="Đủ dữ liệu", members=0, capital="Không áp dụng",
            )
            window.cases = [company_case, location_case]
            window._refresh_cases()
            self.assertNotIn(location_case, window._filtered_cases())
            self.assertEqual("4. Thủ tục của\nđơn vị phụ thuộc", window.nav_buttons["dependent_units"].text())
            dependent_widgets = [
                item_widget
                for index in range(window.dependent_cases_layout.count())
                if (item_widget := window.dependent_cases_layout.itemAt(index).widget()) is not None
            ]
            self.assertTrue(
                any(
                    any(label.text() == "Địa điểm A" for label in card.findChildren(QLabel))
                    for card in dependent_widgets
                    if card is not None
                )
            )
        finally:
            window.close()
            window.deleteLater()
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
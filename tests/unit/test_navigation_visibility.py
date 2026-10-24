from __future__ import annotations

import sys
import unittest

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication, QLabel, QWidget
import shiboken6

from mingo_assistant.models.case import CaseSummary
from mingo_assistant.ui.main_window import MainWindow, NAV_ITEMS
from mingo_assistant.ui.views.household_business_workspace import (
    HOUSEHOLD_BUSINESS_CASE_TYPE,
    HouseholdBusinessWorkspace,
)
from mingo_assistant.ui.views.location_business_workspace import LOCATION_CASE_TYPE


class NavigationVisibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_templates_follows_section_five_and_legacy_lookup_is_hidden_in_every_menu(self) -> None:
        window = MainWindow()
        try:
            keys = [key for key, _label in NAV_ITEMS]
            self.assertEqual(keys.index("household_business") + 1, keys.index("templates"))
            for menu in (window.nav_buttons, window.top_nav_buttons, window.slim_nav_buttons):
                self.assertIn("templates", menu)
                self.assertIn("industry_lookup", menu)
                self.assertNotIn("legacy_industry_lookup", menu)
                self.assertEqual(keys, list(menu))
            self.assertEqual("6. Biểu mẫu", window.nav_buttons["templates"].text())
            self.assertEqual("6. Biểu mẫu", window.top_nav_buttons["templates"].text())
            self.assertEqual("6. Biểu mẫu", window.slim_nav_buttons["templates"].toolTip())
            # Hiding the entry must not remove the existing lookup implementation.
            self.assertIn("legacy_industry_lookup", window._navigation_page_registry())
        finally:
            window.close()
            window.deleteLater()

    def test_templates_entry_opens_its_own_placeholder_page_and_can_return(self) -> None:
        window = MainWindow()
        try:
            for menu in (window.nav_buttons, window.top_nav_buttons, window.slim_nav_buttons):
                window._select_nav("business_registration")
                menu["templates"].click()
                self.assertIs(window.templates_page, window.stack.currentWidget())
                self.assertEqual("templates", window._current_nav_key)
                self.assertIsNone(window.current_workspace)
                window._select_nav("templates", is_user_action=True)
                self.assertIs(window.templates_page, window.stack.currentWidget())
            labels = {label.text() for label in window.templates_page.findChildren(QLabel)}
            self.assertIn("Biểu mẫu", labels)
            self.assertEqual(2, len(window.templates_page.group_buttons))
            self.assertFalse(window.templates_page.use_template_button.isEnabled())
            window._select_nav("household_business")
            self.assertIs(window.household_business_page, window.stack.currentWidget())
            window._select_nav("industry_lookup")
            self.assertIs(window.industry_lookup_page, window.stack.currentWidget())
        finally:
            window.close()
            window.deleteLater()

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
            self.assertEqual("1 hồ sơ", window.dependent_cases_count_label.text())
            self.assertEqual(window._card_column_count(), window.current_dependent_card_columns)
            self.assertEqual(Qt.ScrollBarAlwaysOff, window.dependent_cases_scroll.horizontalScrollBarPolicy())
            self.assertFalse(
                any(widget.objectName() == "CreateCard" for widget in window.dependent_units_page.findChildren(QWidget))
            )
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

    def test_household_business_is_section_five_and_has_its_own_case_list(self) -> None:
        window = MainWindow()
        try:
            household_case = CaseSummary(
                id="household-test",
                company_name="Hộ kinh doanh An Nhiên",
                case_type=HOUSEHOLD_BUSINESS_CASE_TYPE,
                owner="Nguyễn Văn An",
                updated_at="18/10/2026",
                status="Bản nháp",
                condition="Thiếu thông tin",
                members=1,
                capital="100.000.000",
            )
            window.cases = [household_case]
            window._refresh_cases()

            self.assertEqual(
                "5. Thủ tục thành lập\nhộ kinh doanh",
                window.nav_buttons["household_business"].text(),
            )
            self.assertNotIn(household_case, window._filtered_cases())
            self.assertEqual("1 hồ sơ", window.household_cases_count_label.text())
            self.assertTrue(window.household_intro.isHidden())
            self.assertFalse(window.household_cases_group.isHidden())
            household_widgets = [
                item_widget
                for index in range(window.household_cases_layout.count())
                if (item_widget := window.household_cases_layout.itemAt(index).widget()) is not None
            ]
            self.assertTrue(
                any(
                    any(label.toolTip() == "Hộ kinh doanh An Nhiên" for label in card.findChildren(QLabel))
                    for card in household_widgets
                )
            )
        finally:
            window.close()
            window.deleteLater()

    def test_empty_household_section_reuses_existing_intro_cards(self) -> None:
        window = MainWindow()
        try:
            window.cases = []
            window._refresh_cases()
            window._select_nav("household_business")

            self.assertTrue(window.household_cases_group.isHidden())
            self.assertFalse(window.household_intro.isHidden())
            self.assertTrue(
                any(widget.objectName() == "CreateCard" for widget in window.household_intro.findChildren(QWidget))
            )
            intro_texts = {label.text() for label in window.household_intro.findChildren(QLabel)}
            self.assertIn("Tạo hồ sơ mới", intro_texts)
            self.assertIn("Thành lập hộ kinh doanh", intro_texts)
        finally:
            window.close()
            window.deleteLater()

    def test_household_section_opens_workspace_and_returns_to_its_own_page(self) -> None:
        window = MainWindow()
        try:
            window._select_nav("household_business")
            self.assertIs(window.household_business_page, window.stack.currentWidget())

            window._open_household_business_workspace()
            self.assertIsInstance(window.current_workspace, HouseholdBusinessWorkspace)
            self.assertEqual("household_business", window._current_nav_key)

            window.current_workspace.on_back()
            self.assertIs(window.household_business_page, window.stack.currentWidget())
        finally:
            window.close()
            window.deleteLater()

    def test_replacing_fullscreen_views_keeps_one_live_transient_widget(self) -> None:
        window = MainWindow()
        retired: list[QWidget] = []
        try:
            baseline = window.stack.count()
            for _ in range(6):
                workspace = QWidget()
                current = window.current_workspace
                if current is not None:
                    retired.append(current)
                window._show_transient_view("current_workspace", workspace)
                self.assertEqual(baseline + 1, window.stack.count())
                self.assertIs(workspace, window.current_workspace)
                self.assertIsNone(window.current_documents_view)

            retired.append(window.current_workspace)
            documents = QWidget()
            window._show_transient_view("current_documents_view", documents)
            self.assertEqual(baseline + 1, window.stack.count())
            self.assertIsNone(window.current_workspace)
            self.assertIs(documents, window.current_documents_view)

            self.app.processEvents()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            self.assertTrue(all(not shiboken6.isValid(widget) for widget in retired))
        finally:
            window.close()
            window.deleteLater()


if __name__ == "__main__":
    unittest.main()

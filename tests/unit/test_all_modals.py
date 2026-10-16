import sys
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication

from mingo_assistant.ui.dialogs.business_amendment_modal import (
    AMENDMENT_PROCEDURES,
    BusinessAmendmentModal,
)
from mingo_assistant.ui.dialogs.dependent_unit_modal import (
    UNIT_TYPE_SPECS,
    DependentUnitModal,
)
from mingo_assistant.ui.dialogs.dissolution_modal import (
    DISSOLUTION_COMPANY_TYPES,
    TAX_STATUS_OPTIONS,
    DissolutionModal,
)
from mingo_assistant.ui.main_window import NAV_ITEMS, MainWindow


class TestAllModalsAndNavigation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    # 1. BusinessAmendmentModal tests
    def test_business_amendment_modal_data_and_selection(self):
        self.assertEqual(len(AMENDMENT_PROCEDURES), 5)
        modal = BusinessAmendmentModal()
        self.assertEqual(modal.modal_box.width(), 980)
        self.assertEqual(len(modal.procedure_widgets), 5)
        self.assertIsNotNone(modal.selected_option)
        self.assertEqual(modal.selected_option.id, "amend_address")
        self.assertTrue(modal.create_button.isEnabled())

        # Select another procedure
        modal._on_procedure_selected("amend_capital")
        self.assertEqual(modal.selected_option.id, "amend_capital")
        self.assertIn("Thay đổi vốn điều lệ", modal.selected_summary_label.text())

        # Emit signal on create
        events = []
        modal.procedure_chosen.connect(lambda pid, pname, ready: events.append((pid, pname, ready)))
        modal._on_create_clicked()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][0], "amend_capital")

    # 2. DependentUnitModal tests
    def test_dependent_unit_modal_switching_and_selection(self):
        self.assertEqual(len(UNIT_TYPE_SPECS), 3)
        modal = DependentUnitModal()
        self.assertEqual(modal.current_unit_id, "chi_nhanh")
        self.assertTrue(modal.unit_cards["chi_nhanh"].is_active)
        self.assertEqual(len(modal.procedure_items), 3)
        self.assertEqual(modal.selected_procedure.id, "cn_create")

        # Switch to Văn phòng đại diện
        modal._on_unit_card_clicked("vpdd")
        self.assertEqual(modal.current_unit_id, "vpdd")
        self.assertTrue(modal.unit_cards["vpdd"].is_active)
        self.assertEqual(len(modal.procedure_items), 3)
        self.assertEqual(modal.selected_procedure.unit_type_id, "vpdd")

        # Switch to Địa điểm kinh doanh
        modal._on_unit_card_clicked("ddkd")
        self.assertEqual(modal.current_unit_id, "ddkd")
        self.assertEqual(modal.selected_procedure.unit_type_id, "ddkd")

        # Emit signal on create
        events = []
        modal.procedure_chosen.connect(lambda ut, act, title, ready: events.append((ut, act, title, ready)))
        modal._on_create_clicked()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][0], "ddkd")

    # 3. DissolutionModal tests
    def test_dissolution_modal_matrix_selection(self):
        self.assertEqual(len(DISSOLUTION_COMPANY_TYPES), 3)
        self.assertEqual(len(TAX_STATUS_OPTIONS), 2)

        modal = DissolutionModal()
        self.assertEqual(modal.current_type_id, "tnhh_1tv")
        self.assertTrue(modal.company_cards["tnhh_1tv"].is_active)
        self.assertEqual(modal.selected_tax_status.id, "locked_mst")
        self.assertIn("TNHH một thành viên", modal.selected_summary_label.text())
        self.assertIn("bị khóa", modal.selected_summary_label.text())

        # Switch company type to Co Phan
        modal._on_type_card_clicked("co_phan")
        self.assertEqual(modal.current_type_id, "co_phan")
        self.assertIn("cổ phần", modal.selected_summary_label.text())

        # Switch tax status to active_mst
        modal._on_tax_status_selected("active_mst")
        self.assertEqual(modal.selected_tax_status.id, "active_mst")
        self.assertIn("không bị khóa", modal.selected_summary_label.text())

        # Emit signal on create
        events = []
        modal.dissolution_chosen.connect(lambda ct, st, title, ready: events.append((ct, st, title, ready)))
        modal._on_create_clicked()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][0], "co_phan")
        self.assertEqual(events[0][1], "active_mst")

    # 4. Navigation & MainWindow Integration tests
    def test_main_window_nav_items_architecture(self):
        keys = [item[0] for item in NAV_ITEMS]
        self.assertEqual(
            keys,
            [
                "business_registration",
                "business_amendment",
                "dissolution",
                "dependent_units",
                "industry_lookup",
                "trash",
            ],
        )

    def test_main_window_category_pages_routing(self):
        with patch.object(MainWindow, "__init__", return_value=None):
            win = MainWindow()
            win._open_business_creation_modal = MagicMock()
            win._open_business_amendment_modal = MagicMock()
            win._open_dependent_unit_modal = MagicMock()
            win._open_dissolution_modal = MagicMock()
            win._open_authorized_person_manager = MagicMock()
            win._refresh_industry_lookup = MagicMock()
            win._refresh_trash = MagicMock()
            win._show_coming_soon = MagicMock()

            win.nav_buttons = {}
            win.top_nav_buttons = {}
            win.slim_nav_buttons = {}
            win.stack = MagicMock()
            win.business_page = MagicMock()
            win.business_amendment_page = MagicMock()
            win.dependent_units_page = MagicMock()
            win.dissolution_page = MagicMock()
            win.industry_lookup_page = MagicMock()
            win.trash_page = MagicMock()
            win.coming_soon_page = MagicMock()

            # 1. Initial selection without user action sets page without opening modal
            win.stack.currentWidget.return_value = None
            win._select_nav("business_registration", is_user_action=False)
            win.stack.setCurrentWidget.assert_called_with(win.business_page)
            win._open_business_creation_modal.assert_not_called()

            # 2. User click while already active triggers modal
            win.stack.currentWidget.return_value = win.business_page
            win._select_nav("business_registration", is_user_action=True)
            win._open_business_creation_modal.assert_called_once()

            # 3. Amendment category
            win.stack.currentWidget.return_value = win.business_amendment_page
            win._select_nav("business_amendment", is_user_action=True)
            win._open_business_amendment_modal.assert_called_once()

            # 4. Dependent units category
            win.stack.currentWidget.return_value = win.dependent_units_page
            win._select_nav("dependent_units", is_user_action=True)
            win._open_dependent_unit_modal.assert_called_once()

            # 5. Dissolution category
            win.stack.currentWidget.return_value = win.dissolution_page
            win._select_nav("dissolution", is_user_action=True)
            win._open_dissolution_modal.assert_called_once()


if __name__ == "__main__":
    unittest.main()

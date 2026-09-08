import unittest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog

from mingo_assistant.ui.dialogs.business_creation_modal import (
    COMPANY_TYPE_SPECS,
    BusinessCreationModal,
    CompanyTypeCard,
    DossierListItem,
    DossierOption,
)


class TestBusinessCreationModal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_company_specs_data_integrity(self):
        self.assertEqual(len(COMPANY_TYPE_SPECS), 3)
        spec_ids = [spec["id"] for spec in COMPANY_TYPE_SPECS]
        self.assertIn("tnhh_1tv", spec_ids)
        self.assertIn("tnhh_2tv", spec_ids)
        self.assertIn("co_phan", spec_ids)

        tnhh_1tv = next(s for s in COMPANY_TYPE_SPECS if s["id"] == "tnhh_1tv")
        self.assertEqual(len(tnhh_1tv["dossiers"]), 1)
        self.assertTrue(tnhh_1tv["dossiers"][0].is_ready)
        self.assertEqual(tnhh_1tv["dossiers"][0].case_type, "TNHH một thành viên")

        tnhh_2tv = next(s for s in COMPANY_TYPE_SPECS if s["id"] == "tnhh_2tv")
        self.assertEqual(len(tnhh_2tv["dossiers"]), 2)
        self.assertFalse(tnhh_2tv["dossiers"][0].is_ready)
        self.assertEqual(tnhh_2tv["dossiers"][0].case_type, "TNHH hai thành viên (Cá nhân)")
        self.assertEqual(tnhh_2tv["dossiers"][1].case_type, "TNHH hai thành viên (Tổ chức)")

        co_phan = next(s for s in COMPANY_TYPE_SPECS if s["id"] == "co_phan")
        self.assertFalse(co_phan["dossiers"][0].is_ready)

    def test_company_type_card_selection(self):
        card = CompanyTypeCard("tnhh_1tv", "Công ty TNHH\nmột thành viên", "1 chủ sở hữu", "🏢")
        self.assertFalse(card.is_active)

        card.set_active(True)
        self.assertTrue(card.is_active)
        self.assertEqual(card.property("active"), "true")

        clicked_ids = []
        card.clicked.connect(clicked_ids.append)
        card.mousePressEvent(None)
        self.assertEqual(clicked_ids, ["tnhh_1tv"])

    def test_dossier_list_item_selection_and_activation(self):
        option = DossierOption(
            id="test_id",
            title="Hồ sơ thử nghiệm",
            description="Mô tả thử nghiệm",
            badge="Sẵn sàng",
            case_type="TNHH một thành viên",
            is_ready=True,
            icon="📄",
        )
        item = DossierListItem(option)
        self.assertFalse(item.is_selected)

        item.set_selected(True)
        self.assertTrue(item.is_selected)
        self.assertEqual(item.property("selected"), "true")

        selected_ids = []
        item.selected.connect(selected_ids.append)
        item.mousePressEvent(None)
        self.assertEqual(selected_ids, ["test_id"])

        activated_ids = []
        item.activated.connect(activated_ids.append)
        item.mouseDoubleClickEvent(None)
        self.assertEqual(activated_ids, ["test_id"])

    def test_modal_initial_state(self):
        modal = BusinessCreationModal()
        self.assertEqual(modal.modal_box.width(), 980)
        self.assertEqual(modal.current_type_id, "tnhh_1tv")
        self.assertTrue(modal.company_cards["tnhh_1tv"].is_active)
        self.assertFalse(modal.company_cards["tnhh_2tv"].is_active)
        self.assertFalse(modal.company_cards["co_phan"].is_active)

        # In TNHH 1TV, exactly 1 item is listed and auto-selected
        self.assertEqual(len(modal.dossier_items), 1)
        self.assertIsNotNone(modal.selected_dossier)
        self.assertEqual(modal.selected_dossier.case_type, "TNHH một thành viên")
        self.assertTrue(modal.selected_dossier.is_ready)
        self.assertTrue(modal.create_button.isEnabled())

    def test_modal_switching_types(self):
        modal = BusinessCreationModal()

        # Switch to TNHH 2TV
        modal._on_type_card_clicked("tnhh_2tv")
        self.assertEqual(modal.current_type_id, "tnhh_2tv")
        self.assertTrue(modal.company_cards["tnhh_2tv"].is_active)
        self.assertFalse(modal.company_cards["tnhh_1tv"].is_active)
        self.assertEqual(len(modal.dossier_items), 2)
        self.assertEqual(modal.selected_dossier.case_type, "TNHH hai thành viên (Cá nhân)")
        self.assertFalse(modal.selected_dossier.is_ready)

        # Switch to Co Phan
        modal._on_type_card_clicked("co_phan")
        self.assertEqual(modal.current_type_id, "co_phan")
        self.assertTrue(modal.company_cards["co_phan"].is_active)
        self.assertEqual(modal.selected_dossier.case_type, "Công ty cổ phần")
        self.assertFalse(modal.selected_dossier.is_ready)

    def test_modal_create_button_emits_and_accepts(self):
        modal = BusinessCreationModal()
        events = []
        modal.dossier_chosen.connect(lambda ct, ready: events.append((ct, ready)))

        modal._on_create_clicked()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0], ("TNHH một thành viên", True))

    def test_modal_custom_parent_frameless_geometry(self):
        parent_widget = QDialog()
        parent_widget.resize(1100, 800)
        modal = BusinessCreationModal(parent=parent_widget)
        self.assertTrue(modal.windowFlags() & Qt.FramelessWindowHint)
        self.assertEqual(modal.size(), parent_widget.size())

    def test_mainwindow_modal_ready_routes_to_workspace(self):
        from unittest.mock import MagicMock, patch
        from mingo_assistant.ui.main_window import MainWindow

        with patch.object(MainWindow, "__init__", return_value=None):
            win = MainWindow()
            win._open_new_business_case = MagicMock()
            win.stack = MagicMock()
            win.coming_soon_page = MagicMock()

            with patch("mingo_assistant.ui.dialogs.business_creation_modal.BusinessCreationModal") as MockModalCls:
                mock_modal = MagicMock()
                mock_modal.exec.return_value = QDialog.DialogCode.Accepted

                def fake_connect(callback):
                    callback("TNHH một thành viên", True)

                mock_modal.dossier_chosen.connect.side_effect = fake_connect
                MockModalCls.return_value = mock_modal

                win._open_business_creation_modal()

                win._open_new_business_case.assert_called_once()
                win.stack.setCurrentWidget.assert_not_called()

    def test_mainwindow_modal_not_ready_routes_to_coming_soon(self):
        from unittest.mock import MagicMock, patch
        from mingo_assistant.ui.main_window import MainWindow

        with patch.object(MainWindow, "__init__", return_value=None):
            win = MainWindow()
            win._open_new_business_case = MagicMock()
            win.stack = MagicMock()
            win.coming_soon_page = MagicMock()

            with patch("mingo_assistant.ui.dialogs.business_creation_modal.BusinessCreationModal") as MockModalCls:
                mock_modal = MagicMock()
                mock_modal.exec.return_value = QDialog.DialogCode.Accepted

                def fake_connect(callback):
                    callback("TNHH hai thành viên trở lên", False)

                mock_modal.dossier_chosen.connect.side_effect = fake_connect
                MockModalCls.return_value = mock_modal

                win._open_business_creation_modal()

                win._open_new_business_case.assert_not_called()
                win.stack.setCurrentWidget.assert_called_once_with(win.coming_soon_page)

    def test_mainwindow_modal_rejected_does_nothing(self):
        from unittest.mock import MagicMock, patch
        from mingo_assistant.ui.main_window import MainWindow

        with patch.object(MainWindow, "__init__", return_value=None):
            win = MainWindow()
            win._open_new_business_case = MagicMock()
            win.stack = MagicMock()
            win.coming_soon_page = MagicMock()

            with patch("mingo_assistant.ui.dialogs.business_creation_modal.BusinessCreationModal") as MockModalCls:
                mock_modal = MagicMock()
                mock_modal.exec.return_value = QDialog.DialogCode.Rejected
                MockModalCls.return_value = mock_modal

                win._open_business_creation_modal()

                win._open_new_business_case.assert_not_called()
                win.stack.setCurrentWidget.assert_not_called()

    def test_liquid_glass_modal_box_and_opacity_slider(self):
        from mingo_assistant.ui.dialogs.business_creation_modal import LiquidGlassModalBox
        modal = BusinessCreationModal()
        self.assertIsInstance(modal.modal_box, LiquidGlassModalBox)
        self.assertFalse(modal.modal_box._pixmap.isNull())
        self.assertGreaterEqual(modal.modal_box.bg_opacity, 0.0)
        self.assertLessEqual(modal.modal_box.bg_opacity, 1.0)

        # Slider inspection
        self.assertIsNotNone(modal.opacity_slider)
        self.assertEqual(modal.opacity_slider.minimum(), 0)
        self.assertEqual(modal.opacity_slider.maximum(), 100)
        self.assertEqual(modal.opacity_slider.value(), int(round(modal.modal_box.bg_opacity * 100)))

        # Adjust slider
        modal.opacity_slider.setValue(42)
        self.assertAlmostEqual(modal.modal_box.bg_opacity, 0.42, places=2)
        self.assertEqual(modal.opacity_val_label.text(), "42%")

    def test_tech_image_sidebar_in_main_window(self):
        from mingo_assistant.ui.main_window import MainWindow, TechImageSidebar
        win = MainWindow()
        self.assertIsInstance(win.sidebar, TechImageSidebar)
        self.assertFalse(win.sidebar._pixmap.isNull())

    def test_liquid_glass_sidebar_wallpaper_and_white_text(self):
        from mingo_assistant.ui.main_window import MainWindow
        from mingo_assistant.ui.styles import stylesheet_for_theme
        win = MainWindow()
        win._apply_layout_structure("liquid_glass")
        self.assertEqual(win.sidebar._layout_mode, "liquid_glass")
        self.assertIsNotNone(win.sidebar._liquid_glass_pixmap)
        self.assertFalse(win.sidebar._liquid_glass_pixmap.isNull())

        # Test that liquid glass stylesheet contains white text for sidebar
        css = stylesheet_for_theme("rose", layout="liquid_glass")
        self.assertIn("QFrame#Sidebar QLabel#AppTitle {color: #ffffff;", css)
        self.assertIn("QFrame#Sidebar QPushButton#NavButton", css)
        self.assertIn("color: rgba(255, 255, 255,", css)


if __name__ == "__main__":
    unittest.main()



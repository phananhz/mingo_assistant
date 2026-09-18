from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication, QCheckBox, QLineEdit, QTextEdit

from mingo_assistant.ui.dialogs.dependent_unit_modal import UNIT_TYPE_SPECS
from mingo_assistant.ui.views.location_business_update_workspace import (
    LOCATION_UPDATE_CASE_TYPE,
    LOCATION_UPDATE_TEMPLATE_FOLDER,
    UPDATE_FIELD_GROUPS,
    LocationBusinessUpdateWorkspace,
)


class LocationBusinessUpdateWorkspaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_update_has_change_selection_and_legal_signer(self) -> None:
        ddkd = next(spec for spec in UNIT_TYPE_SPECS if spec["id"] == "ddkd")
        option = next(item for item in ddkd["procedures"] if item.id == "ddkd_update")
        self.assertTrue(option.is_ready)
        self.assertEqual("Thay \u0111\u1ed5i n\u1ed9i dung \u0111\u1ecba \u0111i\u1ec3m kinh doanh", option.title)

        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = LocationBusinessUpdateWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
            )
            try:
                self.assertEqual(
                    project_root / "assets" / "templates" / "word" / Path(*LOCATION_UPDATE_TEMPLATE_FOLDER),
                    workspace._template_and_export_dirs()[0],
                )
                self.assertEqual([title for title, _fields in UPDATE_FIELD_GROUPS], list(workspace.form_sections))
                self.assertEqual("Th\u00f4ng tin ng\u01b0\u1eddi \u0111\u01b0\u1ee3c \u1ee7y quy\u1ec1n", list(workspace.form_sections)[-1])
                self.assertNotIn("Ng\u00e0nh ngh\u1ec1 kinh doanh", workspace.form_sections)
                self.assertIn("location_business_name", workspace.fields)
                self.assertIn("location_business_code", workspace.fields)
                self.assertIn("tax_labor_count", workspace.fields)
                self.assertNotIn("change_detail_selector", vars(workspace))
                self.assertTrue(hasattr(workspace, "update_organization_selector"))
                self.assertEqual(1, workspace.update_organization_selector.count())
                workspace.personal_profiles.append({"personal_full_name": "PERSONAL PROFILE"})
                workspace.organization_profiles.append({
                    "organization_owner_name": "ORGANIZATION PROFILE",
                    "organization_owner_registration_number": "0312345678",
                    "organization_owner_address_detail": "1 Sample Street",
                    "organization_owner_ward": "Sample Ward",
                    "organization_owner_province": "Ha Noi",
                    "organization_owner_country": "Viet Nam",
                })
                workspace._refresh_update_organization_selector()
                self.assertEqual(2, workspace.update_organization_selector.count())
                self.assertEqual("profile:0", workspace.update_organization_selector.itemData(1))
                self.assertNotIn("PERSONAL PROFILE", workspace.update_organization_selector.itemText(1))
                workspace.update_organization_selector.setCurrentIndex(1)
                self.assertEqual("ORGANIZATION PROFILE", workspace.fields["parent_entity_name"].text())
                selected = workspace.fields["change_address_selected"]
                self.assertIsInstance(selected, QCheckBox)
                self.assertTrue(workspace.change_forms["change_address_selected"].isHidden())
                selected.setChecked(True)
                self.assertFalse(workspace.change_forms["change_address_selected"].isHidden())
                self.assertTrue(workspace.change_option_cards["change_address_selected"].property("selected"))
                self.assertFalse(workspace.fields["change_address_selected"].icon().isNull())
                self.assertIn("QCheckBox::indicator { image: none; width: 0px", workspace.fields["change_address_selected"].styleSheet())
                self.assertIn("border: 2px solid #6f58c9", workspace.change_option_cards["change_address_selected"].styleSheet())
                self.assertTrue(workspace.change_option_indicators["change_address_selected"].isHidden())
                workspace.fields["new_location_address_detail"].setText("1 Sample Street")
                self.assertTrue(workspace.change_option_cards["change_address_selected"].property("completed"))
                self.assertIn("border: 2px solid #21874b", workspace.change_option_cards["change_address_selected"].styleSheet())
                self.assertFalse(workspace.change_option_indicators["change_address_selected"].isHidden())
                self.assertTrue(all(title.startswith("\u0110\u0103ng k\u00fd") for _key, title, _fields in workspace.change_options))
                self.assertIn("new_location_phone", workspace.fields)
                self.assertIn("new_location_website", workspace.fields)
                business_lines = workspace.fields["change_business_lines_selected"]
                business_lines.setChecked(True)
                self.assertFalse(workspace.change_forms["change_business_lines_selected"].isHidden())
                workspace.fields["change_name_selected"].setChecked(True)
                visible_in_template_order = [
                    key for key in workspace.change_form_order
                    if not workspace.change_forms[key].isHidden()
                ]
                self.assertEqual(
                    ["change_name_selected", "change_address_selected", "change_business_lines_selected"],
                    visible_in_template_order,
                )
                self.assertTrue(hasattr(workspace, "business_line_table"))
                self.assertEqual(7, len(workspace.business_line_rows))
                self.assertTrue(workspace.business_line_rows[0].main_checkbox.isEnabled())
                workspace.business_line_rows[0].main_checkbox.setChecked(True)
                workspace.business_line_rows[1].main_checkbox.setChecked(True)
                self.assertFalse(workspace.business_line_rows[0].main_checkbox.isChecked())
                self.assertTrue(workspace.business_line_rows[1].main_checkbox.isChecked())
                self.assertIn("m\u1ed9t ng\u00e0nh", workspace.business_line_rows[0].main_checkbox.toolTip())
                # The seven rows in the notification template are only sample
                # rows. The shared industry editor must continue adding rows
                # for a dossier with more industries.
                for _ in range(8):
                    self.assertTrue(workspace._append_business_line_row(visible=True))
                self.assertEqual(15, len(workspace.business_line_rows))
                workspace.business_line_rows[-1].name_field.setText("LINE FIFTEEN")
                workspace.business_line_rows[-1].code_field.setText("1515")
                self.assertTrue(workspace._change_option_has_entered_data("change_business_lines_selected", ()))
                manual_x = workspace.fields["tax_accounting_independent_x"]
                self.assertIsInstance(manual_x, QCheckBox)
                self.assertFalse(manual_x.isEnabled())
                self.assertIn("Ph\u1ea7n n\u00e0y c\u1ea7n \u0111i\u1ec1n th\u1ee7 c\u00f4ng", manual_x.text())
                self.assertIsInstance(workspace.fields["tax_notification_phone"], QLineEdit)
                self.assertFalse(workspace.fields["tax_notification_phone"].isReadOnly())
                self.assertFalse(workspace.fields["tax_notification_email"].isReadOnly())
                supplemental = workspace.fields["supplemental_registration_content"]
                self.assertIsInstance(supplemental, QTextEdit)
                supplemental.setPlainText("N\u1ed9i dung b\u1ed5 sung\nD\u00f2ng th\u1ee9 hai\n\nD\u00f2ng th\u1ee9 t\u01b0")
                self.assertFalse(workspace.fields["change_supplemental_selected"].isChecked())
                self.assertFalse(workspace.change_option_indicators["change_supplemental_selected"].isHidden())
                workspace.fields["legal_representative_full_name"].setText("NGUYEN VAN A")
                values = workspace.form_values()
                self.assertEqual(
                    "N\u1ed9i dung b\u1ed5 sung\nD\u00f2ng th\u1ee9 hai\n\nD\u00f2ng th\u1ee9 t\u01b0",
                    values["supplemental_registration_content"],
                )
                self.assertEqual(values["supplemental_registration_content"], values["supplemental_registration_content_1"])
                self.assertEqual("", values["supplemental_registration_content_2"])
                self.assertEqual("", values["supplemental_registration_content_3"])
                self.assertEqual("", values["tax_accounting_independent_x"])
                self.assertEqual("X", values["business_line_2_is_main"])
                self.assertEqual("NGUYEN VAN A", values["signer_full_name"])
                self.assertEqual("X", values["change_address_selected"])
                self.assertEqual("", values["change_supplemental_selected"])
                self.assertEqual(LOCATION_UPDATE_CASE_TYPE, workspace.build_case_summary().case_type)
            finally:
                workspace.deleteLater()

    def test_entered_change_data_keeps_its_marker_after_the_form_is_collapsed(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = LocationBusinessUpdateWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
            )
            try:
                selected = workspace.fields["change_address_selected"]
                selected.setChecked(True)
                workspace.fields["new_location_phone"].setText("0901000001")
                self.assertFalse(workspace.change_option_indicators["change_address_selected"].isHidden())
                selected.setChecked(False)
                self.assertTrue(workspace.change_forms["change_address_selected"].isHidden())
                self.assertFalse(workspace.change_option_indicators["change_address_selected"].isHidden())
                workspace.fields["new_location_phone"].clear()
                self.assertTrue(workspace.change_option_indicators["change_address_selected"].isHidden())
            finally:
                workspace.deleteLater()

    def test_person_dropdowns_fill_manager_and_accountant_and_warn_on_matching_id(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = LocationBusinessUpdateWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
            )
            try:
                person = workspace.ocr_people[0]
                person.data = {
                    "legal_representative_full_name": "NGUYEN VAN A",
                    "legal_representative_date_of_birth": "01/01/1990",
                    "legal_representative_gender": "Nam",
                    "legal_representative_id_number": "001090000001",
                    "personal_phone": "0901000001",
                }
                workspace._refresh_person_fill_selectors()
                workspace.fields["change_manager_selected"].setChecked(True)
                manager_selector = workspace.person_fill_selectors["location_manager"]
                manager_selector.setCurrentIndex(1)
                workspace.fields["legal_representative_id_number"].setText("001090000001")
                self.assertEqual("001090000001", workspace.fields["location_manager_id_number"].text())
                self.assertFalse(workspace.location_manager_identity_warning.isHidden())
                workspace.fields["change_tax_selected"].setChecked(True)
                accountant_selector = workspace.person_fill_selectors["tax_accountant"]
                accountant_selector.setCurrentIndex(1)
                self.assertEqual("Nam", workspace.fields["tax_accountant_gender"].text())
                self.assertEqual("001090000001", workspace.fields["tax_accountant_id_number"].text())
                self.assertEqual("0901000001", workspace.fields["tax_accountant_phone"].text())
            finally:
                workspace.deleteLater()

    def test_update_accepts_unlimited_supplemental_lines(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = LocationBusinessUpdateWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
            )
            try:
                values = {"supplemental_registration_content": "one\ntwo\nthree\nfour"}
                self.assertNotIn(
                    "N\u1ed9i dung b\u1ed5 sung, c\u1eadp nh\u1eadt ch\u1ec9 h\u1ed7 tr\u1ee3 t\u1ed1i \u0111a 3 d\u00f2ng theo m\u1eabu Word",
                    workspace._missing_required_fields(values),
                )
            finally:
                workspace.deleteLater()


    def test_business_line_change_requires_a_main_business_line(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = LocationBusinessUpdateWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
            )
            try:
                values = {
                    "business_registration_office": "Phòng Đăng ký kinh doanh",
                    "parent_entity_name": "COMPANY SAMPLE",
                    "parent_entity_registration_number": "0312345678",
                    "legal_representative_full_name": "NGUYEN VAN A",
                    "legal_representative_id_number": "001090000001",
                    "legal_representative_position": "Director",
                    "authorized_person_full_name": "TRAN THI B",
                    "authorized_person_id_number": "001090000002",
                    "authorized_person_contact_address": "Sample address",
                    "location_business_name": "LOCATION SAMPLE",
                    "location_business_code": "00001",
                    "business_line_1_name": "LINE ONE",
                    "business_line_1_code": "6201",
                }
                missing = workspace._missing_required_fields(values)
                self.assertIn("Đăng ký thay đổi ngành, nghề kinh doanh phải chọn một ngành nghề kinh doanh chính", missing)
                self.assertNotIn("Cần nhập ít nhất một nội dung đăng ký thay đổi", missing)
            finally:
                workspace.deleteLater()
if __name__ == "__main__":
    unittest.main()

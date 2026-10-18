from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton

from mingo_assistant.ui.views.business_registration_workspace import (
    BusinessRegistrationWorkspace,
)
from mingo_assistant.models.business_registration import OcrPerson
from mingo_assistant.services.documents.household_business_generator import (
    HouseholdBusinessTemplateGenerator,
)
from mingo_assistant.ui.views.household_business_workspace import (
    HOUSEHOLD_BUSINESS_CASE_TYPE,
    HOUSEHOLD_CAPITAL_SECTION,
    HOUSEHOLD_DETAILS_SECTION,
    HOUSEHOLD_OWNER_SECTION,
    HOUSEHOLD_TAX_SECTION,
    HouseholdBusinessWorkspace,
)


ROOT = Path(__file__).resolve().parents[2]


class HouseholdBusinessWorkspaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def _workspace(self, export_root: Path) -> HouseholdBusinessWorkspace:
        return HouseholdBusinessWorkspace(
            on_back=lambda: None,
            on_save=lambda case: None,
            bundle_root=ROOT,
            default_export_root=export_root,
        )

    def test_reuses_registration_form_and_cccd_scanner_and_enables_export(self) -> None:
        self.assertTrue(issubclass(HouseholdBusinessWorkspace, BusinessRegistrationWorkspace))
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self._workspace(Path(temp_dir))
            try:
                buttons = workspace.findChildren(QPushButton)
                button_texts = {button.text() for button in buttons}
                self.assertIn("Quét tài liệu", button_texts)
                self.assertIn("+ Thêm người", button_texts)
                export_buttons = [button for button in buttons if button.text() == "Xuất hồ sơ"]
                self.assertTrue(export_buttons)
                self.assertTrue(all(button.isEnabled() for button in export_buttons))
                self.assertEqual("qr", workspace.ocr_engine_input.currentData())
                self.assertIn("applicant_id_number", workspace.fields)
                self.assertIn("company_name", workspace.fields)
            finally:
                workspace.deleteLater()

    def test_authorized_person_name_is_uppercased_in_field_and_form_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self._workspace(Path(temp_dir))
            try:
                name_field = workspace.fields["authorized_person_full_name"]
                self.assertIsInstance(name_field, QLineEdit)

                name_field.setText("Mai Xuân Lương")

                self.assertEqual("MAI XUÂN LƯƠNG", name_field.text())
                self.assertEqual(
                    "MAI XUÂN LƯƠNG",
                    workspace.form_values()["authorized_person_full_name"],
                )
            finally:
                workspace.deleteLater()

    def test_owner_dropdown_keeps_hidden_authorization_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self._workspace(Path(temp_dir))
            try:
                person = OcrPerson(
                    "Nguyễn Văn Chủ Hộ",
                    role="applicant",
                    data={
                        "legal_representative_full_name": "Nguyễn Văn Chủ Hộ",
                        "legal_representative_id_number": "001090000001",
                        "legal_representative_date_of_birth": "01/01/1990",
                        "legal_representative_gender": "Nam",
                        "legal_representative_issue_date": "02/02/2021",
                        "legal_representative_issue_place": "Bộ Công an",
                        "legal_representative_permanent_address": "01 Đường Mẫu, Hà Nội",
                    },
                )
                workspace._fill_section_from_person("applicant", person)
                values = workspace.form_values()
                self.assertEqual("Nguyễn Văn Chủ Hộ", values["household_owner_full_name"])
                self.assertEqual("02/02/2021", values["household_owner_issue_date"])
                self.assertEqual("Bộ Công an", values["household_owner_issue_place"])
                self.assertEqual("01 Đường Mẫu, Hà Nội", values["household_owner_contact_address"])
            finally:
                workspace.deleteLater()

    def test_household_export_uses_its_own_generator_and_template_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self._workspace(Path(temp_dir))
            try:
                template_dir, export_root = workspace._template_and_export_dirs()
                self.assertIs(HouseholdBusinessTemplateGenerator, workspace._document_generator_class())
                self.assertEqual(ROOT / "assets" / "templates" / "word" / "household_business", template_dir)
                self.assertEqual(Path(temp_dir), export_root)
            finally:
                workspace.deleteLater()

    def test_saved_draft_keeps_household_case_type_and_migrates_early_keys(self) -> None:
        migrated = HouseholdBusinessWorkspace._registration_compatible_values(
            {
                "household_business_name": "Hộ kinh doanh An Nhiên",
                "household_owner_full_name": "Nguyễn Văn An",
                "household_owner_id_number": "001090000001",
            }
        )
        self.assertEqual("Hộ kinh doanh An Nhiên", migrated["company_name"])
        self.assertEqual("Nguyễn Văn An", migrated["applicant_full_name"])
        self.assertEqual("001090000001", migrated["applicant_id_number"])

        legacy_registration = HouseholdBusinessWorkspace._registration_compatible_values(
            {
                "legal_representative_full_name": "Nguyễn Văn Cũ",
                "legal_representative_id_number": "001090000009",
                "company_foreign_name": "OLD HOUSEHOLD NAME",
            }
        )
        self.assertEqual("Nguyễn Văn Cũ", legacy_registration["applicant_full_name"])
        self.assertEqual("001090000009", legacy_registration["applicant_id_number"])
        self.assertEqual("OLD HOUSEHOLD NAME", legacy_registration["company_english_name"])

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self._workspace(Path(temp_dir))
            try:
                workspace._set_field("company_name", "Hộ kinh doanh An Nhiên")
                summary = workspace.build_case_summary()
                self.assertEqual(HOUSEHOLD_BUSINESS_CASE_TYPE, summary.case_type)
                self.assertEqual("Hộ kinh doanh An Nhiên", summary.company_name)
                self.assertEqual(
                    str(workspace.FORM_SCHEMA_VERSION),
                    summary.form_values["household_schema_version"],
                )
            finally:
                workspace.deleteLater()

    def test_receiving_office_and_signing_place_are_manual_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self._workspace(Path(temp_dir))
            try:
                office = workspace.fields["business_registration_office"]
                place = workspace.fields["document_place"]
                self.assertIsInstance(office, QLineEdit)
                self.assertIsInstance(place, QLineEdit)
                self.assertIsNone(office.completer())
                self.assertFalse(place.isReadOnly())

                workspace._set_field("company_province", "Thành phố Hà Nội")
                self.assertEqual("", office.text())

                office.setText("Phòng do người dùng nhập")
                self.assertEqual("", place.text())

                place.setText("Hà Nội")
                workspace._set_field("document_day", "18")
                workspace._set_field("document_month", "10")
                workspace._set_field("document_year", "2026")
                values = workspace.form_values()
                self.assertEqual("Phòng do người dùng nhập", values["business_registration_office"])
                self.assertEqual("Hà Nội", values["document_place"])
                self.assertEqual("Hà Nội, ngày 18 tháng 10 năm 2026", values["document_place_date"])
            finally:
                workspace.deleteLater()

    def test_receiving_office_and_signing_place_are_required_for_export(self) -> None:
        missing_values = {"business_registration_office": "", "document_place": ""}
        self.assertEqual(
            ["Phòng đăng ký kinh doanh", "Nơi ký"],
            HouseholdBusinessWorkspace._missing_manual_signing_fields(missing_values),
        )
        complete_values = {
            "business_registration_office": "Phòng Đăng ký kinh doanh số 1",
            "document_place": "Hà Nội",
        }
        self.assertEqual([], HouseholdBusinessWorkspace._missing_manual_signing_fields(complete_values))

    def test_full_household_address_is_split_into_three_editable_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self._workspace(Path(temp_dir))
            try:
                address = workspace.fields["company_address_detail"]
                address.setText("Số Nhà 13 Thôn 4, Xã Hòa Lạc, Thành phố Hà Nội")
                workspace._flush_pending_address_sync()

                self.assertEqual("Số Nhà 13 Thôn 4", workspace._field_value("company_address_detail"))
                self.assertEqual("Xã Hòa Lạc", workspace._field_value("company_ward"))
                self.assertEqual("Thành phố Hà Nội", workspace._field_value("company_province"))

                workspace._set_field("company_ward", "Xã người dùng sửa")
                workspace._set_field("company_province", "Tỉnh người dùng sửa")
                workspace._set_field("company_address_detail", "Số 20 đường mới")
                workspace._flush_pending_address_sync()

                self.assertEqual("Số 20 đường mới", workspace._field_value("company_address_detail"))
                self.assertEqual("Xã người dùng sửa", workspace._field_value("company_ward"))
                self.assertEqual("Tỉnh người dùng sửa", workspace._field_value("company_province"))
            finally:
                workspace.deleteLater()

    def test_new_complete_household_address_replaces_previous_address_parts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self._workspace(Path(temp_dir))
            try:
                workspace._set_field("company_ward", "Phường cũ")
                workspace._set_field("company_province", "Tỉnh cũ")
                workspace._set_field(
                    "company_address_detail",
                    "Căn 12; Khu phố 3; PHƯỜNG Bến Nghé; THÀNH PHỐ Hồ Chí Minh",
                )
                workspace._flush_pending_address_sync()

                self.assertEqual("Căn 12, Khu phố 3", workspace._field_value("company_address_detail"))
                self.assertEqual("PHƯỜNG Bến Nghé", workspace._field_value("company_ward"))
                self.assertEqual("THÀNH PHỐ Hồ Chí Minh", workspace._field_value("company_province"))
            finally:
                workspace.deleteLater()

    def test_household_address_split_accepts_special_zone_and_province(self) -> None:
        self.assertEqual(
            ("Thôn Mẫu", "Đặc khu Côn Đảo", "Tỉnh Bà Rịa - Vũng Tàu"),
            HouseholdBusinessWorkspace._split_household_business_address(
                "Thôn Mẫu\nĐặc khu Côn Đảo\nTỉnh Bà Rịa - Vũng Tàu"
            ),
        )
        self.assertIsNone(
            HouseholdBusinessWorkspace._split_household_business_address(
                "Số 1 đường A, Phường B"
            )
        )

    def test_full_address_in_detail_field_is_not_enabled_for_other_dossiers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = BusinessRegistrationWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=ROOT,
                default_export_root=Path(temp_dir),
            )
            try:
                full_address = "Số 13 Thôn 4, Xã Hòa Lạc, Thành phố Hà Nội"
                workspace._set_field("company_address_detail", full_address)
                workspace._flush_pending_address_sync()
                self.assertEqual(full_address, workspace._field_value("company_address_detail"))
                self.assertEqual("", workspace._field_value("company_ward"))
                self.assertEqual("", workspace._field_value("company_province"))
            finally:
                workspace.deleteLater()

    def test_household_form_uses_only_its_own_template_sections_and_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self._workspace(Path(temp_dir))
            try:
                self.assertIn(HOUSEHOLD_OWNER_SECTION, workspace.form_sections)
                self.assertIn(HOUSEHOLD_DETAILS_SECTION, workspace.form_sections)
                self.assertIn(HOUSEHOLD_CAPITAL_SECTION, workspace.form_sections)
                self.assertIn(HOUSEHOLD_TAX_SECTION, workspace.form_sections)
                for removed in (
                    "Thông tin người đại diện pháp luật",
                    "Thông tin chủ sở hữu",
                    "Thông tin giám đốc/Tổng giám đốc",
                    "Thông tin đăng ký thuế và bảo hiểm xã hội",
                ):
                    self.assertNotIn(removed, workspace.form_sections)
                self.assertNotIn("applicant_phone", workspace.fields)
                self.assertNotIn("applicant_email", workspace.fields)
                self.assertNotIn("company_fax", workspace.fields)
                self.assertNotIn("company_website", workspace.fields)
                self.assertNotIn("legal_representative_full_name", workspace.fields)
                self.assertEqual({"tax_labor_count"}, {key for key in workspace.fields if key.startswith("tax_")})
            finally:
                workspace.deleteLater()

    def test_household_capital_formats_number_currency_and_words(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self._workspace(Path(temp_dir))
            try:
                workspace._set_field("charter_capital_number", "40000000")
                self.assertEqual("40.000.000", workspace._field_value("charter_capital_number"))
                self.assertEqual(
                    "40.000.000 VNĐ (Bốn mươi triệu đồng)",
                    workspace._field_value("charter_capital_full_text"),
                )
                values = workspace.form_values()
                self.assertEqual("40.000.000", values["household_capital"])
            finally:
                workspace.deleteLater()

    def test_household_form_values_map_to_request_template_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self._workspace(Path(temp_dir))
            try:
                entries = {
                    "applicant_full_name": "Nguyễn Văn A",
                    "applicant_date_of_birth": "01/01/2001",
                    "applicant_gender": "Nam",
                    "applicant_id_number": "123456789",
                    "company_name": "Hộ kinh doanh Nguyễn Văn A",
                    "company_english_name": "NGUYEN VAN A HOUSEHOLD BUSINESS",
                    "company_short_name": "HKD NVA",
                    "company_address_detail": "Số 4 đường 5, Khu phố 6",
                    "company_ward": "Xã A",
                    "company_province": "Thành phố Hồ Chí Minh",
                    "company_phone": "0987654321",
                    "company_email": "hkd@example.com",
                    "tax_labor_count": "1",
                }
                for key, value in entries.items():
                    workspace._set_field(key, value)
                values = workspace.form_values()
                self.assertEqual("Nguyễn Văn A", values["household_owner_full_name"])
                self.assertEqual("Hộ kinh doanh Nguyễn Văn A", values["household_business_name"])
                self.assertEqual("NGUYEN VAN A HOUSEHOLD BUSINESS", values["household_foreign_name"])
                self.assertEqual("1", values["household_labor_count"])
            finally:
                workspace.deleteLater()


if __name__ == "__main__":
    unittest.main()

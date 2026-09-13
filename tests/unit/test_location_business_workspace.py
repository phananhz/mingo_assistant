from __future__ import annotations

import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from PySide6.QtWidgets import QApplication, QFrame, QGroupBox, QLabel

from mingo_assistant.services.documents.dependent_unit_generator import DependentUnitTemplateGenerator
from mingo_assistant.ui.dialogs.dependent_unit_modal import UNIT_TYPE_SPECS
from mingo_assistant.ui.views.business_registration_workspace import BusinessRegistrationWorkspace
from mingo_assistant.ui.views.location_business_workspace import (
    LOCATION_CASE_TYPE,
    LocationBusinessWorkspace,
)


class LocationBusinessWorkspaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_ready_procedure_uses_location_workspace_and_templates(self) -> None:
        ddkd = next(spec for spec in UNIT_TYPE_SPECS if spec["id"] == "ddkd")
        create = next(option for option in ddkd["procedures"] if option.id == "ddkd_create")
        self.assertTrue(create.is_ready)

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = LocationBusinessWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=Path(__file__).resolve().parents[2],
                default_export_root=Path(temp_dir),
            )
            try:
                template_dir, _ = workspace._template_and_export_dirs()
                self.assertEqual(
                    Path(__file__).resolve().parents[2]
                    / "assets"
                    / "templates"
                    / "word"
                    / "dependent_units"
                    / "ddkd_create",
                    template_dir,
                )
                self.assertIs(DependentUnitTemplateGenerator, workspace._document_generator_class())
                self.assertIn("location_manager_full_name", workspace.fields)
                self.assertNotIn("charter_capital_number", workspace.fields)
                self.assertIn("legal_representative_full_name", workspace.fields)
                self.assertIn("legal_representative_id_number", workspace.fields)
                self.assertIn("legal_representative_position", workspace.fields)

                workspace.fields["location_business_name"].setText("Địa điểm kinh doanh A")
                workspace.fields["parent_entity_name"].setText("Công ty TNHH Mingo")
                case = workspace.build_case_summary()
                self.assertEqual(LOCATION_CASE_TYPE, case.case_type)
                self.assertEqual("Địa điểm kinh doanh A", case.company_name)
                self.assertEqual("Không áp dụng", case.capital)
            finally:
                workspace.deleteLater()

    def test_location_validation_does_not_require_company_establishment_fields(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = LocationBusinessWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
            )
            try:
                issues = workspace._validation_issues({})

                self.assertIn("Tên địa điểm kinh doanh", issues)
                self.assertIn("Tên doanh nghiệp chủ quản", issues)
                self.assertNotIn("Họ tên chủ sở hữu", issues)
                self.assertNotIn("Số CCCD chủ sở hữu", issues)
                self.assertNotIn("Địa chỉ liên lạc của chủ sở hữu", issues)
                self.assertNotIn("Số điện thoại công ty (dùng cho thông tin đăng ký thuế)", issues)
                self.assertNotIn("Vốn điều lệ", issues)
                self.assertNotIn("Địa chỉ thường trú", issues)
                self.assertNotIn("Nơi cấp CCCD của người đại diện pháp luật", issues)
            finally:
                workspace.deleteLater()




    def test_export_location_uses_a_new_version_folder(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            export_root = Path(temp_dir)
            workspace = LocationBusinessWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=export_root,
            )
            try:
                values = {
                    "parent_entity_name": "COMPANY A",
                    "location_business_name": "LOCATION A",
                }
                company_dir = workspace._case_export_dir(export_root, values)
                self.assertEqual("COMPANY A", company_dir.name)
                version_name = "Lần xuất 20260913_101500_123456"
                self.assertEqual(
                    company_dir / version_name,
                    workspace._export_output_dir(company_dir, values, "LOCATION A", version_name),
                )
                versions = workspace._next_export_versions(
                    str(company_dir), str(company_dir / version_name), "10/09/2026 12:00:00", ["1. request.docx"], version_name
                )
                self.assertEqual(1, len(versions))
                self.assertEqual(str(company_dir / version_name), versions[0]["export_dir"])
            finally:
                workspace.deleteLater()


    def test_manager_type_excludes_the_other_identity_fields_and_syncs_contacts(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = LocationBusinessWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
            )
            try:
                workspace.fields["location_phone"].setText("0909000000")
                workspace.fields["location_email"].setText("location@example.test")
                workspace.fields["location_manager_person_type"].setCurrentIndex(1)
                workspace.fields["location_manager_id_number"].setText("VN-ID")
                workspace.fields["location_manager_passport_number"].setText("P1234567")
                workspace.fields["location_manager_foreign_country"].setText("Country A")
                workspace.fields["location_manager_address_detail"].setText("Foreign contact street")
                workspace.fields["location_manager_ward"].setText("Foreign contact ward")
                workspace.fields["location_manager_province"].setText("Foreign contact province")
                workspace.fields["location_manager_nationality"].setText("Foreign contact country")
                values = workspace.form_values()
                self.assertEqual("", values["location_manager_id_number"])
                self.assertEqual("P1234567", values["location_manager_passport_number"])
                self.assertEqual("Foreign contact street", values["location_manager_address_detail"])
                self.assertEqual("Foreign contact ward", values["location_manager_ward"])
                self.assertEqual("Foreign contact province", values["location_manager_province"])
                self.assertEqual("Foreign contact country", values["location_manager_nationality"])
                self.assertEqual("0909000000", values["tax_notification_phone"])
                self.assertEqual("location@example.test", values["tax_notification_email"])
                self.assertTrue(workspace.fields["tax_notification_phone"].isReadOnly())
                self.assertTrue(workspace.fields["location_manager_id_number"].isHidden())
                self.assertFalse(workspace.fields["location_manager_address_detail"].isHidden())
                self.assertFalse(workspace.fields["location_manager_ward"].isHidden())
                self.assertFalse(workspace.fields["location_manager_province"].isHidden())
                self.assertFalse(workspace.fields["location_manager_nationality"].isHidden())

                workspace.fields["location_manager_person_type"].setCurrentIndex(0)
                values = workspace.form_values()
                self.assertEqual("P1234567", values["location_manager_passport_number"])
                self.assertEqual("Country A", values["location_manager_foreign_country"])
                self.assertFalse(workspace.fields["location_manager_id_number"].isHidden())
            finally:
                workspace.deleteLater()

    def test_location_manager_layout_has_word_section_boundaries(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = LocationBusinessWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
            )
            try:
                titles = {group.title() for group in workspace.findChildren(QGroupBox)}
                self.assertIn("Phần A · Thông tin định danh và liên lạc", titles)
                self.assertIn("Địa chỉ liên lạc", titles)
                self.assertIn("Phần B · Kê khai bổ sung khi không có số định danh cá nhân", titles)
                note = workspace.findChild(QLabel, "LocationManagerSupplementNote")
                self.assertIsNotNone(note)
                self.assertIn("Trường hợp không có số định danh cá nhân", note.text())
            finally:
                workspace.deleteLater()


    def test_scanned_documents_require_explicit_location_role_selection(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = LocationBusinessWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
            )
            try:
                workspace._apply_organization_values_to_current_person(
                    {
                        "organization_owner_name": "C\u00d4NG TY TNHH MIN",
                        "organization_owner_registration_number": "0312345678",
                    },
                    "PDF text",
                    "text",
                )
                self.assertEqual("C\u00d4NG TY TNHH MIN", workspace.fields["parent_entity_name"].text())
                self.assertEqual("0312345678", workspace.fields["parent_entity_registration_number"].text())

                workspace._apply_cccd_values_to_current_person(
                    {
                        "legal_representative_full_name": "NGUY\u1ec4N V\u0102N A",
                        "legal_representative_id_number": "012345678901",
                        "legal_representative_date_of_birth": "01/01/1990",
                        "legal_representative_gender": "Nam",
                        "legal_representative_nationality": "Vi\u1ec7t Nam",
                        "legal_representative_permanent_address": "1 Duong A, Phuong B, Ha Noi",
                    },
                    apply_to_form=True,
                )
                self.assertEqual("", workspace.fields["location_manager_full_name"].text())
                self.assertEqual("", workspace.fields["legal_representative_full_name"].text())
                person = workspace.ocr_people[workspace.current_person_index]
                workspace._fill_section_from_person("location_manager", person)
                self.assertEqual("NGUY\u1ec4N V\u0102N A", workspace.fields["location_manager_full_name"].text())
                self.assertEqual("012345678901", workspace.fields["location_manager_id_number"].text())
                self.assertEqual("Ng\u01b0\u1eddi Vi\u1ec7t Nam", workspace.fields["location_manager_person_type"].currentText())
            finally:
                workspace.deleteLater()

    def test_legal_representative_is_independent_from_location_manager(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = LocationBusinessWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
            )
            try:
                workspace._apply_cccd_values_to_current_person(
                    {
                        "legal_representative_full_name": "NGUY\u1ec4N V\u0102N A",
                        "legal_representative_id_number": "012345678901",
                        "legal_representative_date_of_birth": "01/01/1990",
                        "legal_representative_gender": "Nam",
                        "legal_representative_nationality": "Vi\u1ec7t Nam",
                        "legal_representative_permanent_address": "1 Duong A, Phuong B, Ha Noi",
                    },
                    apply_to_form=True,
                )
                person = workspace.ocr_people[workspace.current_person_index]
                self.assertEqual("", workspace.fields["location_manager_full_name"].text())
                workspace._fill_section_from_person("legal_representative", person)
                self.assertEqual("NGUY\u1ec4N V\u0102N A", workspace.fields["legal_representative_full_name"].text())
                self.assertEqual("012345678901", workspace.fields["legal_representative_id_number"].text())
                workspace.fields['legal_representative_position'].setText('Giám đốc điều hành')
                self.assertEqual('Giám đốc điều hành', workspace.form_values()['legal_representative_position'])
                self.assertEqual("", workspace.fields["location_manager_full_name"].text())
                workspace._fill_section_from_person("location_manager", person)
                self.assertEqual("NGUY\u1ec4N V\u0102N A", workspace.fields["location_manager_full_name"].text())
                self.assertEqual("NGUY\u1ec4N V\u0102N A", workspace.form_values()["signer_full_name"])
            finally:
                workspace.deleteLater()
    def test_saving_recognized_organization_confirms_and_updates_parent(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = LocationBusinessWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
            )
            try:
                workspace.organization_card_fields["organization_owner_name"].setText("COMPANY A")
                workspace.organization_card_fields["organization_owner_registration_number"].setText("0312345678")
                workspace.organization_card_fields["organization_owner_address_detail"].setPlainText("1 STREET A")
                with patch(
                    "mingo_assistant.ui.views.location_business_workspace.QMessageBox.information"
                ) as information:
                    workspace._save_organization_profile()
                information.assert_called_once()
                self.assertEqual("COMPANY A", workspace.fields["parent_entity_name"].text())
                self.assertEqual("0312345678", workspace.fields["parent_entity_registration_number"].text())
                self.assertEqual(1, len(workspace.organization_profiles))
                values = workspace.form_values()
                self.assertEqual("COMPANY A", values["company_name"])
                self.assertEqual("1 STREET A", values["company_address"])
            finally:
                workspace.deleteLater()
    def test_full_location_address_splits_to_existing_fields(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = LocationBusinessWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
            )
            try:
                workspace.fields["location_full_address"].setText("13/5 Ao Doi, Phuong Binh Tan, Thanh pho Ho Chi Minh")
                workspace._sync_address_parts("location_full_address")
                self.assertTrue(workspace.fields["location_address_detail"].text())
                self.assertTrue(workspace.fields["location_ward"].text())
                self.assertTrue(workspace.fields["location_province"].text())
            finally:
                workspace.deleteLater()
    def test_location_workspace_does_not_show_word_export_preview(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = LocationBusinessWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
            )
            try:
                self.assertNotIn(
                    "Xem tr\u01b0\u1edbc d\u1eef li\u1ec7u tr\u01b0\u1edbc khi xu\u1ea5t Word",
                    [group.title() for group in workspace.findChildren(QGroupBox)],
                )
            finally:
                workspace.deleteLater()
    def test_all_form_tabs_expand_to_the_available_width(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        for workspace_type in (BusinessRegistrationWorkspace, LocationBusinessWorkspace):
            with self.subTest(workspace=workspace_type.__name__), tempfile.TemporaryDirectory() as temp_dir:
                workspace = workspace_type(
                    on_back=lambda: None,
                    on_save=lambda case: None,
                    bundle_root=project_root,
                    default_export_root=Path(temp_dir),
                )
                try:
                    workspace.resize(1920, 1200)
                    workspace.show()
                    self.app.processEvents()
                    for index in range(workspace.form_stack.count()):
                        workspace._select_form_section(index)
                        self.app.processEvents()
                        self.assertEqual(
                            workspace.form_stack.width(),
                            workspace.form_stack.currentWidget().width(),
                        )
                finally:
                    workspace.deleteLater()

    def test_each_business_line_is_a_bordered_row_card(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        for workspace_type in (BusinessRegistrationWorkspace, LocationBusinessWorkspace):
            with self.subTest(workspace=workspace_type.__name__), tempfile.TemporaryDirectory() as temp_dir:
                workspace = workspace_type(
                    on_back=lambda: None,
                    on_save=lambda case: None,
                    bundle_root=project_root,
                    default_export_root=Path(temp_dir),
                )
                try:
                    workspace.resize(1920, 1200)
                    workspace.show()
                    self.app.processEvents()
                    industry_index = list(workspace.form_sections).index("Ngành nghề kinh doanh")
                    workspace._select_form_section(industry_index)
                    self.app.processEvents()
                    table = workspace.business_line_table
                    self.assertIsNotNone(table)
                    row = workspace.business_line_rows[0]
                    card = row.cells[0]
                    self.assertEqual("BusinessLineRow", card.objectName())
                    self.assertEqual(QFrame.Box, card.frameShape())
                    self.assertIn("border: 2px solid #557fae", card.styleSheet())
                    self.assertEqual(1, len(workspace.business_line_rows[0].cells))
                    self.assertEqual(156, card.height())
                    self.assertLess(row.detail_field.geometry().bottom(), card.contentsRect().bottom())
                    self.assertIs(card, table.layout().itemAtPosition(1, 0).widget())
                    self.assertEqual(table.layout().contentsRect().width(), card.width())
                finally:
                    workspace.deleteLater()
if __name__ == "__main__":
    unittest.main()

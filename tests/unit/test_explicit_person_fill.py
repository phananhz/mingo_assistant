from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from mingo_assistant.services.organization_documents.organization_document_service import OrganizationDocumentResult
from mingo_assistant.services.qr import IdentityScanResult
from mingo_assistant.ui.views.business_registration_workspace import BusinessRegistrationWorkspace


class ExplicitPersonFillTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_company_scan_applies_to_the_selected_role(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = BusinessRegistrationWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
            )
            try:
                workspace.ocr_people[workspace.current_person_index].role = "legal_representative"
                workspace._apply_cccd_values_to_current_person({
                    "legal_representative_full_name": "NGƯỜI MẪU",
                    "legal_representative_id_number": "000000000000",
                })
                self.assertEqual("NGƯỜI MẪU", workspace.fields["legal_representative_full_name"].text())
                self.assertEqual("000000000000", workspace.fields["legal_representative_id_number"].text())
            finally:
                workspace.deleteLater()

    def test_authorized_profile_replaces_all_previous_personal_information(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        profile = {
            "authorized_person_full_name": "NGƯỜI ỦY QUYỀN MẪU",
            "authorized_person_gender": "",
            "authorized_person_id_number": "000000000000",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = BusinessRegistrationWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
                authorized_person_defaults={"__profiles": [profile]},
            )
            try:
                workspace._set_field("authorized_person_date_of_birth", "01/01/1990")
                workspace._set_field("authorized_person_phone", "0900000000")
                workspace._set_field("authorized_person_email", "old@example.test")

                workspace._fill_authorized_person_from_profile("authorized_profile:0")

                self.assertEqual("NGƯỜI ỦY QUYỀN MẪU", workspace._field_value("authorized_person_full_name"))
                self.assertEqual("000000000000", workspace._field_value("authorized_person_id_number"))
                self.assertEqual("", workspace._field_value("authorized_person_date_of_birth"))
                self.assertEqual("", workspace._field_value("authorized_person_phone"))
                self.assertEqual("", workspace._field_value("authorized_person_email"))
            finally:
                workspace.deleteLater()

    def test_saved_cccd_profile_reapplies_and_overwrites_linked_form(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = BusinessRegistrationWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
            )
            try:
                recognized = {
                    "legal_representative_full_name": "NGƯỜI MẪU",
                    "legal_representative_id_number": "000000000000",
                    "legal_representative_issue_place": "Bộ Công an",
                    "legal_representative_permanent_address": "1 Đường A",
                }
                workspace._update_cccd_result_fields(recognized)
                with patch(
                    "mingo_assistant.ui.views.business_registration_workspace.QMessageBox.information"
                ):
                    workspace._save_cccd_personal_profile()

                selector = workspace.person_fill_selectors["legal_representative"]
                selected_index = selector.findData("person:0")
                selector.setCurrentIndex(selected_index)
                self.assertEqual("NGƯỜI MẪU", workspace._field_value("legal_representative_full_name"))

                workspace._set_field("legal_representative_full_name", "MANUAL VALUE")
                workspace.ocr_card_fields["legal_representative_full_name"].setText("NGƯỜI MẪU MỚI")
                with patch(
                    "mingo_assistant.ui.views.business_registration_workspace.QMessageBox.information"
                ):
                    workspace._save_cccd_personal_profile()
                self.assertEqual("NGƯỜI MẪU MỚI", workspace._field_value("legal_representative_full_name"))

                workspace._set_field("legal_representative_id_number", "")
                selector.activated.emit(selected_index)
                self.assertEqual("000000000000", workspace._field_value("legal_representative_id_number"))
            finally:
                workspace.deleteLater()

    def test_erc_scan_switches_result_card_without_mutating_the_dossier_form(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = BusinessRegistrationWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
            )
            try:
                workspace._set_field("beneficial_owner_full_name", "CHỦ SỞ HỮU CÁ NHÂN")
                result = OrganizationDocumentResult(
                    values={
                        "organization_owner_name": "CÔNG TY ERC",
                        "organization_owner_registration_number": "0312345678",
                    },
                    raw_text="GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP",
                    extraction_method="ocr",
                    document_type="erc",
                )
                with patch.object(workspace.organization_document_service, "extract_pdf", return_value=result):
                    workspace._scan_organization_document("sample.pdf")

                self.assertEqual(1, workspace.recognition_result_stack.currentIndex())
                self.assertEqual("CÔNG TY ERC", workspace.organization_card_fields["organization_owner_name"].text())
                self.assertEqual("CHỦ SỞ HỮU CÁ NHÂN", workspace._field_value("beneficial_owner_full_name"))
                self.assertEqual("Cá nhân", workspace.owner_type_selector.currentText())
                self.assertFalse(workspace.ocr_people[0].recognition_saved)
            finally:
                workspace.deleteLater()

    def test_cccd_scan_uses_both_sides_and_parses_ocr_fallback(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = BusinessRegistrationWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
            )
            try:
                person = workspace.ocr_people[workspace.current_person_index]
                person.front_path = "front.jpg"
                person.back_path = "back.jpg"
                ocr_text = """Số / No.: 012345678901
Họ và tên / Full name: NGUYEN VAN TEST
Ngày sinh / Date of birth: 01/01/1990
Giới tính / Sex: Nam
Quốc tịch / Nationality: Việt Nam
Nơi cư trú / Place of residence: Khu 1, Ban Nguyen, Lam Thao, Phu Tho
Ngày, tháng, năm cấp / Date, month, year of issue: 19/03/2025"""
                scan_result = IdentityScanResult(ocr_text, "ocr", "back.jpg")

                with patch.object(workspace.ocr_service, "scan_identity", return_value=scan_result) as scan_identity:
                    workspace._run_qr_scan(person.front_path)

                image_paths = scan_identity.call_args.args[0]
                self.assertEqual(image_paths, ["front.jpg", "back.jpg"])
                self.assertEqual(
                    workspace.ocr_card_fields["legal_representative_id_number"].text(),
                    "012345678901",
                )
                self.assertEqual(
                    workspace.ocr_card_fields["legal_representative_full_name"].text(),
                    "NGUYEN VAN TEST",
                )
                self.assertEqual(
                    workspace.ocr_card_fields["legal_representative_issue_place"].currentText(),
                    "Bộ Công an",
                )
                self.assertFalse(person.recognition_saved)
            finally:
                workspace.deleteLater()

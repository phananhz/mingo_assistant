from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

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

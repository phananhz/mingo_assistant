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
                    "legal_representative_full_name": "NGUYỄN VĂN MẪU",
                    "legal_representative_id_number": "001090000001",
                })
                self.assertEqual("NGUYỄN VĂN MẪU", workspace.fields["legal_representative_full_name"].text())
                self.assertEqual("001090000001", workspace.fields["legal_representative_id_number"].text())
            finally:
                workspace.deleteLater()

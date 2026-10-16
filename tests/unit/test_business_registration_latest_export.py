from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QRadioButton

from mingo_assistant.models.case import CaseSummary
from mingo_assistant.ui.views.business_registration_documents import (
    BusinessRegistrationDocumentsView,
)
from mingo_assistant.application.registration import RegistrationExportPlanner
from mingo_assistant.ui.views.business_registration_workspace import BusinessRegistrationWorkspace


class BusinessRegistrationLatestExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def _case(root: Path, case_type: str = "TNHH một thành viên") -> CaseSummary:
        versions: list[dict[str, object]] = []
        for number in (1, 2):
            export_dir = root / f"bản {number}" / "company"
            export_dir.mkdir(parents=True)
            file_name = f"document-{number}.docx"
            (export_dir / file_name).write_bytes(b"")
            versions.append(
                {
                    "name": f"bản {number}",
                    "case_export_dir": str(root),
                    "export_dir": str(export_dir),
                    "exported_at": f"0{number}/01/2026",
                    "documents": [file_name],
                }
            )
        return CaseSummary(
            id="case-1",
            company_name="Company",
            case_type=case_type,
            owner="Owner",
            updated_at="",
            status="Đã tạo hồ sơ",
            condition="Đủ dữ liệu",
            members=1,
            capital="",
            export_dir=str(root),
            export_versions=versions,
        )

    def test_registration_view_shows_only_latest_files_without_version_selector(self) -> None:
        with TemporaryDirectory() as temp_dir:
            view = BusinessRegistrationDocumentsView(
                self._case(Path(temp_dir)),
                lambda: None,
                lambda: None,
            )

            versions = view._versions()
            labels = [label.text() for label in view.findChildren(QLabel)]

            self.assertEqual(len(versions), 1)
            self.assertEqual([path.name for path in versions[0]["files"]], ["document-2.docx"])
            self.assertIn("File Word mới nhất", labels)
            self.assertFalse(any("phiên bản" in label.casefold() for label in labels))
            self.assertFalse(view.findChildren(QRadioButton))
            view.deleteLater()

    def test_other_workflows_still_show_version_history(self) -> None:
        with TemporaryDirectory() as temp_dir:
            view = BusinessRegistrationDocumentsView(
                self._case(Path(temp_dir), case_type="Other workflow"),
                lambda: None,
                lambda: None,
            )

            self.assertEqual(len(view._versions()), 2)
            self.assertEqual(len(view.findChildren(QRadioButton)), 2)
            view.deleteLater()

    def test_cleanup_removes_old_versions_but_keeps_latest_and_unrelated_folders(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old = root / "bản 1"
            keep = root / "bản 2" / "company"
            unrelated = root / "notes"
            for path in (old, keep, unrelated):
                path.mkdir(parents=True)

            holder = type("WorkspaceHolder", (), {"export_planner": RegistrationExportPlanner()})()
            failures = BusinessRegistrationWorkspace._remove_previous_export_versions(holder, root, keep)

            self.assertEqual(failures, [])
            self.assertFalse(old.exists())
            self.assertTrue(keep.exists())
            self.assertTrue(unrelated.exists())


if __name__ == "__main__":
    unittest.main()

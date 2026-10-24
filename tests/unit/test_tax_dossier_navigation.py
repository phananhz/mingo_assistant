from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from mingo_assistant.app.paths import AppPaths
from mingo_assistant.models.case import CaseSummary
from mingo_assistant.repositories.case_repository import CaseRepository
from mingo_assistant.ui.main_window import MainWindow
from mingo_assistant.ui.views.business_registration_documents import BusinessRegistrationDocumentsView
from mingo_assistant.ui.views.tax_restoration_workspace import TaxRestorationWorkspace
from mingo_assistant.ui.views.tax_template_workspace import TAX_TEMPLATE_CASE_TYPE


ROOT = Path(__file__).resolve().parents[2]


class TaxDossierNavigationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def click(widget, text):
        next(button for button in widget.findChildren(QPushButton) if button.text() == text).click()

    @staticmethod
    def case(case_id, name):
        return CaseSummary(
            id=case_id, company_name=name, case_type=TAX_TEMPLATE_CASE_TYPE,
            owner="", updated_at="", status="Bản nháp", condition="", members=0, capital="",
            form_values={"tax_template_id": "tax-25", "tax_dossier_name": name},
        )

    def test_open_views_exact_export_and_edit_opens_only_the_selected_editor(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repo = CaseRepository(root / "cases.json")
            cases, files = [], []
            for index in (1, 2):
                folder = root / f"case-{index}" / "bản 1"
                folder.mkdir(parents=True)
                document = folder / f"document-{index}.docx"
                document.write_bytes(b"file path fixture")
                files.append(document)
                cases.append(replace(
                    self.case(f"tax-{index}", f"Hồ sơ {index}"), status="Đã tạo hồ sơ",
                    export_dir=str(folder.parent), generated_documents=[document.name],
                    export_versions=[{"name": "bản 1", "export_dir": str(folder), "documents": [document.name]}],
                ))
            repo._write_cases(cases)
            before = [case.to_dict() for case in repo.list_cases()]
            window = MainWindow(app_paths=AppPaths(ROOT, root, root / "exports"), case_repository=repo)
            try:
                window._select_nav("templates")
                page = window.templates_page
                page.tabs.setCurrentIndex(1)
                page.dossiers.search.setText("Hồ sơ 1")
                self.click(page.dossiers.cards[0], "Mở")
                view = window.current_documents_view
                self.assertIsInstance(view, BusinessRegistrationDocumentsView)
                self.assertIs(view, window.stack.currentWidget())
                self.assertIsNone(window.current_workspace)
                self.assertEqual("tax-1", view.case.id)
                self.assertEqual([files[0]], view.displayed_versions[0]["files"])
                with patch("mingo_assistant.ui.views.business_registration_documents.QDesktopServices.openUrl", return_value=True) as opened:
                    self.click(view, "Mở file")
                self.assertEqual(files[0].resolve(), Path(opened.call_args.args[0].toLocalFile()).resolve())
                self.assertEqual(before, [case.to_dict() for case in repo.list_cases()])
                self.click(view, "Sửa dữ liệu hồ sơ")
                self.assertIsInstance(window.current_workspace, TaxRestorationWorkspace)
                self.assertEqual("tax-1", window.current_workspace.case_id)
                window.current_workspace.on_back()
                self.assertIs(page, window.stack.currentWidget())
                self.assertEqual(1, page.tabs.currentIndex())
                page.dossiers.search.setText("Hồ sơ 2")
                self.click(page.dossiers.cards[0], "Sửa")
                self.assertIsInstance(window.current_workspace, TaxRestorationWorkspace)
                self.assertEqual("tax-2", window.current_workspace.case_id)
                self.assertIsNone(window.current_documents_view)
                self.assertEqual(before, [case.to_dict() for case in repo.list_cases()])
            finally:
                window.hide()
                window.close()
                window.deleteLater()
                self.app.processEvents()

    def test_open_draft_shows_no_export_message_without_entering_editor(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repo = CaseRepository(root / "cases.json")
            case = self.case("draft-tax", "Hồ sơ chưa xuất")
            repo._write_cases([case])
            window = MainWindow(app_paths=AppPaths(ROOT, root, root / "exports"), case_repository=repo)
            try:
                window._select_nav("templates")
                page = window.templates_page
                page.tabs.setCurrentIndex(1)
                self.click(page.dossiers.cards[0], "Mở")
                view = window.current_documents_view
                self.assertEqual(case.id, view.case.id)
                self.assertIsNone(window.current_workspace)
                self.assertFalse(view.displayed_versions)
                self.assertTrue(any("chưa có file Word" in label.text() for label in view.findChildren(QLabel)))
                self.click(view, "← Quay lại")
                self.assertIs(page, window.stack.currentWidget())
                self.assertEqual(1, page.tabs.currentIndex())
                self.click(page.dossiers.cards[0], "Sửa")
                self.assertEqual(case.id, window.current_workspace.case_id)
            finally:
                window.hide()
                window.close()
                window.deleteLater()
                self.app.processEvents()

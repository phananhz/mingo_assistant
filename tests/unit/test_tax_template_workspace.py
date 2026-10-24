from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from dataclasses import replace

from PySide6.QtWidgets import QApplication, QPushButton, QMessageBox
from PySide6.QtTest import QTest

from mingo_assistant.app.paths import AppPaths
from mingo_assistant.repositories.case_repository import CaseRepository
from mingo_assistant.services.organization_documents.organization_document_service import OrganizationDocumentResult
from mingo_assistant.ui.main_window import MainWindow
from mingo_assistant.ui.views.tax_template_workspace import TaxTemplateWorkspace, TAX_TEMPLATE_CASE_TYPE
from mingo_assistant.ui.views.tax_customs_confirmation_workspace import TaxCustomsConfirmationWorkspace
from mingo_assistant.ui.views.template_library_catalog import TEMPLATE_GROUPS


ROOT = Path(__file__).resolve().parents[2]


class TaxTemplateTests(TestCase):
    @staticmethod
    def click_card(panel, text):
        next(button for button in panel.cards[0].findChildren(QPushButton) if button.text() == text).click()

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_tax_catalog_scans_restores_draft_and_blocks_unconfirmed_export(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repo = CaseRepository(root / "cases.json")
            repo._write_cases([])
            window = MainWindow(app_paths=AppPaths(ROOT, root, root / "exports"), case_repository=repo)
            try:
                page = window.templates_page
                page.select_group("tax")
                page.template_list.setCurrentRow(9)
                selected = page.selected_template
                page.use_template_button.click()
                w = window.current_workspace
                self.assertIsInstance(w, TaxCustomsConfirmationWorkspace)
                self.assertEqual(selected.id, w.tax_template.id)
                self.assertTrue(any("Xuất" in b.text() for b in w.findChildren(QPushButton)))
                self.assertIn("authorized_person_full_name", w.fields)
                self.assertIn("authorized_person_phone", w.fields)
                w.draft_progress.flush()
                self.assertEqual([], repo.list_cases())
                result = OrganizationDocumentResult({"organization_owner_name": "CÔNG TY THỬ", "organization_owner_registration_number": "0312345678"}, "Văn bản quét thử", "text")
                with patch("mingo_assistant.ui.views.business_registration.scan_worker.read_certificate", return_value=result):
                    w._start_background_scan("sample.pdf", "erc")
                    for _ in range(300):
                        QTest.qWait(10)
                        if w._scan_thread is None:
                            break
                    self.assertIsNone(w._scan_thread)
                self.assertIn("Văn bản quét thử", w.raw_ocr_text.toPlainText())
                self.assertFalse(w.ocr_people[0].recognition_saved)
                w.draft_progress.flush()
                saved = repo.get_case(w.case_id)
                self.assertEqual(TAX_TEMPLATE_CASE_TYPE, saved.case_type)
                self.assertEqual(selected.id, saved.form_values["tax_template_id"])
                with patch("mingo_assistant.ui.views.business_registration_workspace.DocxExportWorker") as worker, \
                        patch.object(QMessageBox, "warning") as warning:
                    w._export_documents()
                    worker.assert_not_called()
                    warning.assert_called_once()
                window._open_case_workspace(saved)
                restored = window.current_workspace
                self.assertIsInstance(restored, TaxTemplateWorkspace)
                self.assertEqual(selected.id, restored.tax_template.id)
                self.assertIn("Văn bản quét thử", restored.raw_ocr_text.toPlainText())
                restored._set_field("tax_dossier_name", "Hồ sơ Công ty A")
                restored.draft_progress.flush()
                restored.on_back()
                self.assertIs(page, window.stack.currentWidget())
                self.assertEqual(1, page.tabs.currentIndex())
                self.assertEqual(1, len(page.dossiers.cards))
                self.assertIn("Hồ sơ Công ty A", page.dossiers.visible_cases[0].company_name)
                self.click_card(page.dossiers, "M\u1edf")
                self.assertEqual(saved.id, window.current_documents_view.case.id)
                self.assertIsNone(window.current_workspace)
                window.current_documents_view.on_edit()
                self.assertEqual(saved.id, window.current_workspace.case_id)
                self.assertEqual("Hồ sơ Công ty A", window.current_workspace._field_value("tax_dossier_name"))
                other = replace(saved, id="independent-tax-case")
                repo.save_case(other)
                with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
                    window._delete_tax_case(saved.id)
                self.assertFalse(repo.get_case(saved.id).is_deleted)
                with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
                    window._delete_tax_case(saved.id)
                self.assertTrue(repo.get_case(saved.id).is_deleted)
                self.assertFalse(repo.get_case(other.id).is_deleted)
                self.assertEqual([other.id], [case.id for case in page.dossiers.visible_cases])
            finally:
                window.hide()
                window.close()
                window.deleteLater()
                self.app.processEvents()

    def test_all_tax_preview_assets_match_source_including_doc(self):
        from mingo_assistant.services.documents.template_library import TemplateLibraryFiles
        items = TEMPLATE_GROUPS[1].items
        files = TemplateLibraryFiles(ROOT, {item.id: item.filename for item in items}, "tax")
        source = ROOT / "TemplatesBefore/8. Biểu mẫu/8. Biểu mẫu/Biểu mẫu Thuế"
        for item in items:
            self.assertTrue(files.source(item.id).is_file())
            if source.is_dir():
                self.assertEqual((source / item.filename).read_bytes(), files.source(item.id).read_bytes())

    def test_two_tax_dossiers_keep_independent_people_buffers_and_saved_data(self):
        with TemporaryDirectory() as directory:
            repo = CaseRepository(Path(directory) / "cases.json")
            repo._write_cases([])
            workspaces = []
            try:
                for _ in range(2):
                    w = TaxTemplateWorkspace(on_back=lambda: None, on_save=repo.save_case, bundle_root=ROOT)
                    w.enable_draft_progress()
                    workspaces.append(w)
                first, second = workspaces
                self.assertNotEqual(first.case_id, second.case_id)
                self.assertIsNot(first.ocr_people, second.ocr_people)
                self.assertIsNot(first.ocr_people[0], second.ocr_people[0])
                first.raw_ocr_text.setPlainText("Nguồn hồ sơ A")
                first.ocr_people[0].front_path = "A.pdf"
                first.draft_progress.flush()
                saved_a = repo.get_case(first.case_id).to_dict()
                self.assertEqual("", second.raw_ocr_text.toPlainText())
                self.assertEqual("", second.ocr_people[0].front_path)
                second.raw_ocr_text.setPlainText("Nguồn hồ sơ B")
                second.ocr_people[0].front_path = "B.pdf"
                second.draft_progress.flush()
                self.assertEqual(saved_a, repo.get_case(first.case_id).to_dict())
                self.assertEqual("Nguồn hồ sơ A", first.raw_ocr_text.toPlainText())
                for case in repo.list_cases():
                    self.assertFalse(any(key.startswith("member_") for key in case.form_values))
                    self.assertEqual(TAX_TEMPLATE_CASE_TYPE, case.case_type)
            finally:
                for w in workspaces:
                    w.draft_progress.stop()
                    w.deleteLater()
                self.app.processEvents()

    def test_dossier_list_filters_cases_searches_and_opens_exact_id(self):
        from mingo_assistant.models.case import CaseSummary
        from mingo_assistant.ui.views.tax_dossier_list import TaxDossierList
        panel = TaxDossierList()
        first = CaseSummary(
            id="tax-a", company_name="Hồ sơ Công ty A", case_type=TAX_TEMPLATE_CASE_TYPE,
            owner="", updated_at="24/10/2026", status="Bản nháp", condition="", members=0, capital="",
            form_values={"tax_template_title": "Cam kết chung", "tax_template_id": "tax-commitment"},
        )
        second = replace(first, id="tax-b", company_name="Hồ sơ Công ty B", form_values={"tax_template_id": "tax-invoice", "tax_template_title": "Cam kết không phát hành hóa đơn"})
        opened = []
        panel.open_requested.connect(opened.append)
        try:
            panel.set_cases([first, second, replace(first, id="deleted", is_deleted=True), replace(first, id="business", case_type="TNHH một thành viên")])
            self.assertEqual(2, len(panel.cards))
            self.assertEqual(11, panel.template_filter.count())
            panel.template_filter.setCurrentIndex(panel.template_filter.findData("tax-commitment"))
            self.assertEqual(1, len(panel.cards))
            panel.search.setText("cong ty b")
            self.assertEqual(0, len(panel.cards))
            self.assertEqual([], panel.visible_cases)
            panel.template_filter.setCurrentIndex(panel.template_filter.findData("tax-invoice"))
            self.assertEqual(1, len(panel.cards))
            panel.set_cases([first, second])
            self.assertEqual("tax-invoice", panel.template_filter.currentData())
            self.assertEqual(1, len(panel.cards))
            panel.template_filter.setCurrentIndex(0)
            panel.search.setText("cong ty a")
            self.assertEqual(1, len(panel.cards))
            self.click_card(panel, "M\u1edf")
            self.assertEqual(["tax-a"], opened)
            panel.set_cases([first, second])
            self.click_card(panel, "M\u1edf")
            self.assertEqual("tax-a", opened[-1])
            panel.search.setText("khong tim thay")
            self.assertEqual(0, len(panel.cards))
            self.assertEqual([], panel.visible_cases)
            self.assertEqual([], panel.cards)
        finally:
            panel.deleteLater()
            self.app.processEvents()

    def test_card_actions_keep_exact_case_id_and_filter_width_is_equal(self):
        from mingo_assistant.models.case import CaseSummary
        from mingo_assistant.ui.views.tax_dossier_list import TaxDossierList
        panel = TaxDossierList()
        case = CaseSummary(id="unique-case", company_name="Hồ sơ A", case_type=TAX_TEMPLATE_CASE_TYPE, owner="", updated_at="24/10/2026", status="Bản nháp", condition="", members=0, capital="")
        opened, edited, deleted = [], [], []
        panel.open_requested.connect(opened.append)
        panel.edit_requested.connect(edited.append)
        panel.delete_requested.connect(deleted.append)
        try:
            panel.set_cases([case])
            panel.resize(1100, 700)
            panel.show()
            self.app.processEvents()
            self.assertLessEqual(abs(panel.search.width() - panel.template_filter.width()), 1)
            self.click_card(panel, "Mở")
            self.click_card(panel, "Sửa")
            self.click_card(panel, "Xóa")
            self.assertEqual([case.id], opened)
            self.assertEqual([case.id], edited)
            self.assertEqual([case.id], deleted)
            panel.resize(570, 700)
            self.app.processEvents()
            self.assertLessEqual(abs(panel.search.width() - panel.template_filter.width()), 1)
        finally:
            panel.close()
            panel.deleteLater()
            self.app.processEvents()

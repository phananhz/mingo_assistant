from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4
from zipfile import ZipFile

from lxml import etree
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QTextEdit

from mingo_assistant.app.paths import AppPaths
from mingo_assistant.models.case import CaseSummary
from mingo_assistant.repositories.case_repository import CaseRepository
from mingo_assistant.services.documents.tax_termination_generator import TaxTerminationGenerator
from mingo_assistant.ui.main_window import MainWindow
from mingo_assistant.ui.views.tax_template_workspace import TAX_TEMPLATE_CASE_TYPE
from mingo_assistant.ui.views.tax_termination_workspace import TaxTerminationWorkspace


ROOT = Path(__file__).resolve().parents[2]
VALUES = {
    "tax_company_name": "CÔNG TY TNHH KIỂM THỬ",
    "tax_registration_number": "0312345678",
    "tax_address": "12 Đường Kiểm Thử, Lâm Đồng, Việt Nam",
    "tax_receiving_authority": "Thuế cơ sở kiểm thử",
    "tax_signing_place": "Tỉnh Lâm Đồng",
    "tax_taxpayer": "NGUYỄN VĂN A",
    "tax_termination_reason": "Doanh nghiệp không còn hoạt động kinh doanh\nThực hiện thủ tục giải thể doanh nghiệp.",
    "tax_attached_documents": "- Quyết định của Chủ sở hữu Công ty về việc giải thể doanh nghiệp.\n- Tài liệu gửi kèm theo hồ sơ.",
}


class TaxTerminationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_catalog_routes_to_two_wrapped_manual_fields_and_erc_scanner(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repo = CaseRepository(root / "cases.json")
            repo._write_cases([])
            window = MainWindow(app_paths=AppPaths(ROOT, root, root / "exports"), case_repository=repo)
            try:
                window._open_tax_template_workspace("tax-24")
                workspace = window.current_workspace
                self.assertIsInstance(workspace, TaxTerminationWorkspace)
                self.assertEqual("erc", workspace.scan_document_type_input.currentData())
                self.assertNotIn("tax_business_industry", workspace.fields)
                self.assertNotIn("tax_invoice_notice_commitment", workspace.fields)
                for key, _ in workspace.MANUAL_FIELDS:
                    field = workspace.fields[key]
                    self.assertIsInstance(field, QTextEdit)
                    self.assertGreaterEqual(field.minimumHeight(), 110)
                    self.assertEqual(QTextEdit.WidgetWidth, field.lineWrapMode())
            finally:
                window.hide()
                window.close()
                window.deleteLater()
                self.app.processEvents()

    def test_only_highlighted_text_changes_and_multiline_values_preserve_drawing(self):
        with TemporaryDirectory() as directory:
            generator = TaxTerminationGenerator(ROOT / "assets/templates/library/tax", directory)
            result = generator.generate(VALUES, "QA")
            with ZipFile(generator.template_dir / generator.FILENAME) as source, \
                    ZipFile(result.generated[0].output_path) as output:
                for name in source.namelist():
                    if name != "word/document.xml":
                        self.assertEqual(source.read(name), output.read(name))
                original = etree.fromstring(source.read("word/document.xml"))
                generated = etree.fromstring(output.read("word/document.xml"))
                runs = generated.xpath(
                    "//w:r[w:rPr/w:highlight[@w:val='green'] and w:t]", namespaces=generator.NS
                )
                actual = [
                    "".join("\n" if node.tag == generator.W + "br" else (node.text or "")
                            for node in run.xpath("w:t|w:br", namespaces=generator.NS))
                    for run in runs
                ]
                self.assertEqual([
                    "CÔNG TY TNHH", "KIỂM THỬ", "Lâm Đồng", VALUES["tax_receiving_authority"],
                    VALUES["tax_company_name"], VALUES["tax_registration_number"], VALUES["tax_address"],
                    VALUES["tax_termination_reason"], VALUES["tax_attached_documents"], VALUES["tax_taxpayer"],
                ], actual)
                # Preserve every other element, including the highlighted
                # non-text shape, paragraph layout and English labels.
                for document in (original, generated):
                    for run in document.xpath("//w:r[w:rPr/w:highlight]", namespaces=generator.NS):
                        for node in run.xpath("w:t|w:br", namespaces=generator.NS):
                            run.remove(node)
                self.assertEqual(etree.tostring(original), etree.tostring(generated))
            for key in ("tax_termination_reason", "tax_attached_documents"):
                with self.assertRaises(ValueError):
                    generator.generate(dict(VALUES, **{key: ""}), "Missing manual input")

    def test_erc_manual_inputs_restore_and_export_in_independent_case(self):
        with TemporaryDirectory() as directory, patch.object(QMessageBox, "information"), \
                patch.object(QMessageBox, "warning"):
            repo = CaseRepository(Path(directory) / "cases.json")
            repo._write_cases([])
            workspaces = []

            def create(case=None):
                if case is None:
                    case = CaseSummary.from_dict({
                        "id": str(uuid4()), "case_type": TAX_TEMPLATE_CASE_TYPE,
                        "form_values": {"tax_template_id": "tax-24"},
                    })
                workspace = TaxTerminationWorkspace(
                    on_back=lambda: None, on_save=repo.save_case, bundle_root=ROOT,
                    default_export_root=Path(directory) / "exports", case=case,
                )
                workspaces.append(workspace)
                workspace.enable_draft_progress()
                return workspace

            try:
                workspace = create()
                recognized = {
                    "organization_owner_name": VALUES["tax_company_name"],
                    "organization_owner_registration_number": VALUES["tax_registration_number"],
                    "organization_owner_issue_date": "01/02/2020",
                    "organization_owner_issue_place": "Sở Tài chính Lâm Đồng",
                    "organization_owner_address_full": VALUES["tax_address"],
                    "tax_legal_representatives": "NGUYỄN VĂN A\nTRẦN THỊ B",
                }
                workspace._apply_organization_values_to_current_person(recognized, "ERC test", "text")
                workspace._update_organization_result_fields(recognized)
                workspace._save_organization_profile()
                workspace.taxpayer.setCurrentText(VALUES["tax_taxpayer"])
                for key in ("tax_receiving_authority", "tax_signing_place", "tax_termination_reason", "tax_attached_documents"):
                    workspace._set_field(key, VALUES[key])
                workspace.draft_progress.flush()
                reopened = create(repo.get_case(workspace.case_id))
                for key, _ in reopened.MANUAL_FIELDS:
                    self.assertEqual(VALUES[key], reopened._field_value(key))
                other = create()
                self.assertEqual("", other._field_value("tax_termination_reason"))
                self.assertNotEqual(
                    reopened._case_export_folder_name(reopened.form_values()),
                    other._case_export_folder_name(other.form_values()),
                )
                self.assertEqual([], reopened._validation_issues(reopened.form_values()))
                reopened._export_documents()
                for _ in range(500):
                    QTest.qWait(10)
                    if reopened._export_thread is None:
                        break
                self.assertIsNone(reopened._export_thread)
                saved = repo.get_case(reopened.case_id)
                self.assertEqual("Đã tạo hồ sơ", saved.status)
                self.assertEqual("tax-24", saved.form_values["tax_template_id"])
                self.assertTrue(list(Path(saved.export_dir).rglob("*.docx")))
            finally:
                for workspace in workspaces:
                    workspace.draft_progress.stop()
                    workspace.deleteLater()
                self.app.processEvents()

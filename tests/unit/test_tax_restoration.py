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
from mingo_assistant.services.documents.tax_restoration_generator import TaxRestorationGenerator
from mingo_assistant.ui.main_window import MainWindow
from mingo_assistant.ui.views.tax_restoration_workspace import TaxRestorationWorkspace
from mingo_assistant.ui.views.tax_template_workspace import TAX_TEMPLATE_CASE_TYPE
from mingo_assistant.ui.views.tax_termination_workspace import TaxTerminationWorkspace


ROOT = Path(__file__).resolve().parents[2]
VALUES = {
    "tax_company_name": "CÔNG TY CỔ PHẦN KIỂM THỬ",
    "tax_registration_number": "0312345678",
    "tax_address": "12 Đường Kiểm Thử, Lâm Đồng, Việt Nam",
    "tax_receiving_authority": "Thuế cơ sở kiểm thử",
    "tax_signing_place": "Tỉnh Lâm Đồng",
    "tax_taxpayer": "NGUYỄN VĂN A",
    "tax_restoration_reason": "Đề nghị khôi phục mã số thuế\nĐể thực hiện thủ tục giải thể doanh nghiệp.",
}


class TaxRestorationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_catalog_routes_to_erc_workspace_with_only_restoration_reason(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repo = CaseRepository(root / "cases.json")
            repo._write_cases([])
            window = MainWindow(app_paths=AppPaths(ROOT, root, root / "exports"), case_repository=repo)
            try:
                window._open_tax_template_workspace("tax-25")
                workspace = window.current_workspace
                self.assertIsInstance(workspace, TaxRestorationWorkspace)
                self.assertEqual("erc", workspace.scan_document_type_input.currentData())
                field = workspace.fields["tax_restoration_reason"]
                self.assertIsInstance(field, QTextEdit)
                self.assertGreaterEqual(field.minimumHeight(), 110)
                self.assertEqual(QTextEdit.WidgetWidth, field.lineWrapMode())
                for key in ("tax_termination_reason", "tax_attached_documents", "tax_business_industry"):
                    self.assertNotIn(key, workspace.fields)
            finally:
                window.hide()
                window.close()
                window.deleteLater()
                self.app.processEvents()

    def test_generator_preserves_fixed_text_and_heading_drawing_with_multiline_reason(self):
        with TemporaryDirectory() as directory:
            generator = TaxRestorationGenerator(ROOT / "assets/templates/library/tax", directory)
            result = generator.generate(VALUES, "QA")
            with ZipFile(generator.template_dir / generator.FILENAME) as source, \
                    ZipFile(result.generated[0].output_path) as output:
                for name in source.namelist():
                    if name != "word/document.xml":
                        self.assertEqual(source.read(name), output.read(name))
                original = etree.fromstring(source.read("word/document.xml"))
                generated = etree.fromstring(output.read("word/document.xml"))
                runs = generated.xpath("//w:r[w:rPr/w:highlight and w:t]", namespaces=generator.NS)
                actual = [
                    "".join("\n" if node.tag == generator.W + "br" else (node.text or "")
                            for node in run.xpath("w:t|w:br", namespaces=generator.NS))
                    for run in runs
                ]
                self.assertEqual([
                    "CÔNG TY CỔ PHẦN", "KIỂM THỬ", "Lâm Đồng", VALUES["tax_receiving_authority"],
                    VALUES["tax_company_name"], VALUES["tax_registration_number"], VALUES["tax_address"],
                    VALUES["tax_restoration_reason"], VALUES["tax_taxpayer"],
                ], actual)
                for document in (original, generated):
                    signature = document.xpath("//w:r[w:rPr/w:highlight and w:t]", namespaces=generator.NS)[-1]
                    body = document.find(generator.W + "body")
                    tails = list(signature.getparent().itersiblings()) + [body[-2]]
                    self.assertEqual(4, len(tails))
                    for paragraph in tails:
                        self.assertTrue(all(child.tag == generator.W + "pPr" for child in paragraph))
                        if document is generated:
                            self.assertEqual(["20"], paragraph.xpath("w:pPr/w:spacing/@w:line", namespaces=generator.NS))
                        # Only these four empty paragraphs may have compacted
                        # spacing; all visible content/layout remains protected.
                        paragraph.getparent().remove(paragraph)
                    for run in document.xpath("//w:r[w:rPr/w:highlight]", namespaces=generator.NS):
                        for node in run.xpath("w:t|w:br", namespaces=generator.NS):
                            run.remove(node)
                self.assertEqual(etree.tostring(original), etree.tostring(generated))
            with self.assertRaises(ValueError):
                generator.generate(dict(VALUES, tax_restoration_reason=""), "Missing reason")

    def test_erc_draft_restore_export_and_independence_from_termination(self):
        with TemporaryDirectory() as directory, patch.object(QMessageBox, "information"), \
                patch.object(QMessageBox, "warning"):
            repo = CaseRepository(Path(directory) / "cases.json")
            repo._write_cases([])
            workspaces = []

            def create(case=None, template_id="tax-25"):
                if case is None:
                    case = CaseSummary.from_dict({
                        "id": str(uuid4()), "case_type": TAX_TEMPLATE_CASE_TYPE,
                        "form_values": {"tax_template_id": template_id},
                    })
                cls = TaxRestorationWorkspace if template_id == "tax-25" else TaxTerminationWorkspace
                workspace = cls(
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
                for key in ("tax_receiving_authority", "tax_signing_place", "tax_restoration_reason"):
                    workspace._set_field(key, VALUES[key])
                workspace.draft_progress.flush()
                reopened = create(repo.get_case(workspace.case_id))
                self.assertEqual(VALUES["tax_restoration_reason"], reopened._field_value("tax_restoration_reason"))
                other = create(template_id="tax-24")
                self.assertNotIn("tax_restoration_reason", other.fields)
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
                self.assertEqual("tax-25", saved.form_values["tax_template_id"])
                self.assertTrue(list(Path(saved.export_dir).rglob("*.docx")))
            finally:
                for workspace in workspaces:
                    workspace.draft_progress.stop()
                    workspace.deleteLater()
                self.app.processEvents()

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from zipfile import ZipFile

from lxml import etree
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QTextEdit

from mingo_assistant.app.paths import AppPaths
from mingo_assistant.repositories.case_repository import CaseRepository
from mingo_assistant.services.documents.tax_invoice_commitment_generator import (
    TaxInvoiceCommitmentGenerator,
)
from mingo_assistant.services.organization_documents.tax_commitment_document_service import (
    registration_dates,
)
from mingo_assistant.ui.main_window import MainWindow
from mingo_assistant.ui.views.tax_invoice_commitment_workspace import (
    TaxInvoiceCommitmentWorkspace,
)


ROOT = Path(__file__).resolve().parents[2]
ERC_TEXT = """Đăng ký lần đầu: ngày 01 tháng 02 năm 2020
Đăng ký thay đổi lần thứ: 2, ngày 03 tháng 04 năm 2025"""
VALUES = {
    "tax_company_name": "CÔNG TY TNHH KIỂM THỬ",
    "tax_signing_place": "Lâm Đồng",
    "tax_receiving_authority": "Thuế cơ sở kiểm thử",
    "tax_registration_number": "0312345678",
    "tax_issue_place": "Sở Tài chính Thành phố Hồ Chí Minh",
    "tax_issue_date": "01/02/2020",
    "tax_address": "12 Đường Kiểm Thử, Phường Tân Phú, Thành phố Hồ Chí Minh, Việt Nam",
    "tax_taxpayer": "NGUYỄN VĂN A",
    "tax_invoice_notice_commitment": (
        "NĐ 51/2010/NĐ-CP\n"
        "và chưa sử dụng hóa đơn giấy"
    ),
    "tax_einvoice_registration_commitment": (
        "123/2020/NĐ-CP\n"
        "và chưa phát sinh dữ liệu hóa đơn điện tử"
    ),
}


class TaxInvoiceCommitmentTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_selected_template_has_two_multiline_manual_fields(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repo = CaseRepository(root / "cases.json")
            repo._write_cases([])
            window = MainWindow(
                app_paths=AppPaths(ROOT, root, root / "exports"), case_repository=repo
            )
            try:
                window._open_tax_template_workspace("tax-invoice")
                workspace = window.current_workspace
                self.assertIsInstance(workspace, TaxInvoiceCommitmentWorkspace)
                self.assertNotIn("tax_business_industry", workspace.fields)
                for key, _ in workspace.MANUAL_FIELDS:
                    self.assertIsInstance(workspace.fields[key], QTextEdit)
                    self.assertGreaterEqual(workspace.fields[key].minimumHeight(), 110)
            finally:
                window.hide()
                window.close()
                window.deleteLater()
                self.app.processEvents()

    def test_generator_changes_only_highlighted_slots_and_normalizes_place(self):
        with TemporaryDirectory() as directory:
            generator = TaxInvoiceCommitmentGenerator(
                ROOT / "assets/templates/library/tax", Path(directory)
            )
            values = dict(VALUES, tax_signing_place="Tỉnh Lâm Đồng")
            result = generator.generate(values, "Kiểm thử", Path(directory) / "export")
            with ZipFile(generator.template_dir / generator.FILENAME) as original, ZipFile(
                result.generated[0].output_path
            ) as output:
                for name in original.namelist():
                    if name != "word/document.xml":
                        self.assertEqual(original.read(name), output.read(name))
                xml = etree.fromstring(output.read("word/document.xml"))
                source_xml = etree.fromstring(original.read("word/document.xml"))
                # All protected text, formatting and list structure must survive.
                for document in (source_xml, xml):
                    for run in document.xpath(
                        "//w:r[w:rPr/w:highlight[@w:val='green']]",
                        namespaces=generator.NS,
                    ):
                        for child in list(run):
                            if child.tag != generator.W + "rPr":
                                run.remove(child)
                self.assertEqual(
                    etree.tostring(source_xml), etree.tostring(xml)
                )
                xml = etree.fromstring(output.read("word/document.xml"))
                paragraphs = xml.xpath(
                    "//w:p[.//w:r[w:rPr/w:highlight[@w:val='green']]]",
                    namespaces=generator.NS,
                )
                texts = [
                    "\n".join(paragraph.xpath(".//w:t/text()", namespaces=generator.NS))
                    for paragraph in paragraphs
                ]
                self.assertIn("Lâm Đồng", texts[1])
                self.assertIn(", ngày", texts[1])
                self.assertNotIn("Tỉnh Lâm Đồng", texts[1])
                self.assertIn("Không thông báo phát hành hóa đơn", texts[8])
                self.assertEqual(1, texts[8].count("Không thông báo phát hành hóa đơn"))
                self.assertIn("chưa sử dụng hóa đơn giấy", texts[8])
                self.assertIn("Không đăng ký hóa đơn điện tử", texts[9])
                self.assertEqual(1, texts[9].count("Không đăng ký hóa đơn điện tử"))
            with self.assertRaises(ValueError):
                generator.generate({}, "Thiếu dữ liệu")

    def test_save_restore_export_and_case_folder_are_independent(self):
        with TemporaryDirectory() as directory, patch.object(
            QMessageBox, "information"
        ), patch.object(QMessageBox, "warning"):
            repo = CaseRepository(Path(directory) / "cases.json")
            repo._write_cases([])
            workspaces = []
            try:
                workspace = TaxInvoiceCommitmentWorkspace(
                    on_back=lambda: None,
                    on_save=repo.save_case,
                    bundle_root=ROOT,
                    default_export_root=Path(directory) / "exports",
                )
                workspaces.append(workspace)
                workspace.enable_draft_progress()
                recognized = {
                    "organization_owner_name": VALUES["tax_company_name"],
                    "organization_owner_registration_number": VALUES[
                        "tax_registration_number"
                    ],
                    "organization_owner_issue_date": "",
                    "organization_owner_issue_place": VALUES["tax_issue_place"],
                    "organization_owner_address_full": VALUES["tax_address"],
                    "tax_registration_dates": json.dumps(
                        registration_dates(ERC_TEXT), ensure_ascii=False
                    ),
                    "tax_legal_representatives": "NGUYỄN VĂN A\nTRẦN THỊ B",
                }
                workspace._apply_organization_values_to_current_person(
                    recognized, ERC_TEXT, "text"
                )
                workspace._update_organization_result_fields(recognized)
                workspace.registration_date.setCurrentIndex(1)
                workspace._save_organization_profile()
                workspace.taxpayer.setCurrentText(VALUES["tax_taxpayer"])
                for key in (
                    "tax_signing_place",
                    "tax_receiving_authority",
                    "tax_invoice_notice_commitment",
                    "tax_einvoice_registration_commitment",
                ):
                    workspace._set_field(key, VALUES[key])
                workspace.draft_progress.flush()

                reopened = TaxInvoiceCommitmentWorkspace(
                    on_back=lambda: None,
                    on_save=repo.save_case,
                    bundle_root=ROOT,
                    default_export_root=Path(directory) / "exports",
                    case=repo.get_case(workspace.case_id),
                )
                workspaces.append(reopened)
                reopened.enable_draft_progress()
                self.assertEqual(
                    VALUES["tax_invoice_notice_commitment"],
                    reopened._field_value("tax_invoice_notice_commitment"),
                )
                other = TaxInvoiceCommitmentWorkspace(
                    on_back=lambda: None, on_save=lambda case: None, bundle_root=ROOT
                )
                workspaces.append(other)
                self.assertNotEqual(
                    reopened._case_export_folder_name(reopened.form_values()),
                    other._case_export_folder_name(other.form_values()),
                )
                reopened._export_documents()
                for _ in range(500):
                    QTest.qWait(10)
                    if reopened._export_thread is None:
                        break
                self.assertIsNone(reopened._export_thread)
                exported = repo.get_case(reopened.case_id)
                self.assertEqual("Đã tạo hồ sơ", exported.status)
                self.assertEqual(1, len(exported.generated_documents))
                self.assertTrue(list(Path(exported.export_dir).rglob("*.docx")))
            finally:
                for workspace in workspaces:
                    if hasattr(workspace, "draft_progress"):
                        workspace.draft_progress.stop()
                    workspace.deleteLater()
                self.app.processEvents()

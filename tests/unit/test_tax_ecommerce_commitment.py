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
from mingo_assistant.services.documents.tax_ecommerce_commitment_generator import (
    TaxEcommerceCommitmentGenerator,
)
from mingo_assistant.services.organization_documents.tax_commitment_document_service import (
    registration_dates,
)
from mingo_assistant.ui.main_window import MainWindow
from mingo_assistant.ui.views.tax_ecommerce_commitment_workspace import (
    TaxEcommerceCommitmentWorkspace,
)


ROOT = Path(__file__).resolve().parents[2]
ERC_TEXT = """Đăng ký lần đầu: ngày 01 tháng 02 năm 2020
Đăng ký thay đổi lần thứ: 2, ngày 03 tháng 04 năm 2025"""
VALUES = {
    "tax_company_name": "CÔNG TY TNHH KIỂM THỬ",
    "tax_signing_place": "Thành phố Hồ Chí Minh",
    "tax_receiving_authority": "Thuế cơ sở 3 Thành phố Hồ Chí Minh",
    "tax_registration_number": "0312345678",
    "tax_issue_place": "Sở Tài chính Thành phố Hồ Chí Minh",
    "tax_issue_date": "01/02/2020",
    "tax_address": "12 Đường Kiểm Thử, Phường Tân Phú, Thành phố Hồ Chí Minh, Việt Nam",
    "tax_taxpayer": "NGUYỄN VĂN A",
    "tax_business_industry": "Bán lẻ hàng hóa khác trong các cửa hàng chuyên doanh (4773)",
}


class TaxEcommerceCommitmentTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_selected_template_reuses_complete_revenue_form(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repo = CaseRepository(root / "cases.json")
            repo._write_cases([])
            window = MainWindow(
                app_paths=AppPaths(ROOT, root, root / "exports"), case_repository=repo
            )
            try:
                window._open_tax_template_workspace("tax-ecommerce")
                workspace = window.current_workspace
                self.assertIsInstance(workspace, TaxEcommerceCommitmentWorkspace)
                self.assertIsInstance(workspace.fields["tax_business_industry"], QTextEdit)
                self.assertIn("tax_signing_place", workspace.fields)
                self.assertIsNotNone(workspace.fields["tax_signing_place"].completer())
                self.assertEqual("erc", workspace.scan_document_type_input.currentData())
            finally:
                window.hide()
                window.close()
                window.deleteLater()
                self.app.processEvents()

    def test_generator_fills_fragmented_green_groups_and_preserves_package(self):
        with TemporaryDirectory() as directory:
            generator = TaxEcommerceCommitmentGenerator(
                ROOT / "assets/templates/library/tax", Path(directory)
            )
            result = generator.generate(VALUES, "Kiểm thử", Path(directory) / "export")
            with ZipFile(generator.template_dir / generator.FILENAME) as original, ZipFile(
                result.generated[0].output_path
            ) as output:
                for name in original.namelist():
                    if name != "word/document.xml":
                        self.assertEqual(original.read(name), output.read(name))
                xml = etree.fromstring(output.read("word/document.xml"))
                highlighted_paragraphs = xml.xpath(
                    "//w:p[.//w:r[w:rPr/w:highlight[@w:val='green']]]",
                    namespaces=generator.NS,
                )
                texts = [
                    "".join(paragraph.xpath(".//w:t/text()", namespaces=generator.NS))
                    for paragraph in highlighted_paragraphs
                ]
                for expected in (
                    VALUES["tax_signing_place"],
                    VALUES["tax_receiving_authority"],
                    VALUES["tax_company_name"],
                    VALUES["tax_registration_number"],
                    VALUES["tax_issue_place"],
                    VALUES["tax_issue_date"],
                    VALUES["tax_address"],
                    VALUES["tax_taxpayer"],
                    VALUES["tax_business_industry"],
                ):
                    self.assertTrue(any(expected in text for text in texts), expected)
                self.assertEqual(50, len(xml.xpath(
                    "//w:r[w:rPr/w:highlight[@w:val='green']]", namespaces=generator.NS
                )))
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
                workspace = TaxEcommerceCommitmentWorkspace(
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
                    "tax_business_industry",
                ):
                    workspace._set_field(key, VALUES[key])
                workspace.draft_progress.flush()

                reopened = TaxEcommerceCommitmentWorkspace(
                    on_back=lambda: None,
                    on_save=repo.save_case,
                    bundle_root=ROOT,
                    default_export_root=Path(directory) / "exports",
                    case=repo.get_case(workspace.case_id),
                )
                workspaces.append(reopened)
                reopened.enable_draft_progress()
                self.assertEqual(
                    VALUES["tax_business_industry"],
                    reopened._field_value("tax_business_industry"),
                )
                other = TaxEcommerceCommitmentWorkspace(
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

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from zipfile import ZipFile

from lxml import etree
from PySide6.QtWidgets import QApplication, QMessageBox, QLineEdit, QTextEdit
from PySide6.QtTest import QTest

from mingo_assistant.app.paths import AppPaths
from mingo_assistant.repositories.case_repository import CaseRepository
from mingo_assistant.services.documents.tax_revenue_commitment_generator import (
    TaxRevenueCommitmentGenerator,
)
from mingo_assistant.services.organization_documents.tax_commitment_document_service import (
    registration_dates,
)
from mingo_assistant.ui.main_window import MainWindow
from mingo_assistant.ui.views.tax_invoice_commitment_workspace import (
    TaxInvoiceCommitmentWorkspace,
)
from mingo_assistant.ui.views.tax_revenue_commitment_workspace import (
    TaxRevenueCommitmentWorkspace,
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
    "tax_business_industry": "Bán lẻ hàng hóa khác trong các cửa hàng chuyên doanh\nMã ngành 4773",
}


class TaxRevenueCommitmentTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_selected_template_uses_revenue_workspace_only(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repo = CaseRepository(root / "cases.json")
            repo._write_cases([])
            window = MainWindow(app_paths=AppPaths(ROOT, root, root / "exports"), case_repository=repo)
            try:
                window._open_tax_template_workspace("tax-revenue")
                self.assertIsInstance(window.current_workspace, TaxRevenueCommitmentWorkspace)
                self.assertIsInstance(
                    window.current_workspace.fields["tax_signing_place"], QLineEdit
                )
                signing_place = window.current_workspace.fields["tax_signing_place"]
                self.assertIsNotNone(signing_place.completer())
                self.assertIn(
                    "Thành phố Hồ Chí Minh",
                    signing_place.completer().model().stringList(),
                )
                self.assertIn("Lâm Đồng", signing_place.completer().model().stringList())
                self.assertIn("Hải Phòng", signing_place.completer().model().stringList())
                window.current_workspace._refresh_signing_place_suggestions(
                    signing_place, "hcm"
                )
                self.assertEqual(
                    ["Thành phố Hồ Chí Minh"],
                    signing_place.completer().model().stringList(),
                )
                self.assertIsInstance(window.current_workspace.fields["tax_business_industry"], QTextEdit)
                self.assertGreaterEqual(
                    window.current_workspace.fields["tax_business_industry"].minimumHeight(), 110
                )
                window.current_workspace.on_back()
                window._open_tax_template_workspace("tax-invoice")
                self.assertIsInstance(
                    window.current_workspace, TaxInvoiceCommitmentWorkspace
                )
                self.assertNotIn("tax_business_industry", window.current_workspace.fields)
            finally:
                window.hide()
                window.close()
                window.deleteLater()
                self.app.processEvents()

    def test_generator_fills_all_green_slots_and_preserves_package(self):
        with TemporaryDirectory() as directory:
            generator = TaxRevenueCommitmentGenerator(
                ROOT / "assets/templates/library/tax", Path(directory)
            )
            result = generator.generate(VALUES, "Kiểm thử", Path(directory) / "export")
            expected = generator._replacement_values(VALUES)
            with ZipFile(generator.template_dir / generator.FILENAME) as original, ZipFile(
                result.generated[0].output_path
            ) as output:
                for name in original.namelist():
                    if name != "word/document.xml":
                        self.assertEqual(original.read(name), output.read(name))
                xml = etree.fromstring(output.read("word/document.xml"))
                runs = xml.xpath(
                    "//w:r[w:rPr/w:highlight[@w:val='green']]", namespaces=generator.NS
                )
                actual = []
                for run in runs:
                    pieces = []
                    for node in run.xpath("w:t|w:br", namespaces=generator.NS):
                        pieces.append(
                            "\n" if node.tag == generator.W + "br" else (node.text or "")
                        )
                    actual.append("".join(pieces))
                self.assertEqual(list(expected), actual)
            with self.assertRaises(ValueError):
                generator.generate({}, "Thiếu dữ liệu")

    def test_erc_data_industry_save_restore_and_export_are_independent(self):
        with TemporaryDirectory() as directory, patch.object(
            QMessageBox, "information"
        ), patch.object(QMessageBox, "warning"):
            repo = CaseRepository(Path(directory) / "cases.json")
            repo._write_cases([])
            workspaces = []
            try:
                workspace = TaxRevenueCommitmentWorkspace(
                    on_back=lambda: None,
                    on_save=repo.save_case,
                    bundle_root=ROOT,
                    default_export_root=Path(directory) / "exports",
                )
                workspaces.append(workspace)
                workspace.enable_draft_progress()
                recognized = {
                    "organization_owner_name": VALUES["tax_company_name"],
                    "organization_owner_registration_number": VALUES["tax_registration_number"],
                    "organization_owner_issue_date": "",
                    "organization_owner_issue_place": VALUES["tax_issue_place"],
                    "organization_owner_address_full": VALUES["tax_address"],
                    "tax_registration_dates": json.dumps(
                        registration_dates(ERC_TEXT), ensure_ascii=False
                    ),
                    "tax_legal_representatives": "NGUYỄN VĂN A\nTRẦN THỊ B",
                }
                workspace._apply_organization_values_to_current_person(recognized, ERC_TEXT, "text")
                workspace._update_organization_result_fields(recognized)
                workspace.registration_date.setCurrentIndex(1)
                workspace._save_organization_profile()
                self.assertEqual("", workspace._field_value("tax_signing_place"))
                workspace.taxpayer.setCurrentText(VALUES["tax_taxpayer"])
                workspace._set_field(
                    "tax_receiving_authority", VALUES["tax_receiving_authority"]
                )
                workspace._set_field("tax_signing_place", VALUES["tax_signing_place"])
                workspace._set_field("tax_business_industry", VALUES["tax_business_industry"])
                values = workspace.form_values()
                self.assertEqual("Thành phố Hồ Chí Minh", values["tax_signing_place"])
                workspace._set_field("tax_signing_place", "Tỉnh Lâm Đồng")
                self.assertEqual("Lâm Đồng", workspace.form_values()["tax_signing_place"])
                workspace._set_field("tax_signing_place", VALUES["tax_signing_place"])
                self.assertEqual(VALUES["tax_business_industry"], values["tax_business_industry"])
                workspace.draft_progress.flush()

                reopened = TaxRevenueCommitmentWorkspace(
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
                other = TaxRevenueCommitmentWorkspace(
                    on_back=lambda: None, on_save=lambda case: None, bundle_root=ROOT
                )
                workspaces.append(other)
                self.assertEqual("", other._field_value("tax_business_industry"))
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

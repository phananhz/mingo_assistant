import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from zipfile import ZipFile

from lxml import etree
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtTest import QTest

from mingo_assistant.services.organization_documents.tax_commitment_document_service import registration_dates, legal_representatives, TaxCommitmentDocumentService
from mingo_assistant.services.documents.tax_commitment_generator import TaxCommitmentGenerator
from mingo_assistant.ui.views.tax_commitment_workspace import TaxCommitmentWorkspace
from mingo_assistant.ui.views.tax_invoice_commitment_workspace import TaxInvoiceCommitmentWorkspace
from mingo_assistant.ui.views.tax_template_workspace import TaxTemplateWorkspace
from mingo_assistant.repositories.case_repository import CaseRepository

ROOT = Path(__file__).resolve().parents[2]
TEXT = """SỞ TÀI CHÍNH THÀNH PHỐ HỒ CHÍ MINH
PHÒNG ĐĂNG KÝ KINH DOANH
GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP
CÔNG TY TRÁCH NHIỆM HỮU HẠN
Mã số doanh nghiệp: 0312345678
Đăng ký lần đầu: ngày 01 tháng 02 năm 2020
Đăng ký thay đổi lần thứ: 2, ngày 03 tháng 04 năm 2025
1. Tên công ty
Tên công ty viết bằng tiếng Việt: CÔNG TY TNHH KIỂM THỬ
2. Địa chỉ trụ sở chính: 12 Đường Kiểm Thử, Phường Tân Phú, Thành phố Hồ Chí Minh, Việt Nam
3. Vốn điều lệ: 1000000000
5. Người đại diện theo pháp luật của công ty
Họ và tên: NGUYỄN VĂN A Giới tính: Nam
Chức danh: Giám đốc
Họ, chữ đệm và tên: TRẦN THỊ B
Chức danh: Tổng giám đốc
"""
VALUES = {
    "tax_company_name": "CÔNG TY TNHH KIỂM THỬ", "tax_registration_number": "0312345678",
    "tax_issue_date": "01/02/2020", "tax_issue_place": "Sở Tài chính Thành phố Hồ Chí Minh",
    "tax_address": "12 Đường Kiểm Thử, Phường Tân Phú, Thành phố Hồ Chí Minh, Việt Nam",
    "tax_receiving_authority": "Thuế cơ sở kiểm thử", "tax_taxpayer": "TRẦN THỊ B",
}


class TaxCommitmentTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_dates_and_all_representatives_come_from_erc(self):
        dates = registration_dates(TEXT)
        self.assertEqual(["Đăng ký lần đầu", "Đăng ký thay đổi lần hai"], [d["label"] for d in dates])
        self.assertEqual(["01/02/2020", "03/04/2025"], [d["date"] for d in dates])
        self.assertEqual(["NGUYỄN VĂN A", "TRẦN THỊ B"], legal_representatives(TEXT))
        self.assertEqual([], registration_dates("Đăng ký lần đầu: ngày 31 tháng 02 năm 2020"))
        self.assertEqual([], legal_representatives("Chủ sở hữu\nHọ và tên: KHÔNG PHẢI NGƯỜI ĐẠI DIỆN"))
        service = TaxCommitmentDocumentService(bundle_root=ROOT)
        result = service._build_certificate_result(TEXT, TEXT, "text", source="pdf_text")
        self.assertEqual("", result.values["organization_owner_issue_date"])
        self.assertIn("Thành phố Hồ Chí Minh", result.values["organization_owner_address_full"])

    def test_native_pdf_reads_representatives_on_later_page_without_ocr(self):
        import fitz
        font = Path("C:/Windows/Fonts/arial.ttf")
        if not font.is_file():
            self.skipTest("Vietnamese font not available for synthetic native PDF")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "erc.pdf"
            document = fitz.open()
            parts = TEXT.split("5. Người đại diện")
            for text in (parts[0], "5. Người đại diện" + parts[1]):
                page = document.new_page(width=900, height=1000)
                page.insert_font(fontname="vietnamese", fontfile=str(font))
                page.insert_text((40, 40), text, fontname="vietnamese", fontsize=10)
            document.save(path)
            document.close()
            service = TaxCommitmentDocumentService(bundle_root=ROOT)
            with patch.object(service, "_extract_with_ocr", side_effect=AssertionError("Native PDF should not require OCR")):
                result = service.extract_pdf(path)
            self.assertIn("TRẦN THỊ B", result.values["tax_legal_representatives"])
            self.assertEqual(2, len(json.loads(result.values["tax_registration_dates"])))

    def test_only_selected_tax_template_uses_special_workspace(self):
        from mingo_assistant.app.paths import AppPaths
        from mingo_assistant.ui.main_window import MainWindow
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repo = CaseRepository(root / "cases.json")
            repo._write_cases([])
            window = MainWindow(app_paths=AppPaths(ROOT, root, root / "exports"), case_repository=repo)
            try:
                window._open_tax_template_workspace("tax-commitment")
                self.assertIsInstance(window.current_workspace, TaxCommitmentWorkspace)
                window.current_workspace.on_back()
                window._open_tax_template_workspace("tax-invoice")
                self.assertIsInstance(
                    window.current_workspace, TaxInvoiceCommitmentWorkspace
                )
                self.assertIn("tax_receiving_authority", window.current_workspace.fields)
                self.assertNotIn("tax_business_industry", window.current_workspace.fields)
            finally:
                window.hide()
                window.close()
                window.deleteLater()
                self.app.processEvents()

    def test_generator_changes_only_mapped_green_text_and_preserves_package(self):
        with TemporaryDirectory() as directory:
            generator = TaxCommitmentGenerator(ROOT / "assets/templates/library/tax", Path(directory))
            result = generator.generate(VALUES, "Kiểm thử", Path(directory) / "export")
            with ZipFile(generator.template_dir / generator.FILENAME) as original, ZipFile(result.generated[0].output_path) as output:
                for name in original.namelist():
                    if name != "word/document.xml":
                        self.assertEqual(original.read(name), output.read(name))
                before = etree.fromstring(original.read("word/document.xml"))
                after = etree.fromstring(output.read("word/document.xml"))
                runs = after.xpath("//w:r[w:rPr/w:highlight[@w:val='green']]", namespaces=generator.NS)
                self.assertEqual([VALUES[key] for key in generator.KEYS], ["".join(r.xpath("w:t/text()", namespaces=generator.NS)) for r in runs])
                for xml in (before, after):
                    for run in xml.xpath("//w:r[w:rPr/w:highlight[@w:val='green']]", namespaces=generator.NS):
                        for text in run.xpath("w:t", namespaces=generator.NS):
                            text.text = ""
                            text.attrib.clear()
                self.assertEqual(etree.tostring(before), etree.tostring(after))
            with self.assertRaises(ValueError):
                generator.generate({}, "Kiểm thử")

    def test_confirm_select_restore_manual_taxpayer_and_export_independently(self):
        with TemporaryDirectory() as directory, patch.object(QMessageBox, "information"), patch.object(QMessageBox, "warning") as warning:
            repo = CaseRepository(Path(directory) / "cases.json")
            repo._write_cases([])
            workspaces = []
            try:
                w = TaxCommitmentWorkspace(on_back=lambda: None, on_save=repo.save_case, bundle_root=ROOT, default_export_root=Path(directory) / "exports")
                workspaces.append(w)
                w.enable_draft_progress()
                self.assertEqual("erc", w.scan_document_type_input.currentData())
                self.assertNotIn("document_place", w.fields)
                self.assertNotIn("document_day", w.fields)
                values = {
                    "organization_owner_name": VALUES["tax_company_name"],
                    "organization_owner_registration_number": VALUES["tax_registration_number"],
                    "organization_owner_issue_date": "", "organization_owner_issue_place": VALUES["tax_issue_place"],
                    "organization_owner_address_full": VALUES["tax_address"],
                    "tax_registration_dates": json.dumps(registration_dates(TEXT), ensure_ascii=False),
                    "tax_legal_representatives": "NGUYỄN VĂN A\nTRẦN THỊ B",
                }
                w._apply_organization_values_to_current_person(values, TEXT, "text")
                w._update_organization_result_fields(values)
                self.assertEqual("", w.form_values()["tax_company_name"])
                w._save_organization_profile()
                self.assertTrue(warning.called)
                self.assertFalse(w.ocr_people[0].recognition_saved)
                w.registration_date.setCurrentIndex(1)
                w._save_organization_profile()
                self.assertEqual(2, w.taxpayer.count())
                self.assertEqual("", w.taxpayer.currentText())
                w.taxpayer.setCurrentText("NGƯỜI NỘP THUẾ NHẬP TAY")
                w._update_organization_result_fields(values)
                w.registration_date.setCurrentIndex(2)
                w._save_organization_profile()
                self.assertEqual("NGƯỜI NỘP THUẾ NHẬP TAY", w.taxpayer.currentText())
                w._set_field("tax_receiving_authority", VALUES["tax_receiving_authority"])
                w.draft_progress.flush()
                saved = repo.get_case(w.case_id)
                other = TaxCommitmentWorkspace(on_back=lambda: None, on_save=repo.save_case, bundle_root=ROOT)
                workspaces.append(other)
                other.enable_draft_progress()
                self.assertEqual("", other.form_values()["tax_company_name"])
                self.assertNotEqual(w._case_export_folder_name(w.form_values()), other._case_export_folder_name(other.form_values()))
                reopened = TaxCommitmentWorkspace(on_back=lambda: None, on_save=repo.save_case, bundle_root=ROOT, case=saved)
                workspaces.append(reopened)
                reopened.enable_draft_progress()
                self.assertEqual("NGƯỜI NỘP THUẾ NHẬP TAY", reopened.taxpayer.currentText())
                self.assertEqual("03/04/2025", reopened.form_values()["tax_issue_date"])
                reopened.registration_date.setEditText("05/06/2024")
                self.assertEqual("05/06/2024", reopened._organization_result_values()["organization_owner_issue_date"])
                self.assertTrue(reopened._validation_issues(reopened.form_values()))
                reopened._save_organization_profile()
                reopened.draft_progress.flush()
                restored_manual = TaxCommitmentWorkspace(on_back=lambda: None, on_save=repo.save_case, bundle_root=ROOT, case=repo.get_case(w.case_id))
                workspaces.append(restored_manual)
                restored_manual.enable_draft_progress()
                self.assertEqual("05/06/2024", restored_manual._organization_result_values()["organization_owner_issue_date"])
                w._export_documents()
                for _ in range(500):
                    QTest.qWait(10)
                    if w._export_thread is None:
                        break
                self.assertIsNone(w._export_thread)
                exported = repo.get_case(w.case_id)
                self.assertEqual("Đã tạo hồ sơ", exported.status)
                self.assertTrue(list(Path(exported.export_dir).rglob("*.docx")))
                self.assertEqual(1, len(exported.generated_documents))
                generic = TaxTemplateWorkspace(on_back=lambda: None, on_save=lambda c: None, bundle_root=ROOT)
                workspaces.append(generic)
                with self.assertRaises(ValueError):
                    generic._document_generator_class()
            finally:
                for workspace in workspaces:
                    if hasattr(workspace, "draft_progress"):
                        workspace.draft_progress.stop()
                    workspace.deleteLater()
                self.app.processEvents()

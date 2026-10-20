from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, patch

import fitz

from mingo_assistant.services.organization_documents.pdf_text import extract_certificate_text
from mingo_assistant.services.organization_documents.organization_document_service import OrganizationDocumentService


class CertificatePdfTextTests(TestCase):
    def test_missing_to_unicode_map_is_recovered_from_embedded_font(self):
        with fitz.open() as document:
            page = document.new_page()
            xref = page.insert_font(fontname="fixture", fontbuffer=fitz.Font("cjk").buffer)
            # Write the footer before the header, as in the customer PDFs.
            for y, text in ((150, "2. Dia chi tru so chinh:"), (70, "GIAY CHUNG NHAN DANG KY DOANH NGHIEP"),
                            (95, "Ma so doanh nghiep: 0312345678"), (125, "CONG TY TNHH MINH AN")):
                page.insert_text((40, y), text, fontname="fixture", fontsize=11)
            document.xref_set_key(xref, "ToUnicode", "null")
            data = document.tobytes()
        with fitz.open(stream=data, filetype="pdf") as document:
            self.assertNotIn("GIAY CHUNG NHAN", document[0].get_text())
            recovered = extract_certificate_text(document)
        self.assertIn("GIAY CHUNG NHAN DANG KY DOANH NGHIEP", recovered)
        self.assertIn("Ma so doanh nghiep: 0312345678", recovered)
        self.assertIn("CONG TY TNHH MINH AN", recovered)
        self.assertLess(recovered.index("GIAY CHUNG NHAN"), recovered.index("2. Dia chi"))

    def test_healthy_text_does_not_inspect_or_reinterpret_fonts(self):
        page = MagicMock()
        page.get_text.return_value = "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP\nMã số: 0312345678"
        self.assertEqual(page.get_text.return_value, extract_certificate_text([page]))
        page.get_texttrace.assert_not_called()
        page.get_fonts.assert_not_called()

    def test_unrecoverable_pdf_keeps_the_existing_ocr_fallback(self):
        page = MagicMock()
        page.get_text.return_value = "\ufffd" * 30
        with patch("mingo_assistant.services.organization_documents.pdf_text._recover_page", side_effect=RuntimeError("bad font")):
            self.assertEqual("\ufffd" * 30, extract_certificate_text([page]))

    def test_wrapped_company_name_keeps_trade_words_and_numeric_lines(self):
        service = OrganizationDocumentService()
        for continuation in ("THƯƠNG MẠI VÀ DỊCH VỤ MINH AN", "MẠI MINH AN", "369"):
            with self.subTest(continuation=continuation):
                result = service._company_name([
                    "Tên công ty viết bằng tiếng Việt: CÔNG TY TNHH",
                    continuation,
                    "Tên công ty viết bằng tiếng nước ngoài: OTHER COMPANY",
                    "2. Địa chỉ trụ sở chính",
                ])
                self.assertEqual(f"CÔNG TY TNHH {continuation}", result)

    def test_short_village_address_from_valid_pdf_does_not_require_ocr(self):
        service = OrganizationDocumentService()
        result = service._document_result({
            "organization_owner_name": "CÔNG TY TNHH KIỂM THỬ",
            "organization_owner_registration_number": "0312345678",
            "organization_owner_address_detail": "Ấp Xóm Cò",
            "organization_owner_ward": "Xã Nhơn Ninh",
            "organization_owner_province": "Tây Ninh",
        }, "", "text", source="pdf_text")
        self.assertFalse(service._needs_ocr_fallback(result))
        self.assertTrue(service._needs_ocr_fallback(service._document_result({
            **result.values, "organization_owner_registration_number": "03123",
        }, "", "text", source="pdf_text")))

    def test_readable_short_text_address_does_not_depend_on_place_matching(self):
        service = OrganizationDocumentService()
        values = {
            "organization_owner_name": "CÔNG TY TNHH KIỂM THỬ",
            "organization_owner_registration_number": "0312345678",
            "organization_owner_address_detail": "Thôn Nhì",
            "organization_owner_ward": "",
            "organization_owner_province": "",
        }
        result = service._document_result(values, "", "text", source="pdf_text")
        self.assertFalse(service._needs_ocr_fallback(result))
        for address in ("", "Số 757D đường Nguyn Th Đnh", "???"):
            with self.subTest(address=address):
                damaged = service._document_result(
                    {**values, "organization_owner_address_detail": address}, "", "text", source="pdf_text",
                )
                self.assertTrue(service._needs_ocr_fallback(damaged))

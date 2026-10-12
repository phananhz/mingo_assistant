from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from mingo_assistant.services.organization_documents.business_amendment_document_service import BusinessAmendmentDocumentService
from mingo_assistant.services.organization_documents.organization_document_service import OrganizationDocumentService


CERTIFICATE = """SỞ TÀI CHÍNH
THÀNH PHỐ HỒ CHÍ MINH
PHÒNG ĐĂNG KÝ KINH DOANH
GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP
Mã số doanh nghiệp: 0319291466
Đăng ký lần đầu: ngày 02 tháng 12 năm 2025
Đăng ký thay đổi lần thứ: 2, ngày 08 tháng 10 năm 2026
1. Tên công ty
Tên công ty viết bằng tiếng Việt: CÔNG TY TNHH KIỂM THỬ
Tên công ty viết bằng tiếng nước ngoài: VIETNAM COMPANY LIMITED
Tên công ty viết tắt:
2. Địa chỉ trụ sở chính
13/5 Ao Đôi, Phường Bình Tân, Thành phố Hồ Chí Minh, Việt Nam
S Fax:
Điện thoại: 0900000000
Email: test@example.com
3. Vốn điều lệ
2.000.000.000 đồng
Mệnh giá cổ phần: 10.000 đồng
Tổng số cổ phần:
200.000
4. Thông tin về chủ sở hữu
Tên tổ chức: FOREIGN OWNER
Mã số doanh nghiệp: 9999999999
5. Người đại diện theo pháp luật của công ty
Họ, chữ đệm và tên: NGUYỄN THỊ KIỂM THỬ
Giới tính: Nữ
Sinh ngày: 30/01/1998
Quốc tịch: Việt Nam
Loại giấy tờ pháp lý của cá nhân: Thẻ căn cước công dân
Số giấy tờ pháp lý của cá nhân: 012345678901
Ngày cấp: 10/05/2021
Nơi cấp: Cục Cảnh sát
Chức danh: Giám đốc
Địa chỉ liên lạc: 123 đường Kiểm Thử, Phường An Lạc, Thành phố Hồ Chí Minh, Việt Nam
KT.TRƯỞNG PHÒNG
PHÓ TRƯỞNG PHÒNG
ISSUER NAME
"""


class BusinessAmendmentDocumentTests(unittest.TestCase):
    def test_public_pdf_result_contains_only_company_name_and_code(self):
        service = BusinessAmendmentDocumentService()
        rich = service._extract_supported_document(CERTIFICATE, "text", source="pdf_text")
        with patch.object(OrganizationDocumentService, "extract_pdf", return_value=rich):
            result = service.extract_pdf(Path("test.pdf"))
        self.assertEqual(set(service.RECOGNIZED_FIELDS), set(result.values))
        self.assertEqual("CÔNG TY TNHH KIỂM THỬ", result.values["organization_owner_name"])
        self.assertEqual("0319291466", result.values["organization_owner_registration_number"])
        self.assertTrue(set(result.field_sources).issubset(service.RECOGNIZED_FIELDS))
        self.assertTrue(set(result.field_confidences).issubset(service.RECOGNIZED_FIELDS))
        self.assertFalse(any("người đại diện" in warning.casefold() for warning in result.warnings))

    def test_extracts_company_capital_shares_and_representative_in_separate_sections(self):
        service = BusinessAmendmentDocumentService()
        result = service._extract_supported_document(CERTIFICATE, "text", source="pdf_text")
        values = result.values
        self.assertEqual("CÔNG TY TNHH KIỂM THỬ", values["organization_owner_name"])
        self.assertEqual("0319291466", values["organization_owner_registration_number"])
        self.assertEqual("2000000000", values["organization_capital"])
        self.assertEqual("200000", values["organization_share_count"])
        self.assertEqual("10000", values["organization_share_par_value"])
        self.assertEqual("02/12/2025", values["organization_first_registration_date"])
        self.assertEqual("08/10/2026", values["organization_owner_issue_date"])
        self.assertEqual("VIETNAM COMPANY LIMITED", values["organization_english_name"])
        self.assertEqual("", values["organization_short_name"])
        self.assertEqual("NGUYỄN THỊ KIỂM THỬ", values["legal_representative_full_name"])
        self.assertEqual("012345678901", values["legal_representative_id_number"])
        self.assertEqual("30/01/1998", values["legal_representative_date_of_birth"])
        self.assertNotIn("ISSUER", values["legal_representative_contact_address"])
        self.assertNotIn("Fax", values["organization_original_address"])
        self.assertEqual(CERTIFICATE, result.raw_text)

    def test_owner_document_cannot_be_used_as_registered_company(self):
        service = BusinessAmendmentDocumentService()
        owner = "4. Thông tin về chủ sở hữu\nTên tổ chức: OWNER\nMã số doanh nghiệp: 9999999999\n5. Other"
        self.assertIsNone(service._extract_supported_document(owner, "text"))

    def test_existing_extractor_does_not_gain_amendment_fields(self):
        values = OrganizationDocumentService()._extract_supported_document(CERTIFICATE, "text").values
        self.assertNotIn("organization_capital", values)
        self.assertNotIn("legal_representative_full_name", values)

    def test_disagreement_is_reported_and_valid_id_beats_document_type(self):
        service = BusinessAmendmentDocumentService()
        first = service._document_result({"organization_owner_name": "COMPANY", "legal_representative_id_number": "Thẻ căn cước",
                                         "legal_representative_passport_number": "EQ1234567"}, "text", "ocr", source="ppocr_v6")
        second = service._document_result({"organization_owner_name": "COMPANY", "legal_representative_id_number": "012345678901",
                                          "legal_representative_passport_number": "E01234567"}, "text", "ocr", source="rapidocr")
        result = service._merge_results(first, second)
        self.assertEqual("012345678901", result.values["legal_representative_id_number"])
        self.assertTrue(any("Hộ chiếu" in warning for warning in result.warnings))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import MagicMock, patch

from mingo_assistant.services.organization_documents.location_certificate_service import (
    LocationCertificateService,
)
from mingo_assistant.services.organization_documents.organization_document_service import (
    DocumentTypeMismatchError,
    OrganizationDocumentService,
)


NOISY_BRC = """GIAY CHUNG NHAN DANG KY DIA DIEM KINH DOANH
Ma so dia diem kinh doanh: 00003
1. Ten dia diem kinh doanh: DIA DIEM KINH DOANH SO 3 - CONG TY TNHH VIEN DONG
Ten dia diem kinh doanh viet bang tieng nuoc ngoai:
2. Dja chi:
Biet thu lien ke can 206 Louis 2, Khu do thi Louis City Dai Mo,
Phuong Dai Mo, Thanh pho Ha Noi, Viet Nam
Dien thoai:
3. Thong tin ve nguoi dung dau
4. Thong tin ve doanh nghiep/chi nhanh chu quan:
Ten doanh nghiep/chi nhanh: CONG TY TNHH VIEN DONG
Ma so doanh nghiep/chi nhanh: 0112345678
Dia chi tru so chinh cua doanh nghiep/chi nhanh: Ha Noi
"""

ERC_TEXT = """GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP
Mã số doanh nghiệp: 0312345678
1. Tên công ty
Tên công ty viết bằng tiếng Việt: CÔNG TY TNHH KIỂM THỬ
2. Địa chỉ trụ sở chính: Hà Nội
"""


class LocationCertificateOcrQualityTests(TestCase):
    def test_brc_primary_pass_uses_bundled_ppocr_v6(self) -> None:
        service = LocationCertificateService()
        service._vietnamese_ocr = MagicMock()
        service._vietnamese_ocr.is_available = True
        service._vietnamese_ocr.model_dir = Path("models")
        service._vietnamese_ocr.recognize_detailed.return_value = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "GIẤY CHỨNG NHẬN", 0.96)
        ]
        legacy = MagicMock()

        text = service._extract_page_with_ocr(legacy, b"not-an-image")

        self.assertEqual("GIẤY CHỨNG NHẬN", text)
        service._vietnamese_ocr.recognize_detailed.assert_called_once()
        legacy.assert_not_called()

    def test_document_type_classifier_distinguishes_erc_and_brc(self) -> None:
        self.assertEqual("brc", OrganizationDocumentService.detect_document_type(NOISY_BRC))
        self.assertEqual("erc", OrganizationDocumentService.detect_document_type(ERC_TEXT))

    def test_erc_workflow_rejects_brc_before_full_ocr(self) -> None:
        with TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "wrong-brc.pdf"
            pdf_path.touch()
            page = MagicMock()
            page.get_text.return_value = NOISY_BRC
            document = MagicMock()
            document.__iter__.return_value = iter([page])
            service = OrganizationDocumentService()
            with patch(
                "mingo_assistant.services.organization_documents.organization_document_service.fitz.open"
            ) as open_pdf:
                open_pdf.return_value.__enter__.return_value = document
                with patch.object(service, "_extract_with_ocr") as full_ocr:
                    with self.assertRaisesRegex(DocumentTypeMismatchError, "Sai loại tài liệu"):
                        service.extract_pdf(pdf_path)

        full_ocr.assert_not_called()

    def test_brc_workflow_rejects_erc_before_full_ocr(self) -> None:
        with TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "wrong-erc.pdf"
            pdf_path.touch()
            page = MagicMock()
            page.get_text.return_value = ERC_TEXT
            document = MagicMock()
            document.__iter__.return_value = iter([page])
            service = LocationCertificateService()
            with patch(
                "mingo_assistant.services.organization_documents.location_certificate_service.fitz.open"
            ) as open_pdf:
                open_pdf.return_value.__enter__.return_value = document
                with patch.object(service, "_extract_with_ocr") as full_ocr:
                    with self.assertRaisesRegex(DocumentTypeMismatchError, "Sai loại tài liệu"):
                        service.extract_pdf(pdf_path)

        full_ocr.assert_not_called()

    def test_scanned_wrong_type_uses_only_quick_first_page_check(self) -> None:
        with TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "scanned-wrong-brc.pdf"
            pdf_path.touch()
            page = MagicMock()
            page.get_text.return_value = ""
            document = MagicMock()
            document.__iter__.return_value = iter([page])
            service = OrganizationDocumentService()
            with patch(
                "mingo_assistant.services.organization_documents.organization_document_service.fitz.open"
            ) as open_pdf:
                open_pdf.return_value.__enter__.return_value = document
                with patch.object(
                    service, "_extract_first_page_for_type_detection", return_value=NOISY_BRC
                ) as quick_check:
                    with patch.object(service, "_extract_with_ocr") as full_ocr:
                        with self.assertRaises(DocumentTypeMismatchError):
                            service.extract_pdf(pdf_path)

        quick_check.assert_called_once()
        full_ocr.assert_not_called()

    def test_fuzzy_address_label_keeps_multiline_brc_address(self) -> None:
        service = LocationCertificateService()
        values = service._parse_certificate(NOISY_BRC)

        self.assertEqual("00003", values["location_business_code"])
        self.assertEqual("0112345678", values["parent_entity_registration_number"])
        self.assertIn("Biet thu lien ke can 206 Louis 2", values["location_full_address"])
        self.assertIn("phuongdaimo", service._compact(values["location_full_address"]))
        self.assertNotIn("Dien thoai", values["location_full_address"])

    def test_brc_quality_penalizes_missing_letters_in_address(self) -> None:
        service = LocationCertificateService()

        correct = service._field_quality_for_brc(
            "location_full_address",
            "Số 757D, đường Nguyễn Thị Định, Thành phố Hồ Chí Minh",
        )
        damaged = service._field_quality_for_brc(
            "location_full_address",
            "Số 757D, đường Nguyn Th Đnh, Thành phố Hồ Chí Minh",
        )

        self.assertGreater(correct, damaged)
        self.assertLess(damaged, 0.80)

    def test_safe_legal_and_administrative_phrases_restore_common_ocr_errors(self) -> None:
        service = LocationCertificateService()

        restored = service._restore_address(
            "S6 258 pho Bach Mai, Thira dat 1459, ThanhphoThuDirc, Viet Nam"
        )

        self.assertEqual(
            "Số 258 phố Bạch Mai, Thửa đất 1459, Thành phố Thủ Đức, Việt Nam",
            restored,
        )

    def test_location_name_stops_before_noisy_foreign_language_label(self) -> None:
        service = LocationCertificateService()
        noisy = """GIAY CHUNG NHAN DANG KY DIA DIEM KINH DOANH
Ma so dia diem kinh doanh: 00001
1. Ten dia diem kinh doanh:
DA DIEM KINH DOANH - CONG TY CO PHAN DAU TU 358
TEN DA DIM KINH DOANH VIT BNG TING NƯC NGOÀI:
BUSINESS LOCATION - 358 INVESTMENT JOINT STOCK COMPANY
2. Dia chi: So 10 Tran Hung Dao, Phuong Dong Hai, Thanh pho Hai Phong, Viet Nam
3. Thong tin ve nguoi dung dau
4. Thong tin ve doanh nghiep/chi nhanh chu quan:
Ten doanh nghiep/chi nhanh: CONG TY CO PHAN DAU TU 358
Ma so doanh nghiep/chi nhanh: 0202184078
"""

        values = service._parse_certificate(noisy)

        self.assertEqual(
            "ĐỊA ĐIỂM KINH DOANH - CÔNG TY CỔ PHẦN ĐẦU TƯ 358",
            values["location_business_name"],
        )
        self.assertNotIn("BUSINESS LOCATION", values["location_business_name"])

    def test_repeated_company_suffix_repairs_parent_name(self) -> None:
        service = LocationCertificateService()
        values = {
            "parent_entity_name": "CÔNG TY TNHH DUC PHM Y TÉ VN PHÚC",
            "location_business_name": (
                "NHÀ THUỐC BV THÁP MƯỜI - "
                "CÔNG TY TNHH DƯỢC PHẨM Y TẾ VẠN PHÚC"
            ),
        }

        self.assertEqual(
            "CÔNG TY TNHH DƯỢC PHẨM Y TẾ VẠN PHÚC",
            service._parent_name_from_location(values),
        )

    def test_brc_address_repairs_damaged_administrative_prefixes(self) -> None:
        service = LocationCertificateService()

        restored = service._restore_address(
            "Nhà ông Mai Văn Tun, to 12A, khu 4B, Phưng Bãi Cháy, Tinh Qung Ninh, Viet Nam"
        )

        self.assertIn("Tổ 12A", restored)
        self.assertIn("Phường Bãi Cháy", restored)
        self.assertIn("Tỉnh Quảng Ninh", restored)

    def test_company_name_removes_ocr_quote_before_numeric_qualifier(self) -> None:
        service = LocationCertificateService()

        self.assertEqual(
            "CÔNG TY CỔ PHẦN ĐẦU TƯ 358",
            service._restore_name("CÔNG TY CỔ PHẦN ĐẦU TƯ' 358"),
        )

    def test_incomplete_brc_runs_enhanced_pass(self) -> None:
        incomplete = NOISY_BRC.replace(
            "2. Dja chi:\nBiet thu lien ke can 206 Louis 2, Khu do thi Louis City Dai Mo,\n"
            "Phuong Dai Mo, Thanh pho Ha Noi, Viet Nam\n",
            "2. Dja chi:\n",
        )
        with TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "brc.pdf"
            pdf_path.touch()
            service = LocationCertificateService()
            with patch(
                "mingo_assistant.services.organization_documents.location_certificate_service.fitz.open"
            ) as open_pdf:
                open_pdf.return_value.__enter__.return_value.__iter__.return_value = iter(())
                with patch.object(
                    service,
                    "_extract_with_ocr",
                    side_effect=(incomplete, incomplete, NOISY_BRC),
                ) as ocr:
                    result = service.extract_pdf(pdf_path)

        self.assertEqual(3, ocr.call_count)
        self.assertTrue(ocr.call_args.kwargs["enhanced"])
        self.assertIn("rapidocr_enhanced", result.processing_route)
        self.assertIn("Biet thu lien ke can 206 Louis 2", result.values["location_full_address"])

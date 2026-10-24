from __future__ import annotations

from copy import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import unicodedata
from unittest.mock import MagicMock, patch

import fitz

from mingo_assistant.core.cancellation import ScanCancelledError
from mingo_assistant.services.organization_documents.organization_document_service import OrganizationDocumentService
from mingo_assistant.services.organization_documents.location_certificate_service import LocationCertificateService
from mingo_assistant.services.organization_documents.pdf_text import extract_certificate_text
from tests.unit.test_location_certificate_ocr_quality import NOISY_BRC


ERC = "\n".join((
    "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP", "Mã số doanh nghiệp: 0312345678",
    "Tên công ty viết bằng tiếng Việt: CÔNG TY TNHH MINH AN",
    "2. Địa chỉ trụ sở chính: Số 18/2 đường Tân Phú, Việt Nam",
))


class ScanResilienceTests(unittest.TestCase):
    def test_pdf_unicode_format_cleanup_preserves_words_and_identifiers(self):
        page = MagicMock()
        page.get_text.return_value = unicodedata.normalize("NFD", "Nguyễn Huỳnh, P5.09, 10/3/242, HHN01, 00012") + "\u200b\ufeff\u00a0ST\u00ad Moritz"
        result = extract_certificate_text([page])
        self.assertEqual("Nguyễn Huỳnh, P5.09, 10/3/242, HHN01, 00012 ST Moritz", result)
        self.assertTrue(unicodedata.is_normalized("NFC", result))

    def test_huge_pdf_pages_have_bounded_render_dimensions(self):
        for size in (842, 2000, 20000, 100000):
            page = MagicMock()
            page.rect.width, page.rect.height = size * .7, size
            for enhanced in (False, True):
                scale = OrganizationDocumentService._render_scale(page, enhanced=enhanced)
                self.assertLessEqual(size * scale, 4200.01)
                self.assertGreater(scale, 0)

    def test_legal_form_accents_do_not_hide_damaged_proper_name(self):
        service = OrganizationDocumentService()
        for name in ("CÔNG TY TNHH NGUYEN MINH AN", "CÔNG TY TNHH NGUYN VĂN AN", "CÔNG TY TNHH GIAI PHAP SO MINH AN"):
            result = service._document_result({"organization_owner_name": name}, "", "text", source="pdf_text")
            self.assertEqual(name, result.values["organization_owner_name"])
            self.assertLess(result.field_confidences["organization_owner_name"], .80)
            self.assertTrue(service._needs_ocr_fallback(result))
            self.assertTrue(any("Tên tổ chức" in warning for warning in result.warnings))
        for name in ("CÔNG TY TNHH NGUYỄN MINH AN", "CÔNG TY TNHH ROYAL BODY FITNESS", "CÔNG TY TNHH DUONG GROUP", "CÔNG TY TNHH DNG 368"):
            self.assertGreaterEqual(service._field_quality("organization_owner_name", name), .90)

    def test_accented_rereading_beats_damaged_name_without_changing_digits(self):
        service = OrganizationDocumentService()
        damaged = service._document_result({"organization_owner_name": "CÔNG TY TNHH NGUYEN 368", "organization_owner_registration_number": "0312345678"}, "", "text")
        corrected = service._document_result({"organization_owner_name": "CÔNG TY TNHH NGUYỄN 368", "organization_owner_registration_number": "0312345678"}, "", "ocr", source="ppocr_v6")
        result = service._merge_results(damaged, corrected)
        self.assertEqual("CÔNG TY TNHH NGUYỄN 368", result.values["organization_owner_name"])
        self.assertEqual("0312345678", result.values["organization_owner_registration_number"])

    def test_partial_pdf_result_survives_missing_engine_with_warning(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "partial.pdf"
            path.touch()
            service = OrganizationDocumentService()
            module = "mingo_assistant.services.organization_documents.organization_document_service"
            with patch(f"{module}.fitz.open"), patch(f"{module}.extract_certificate_text", return_value=ERC.split("2. Địa chỉ", 1)[0]), \
                    patch.object(service, "_extract_with_ocr", side_effect=RuntimeError("model unavailable")):
                result = service.extract_pdf(path)
            self.assertEqual("0312345678", result.values["organization_owner_registration_number"])
            self.assertTrue(any("OCR không thực hiện" in warning for warning in result.warnings))
            self.assertTrue(any("Địa chỉ trụ sở chính" in warning for warning in result.warnings))

    def test_cancel_propagates_and_failed_enhancement_clears_old_candidates(self):
        service = OrganizationDocumentService()
        service._last_enhanced_text_candidates = ("previous document",)
        with patch.object(service, "_extract_with_ocr", side_effect=RuntimeError()):
            self.assertEqual("", service._safe_ocr_pass(None, None, [], enhanced=True))
        self.assertEqual((), service._last_enhanced_text_candidates)
        with patch.object(service, "_extract_with_ocr", side_effect=ScanCancelledError):
            with self.assertRaises(ScanCancelledError):
                service._safe_ocr_pass(None, None, [])

    def test_engine_failure_is_not_misreported_as_invalid_document(self):
        for service in (OrganizationDocumentService(), LocationCertificateService()):
            module = service.__class__.__module__
            with patch.object(Path, "exists", return_value=True), patch.object(Path, "is_file", return_value=True), \
                    patch(f"{module}.fitz.open"), patch(f"{module}.extract_certificate_text", return_value=""), \
                    patch.object(service, "_extract_first_page_for_type_detection", return_value=""), \
                    patch.object(service, "_extract_with_ocr", side_effect=RuntimeError("broken engine")):
                with self.assertRaisesRegex(RuntimeError, "không phải kết luận tài liệu sai loại"):
                    service.extract_pdf("fixture.pdf")

    def test_brc_reuses_complete_type_detection(self):
        service = LocationCertificateService()
        module = "mingo_assistant.services.organization_documents.location_certificate_service"
        values = {
            "parent_entity_name": "CÔNG TY TNHH MINH AN", "parent_entity_registration_number": "0312345678",
            "location_business_name": "ĐỊA ĐIỂM KINH DOANH CÔNG TY TNHH MINH AN", "location_business_code": "00012",
            "location_full_address": "Số 18 đường Tân Phú, Phường Bình Dương, Thành phố Hồ Chí Minh, Việt Nam",
            "location_ward": "Phường Bình Dương", "location_province": "Thành phố Hồ Chí Minh",
        }
        with patch.object(Path, "is_file", return_value=True), patch(f"{module}.fitz.open"), \
                patch(f"{module}.extract_certificate_text", return_value=""), \
                patch.object(service, "_validate_expected_document_type", return_value=""), \
                patch.object(service, "_extract_first_page_for_type_detection", return_value=NOISY_BRC), \
                patch.object(service, "_parse_certificate", side_effect=[{}, values]), \
                patch.object(service, "_extract_with_ocr") as full_ocr:
            result = service.extract_pdf("fixture.pdf")
        full_ocr.assert_not_called()
        self.assertEqual("00012", result.values["location_business_code"])

    def test_engine_cache_survives_per_scan_copies(self):
        service = OrganizationDocumentService()
        with patch("rapidocr_onnxruntime.RapidOCR") as engine:
            copy(service)._get_legacy_engine()
            copy(service)._get_legacy_engine()
            engine.assert_called_once()

    def test_encrypted_and_empty_pdf_fail_before_ocr(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "locked.pdf"
            with fitz.open() as document:
                document.new_page()
                document.save(path, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="test-owner", user_pw="test-user")
            for service in (OrganizationDocumentService(), LocationCertificateService()):
                with patch.object(service, "_extract_with_ocr") as ocr:
                    with self.assertRaisesRegex(ValueError, "mật khẩu"):
                        service.extract_pdf(path)
                    ocr.assert_not_called()
            document = MagicMock()
            document.page_count, document.needs_pass = 0, False
            with self.assertRaisesRegex(ValueError, "không có trang"):
                OrganizationDocumentService._validate_pdf(document)

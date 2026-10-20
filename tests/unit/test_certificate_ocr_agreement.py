from __future__ import annotations

import unicodedata
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from mingo_assistant.services.organization_documents.location_certificate_service import (
    LocationCertificateService,
)
from mingo_assistant.services.organization_documents.organization_document_service import (
    OrganizationDocumentService,
)


class CertificateOcrAgreementTests(TestCase):
    def test_agreement_ignores_only_case_whitespace_and_unicode_encoding(self):
        key = OrganizationDocumentService._agreement_key
        original = "Số 18/2, đường Tân Phú"
        equivalent = unicodedata.normalize("NFD", "  SỐ  18/2,\nđường TÂN PHÚ  ")
        self.assertEqual(key(original), key(equivalent))
        for different in (
            "Số 18/2, đường Tấn Phú",
            "Số 182, đường Tân Phú",
            "Số 18/2 đường Tân Phú",
            "Số 18/2, đường TânPhú",
        ):
            self.assertNotEqual(key(original), key(different))

    def test_erc_tone_conflict_does_not_increase_confidence(self):
        service = OrganizationDocumentService()
        key = "organization_owner_address_detail"
        primary = service._document_result(
            {key: "Số 18 đường Tân Phú"}, "", "ocr", source="ppocr_v6"
        )
        fallback = service._document_result(
            {key: "Số 18 đường Tấn Phú"}, "", "ocr", source="rapidocr"
        )

        result = service._merge_results(primary, fallback)

        self.assertAlmostEqual(.93, result.field_confidences[key])
        self.assertTrue(any(
            "khác nhau ở: Địa chỉ trụ sở chính" in warning for warning in result.warnings
        ))

    def test_erc_punctuation_conflict_is_not_an_agreement(self):
        service = OrganizationDocumentService()
        key = "organization_owner_address_detail"
        primary = service._document_result(
            {key: "Số 18/2 đường Tân Phú"}, "", "ocr", source="ppocr_v6"
        )
        fallback = service._document_result(
            {key: "Số 182 đường Tân Phú"}, "", "ocr", source="rapidocr"
        )

        result = service._merge_results(primary, fallback)

        self.assertAlmostEqual(.93, result.field_confidences[key])
        self.assertTrue(any("khác nhau ở:" in warning for warning in result.warnings))

    def test_erc_equivalent_text_still_counts_independent_engines_once(self):
        service = OrganizationDocumentService()
        key = "organization_owner_address_detail"
        original = "Số 18 đường Tân Phú"
        equivalent = unicodedata.normalize("NFD", "SỐ  18 ĐƯỜNG TÂN PHÚ")
        primary = service._document_result({key: original}, "", "ocr", source="ppocr_v6")
        enhanced = service._document_result({key: equivalent}, "", "ocr", source="ppocr_v6_enhanced")
        fallback = service._document_result({key: equivalent}, "", "ocr", source="rapidocr")

        same_engine = service._merge_results(primary, enhanced)
        independent = service._merge_results(primary, enhanced, fallback)

        self.assertAlmostEqual(.93, same_engine.field_confidences[key])
        self.assertAlmostEqual(.96, independent.field_confidences[key])
        self.assertFalse(any("khác nhau ở:" in warning for warning in independent.warnings))

    @staticmethod
    def _brc_values(name="TÂN PHÚ", address="Số 18 đường Tân Phú"):
        return {
            "parent_entity_name": "CÔNG TY TNHH " + name,
            "parent_entity_registration_number": "0312345678",
            "location_business_name": "ĐỊA ĐIỂM KINH DOANH - CÔNG TY TNHH " + name,
            "location_business_code": "00001",
            "location_full_address": address + ", Phường Bình Dương, Thành phố Hồ Chí Minh, Việt Nam",
            "location_ward": "Phường Bình Dương",
            "location_province": "Thành phố Hồ Chí Minh",
        }

    def _extract_brc_candidates(self, primary, fallback):
        service = LocationCertificateService()
        service._vietnamese_ocr = MagicMock()
        service._vietnamese_ocr.is_available = True
        module = "mingo_assistant.services.organization_documents.location_certificate_service"
        with patch.object(Path, "is_file", return_value=True), patch(f"{module}.fitz.open"), \
                patch(f"{module}.extract_certificate_text", return_value="certificate"), \
                patch.object(service, "_validate_expected_document_type", return_value="brc"), \
                patch.object(service, "_parse_certificate", side_effect=[{}, primary, fallback]), \
                patch.object(service, "_candidates_are_reliable", side_effect=[False, False, True]), \
                patch.object(service, "_extract_with_ocr", side_effect=["primary", "fallback"]):
            return service.extract_pdf("fixture.pdf")

    def test_brc_conflicting_tones_do_not_increase_name_confidence(self):
        result = self._extract_brc_candidates(self._brc_values(), self._brc_values(name="TẤN PHÚ"))

        self.assertAlmostEqual(.94, result.field_confidences["location_business_name"])
        conflict = next(warning for warning in result.warnings if "khác nhau ở:" in warning)
        self.assertIn("Tên doanh nghiệp/chi nhánh chủ quản", conflict)
        self.assertIn("Tên địa điểm kinh doanh", conflict)

    def test_brc_conflicting_addresses_are_reported(self):
        result = self._extract_brc_candidates(
            self._brc_values(), self._brc_values(address="Số 18 đường Tấn Phú")
        )

        conflict = next(warning for warning in result.warnings if "khác nhau ở:" in warning)
        self.assertIn("Địa chỉ địa điểm kinh doanh", conflict)
        self.assertNotIn("Tên địa điểm kinh doanh", conflict)

    def test_brc_equivalent_unicode_and_case_do_not_trigger_conflict(self):
        primary = self._brc_values()
        fallback = {
            key: unicodedata.normalize("NFD", "  ".join(value.lower().split()))
            for key, value in primary.items()
        }
        result = self._extract_brc_candidates(primary, fallback)

        self.assertAlmostEqual(.97, result.field_confidences["location_business_name"])
        self.assertFalse(any("khác nhau ở:" in warning for warning in result.warnings))

    def test_brc_weak_address_does_not_trigger_confident_conflict_warning(self):
        fallback = self._brc_values()
        fallback["location_full_address"] = "???"
        result = self._extract_brc_candidates(self._brc_values(), fallback)

        self.assertFalse(any("khác nhau ở:" in warning for warning in result.warnings))

from __future__ import annotations

from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from mingo_assistant.services.ocr.vietnamese_line_refiner import VietnameseLineRefiner
from mingo_assistant.services.ocr.certificate_layout import certificate_lines
from mingo_assistant.services.organization_documents.organization_document_service import OrganizationDocumentService
from mingo_assistant.services.organization_documents.location_certificate_service import LocationCertificateService


class PrintedCertificateOcrTests(TestCase):
    def test_address_normalization_preserves_duong_proper_names_and_commas(self):
        address = "Số 35, Đường D18 , Phường Bình Dương, Tỉnh Hải Dương, Việt Nam"
        expected = "Số 35, đường D18, Phường Bình Dương, Tỉnh Hải Dương, Việt Nam"
        self.assertEqual(expected, LocationCertificateService()._restore_address(address))
        self.assertEqual(expected, OrganizationDocumentService._restore_address_ocr(address))

    def test_brc_full_address_keeps_province_prefix_and_intermediate_city(self):
        service = LocationCertificateService()
        for address, province in (
            ("Số 1, Phường Bãi Cháy, Tỉnh Quảng Ninh, Việt Nam", "Quảng Ninh"),
            ("Số 1, Thành phố Thủ Đức, Thành phố Hồ Chí Minh, Việt Nam", "Thành phố Hồ Chí Minh"),
        ):
            self.assertEqual(address, service._canonicalize_address_places(address, {"location_province": province}))

    def test_brc_text_with_unresolved_province_requires_ocr(self):
        from tests.unit.test_location_certificate_ocr_quality import NOISY_BRC
        service = LocationCertificateService()
        values = service._parse_certificate(NOISY_BRC)
        values["location_province"] = ""
        self.assertFalse(service._candidates_are_reliable([("pdf_text", values, NOISY_BRC)]))

    def test_repeated_enhancements_cannot_outvote_complete_address(self):
        service = OrganizationDocumentService()
        key = "organization_owner_address_detail"
        good = service._document_result({key: "Thôn Phúc Nhị"}, "", "ocr", source="ppocr_v6")
        bad = service._document_result({key: "Thôn Phúc Nh"}, "", "ocr", source="ppocr_v6_enhanced")
        merged = service._merge_results(good, bad, bad, bad)
        self.assertEqual(good.values[key], merged.values[key])
        self.assertEqual(good.field_confidences[key], merged.field_confidences[key])
        again = service._merge_results(merged, good, good)
        self.assertEqual(merged.field_confidences[key], again.field_confidences[key])

    def test_agreement_counts_independent_engines_once(self):
        service = OrganizationDocumentService()
        key = "organization_owner_name"
        value = "CÔNG TY TNHH KIỂM THỬ"
        primary = service._document_result({key: value}, "", "ocr", source="ppocr_v6")
        enhanced = service._document_result({key: value}, "", "ocr", source="ppocr_v6_enhanced")
        legacy = service._document_result({key: value}, "", "ocr", source="rapidocr")
        self.assertAlmostEqual(primary.field_confidences[key], service._merge_results(primary, enhanced).field_confidences[key])
        self.assertAlmostEqual(primary.field_confidences[key] + .03, service._merge_results(primary, enhanced, legacy).field_confidences[key])

    def test_final_pass_retains_agreement_between_original_engines(self):
        service = OrganizationDocumentService()
        service._vietnamese_ocr = MagicMock()
        service._vietnamese_ocr.is_available = True
        key = "organization_owner_name"
        name = "CÔNG TY TNHH KIỂM THỬ"
        primary = service._document_result({key: name}, "", "ocr", source="ppocr_v6")
        legacy = service._document_result({key: name}, "", "ocr", source="rapidocr")
        enhanced = service._document_result({key: name + " TRƯỞNG PHÒNG"}, "", "ocr", source="ppocr_v6_enhanced")
        module = "mingo_assistant.services.organization_documents.organization_document_service"
        with patch.object(Path, "exists", return_value=True), patch(f"{module}.fitz.open"), \
                patch(f"{module}.extract_certificate_text", return_value=""), \
                patch.object(service, "_validate_expected_document_type", return_value="erc"), \
                patch.object(service, "_extract_with_ocr", side_effect=["primary", "legacy", "enhanced"]), \
                patch.object(service, "_extract_supported_document", side_effect=[None, primary, legacy, enhanced]), \
                patch.object(service, "_needs_enhanced_pass", return_value=True):
            result = service.extract_pdf("fixture.pdf")
        self.assertEqual(name, result.values[key])
        self.assertAlmostEqual(.97, result.field_confidences[key])

    def test_brc_prefers_complete_name_when_same_engine_variants_tie(self):
        service = LocationCertificateService()
        key = "location_business_name"
        self.assertGreater(service._value_rank(key, "ppocr_v6", "ĐỊA ĐIỂM KINH DOANH - CÔNG TY TNHH MINH AN"),
                           service._value_rank(key, "ppocr_v6_enhanced", "ĐỊA ĐIỂM KINH DOANH - CÔNG TY TNHH MINH"))

    def test_merge_rejects_address_contaminated_by_contact_caption(self):
        service = OrganizationDocumentService()
        key = "organization_owner_address_detail"
        good = service._document_result({key: "Số 18, phố Minh Khai"}, "", "ocr", source="rapidocr")
        bad = service._document_result({key: "S II AI Aam Đin thoi:"}, "", "ocr", source="ppocr_v6_enhanced")
        self.assertEqual(good.values[key], service._merge_results(good, bad).values[key])

    def test_accented_reading_wins_an_equal_quality_tie(self):
        service = OrganizationDocumentService()
        key = "organization_owner_address_detail"
        good = service._document_result({key: "Tầng 3, tòa nhà AB Thanh Xuân"}, "", "ocr", source="ppocr_v6")
        bad = service._document_result({key: "Tang 3, toa nha AB Thanh Xuan"}, "", "ocr", source="rapidocr")
        self.assertEqual(good.values[key], service._merge_results(good, bad).values[key])

    def test_short_village_address_retains_label_and_borrows_only_missing_accents(self):
        service = OrganizationDocumentService()
        key = "organization_owner_address_detail"
        complete = service._document_result({key: "ấp Xom Co"}, "", "ocr", source="rapidocr")
        accented = service._document_result({key: "p Xóm Cò"}, "", "ocr", source="ppocr_v6")
        self.assertEqual("ấp Xóm Cò", service._merge_results(complete, accented).values[key])
        self.assertGreaterEqual(complete.field_confidences[key], .80)

    def test_address_word_enrichment_preserves_letters_digits_and_existing_tones(self):
        enrich = OrganizationDocumentService._enrich_address_words
        self.assertEqual("Số 18, Minh Khai", enrich("Số 18, Minh Khai", ["Số 19, Mình Khai"]))
        self.assertEqual("Phường Bình Trung", enrich("Phường Bình Trung", ["Phường Bình Trường"]))
        self.assertEqual("Số 18, phố Mới", enrich("Số 18, phố Moi", ["Sổ 18, phó Mới"]))

    def test_floor_caption_is_repaired_only_before_a_floor_number(self):
        restore = OrganizationDocumentService._restore_address_ocr
        self.assertEqual("Tầng 3, tòa nhà AB", restore("Tng 3, tòa nhà AB"))
        self.assertEqual("Tầng 2, tòa nhà AB", restore("Tang 2, tòa nhà AB"))
        self.assertEqual("TANG GROUP", restore("TANG GROUP"))

    def test_ascii_duong_is_a_street_caption_only_in_address_context(self):
        restore = OrganizationDocumentService._restore_address_ocr
        self.assertEqual("Số 35 đường D18, Tỉnh Hai Duong", restore("Số 35 Duong D18, Tỉnh Hai Duong"))
        self.assertEqual("đường ABC", restore("Duong ABC"))
        name = "CÔNG TY TNHH DUONG GROUP"
        self.assertEqual(name, OrganizationDocumentService()._document_result({"organization_owner_name": name}, "", "ocr").values["organization_owner_name"])

    def test_pdf_caption_fragments_keep_inline_name_despite_kerning(self):
        def span(left, right, text):
            return ([[left, 10], [right, 10], [right, 24], [left, 24]], text, 1.0)

        lines = [span(10, 51, "1. Tên"), span(50.8, 174, "địa điểm kinh doanh"),
                 span(174, 182.2, ":"), span(182.17, 500, "ĐỊA ĐIỂM KINH DOANH 12 - CÔNG TY TNHH ABC")]
        self.assertEqual(["1. Tên địa điểm kinh doanh: ĐỊA ĐIỂM KINH DOANH 12 - CÔNG TY TNHH ABC"], certificate_lines(lines))

    def test_independent_empty_phone_and_fax_labels_stay_separate(self):
        def span(left, right, text):
            return ([[left, 10], [right, 10], [right, 24], [left, 24]], text, 1.0)

        self.assertEqual(["Điện thoại:", "Fax:"], certificate_lines([
            span(10, 100, "Điện thoại:"), span(120, 160, "Fax:"),
        ]))

    def test_ocr_repairs_legal_form_and_business_terms_in_long_names(self):
        service = OrganizationDocumentService()
        for text, expected in (
            ("CÔNG TY CỔ PHN GIẢI PHÁP MINH AN", "CÔNG TY CỔ PHẦN GIẢI PHÁP MINH AN"),
            ("CÔNG TY CÔ PHN ĐÀU TU VÀ PHÁT TRIỂN 368", "CÔNG TY CỔ PHẦN ĐẦU TƯ VÀ PHÁT TRIỂN 368"),
            ("CÔNG TY TNHH ĐÂU TU XÂY DNG THƯƠNG MẠI ABC", "CÔNG TY TNHH ĐẦU TƯ XÂY DỰNG THƯƠNG MẠI ABC"),
        ):
            with self.subTest(text=text):
                result = service._document_result({"organization_owner_name": text}, "", "ocr")
                self.assertEqual(expected, result.values["organization_owner_name"])

    def test_name_repair_retains_brand_acronyms_and_numbers(self):
        service = OrganizationDocumentService()
        for name in ("CÔNG TY TNHH DNG 368", "CÔNG TY TNHH PHN", "CÔNG TY TNHH MING GROUP", "CÔNG TY TNHH ABC-123"):
            with self.subTest(name=name):
                self.assertEqual(name, service._document_result({"organization_owner_name": name}, "", "ocr").values["organization_owner_name"])

    def test_decoded_pdf_name_is_not_subject_to_ocr_letter_repairs(self):
        name = "CÔNG TY TNHH XÂY DNG ABC"
        result = OrganizationDocumentService()._document_result({"organization_owner_name": name}, "", "text", source="pdf_text")
        self.assertEqual(name, result.values["organization_owner_name"])

    def test_brc_repairs_company_suffix_without_changing_location_number(self):
        name = "ĐỊA ĐIỂM KINH DOANH SỐ 12 - CÔNG TY CỔ PHN MINH AN"
        self.assertEqual("ĐỊA ĐIỂM KINH DOANH SỐ 12 - CÔNG TY CỔ PHẦN MINH AN", LocationCertificateService()._restore_name(name))

    def test_long_printed_line_splits_at_word_gaps_not_between_letters(self):
        image = np.full((40, 1300, 3), 255, dtype=np.uint8)
        word_spaces = []
        position = 8
        for _word in range(10):
            for _letter in range(7):
                cv2.rectangle(image, (position, 8), (position + 8, 31), (0, 0, 0), -1)
                position += 12  # a 3-pixel letter gap must not be a split point
            word_spaces.append((position - 3, position + 17))
            position += 20
        crops = VietnameseLineRefiner._split_long_crop(image)
        self.assertGreater(len(crops), 1)
        offset = 0
        for crop in crops[:-1]:
            offset += crop.shape[1]
            self.assertTrue(any(left <= offset <= right for left, right in word_spaces), offset)
        self.assertEqual(image.shape[1], sum(crop.shape[1] for crop in crops))

    def test_foreign_and_abbreviated_name_labels_do_not_load_refinement_model(self):
        refiner = VietnameseLineRefiner(Path("models"))
        lines = [([[0, 0], [300, 0], [300, 30], [0, 30]], label, .98) for label in (
            "Tên công ty vit tt: TEST CO LTD", "Tên công ty viết bằng tiếng nước ngoài: TEST COMPANY",
        )]
        with patch.object(Path, "is_file", return_value=True), patch.object(refiner, "_load") as load:
            self.assertEqual(lines, refiner.refine(np.zeros((50, 400, 3), dtype=np.uint8), lines))
        load.assert_not_called()

    def test_tiled_refinement_keeps_end_of_name_and_identifier(self):
        refiner = VietnameseLineRefiner(Path("models"))
        original = "CONG TY TNHH THUONG MAI ABC 368"
        lines = [([[0, 0], [700, 0], [700, 35], [0, 35]], original, .98)]
        predictor = MagicMock()
        predictor.predict_batch.return_value = (["CÔNG TY TNHH", "THƯƠNG MẠI ABC 368"], [.97, .98])
        with patch.object(Path, "is_file", return_value=True), patch.object(refiner, "_load", return_value=predictor), \
                patch.object(refiner, "_split_long_crop", return_value=[np.zeros((35, 300, 3), dtype=np.uint8)] * 2):
            result = refiner.refine(np.zeros((60, 800, 3), dtype=np.uint8), lines)
        self.assertEqual("CÔNG TY TNHH THƯƠNG MẠI ABC 368", result[0][1])

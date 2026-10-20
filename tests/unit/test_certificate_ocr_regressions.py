from __future__ import annotations

import unittest

import cv2
import numpy as np

from mingo_assistant.services.ocr.certificate_layout import certificate_lines
from mingo_assistant.services.ocr.vietnamese_line_refiner import VietnameseLineRefiner
from mingo_assistant.services.organization_documents.location_certificate_service import LocationCertificateService


def box(x: float, y: float, width: float, height: float = 20) -> list[list[float]]:
    return [[x, y], [x + width, y], [x + width, y + height], [x, y + height]]


class CertificateOcrRegressionTests(unittest.TestCase):
    def test_brc_name_repair_preserves_numeric_and_alphanumeric_suffix(self):
        service = LocationCertificateService()
        for suffix in (" 1", " SỐ 12", " SO 12", " 3A", ""):
            with self.subTest(suffix=suffix):
                actual = service._restore_name(f"DIA DIEM KINH DOANH{suffix} - CONG TY TNHH TEST")
                expected_suffix = suffix.replace(" SO ", " SỐ ")
                self.assertEqual(f"ĐỊA ĐIỂM KINH DOANH{expected_suffix} - CÔNG TY TNHH TEST", actual)

    def test_brc_parent_branch_code_keeps_all_thirteen_digits(self):
        from tests.unit.test_location_certificate_ocr_quality import NOISY_BRC

        service = LocationCertificateService()
        for code in ("0112345678", "0112345678001", "0112345678-001"):
            with self.subTest(code=code):
                text = NOISY_BRC.replace("0112345678", code)
                self.assertEqual(code.replace("-", ""), service._parse_certificate(text)["parent_entity_registration_number"])

    def test_multiline_brc_name_is_not_mistaken_for_its_own_label(self):
        from tests.unit.test_location_certificate_ocr_quality import NOISY_BRC

        text = NOISY_BRC.replace(
            "1. Ten dia diem kinh doanh: DIA DIEM KINH DOANH SO 3 - CONG TY TNHH VIEN DONG",
            "1. Ten dia diem kinh doanh:\nDIA DIEM KINH DOANH SO 3 -\nCONG TY TNHH VIEN DONG",
        )
        self.assertEqual(
            "ĐỊA ĐIỂM KINH DOANH SỐ 3 - CÔNG TY TNHH VIEN DONG",
            LocationCertificateService()._parse_certificate(text)["location_business_name"],
        )

    def test_brc_house_numbers_are_not_section_boundaries(self):
        from tests.unit.test_location_certificate_ocr_quality import NOISY_BRC

        for address in ("3 Nguyen Thi Dinh", "3-5 Nguyen Thi Dinh", "369 Nguyen Thi Dinh"):
            with self.subTest(address=address):
                text = NOISY_BRC.replace("Biet thu lien ke can 206 Louis 2, Khu do thi Louis City Dai Mo,", address + ",")
                self.assertIn(address.replace("Nguyen Thi Dinh", "Nguyễn Thị Định"),
                              LocationCertificateService()._parse_certificate(text)["location_full_address"])

    def test_empty_phone_does_not_capture_the_fax_label(self):
        from tests.unit.test_location_certificate_ocr_quality import NOISY_BRC

        text = NOISY_BRC.replace("Dien thoai:\n3.", "Dien thoai: Fax:\n3.")

        self.assertNotIn(
            "location_phone",
            LocationCertificateService()._parse_certificate(text),
        )

    def test_confident_address_retains_its_letters_during_accent_restoration(self):
        self.assertEqual("Phường Bình Trung", VietnameseLineRefiner.restore_accents(
            "Phuong Binh Trung", "Phường Bình Trường", allow_letter_repairs=False,
        ))

    def test_ocr_street_label_repairs_do_not_change_house_numbers(self):
        service = LocationCertificateService()
        self.assertEqual("Số 128/3 đường Nguyễn Thị Định", service._restore_address("S6 128/3 durong Nguyen Thi Dinh"))
        self.assertEqual("Phường Binh Trung", service._restore_address("Phurong Binh Trung"))

    def test_fragmented_label_and_value_follow_geometry(self):
        lines = [
            (box(10, 65, 160), "2. Địa chỉ:", .95),
            (box(210, 11, 190), "CÔNG TY TNHH TEST", .95),
            (box(10, 10, 175), "Tên công ty tiếng Việt:", .95),
        ]
        self.assertEqual(["Tên công ty tiếng Việt: CÔNG TY TNHH TEST", "2. Địa chỉ:"], certificate_lines(lines))

    def test_distinct_contacts_and_widely_spaced_columns_stay_separate(self):
        lines = [
            (box(10, 10, 200), "Điện thoại: 0900000012", .95),
            (box(230, 10, 180), "Fax: 0280000000", .95),
            (box(10, 60, 120), "SỞ TÀI CHÍNH", .95),
            (box(500, 60, 180), "CỘNG HÒA XÃ HỘI", .95),
        ]
        self.assertEqual([line[1] for line in lines], certificate_lines(lines))

    def test_skewed_fragments_are_sorted_on_the_text_baseline(self):
        def rotate(points):
            matrix = cv2.getRotationMatrix2D((0, 0), 5, 1)
            return cv2.transform(np.array([points], dtype=np.float32), matrix)[0].tolist()

        lines = [
            (rotate(box(260, 10, 120)), "MINH AN", .95),
            (rotate(box(10, 10, 230)), "CÔNG TY TNHH", .95),
            (rotate(box(10, 45, 300)), "2. Địa chỉ trụ sở chính:", .95),
        ]
        self.assertEqual(["CÔNG TY TNHH MINH AN", "2. Địa chỉ trụ sở chính:"], certificate_lines(lines))

    def test_missing_geometry_preserves_recognizer_order(self):
        self.assertEqual(["first", "second"], certificate_lines([(None, "first", .9), (box(0, 0, 30), "second", .9)]))

    def test_long_line_split_uses_whitespace_without_discarding_ink(self):
        image = np.full((40, 1600, 3), 255, dtype=np.uint8)
        for start in range(10, 1580, 80):
            cv2.rectangle(image, (start, 10), (start + 48, 30), (0, 0, 0), -1)
        crops = VietnameseLineRefiner._split_long_crop(image)
        self.assertGreater(len(crops), 1)
        self.assertEqual(image.shape[1], sum(crop.shape[1] for crop in crops))
        self.assertTrue(all(crop.shape[1] / crop.shape[0] <= 20 for crop in crops))
        self.assertEqual(int((image < 128).sum()), sum(int((crop < 128).sum()) for crop in crops))

    def test_accent_refinement_cannot_delete_letters_in_a_company_name(self):
        self.assertEqual(
            "CÔNG TY TNHH GIẢI PHÁP SỐ MINH AN",
            VietnameseLineRefiner.restore_accents(
                "CÔNG TY TNHH GIÅI PHÁP SÓ MINH AN",
                "CÔN TY TNHH GIẢI PHÁP SỐ MINH AN",
            ),
        )

    def test_refinement_preserves_foreign_spelling_and_short_acronyms(self):
        self.assertEqual(
            "CÔNG TY MING M AN",
            VietnameseLineRefiner.restore_accents("CONG TY MING M AN", "CÔNG TY MÌNH MỸ AN"),
        )


if __name__ == "__main__":
    unittest.main()

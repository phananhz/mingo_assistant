import unittest

from mingo_assistant.services.ocr.vietnamese_line_refiner import VietnameseLineRefiner


class VietnameseLineRefinerTests(unittest.TestCase):
    def test_restores_accents_without_inventing_address_words(self):
        self.assertEqual(
            "Phuong Bến Thành", VietnameseLineRefiner.restore_accents(
                "Phuong Ben Thanh", "Phú Thường Bến Thành"))
        self.assertEqual("THƯƠNG MẠI & DỊCH VỤ X FACTOR", VietnameseLineRefiner.restore_accents(
            "THUONG MAI & DICH VU X FACTOR", "THƯƠNG MẠI & DỊCH VỤ X FACTOR"))

    def test_rejects_changed_digits_and_unrelated_names(self):
        self.assertFalse(VietnameseLineRefiner.accept("So 273 Ly Tu Trong", "Số 278 Lý Tự Trọng", .99))
        self.assertFalse(VietnameseLineRefiner.accept("CONG TY ABC", "CÔNG TY XYZ", .99))
        self.assertFalse(VietnameseLineRefiner.accept("CONG TY ABC", "CÔNG TY ABC", .5))

    def test_accepts_accented_address_with_ocr_label_zero(self):
        self.assertTrue(VietnameseLineRefiner.accept("S0 273 Ly Tu Trong", "Số 273 Lý Tự Trọng", .95))

    def test_fuzzy_address_heading_enables_refinement(self):
        for label in ("2. Dja chi:", "2. Dachi:", "2. Dia chi:", "2. Địa chỉ:"):
            with self.subTest(label=label):
                self.assertTrue(VietnameseLineRefiner.looks_like_address_label(label))

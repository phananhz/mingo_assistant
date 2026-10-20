from __future__ import annotations

from unittest import TestCase

from mingo_assistant.services.ocr.address_evidence import corroborated_address


class AddressOcrEvidenceTests(TestCase):
    def test_two_image_readings_are_required_even_with_correct_pdf_text(self):
        address = "Số 12 đường Mới, Phường An Bình"
        self.assertIsNone(corroborated_address(address, [("pdf_text", address)], raw_primary=address))
        self.assertIsNone(corroborated_address(address, [("pdf_text", address)], legacy=address))

    def test_missing_vowels_can_be_recovered_from_independent_complete_spelling(self):
        self.assertEqual(
            "Số 12 đường Nguyễn An, Phường Hòa Bình",
            corroborated_address(
                "Số 12 đường Nguyễn An, Phường Hòa Bình", [],
                raw_primary="Số 12 đường Nguyn An, Phường Hòa Bình",
                legacy="So 12 duong Nguyen An, Phuong Hoa Binh",
            ),
        )

    def test_independently_agreed_valid_names_and_existing_tones_are_preserved(self):
        for name, proposed in (("Minh", "Mình"), ("Trung", "Trường"), ("Tân", "Tấn")):
            with self.subTest(name=name):
                original = f"Số 12 {name} An, Phường Hòa Bình"
                candidate = f"Số 12 {proposed} An, Phường Hòa Bình"
                self.assertEqual(original, corroborated_address(candidate, [], raw_primary=original, legacy=original))

    def test_agreed_identifiers_keep_their_exact_original_punctuation_and_digits(self):
        for original, proposed in (("50-52", "50-53"), ("HHN01", "HHNO1"),
                                   ("P5.09", "P5.19"), ("10/3/242", "10/3242")):
            with self.subTest(identifier=original):
                address = f"{original} đường Mới"
                self.assertEqual(address, corroborated_address(
                    f"{proposed} đường Mới", [], raw_primary=address, legacy=address,
                ))

    def test_changed_identifiers_without_agreement_are_rejected(self):
        for candidate in ("50-54", "HHN02", "P5.19", "10/3/243"):
            with self.subTest(identifier=candidate):
                self.assertIsNone(corroborated_address(
                    f"{candidate} đường Mới", [],
                    raw_primary="50-52 đường Moi", legacy="50-53 duong Moi",
                ))

    def test_exact_fold_support_allows_glued_word_spacing(self):
        self.assertEqual("Số 12, Thành phố Thủ Đức", corroborated_address(
            "Số 12, Thành phố Thủ Đức", [],
            raw_primary="Số 12, Thành phố ThủĐức", legacy="So 12, Thanh pho ThuDuc",
        ))

    def test_pdf_can_support_a_component_when_both_image_readings_exist(self):
        address = "Số 12 Nguyễn An, Phường Hòa Bình"
        self.assertEqual(address, corroborated_address(
            address, [("pdf_text", address)],
            raw_primary="Số 12 Nguyn An, Phường Hòa Bình",
            legacy="So 12 Nguen An, Phuong Hoa Binh",
        ))

    def test_added_or_dropped_words_and_components_are_rejected(self):
        original = "Số 12 đường An, Phường Hòa Bình"
        for candidate in ("Số 12 đường An Mới, Phường Hòa Bình", "Số 12 An, Phường Hòa Bình", "Số 12 đường An"):
            with self.subTest(candidate=candidate):
                self.assertIsNone(corroborated_address(candidate, [], raw_primary=original, legacy=original))

    def test_unsupported_foreign_or_brand_spelling_is_rejected(self):
        for primary, legacy, candidate in (
            ("Số 12 MING GROUP", "So 12 MING GROUP", "Số 12 MÌNH GROUP"),
            ("Số 12 ST Moritz", "So 12 ST Moritz", "Số 12 ST Moriz"),
        ):
            with self.subTest(candidate=candidate):
                # Agreed foreign tokens are kept when aligned, never replaced.
                result = corroborated_address(candidate, [], raw_primary=primary, legacy=legacy)
                self.assertEqual(primary, result)
        self.assertIsNone(corroborated_address(
            "Số 12 ST Moriz", [], raw_primary="Số 12 ST Moritz", legacy="So 12 ST Mortz",
        ))

    def test_ir_confusion_requires_a_different_engine_preserving_all_other_letters(self):
        candidate = "Số 12 Đức An"
        self.assertEqual(candidate, corroborated_address(
            candidate, [], raw_primary="Số 12 Đc An", legacy="So 12 Dirc An",
        ))
        self.assertIsNone(corroborated_address(
            candidate, [("rapidocr_enhanced", "So 12 Dc An")],
            raw_primary="Số 12 Bc An", legacy="So 12 Dirc An",
        ))

    def test_ir_confusion_cannot_target_a_plain_u_or_unrelated_vowel(self):
        self.assertIsNone(corroborated_address(
            "Số 12 Dục An", [], raw_primary="Số 12 Dc An", legacy="So 12 Dirc An",
        ))
        self.assertIsNone(corroborated_address(
            "Số 12 Dục Trường", [], raw_primary="Số 12 Dc Trng", legacy="So 12 Dirc Truong",
        ))

    def test_ir_confusion_does_not_allow_an_extra_word_supported_only_as_subsequence(self):
        self.assertIsNone(corroborated_address(
            "Số 12 Đức An Mới", [], raw_primary="Số 12 Đc An", legacy="So 12 Dirc An Mới",
        ))

    def test_component_order_cannot_be_rearranged(self):
        original = "Số 12 đường An, Phường Hòa Bình"
        self.assertIsNone(corroborated_address(
            "Phường Hòa Bình, Số 12 đường An", [], raw_primary=original, legacy=original,
        ))

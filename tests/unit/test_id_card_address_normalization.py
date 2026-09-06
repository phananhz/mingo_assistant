import unittest

from mingo_assistant.services.normalization.administrative_place_matcher import AdministrativePlaceMatcher
from mingo_assistant.services.normalization.address_parser import AddressParser
from mingo_assistant.services.ocr.id_card_parser import IdCardParser


class IdCardAddressNormalizationTest(unittest.TestCase):
    def test_matcher_normalizes_noisy_hcm_address(self) -> None:
        matcher = AdministrativePlaceMatcher()

        result = matcher.normalize_address("79/J4, Au Co, Phuong 14, Quan 11, TP Ho Chi Mlnh")

        self.assertEqual(result, "79/J4, Au Co, Phường Hòa Bình, Thành phố Hồ Chí Minh")

    def test_matcher_maps_labeled_old_places_using_after_merger_data(self) -> None:
        matcher = AdministrativePlaceMatcher()

        origin = matcher.normalize_address("Phuong Tinh Hai, Thi xa Nghi Son, Tinh Thanh Hoa")
        residence = matcher.normalize_address(
            "Cao Bac, Phuong Hai Thuong, Thi xa Nghi Son, Tinh Thanh Hoa"
        )

        self.assertEqual(origin, "Phường Hải Bình, Thanh Hóa")
        self.assertEqual(residence, "Cao Bac, Phường Nghi Sơn, Thanh Hóa")

    def test_parser_keeps_origin_and_residence_separate(self) -> None:
        text = """No
025161008294
Ho va ten / Ful name
HOANG THI TIEN
Ngay sinh / Duto
01/04/1961
Sex: Nu
Nationality: Viet Nam
Que quan / Place of origin:
Tu Xa, Lam Thao, Phu Tho
Noi thuong tru / Place of residence: Khu 1
Ban Nguyen, Lam Thao, Phu Tho"""

        card = IdCardParser().parse(text)

        self.assertEqual(card.full_name, "HOANG THI TIEN")
        self.assertEqual(card.place_of_origin, "Xã Phùng Nguyên, Phú Thọ")
        self.assertEqual(card.permanent_address, "Khu 1, Xã Bản Nguyên, Phú Thọ")

    def test_parser_handles_noisy_origin_marker_from_ocr(self) -> None:
        text = """No
025161008294
Ho va ten / Ful name
HOANG THI TIEN
Quoc tich _
Việt Nam
Qui quán / Placo
oo
Từ Xã
Lam Thao, Phú Tho
Uuong uu
Place of residenc"""

        card = IdCardParser().parse(text)

        self.assertEqual(card.place_of_origin, "Xã Phùng Nguyên, Phú Thọ")
        self.assertEqual(card.permanent_address, "")

    def test_parser_continues_to_later_scan_when_first_residence_marker_has_no_value(self) -> None:
        text = """Place of residenc
--- scan 2 ---
Noi thuong tru / Place of residence: Khu 1
Ban Nguyen, Lam Thao, Phu Tho"""

        card = IdCardParser().parse(text)

        self.assertEqual(card.permanent_address, "Khu 1, Xã Bản Nguyên, Phú Thọ")

    def test_parser_reads_visible_front_side_personal_fields(self) -> None:
        text = """CAN CUOC CONG DAN
So / No.: 079067015629
Ho va ten / Full name:
HUYNH VAN TAI
Ngay sinh / Date of birth: 04/04/1967
Gioi tinh / Sex: Nam Quoc tich / Nationality: Viet Nam
Que quan / Place of origin: Tp. Ho Chi Minh
Noi thuong tru / Place of residence: 30/4a Nguyen
Van Cua, P. 13, Q. 8, Tp. Ho Chi Minh"""

        card = IdCardParser().parse(text)

        self.assertEqual(card.id_number, "079067015629")
        self.assertEqual(card.full_name, "HUYNH VAN TAI")
        self.assertEqual(card.date_of_birth, "04/04/1967")
        self.assertEqual(card.gender, "Nam")
        self.assertTrue(card.place_of_origin)
        self.assertIn("30/4a", card.permanent_address)

    def test_parser_normalizes_birth_date_with_common_ocr_digit_errors(self) -> None:
        text = "Ngay sinh / Date of birth: 17/O2/1998"

        card = IdCardParser().parse(text)

        self.assertEqual(card.date_of_birth, "17/02/1998")

    def test_parser_uses_first_plausible_birth_date_when_ocr_splits_label(self) -> None:
        text = """Ho va ten / Ful name:
HUYNH VAN TAI
Ngay sinh
Date
birth: 04/04/1967
Noi thuong tru / Place of residence: 30/4a Nguyen
Van Cua, P. 13, Q. 8, Tp. Ho Chi Minh, 04/04/2027"""

        card = IdCardParser().parse(text)

        self.assertEqual(card.date_of_birth, "04/04/1967")

    def test_parser_uses_visible_date_for_any_card_when_birth_label_is_after_date(self) -> None:
        text = """9F
Ho va ten / Full name:
NGUYEN HONG DUYEN
13/05/2008
Ngay sinh / Date of birth:
Que quan / Place of origin:
Ho Chi Minh
Noi thuong tru / Place of residence: 79/J4 Au Co, Phuong 14, Quan 11, 13/05/2033"""

        card = IdCardParser().parse(text)

        self.assertEqual(card.date_of_birth, "13/05/2008")

    def test_parser_reads_birth_date_after_noisy_birth_label(self) -> None:
        text = """Citizen Identity Card
025161008294
So / No:
Ho va ten / Full name:
HOANG THI TIEN
Ngay sinh / Dato @ birth:
01/04/1961
Viet Na
Quoc tich / Natlonany:
Nu"""

        card = IdCardParser().parse(text)

        self.assertEqual(card.date_of_birth, "01/04/1961")

    def test_parser_reads_chip_id_card_qr_payload(self) -> None:
        qr_text = "079308021854|123456789|NGUYEN HONG DUYEN|13052008|Nu|79/J4 Au Co, Phuong 14, Quan 11, TP Ho Chi Minh|13052023"

        card = IdCardParser().parse_qr(qr_text)

        self.assertEqual(card.id_number, "079308021854")
        self.assertEqual(card.full_name, "NGUYEN HONG DUYEN")
        self.assertEqual(card.date_of_birth, "13/05/2008")
        self.assertEqual(card.gender, "Nữ")
        self.assertIn("79/J4", card.permanent_address)
        self.assertEqual(card.issue_date, "13/05/2023")
    def test_address_parser_uses_normalized_administrative_places(self) -> None:
        result = AddressParser().parse("79/J4, Au Co, Phuong 14, Quan 11, TP Ho Chi Mlnh")

        self.assertEqual(result.street_line, "79/J4, Au Co")
        self.assertEqual(result.ward, "Phường Hòa Bình")
        self.assertEqual(result.province, "Thành phố Hồ Chí Minh")

    def test_matcher_removes_old_district_even_when_it_precedes_ward(self) -> None:
        result = AdministrativePlaceMatcher().normalize_address("Quận 11, Phường 14, TP Hồ Chí Minh")

        self.assertEqual(result, "Phường Hòa Bình, Thành phố Hồ Chí Minh")

    def test_parser_preserves_current_two_tier_address_from_noisy_cccd_text(self) -> None:
        result = AddressParser().parse(
            "34F Ngõ 784 Bạch Đằng Tổ 56, Xã Ô Diên, Thành phố Hà Nội"
        )

        self.assertEqual(result.street_line, "34F Ngõ 784 Bạch Đằng")
        self.assertEqual(result.village, "Tổ 56")
        self.assertEqual(result.ward, "Xã Ô Diên")
        self.assertEqual(result.province, "Thành phố Hà Nội")
        self.assertEqual(
            result.normalized_address,
            "34F Ngõ 784 Bạch Đằng, Tổ 56, Xã Ô Diên, Thành phố Hà Nội",
        )

    def test_matcher_normalizes_common_abbreviated_ward_and_district_labels(self) -> None:
        result = AdministrativePlaceMatcher().normalize_address("P. 14, Q. 11, TP HCM")

        self.assertEqual(result, "Phường Hòa Bình, Thành phố Hồ Chí Minh")

    def test_parser_handles_unaccented_two_tier_cccd_address(self) -> None:
        result = AddressParser().parse(
            "34F Ngo 784 Bach Dang To 56, Xa O Dien, Thanh pho Ha Noi"
        )

        self.assertEqual(result.street_line, "34F Ngo 784 Bach Dang")
        self.assertEqual(result.village, "Tổ 56")
        self.assertEqual(result.ward, "Xã Ô Diên")
        self.assertEqual(result.province, "Thành phố Hà Nội")
        self.assertEqual(
            result.normalized_address,
            "34F Ngo 784 Bach Dang, Tổ 56, Xã Ô Diên, Thành phố Hà Nội",
        )

    def test_matcher_keeps_current_two_tier_tail_without_ward_label(self) -> None:
        result = AdministrativePlaceMatcher().normalize_address(
            "34F Ngõ 784 Bạch Đằng Tổ 56, Hồng Hà, Hà Nội"
        )

        self.assertEqual(
            result,
            "34F Ngõ 784 Bạch Đằng Tổ 56, Phường Hồng Hà, Thành phố Hà Nội",
        )

    def test_matcher_prioritizes_current_ward_when_name_matches_legacy_district(self) -> None:
        result = AdministrativePlaceMatcher().normalize_address(
            "Ba \u0110\u00ecnh, H\u00e0 N\u1ed9i"
        )

        self.assertEqual(
            result,
            "Ph\u01b0\u1eddng Ba \u0110\u00ecnh, Th\u00e0nh ph\u1ed1 H\u00e0 N\u1ed9i",
        )
    def test_matcher_converts_legacy_address_with_unlabeled_district_context(self) -> None:
        result = AdministrativePlaceMatcher().normalize_address(
            "Tu Xa, Lam Thao, Phu Tho"
        )

        self.assertEqual(
            result,
            "X\u00e3 Ph\u00f9ng Nguy\u00ean, Ph\u00fa Th\u1ecd",
        )
    def test_matcher_converts_legacy_address_when_old_district_is_present(self) -> None:
        result = AdministrativePlaceMatcher().normalize_address(
            "Tổ 56, Xã Hồng Hà, Huyện Đan Phượng, Thành phố Hà Nội"
        )

        self.assertEqual(result, "Tổ 56, Xã Ô Diên, Thành phố Hà Nội")

    def test_address_parser_uses_current_two_tier_tail_for_form_fields(self) -> None:
        result = AddressParser().parse(
            "34F Ngõ 784 Bạch Đằng Tổ 56, Hồng Hà, Hà Nội"
        )

        self.assertEqual(result.street_line, "34F Ngõ 784 Bạch Đằng")
        self.assertEqual(result.village, "Tổ 56")
        self.assertEqual(result.ward, "Phường Hồng Hà")
        self.assertEqual(result.province, "Thành phố Hà Nội")
        self.assertEqual(
            result.normalized_address,
            "34F Ngõ 784 Bạch Đằng, Tổ 56, Phường Hồng Hà, Thành phố Hà Nội",
        )

    def test_matcher_does_not_remap_current_ward_name_without_old_district_context(self) -> None:
        result = AdministrativePlaceMatcher().normalize_address("Xã Phùng Nguyên, Phú Thọ")

        self.assertEqual(result, "Xã Phùng Nguyên, Phú Thọ")


    def test_qr_keeps_raw_legacy_address_and_converts_la_khe(self) -> None:
        raw_address = "Thua Dat 133 - Ban Do 30 - Doi 2 - To Dan Pho 5, La Khe, Ha Dong, Ha Noi"
        card = IdCardParser().parse_qr(
            "012345678901|123456789|NGUYEN VAN A|01011990|Nam|"
            + raw_address
            + "|01012025"
        )

        self.assertEqual(card.raw_permanent_address, raw_address)
        self.assertEqual(card.address_status, "converted")
        self.assertEqual(
            card.permanent_address,
            "Thua Dat 133 - Ban Do 30 - Doi 2 - To Dan Pho 5, Ph\u01b0\u1eddng H\u00e0 \u0110\u00f4ng, Th\u00e0nh ph\u1ed1 H\u00e0 N\u1ed9i",
        )

    def test_qr_converts_mong_cai_without_matching_quang_ninh_as_a_district(self) -> None:
        raw_address = "Thon Dong, Van Ninh, Thanh pho Mong Cai, Quang Ninh"
        card = IdCardParser().parse_qr(
            "012345678901|123456789|NGUYEN VAN A|01011990|Nam|"
            + raw_address
            + "|01012025"
        )

        self.assertEqual(card.raw_permanent_address, raw_address)
        self.assertEqual(card.address_status, "converted")
        self.assertEqual(card.permanent_address, "Thon Dong, Ph\u01b0\u1eddng M\u00f3ng C\u00e1i 2, Qu\u1ea3ng Ninh")
        self.assertNotIn("Huy\u1ec7n Qu\u1ea3ng Ninh", card.permanent_address)

    def test_qr_recognizes_an_address_already_in_two_tier_form(self) -> None:
        raw_address = "34F Ngo 784 Bach Dang To 56, Hong Ha, Ha Noi"
        card = IdCardParser().parse_qr(
            "012345678901|123456789|NGUYEN VAN A|01011990|Nam|"
            + raw_address
            + "|01012025"
        )

        self.assertEqual(card.raw_permanent_address, raw_address)
        self.assertEqual(card.address_status, "current")
        self.assertEqual(
            card.permanent_address,
            "34F Ngo 784 Bach Dang To 56, Ph\u01b0\u1eddng H\u1ed3ng H\u00e0, Th\u00e0nh ph\u1ed1 H\u00e0 N\u1ed9i",
        )

    def test_ambiguous_address_stays_raw_until_the_user_confirms_it(self) -> None:
        raw_address = "To Dan Pho 5, Van Ninh, Quang Ninh"
        result = AddressParser().parse(raw_address)

        self.assertEqual(result.raw_address, raw_address)
        self.assertEqual(result.normalization_status, "needs_confirmation")
        self.assertEqual(result.normalized_address, raw_address)


    def test_parser_joins_ordinary_ocr_line_wraps_without_inventing_a_comma(self) -> None:
        parser = IdCardParser()

        address = parser._join_ocr_address_lines(
            ["S\u1ed1 12 Ng\u00f5 5", "\u0110\u01b0\u1eddng L\u00e1ng"]
        )

        self.assertEqual(address, "S\u1ed1 12 Ng\u00f5 5 \u0110\u01b0\u1eddng L\u00e1ng")
if __name__ == "__main__":
    unittest.main()


import unittest

from mingo_assistant.services.normalization.administrative_place_matcher import AdministrativePlaceMatcher
from mingo_assistant.services.normalization.address_parser import AddressParser
from mingo_assistant.services.ocr.id_card_parser import IdCardParser


class IdCardAddressNormalizationTest(unittest.TestCase):
    def test_matcher_normalizes_noisy_hcm_address(self) -> None:
        matcher = AdministrativePlaceMatcher()

        result = matcher.normalize_address("79/J4, Au Co, Phuong 14, Quan 11, TP Ho Chi Mlnh")

        self.assertEqual(result, "79/J4, Au Co, Phường 14, Quận 11, Thành phố Hồ Chí Minh")

    def test_matcher_merges_split_old_places_then_uses_after_merger_name(self) -> None:
        matcher = AdministrativePlaceMatcher()

        origin = matcher.normalize_address("Tinh, Hai, Tinh Gia, Thanh Hoa")
        residence = matcher.normalize_address("Cao Bac, Hai, Thuong, Tinh Gia, Thanh Hoa")

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
        self.assertEqual(card.place_of_origin, "Xã Tứ Xã, Huyện Lâm Thao, Phú Thọ")
        self.assertEqual(card.permanent_address, "Khu 1, Xã Bản Nguyên, Huyện Lâm Thao, Phú Thọ")

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

        self.assertEqual(card.place_of_origin, "Xã Tứ Xã, Huyện Lâm Thao, Phú Thọ")
        self.assertEqual(card.permanent_address, "")

    def test_parser_continues_to_later_scan_when_first_residence_marker_has_no_value(self) -> None:
        text = """Place of residenc
--- scan 2 ---
Noi thuong tru / Place of residence: Khu 1
Ban Nguyen, Lam Thao, Phu Tho"""

        card = IdCardParser().parse(text)

        self.assertEqual(card.permanent_address, "Khu 1, Xã Bản Nguyên, Huyện Lâm Thao, Phú Thọ")

    def test_address_parser_uses_normalized_administrative_places(self) -> None:
        result = AddressParser().parse("79/J4, Au Co, Phuong 14, Quan 11, TP Ho Chi Mlnh")

        self.assertEqual(result.street_line, "79/J4, Au Co")
        self.assertEqual(result.ward, "Phường 14")
        self.assertEqual(result.province, "Thành phố Hồ Chí Minh")


if __name__ == "__main__":
    unittest.main()

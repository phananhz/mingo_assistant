from __future__ import annotations

import unittest

from mingo_assistant.services.documents.value_formatter import DocumentValueFormatter


class DocumentValueFormatterTests(unittest.TestCase):
    def setUp(self) -> None:
        province_map = {
            "Tỉnh Hà Giang": "Tuyên Quang",
            "Thành phố Hồ Chí Minh": "Thành phố Hồ Chí Minh",
        }
        self.formatter = DocumentValueFormatter(lambda value: province_map.get(value, value))

    def test_formats_date_money_and_member_count(self) -> None:
        self.assertEqual(self.formatter.date_component("1/9/2026", 0), "01")
        self.assertEqual(self.formatter.date_component("1/9/2026", 2), "2026")
        self.assertEqual(self.formatter.with_vnd("1.000.000"), "1.000.000 VNĐ")
        self.assertEqual(self.formatter.with_vnd("1.000.000 đồng"), "1.000.000 đồng")
        self.assertEqual(
            self.formatter.member_count({"member_1_full_name": "A", "member_3_full_name": "B"}),
            2,
        )

    def test_splits_and_normalizes_administrative_address_parts(self) -> None:
        values = {
            "company_address": "12 Đường Mẫu, Phường Trung Tâm, Tỉnh Hà Giang",
            "company_address_detail": "",
            "company_ward": "",
            "company_province": "",
        }

        self.assertEqual(self.formatter.company_address_part(values, "detail"), "12 Đường Mẫu")
        self.assertEqual(self.formatter.company_address_part(values, "ward"), "Phường Trung Tâm")
        self.assertEqual(self.formatter.company_address_part(values, "province"), "Tuyên Quang")

    def test_business_lines_keep_detail_code_and_main_flag(self) -> None:
        values = {
            "business_line_2_name": "Bán buôn  Chi tiết: hàng mẫu",
            "business_line_2_detail": "Theo quy định",
            "business_line_2_code": "46-90",
            "business_line_2_is_main": "X",
        }

        self.assertEqual(
            self.formatter.business_lines(values),
            [
                {
                    "name": "Bán buôn\nChi tiết: hàng mẫu\nTheo quy định",
                    "code": "4690",
                    "is_main": True,
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()

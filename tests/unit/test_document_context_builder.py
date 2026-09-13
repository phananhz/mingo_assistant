from __future__ import annotations

import unittest

from mingo_assistant.services.documents.context_builder import DocumentContextBuilder
from mingo_assistant.services.documents.value_formatter import DocumentValueFormatter


class DocumentContextBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        formatter = DocumentValueFormatter(
            lambda value: "Tuyên Quang" if value == "Tỉnh Hà Giang" else value
        )
        self.builder = DocumentContextBuilder(
            formatter,
            uppercase_fields={"company_name"},
            detail_address_fields={"company_address_detail"},
            ward_fields={"company_ward"},
            province_fields={"company_province"},
        )

    def test_resolves_template_specific_dates_and_capital(self) -> None:
        values = {
            "document_day": "1",
            "document_month": "9",
            "document_year": "2026",
            "charter_capital_number": "1.000.000",
            "charter_capital_text": "Một triệu đồng",
        }

        self.assertEqual(self.builder.value_for_target("document_date_only", values), "ngày 1 tháng 9 năm 2026.")
        self.assertEqual(
            self.builder.value_for_target("charter_capital_article_6_text", values),
            "1.000.000 VNĐ (Ghi bằng chữ: Một triệu đồng)",
        )

    def test_resolves_identity_address_and_uppercase_fields(self) -> None:
        values = {
            "company_name": "Công ty mẫu",
            "company_address": "12 Đường A, Phường B, Tỉnh Hà Giang",
            "organization_owner_representative_identity": "CCCD số: 012345678901 - cấp tại nơi mẫu",
        }

        self.assertEqual(self.builder.value_for_target("company_name", values), "CÔNG TY MẪU")
        self.assertEqual(self.builder.value_for_target("company_address_detail", values), "12 Đường A")
        self.assertEqual(self.builder.value_for_target("company_ward", values), "Phường B")
        self.assertEqual(self.builder.value_for_target("company_province", values), "Tuyên Quang")
        self.assertEqual(
            self.builder.value_for_target("organization_owner_representative_id_number", values),
            "012345678901",
        )


if __name__ == "__main__":
    unittest.main()

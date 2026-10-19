import unittest
from pathlib import Path

from mingo_assistant.services.registration_offices import (
    RegistrationOfficeCatalog,
    update_saved_registration_values,
)


class RegistrationOfficeCatalogTest(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = RegistrationOfficeCatalog.load_from_project(Path(__file__).resolve().parents[2])

    def test_loads_all_registration_offices(self) -> None:
        self.assertEqual(len(self.catalog.offices), 34)

    def test_suggests_hcm_office_by_province_name(self) -> None:
        suggestions = self.catalog.suggestions("Hồ Chí Minh")

        self.assertIn("Phòng Đăng ký kinh doanh Thành phố Hồ Chí Minh", suggestions)

    def test_suggests_hcm_office_by_common_abbreviation(self) -> None:
        suggestions = self.catalog.suggestions("tp hcm")

        self.assertEqual(suggestions[0], "Phòng Đăng ký kinh doanh Thành phố Hồ Chí Minh")

    def test_finds_display_name_for_company_province(self) -> None:
        display_name = self.catalog.display_name_for_province("Thành phố Hồ Chí Minh")

        self.assertEqual(display_name, "Phòng Đăng ký kinh doanh Thành phố Hồ Chí Minh")

    def test_uses_current_city_names_for_three_promoted_provinces(self) -> None:
        expected = {
            "Tỉnh Đồng Nai": "Phòng Đăng ký kinh doanh thành phố Đồng Nai",
            "Tỉnh Quảng Ninh": "Phòng Quản lý doanh nghiệp thành phố Quảng Ninh",
            "Tỉnh Bắc Ninh": "Phòng Quản lý doanh nghiệp thành phố Bắc Ninh",
        }

        for legacy_province, office_name in expected.items():
            with self.subTest(province=legacy_province):
                self.assertEqual(office_name, self.catalog.display_name_for_province(legacy_province))
                self.assertEqual(
                    office_name,
                    self.catalog.display_name_for_province(legacy_province.replace("Tỉnh", "Thành phố")),
                )

    def test_updates_saved_office_province_and_signing_place(self) -> None:
        values = update_saved_registration_values({
            "business_registration_office": "Phòng Đăng ký kinh doanh và Quản lý doanh nghiệp Tỉnh Bắc Ninh",
            "company_province": "Tỉnh Bắc Ninh",
            "document_place": "Tỉnh Bắc Ninh",
            "company_address": "Phường Bắc Giang, Tỉnh Bắc Ninh, Việt Nam",
        })

        self.assertEqual("Phòng Quản lý doanh nghiệp thành phố Bắc Ninh", values["business_registration_office"])
        self.assertEqual("Thành phố Bắc Ninh", values["company_province"])
        self.assertEqual("Bắc Ninh", values["document_place"])
        self.assertEqual("Phường Bắc Giang, Thành phố Bắc Ninh, Việt Nam", values["company_address"])

    def test_household_manual_office_is_not_replaced(self) -> None:
        values = update_saved_registration_values(
            {
                "business_registration_office": "Phòng Đăng ký kinh doanh Tỉnh Đồng Nai",
                "company_province": "Tỉnh Đồng Nai",
            },
            update_office=False,
        )

        self.assertEqual("Phòng Đăng ký kinh doanh Tỉnh Đồng Nai", values["business_registration_office"])
        self.assertEqual("Thành phố Đồng Nai", values["company_province"])

    def test_signing_place_keeps_only_ha_noi_and_ho_chi_minh_prefixes(self) -> None:
        from mingo_assistant.services.registration_offices import signing_place_for_province

        expected = {
            "Thành phố Hồ Chí Minh": "Thành phố Hồ Chí Minh",
            "Thành phố Hà Nội": "Thành phố Hà Nội",
            "Thành phố Đồng Nai": "Đồng Nai",
            "Thành phố Hải Phòng": "Hải Phòng",
            "Tỉnh Quảng Ninh": "Quảng Ninh",
        }
        for province, signing_place in expected.items():
            with self.subTest(province=province):
                self.assertEqual(signing_place, signing_place_for_province(province))

    def test_updates_saved_place_date_line_without_changing_the_date(self) -> None:
        values = update_saved_registration_values({
            "document_place_date": "Tỉnh Đồng Nai, ngày 18 tháng 10 năm 2026",
        })

        self.assertEqual("Đồng Nai, ngày 18 tháng 10 năm 2026", values["document_place_date"])

    def test_legacy_office_name_resolves_to_current_city(self) -> None:
        province = self.catalog.province_for_office("Phòng Đăng ký kinh doanh Tỉnh Đồng Nai")

        self.assertEqual("Thành phố Đồng Nai", province)


if __name__ == "__main__":
    unittest.main()

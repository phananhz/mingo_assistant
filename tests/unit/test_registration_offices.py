import unittest
from pathlib import Path

from mingo_assistant.services.registration_offices import RegistrationOfficeCatalog


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


if __name__ == "__main__":
    unittest.main()

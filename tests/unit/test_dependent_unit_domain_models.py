from __future__ import annotations

from dataclasses import replace
from datetime import date
import unittest

from mingo_assistant.domains.dependent_unit import DependentUnitCase


class DependentUnitDomainModelTest(unittest.TestCase):
    def test_foreign_manager_and_representative_passports_round_trip_losslessly(self) -> None:
        values = {
            "parent_entity_name": "CÔNG TY TNHH TEST",
            "location_business_name": "ĐỊA ĐIỂM KINH DOANH TEST",
            "location_manager_full_name": "FOREIGN MANAGER",
            "location_manager_person_type": "Người nước ngoài",
            "location_manager_id_number": "",
            "location_manager_date_of_birth": "1990-02-03",
            "location_manager_passport_number": "P1234567",
            "location_manager_passport_issue_date": "04-05-2025",
            "location_manager_passport_issue_place": "Foreign Authority",
            "location_manager_foreign_country": "Singapore",
            "legal_representative_full_name": "FOREIGN REPRESENTATIVE",
            "legal_representative_person_type": "Người nước ngoài",
            "legal_representative_passport_number": "P7654321",
            "legal_representative_passport_issue_date": "06/07/2025",
            "business_line_2_name": "Dịch vụ thử nghiệm",
            "business_line_2_code": "8299",
            "business_line_2_is_main": "X",
            "tax_accounting_method": "Hạch toán phụ thuộc",
            "custom_future_field": "KEEP",
        }

        dossier = DependentUnitCase.from_form_values(values)
        restored = dossier.to_form_values()

        self.assertEqual(date(1990, 2, 3), dossier.manager.person.date_of_birth)
        self.assertEqual("P1234567", dossier.manager.document.passport_number)
        self.assertEqual("P7654321", dossier.legal_representative.document.passport_number)
        self.assertEqual("", restored["location_manager_id_number"])
        self.assertEqual("P1234567", restored["location_manager_passport_number"])
        self.assertEqual("P7654321", restored["legal_representative_passport_number"])
        self.assertEqual("X", restored["business_line_2_is_main"])
        self.assertEqual("Hạch toán phụ thuộc", restored["tax_accounting_method"])
        self.assertEqual("KEEP", restored["custom_future_field"])

    def test_update_content_and_unknown_fields_survive_typed_edit(self) -> None:
        dossier = DependentUnitCase.from_form_values({
            "location_business_name": "ĐỊA ĐIỂM CŨ",
            "location_business_code": "00001",
            "supplemental_registration_content": "Nội dung cũ\nDòng thứ hai",
            "change_supplemental_selected": "X",
            "business_line_1_name": "Ngành hiện tại",
            "business_line_1_code": "6201",
        })
        changed = replace(dossier, name="ĐỊA ĐIỂM MỚI")
        restored = changed.to_form_values(base={
            "custom_certificate_field": "KEEP",
            "business_line_9_name": "Ngành đã xóa",
            "change_supplemental_selected": "X",
        })

        self.assertEqual("ĐỊA ĐIỂM MỚI", restored["location_business_name"])
        self.assertEqual("Nội dung cũ\nDòng thứ hai", restored["supplemental_registration_content"])
        self.assertEqual("X", restored["change_supplemental_selected"])
        self.assertEqual("KEEP", restored["custom_certificate_field"])
        self.assertEqual("Ngành hiện tại", restored["business_line_1_name"])
        self.assertNotIn("business_line_9_name", restored)

    def test_termination_fields_are_owned_without_dropping_certificate_data(self) -> None:
        values = {
            "location_business_name": "ĐỊA ĐIỂM TEST",
            "location_business_code": "00009",
            "termination_reason": "Kinh doanh không hiệu quả",
            "certificate_scan_path": "D:/protected/certificate.pdf",
        }

        dossier = DependentUnitCase.from_form_values(values)
        restored = dossier.to_form_values()

        self.assertEqual("00009", dossier.business_code)
        self.assertEqual("Kinh doanh không hiệu quả", dossier.termination_reason)
        self.assertEqual("00009", restored["location_business_code"])
        self.assertEqual("Kinh doanh không hiệu quả", restored["termination_reason"])
        self.assertEqual("D:/protected/certificate.pdf", restored["certificate_scan_path"])


if __name__ == "__main__":
    unittest.main()

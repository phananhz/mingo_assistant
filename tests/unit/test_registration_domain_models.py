from __future__ import annotations

from dataclasses import replace
from datetime import date
import unittest

from mingo_assistant.domains.business_registration import RegistrationCase


class RegistrationDomainModelTests(unittest.TestCase):
    def test_legacy_form_values_are_projected_without_changing_storage_shape(self) -> None:
        values = {
            "company_name": "CÔNG TY TNHH TEST",
            "company_address": "1 Đường Test, Phường Test, Thành phố Test",
            "legal_representative_full_name": "NGUYỄN VĂN TEST",
            "authorized_person_full_name": "TRẦN THỊ TEST",
            "charter_capital_number": "3.000.000.000",
            "business_line_2_name": "Dịch vụ thử nghiệm",
            "business_line_2_code": "8299",
            "business_line_2_is_main": "X",
        }

        registration = RegistrationCase.from_form_values(values)

        self.assertEqual(registration.company.name, "CÔNG TY TNHH TEST")
        self.assertEqual(registration.charter_capital_vnd, 3_000_000_000)
        self.assertEqual(registration.authorized_person.person.full_name, "TRẦN THỊ TEST")
        self.assertEqual(registration.business_lines[0].normalized_code, "8299")
        self.assertEqual(registration.business_lines[0].form_index, 2)
        self.assertTrue(registration.business_lines[0].is_main)
        self.assertEqual(dict(registration.legacy_form_values), values)

    def test_money_is_stored_as_integer_not_float(self) -> None:
        registration = RegistrationCase.from_form_values({"charter_capital_number": "1.234.567"})

        self.assertIsInstance(registration.charter_capital_vnd, int)
        self.assertEqual(registration.charter_capital_vnd, 1_234_567)

    def test_typed_round_trip_preserves_unknown_fields_and_dynamic_line_indices(self) -> None:
        values = {
            "company_name": "CÔNG TY TNHH TEST",
            "legal_representative_full_name": "NGUYỄN VĂN TEST",
            "legal_representative_date_of_birth": "02/03/1990",
            "legal_representative_passport_number": "P1234567",
            "authorized_person_full_name": "TRẦN THỊ TEST",
            "authorized_person_date_of_birth": "1992-04-05",
            "authorized_person_issue_date": "06-07-2025",
            "charter_capital_number": "3.000.000.000",
            "document_place": "Thành phố Hồ Chí Minh",
            "document_day": "15",
            "document_month": "10",
            "document_year": "2026",
            "signer_full_name": "NGUYỄN VĂN TEST",
            "business_line_3_name": "Dịch vụ thử nghiệm",
            "business_line_3_code": "8299",
            "business_line_3_is_main": "X",
            "custom_future_field": "KEEP",
        }

        registration = RegistrationCase.from_form_values(values)
        changed = replace(
            registration,
            company=replace(registration.company, name="CÔNG TY TNHH ĐÃ SỬA"),
        )
        restored = changed.to_form_values()

        self.assertEqual(date(1990, 3, 2), registration.legal_representative.date_of_birth)
        self.assertEqual(date(1992, 4, 5), registration.authorized_person.person.date_of_birth)
        self.assertEqual(date(2025, 7, 6), registration.authorized_person.issue_date)
        self.assertEqual("CÔNG TY TNHH ĐÃ SỬA", restored["company_name"])
        self.assertEqual("3.000.000.000", restored["charter_capital_number"])
        self.assertEqual("Dịch vụ thử nghiệm", restored["business_line_3_name"])
        self.assertEqual("X", restored["business_line_3_is_main"])
        self.assertEqual("P1234567", restored["legal_representative_passport_number"])
        self.assertEqual("KEEP", restored["custom_future_field"])
        self.assertEqual(values, registration.legacy_form_values)

    def test_explicit_base_is_preserved_without_reusing_stale_business_lines(self) -> None:
        registration = RegistrationCase.from_form_values({
            "business_line_1_name": "Ngành hiện tại",
            "business_line_1_code": "6201",
        })

        restored = registration.to_form_values(base={
            "custom_external_field": "KEEP",
            "business_line_9_name": "Ngành đã xóa",
        })

        self.assertEqual("KEEP", restored["custom_external_field"])
        self.assertEqual("Ngành hiện tại", restored["business_line_1_name"])
        self.assertNotIn("business_line_9_name", restored)


if __name__ == "__main__":
    unittest.main()

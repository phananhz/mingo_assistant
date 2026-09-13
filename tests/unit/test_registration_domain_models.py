from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()

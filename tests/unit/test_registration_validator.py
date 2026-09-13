from __future__ import annotations

import unittest

from mingo_assistant.domains.business_registration import RegistrationValidator


class RegistrationValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = RegistrationValidator()

    def test_individual_requires_legal_representative_issue_place(self) -> None:
        missing = self.validator.missing_required_fields({})

        self.assertIn("Nơi cấp CCCD của người đại diện pháp luật", missing)
        self.assertNotIn("Tên tổ chức chủ sở hữu", missing)

    def test_organization_uses_organization_owner_requirements(self) -> None:
        missing = self.validator.missing_required_fields({"owner_type": "Tổ chức"})

        self.assertIn("Tên tổ chức chủ sở hữu", missing)
        self.assertNotIn("Họ tên chủ sở hữu", missing)

    def test_authorized_person_and_address_confirmation_rules_are_preserved(self) -> None:
        missing = self.validator.missing_required_fields(
            {"authorized_person_full_name": "NGƯỜI ĐƯỢC ỦY QUYỀN"},
            address_confirmation_required=True,
        )

        self.assertIn("Nơi cấp CCCD của người được ủy quyền", missing)
        self.assertIn("Địa chỉ liên lạc của người được ủy quyền", missing)
        self.assertIn("Xác nhận địa chỉ CCCD trước khi xuất hồ sơ", missing)

    def test_business_line_validation_requires_main_four_digit_line(self) -> None:
        values = {
            "business_line_1_name": "Dịch vụ thử nghiệm",
            "business_line_1_code": "12",
            "business_line_1_is_main": "",
        }

        result = self.validator.validate(values)

        self.assertIn("Chọn 1 ngành nghề chính", result.errors)
        self.assertIn("Mã ngành nghề cấp 4 của ngành 1", result.errors)
        self.assertNotIn("Ít nhất 1 ngành nghề kinh doanh", result.errors)

    def test_business_line_error_preserves_sparse_form_index(self) -> None:
        result = self.validator.validate(
            {
                "business_line_3_name": "Dịch vụ thử nghiệm",
                "business_line_3_code": "12",
                "business_line_3_is_main": "X",
            }
        )

        self.assertIn("Mã ngành nghề cấp 4 của ngành 3", result.errors)


if __name__ == "__main__":
    unittest.main()

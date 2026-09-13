from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from mingo_assistant.domains.business_registration.models import BusinessLine

@dataclass(frozen=True)
class RegistrationValidationResult:
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.errors


class RegistrationValidator:
    """Business-registration validation independent from PySide and DOCX."""

    _INDIVIDUAL_REQUIRED = {
        "beneficial_owner_full_name": "Họ tên chủ sở hữu",
        "beneficial_owner_id_number": "Số CCCD chủ sở hữu",
        "beneficial_owner_address": "Địa chỉ liên lạc của chủ sở hữu",
        "company_name": "Tên doanh nghiệp",
        "company_address": "Địa chỉ trụ sở",
        "company_phone": "Số điện thoại công ty (dùng cho thông tin đăng ký thuế)",
        "charter_capital_number": "Vốn điều lệ",
        "legal_representative_full_name": "Họ tên cá nhân/đại diện",
        "legal_representative_id_number": "Số CCCD",
        "legal_representative_permanent_address": "Địa chỉ thường trú",
        "legal_representative_issue_place": "Nơi cấp CCCD của người đại diện pháp luật",
    }
    _ORGANIZATION_REQUIRED = {
        "organization_owner_name": "Tên tổ chức chủ sở hữu",
        "organization_owner_registration_number": "Mã số doanh nghiệp/Số quyết định thành lập của chủ sở hữu",
        "organization_owner_address_detail": "Địa chỉ chi tiết của chủ sở hữu tổ chức",
        "organization_owner_representative_full_name": "Họ tên người đại diện vốn của tổ chức",
        "organization_owner_representative_identity": "Giấy tờ pháp lý của người đại diện vốn",
    }

    def missing_required_fields(
        self,
        values: Mapping[str, str],
        *,
        address_confirmation_required: bool = False,
    ) -> list[str]:
        required = dict(self._INDIVIDUAL_REQUIRED)
        if values.get("owner_type", "Cá nhân") == "Tổ chức":
            for key in ("beneficial_owner_full_name", "beneficial_owner_id_number", "beneficial_owner_address"):
                required.pop(key, None)
            required.update(self._ORGANIZATION_REQUIRED)
        if values.get("authorized_person_full_name", "").strip() or values.get(
            "authorized_person_id_number", ""
        ).strip():
            required["authorized_person_issue_place"] = "Nơi cấp CCCD của người được ủy quyền"
            required["authorized_person_contact_address"] = "Địa chỉ liên lạc của người được ủy quyền"

        missing = [label for key, label in required.items() if not values.get(key, "").strip()]
        if address_confirmation_required:
            missing.append("Xác nhận địa chỉ CCCD trước khi xuất hồ sơ")
        return missing

    def validate(
        self,
        values: Mapping[str, str],
        *,
        address_confirmation_required: bool = False,
    ) -> RegistrationValidationResult:
        errors = self.missing_required_fields(
            values,
            address_confirmation_required=address_confirmation_required,
        )
        business_lines = BusinessLine.from_form_values(values)
        if not any(line.name for line in business_lines):
            errors.append("Ít nhất 1 ngành nghề kinh doanh")
        if not any(line.is_main for line in business_lines):
            errors.append("Chọn 1 ngành nghề chính")
        for line in business_lines:
            if line.name and len(line.normalized_code) != 4:
                errors.append(f"Mã ngành nghề cấp 4 của ngành {line.form_index}")
        return RegistrationValidationResult(errors=tuple(errors))

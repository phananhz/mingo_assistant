from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Protocol


class ParsedAddressPort(Protocol):
    street_line: str
    village: str
    ward: str
    province: str


class AddressParserPort(Protocol):
    def parse(self, address: str) -> ParsedAddressPort: ...


class RecognizedPersonPort(Protocol):
    data: dict[str, str]
    recognition_type: str


class PersonIdentityRules:
    """Identity comparison and cross-person contact safeguards."""

    @staticmethod
    def same_identity(value: object, id_numbers: set[str]) -> bool:
        digits = re.sub(r"\D", "", str(value or ""))
        return bool(digits and digits in id_numbers)

    @staticmethod
    def clear_cross_person_authorized_contacts(values: dict[str, str]) -> None:
        applicant_id = re.sub(r"\D", "", str(values.get("applicant_id_number", "") or ""))
        authorized_id = re.sub(r"\D", "", str(values.get("authorized_person_id_number", "") or ""))
        applicant_name = re.sub(r"\W", "", str(values.get("applicant_full_name", "") or "").casefold())
        authorized_name = re.sub(r"\W", "", str(values.get("authorized_person_full_name", "") or "").casefold())
        people_are_distinct = (
            bool(applicant_id and authorized_id and applicant_id != authorized_id)
            or bool(not applicant_id and not authorized_id and applicant_name and authorized_name and applicant_name != authorized_name)
        )
        if not people_are_distinct:
            return
        for applicant_key, authorized_key, normalizer in (
            ("applicant_phone", "authorized_person_phone", lambda value: re.sub(r"\D", "", value)),
            ("applicant_email", "authorized_person_email", lambda value: value.casefold()),
        ):
            applicant_value = str(values.get(applicant_key, "") or "").strip()
            authorized_value = str(values.get(authorized_key, "") or "").strip()
            if applicant_value and authorized_value and normalizer(applicant_value) == normalizer(authorized_value):
                values[applicant_key] = ""

    @staticmethod
    def authorization_contact_address(data: Mapping[str, str]) -> str:
        for key in (
            "legal_representative_contact_address",
            "personal_contact_address",
            "legal_representative_permanent_address",
            "personal_permanent_address",
        ):
            value = str(data.get(key, "") or "").strip()
            if value:
                return value
        return ""


class PersonRoleMapper:
    """Map normalized CCCD values to one registration role."""

    def __init__(self, address_parser: AddressParserPort) -> None:
        self._address_parser = address_parser

    def map_fields(
        self,
        card_values: Mapping[str, str],
        role: str,
        person_number: int,
    ) -> dict[str, str]:
        prefix = {
            "legal_representative": "legal_representative",
            "applicant": "applicant",
            "authorized_person": "authorized_person",
            "member": f"member_{person_number}",
            "beneficial_owner": "beneficial_owner",
        }.get(role, "legal_representative")
        source_map = {
            "full_name": "legal_representative_full_name",
            "id_number": "legal_representative_id_number",
            "date_of_birth": "legal_representative_date_of_birth",
            "gender": "legal_representative_gender",
            "permanent_address": "legal_representative_permanent_address",
            "nationality": "legal_representative_nationality",
            "issue_date": "legal_representative_issue_date",
            "expiry_date": "legal_representative_expiry_date",
            "issue_place": "legal_representative_issue_place",
        }
        mapped: dict[str, str] = {}
        for suffix, source_key in source_map.items():
            value = str(card_values.get(source_key, "") or "")
            if not value:
                continue
            if role == "applicant" and suffix == "permanent_address":
                parsed = self._address_parser.parse(value)
                mapped.update(
                    {
                        "applicant_address_detail": parsed.street_line or parsed.village,
                        "applicant_ward": parsed.ward,
                        "applicant_province": parsed.province,
                    }
                )
                continue
            target_key = f"{prefix}_{suffix}"
            if role == "beneficial_owner" and suffix == "permanent_address":
                target_key = "beneficial_owner_address"
            mapped[target_key] = value
        if role == "authorized_person":
            address = PersonIdentityRules.authorization_contact_address(card_values)
            if address:
                mapped["authorized_person_contact_address"] = address
        return mapped


class PersonProfileSynchronizer:
    """Synchronize an edited CCCD across matching in-case person records."""

    ROLE_ID_FIELDS = {
        "legal_representative": "legal_representative_id_number",
        "applicant": "applicant_id_number",
        "authorized_person": "authorized_person_id_number",
        "beneficial_owner": "beneficial_owner_id_number",
    }

    @staticmethod
    def identity_numbers(card_values: Mapping[str, str], previous_id_number: str) -> set[str]:
        return {
            digits
            for value in (previous_id_number, card_values.get("legal_representative_id_number", ""))
            if (digits := re.sub(r"\D", "", str(value or "")))
        }

    @staticmethod
    def update_people(
        people: list[RecognizedPersonPort],
        card_values: Mapping[str, str],
        id_numbers: set[str],
    ) -> int:
        updated_count = 0
        for person in people:
            person_id = person.data.get("legal_representative_id_number", "")
            if not PersonIdentityRules.same_identity(person_id, id_numbers):
                continue
            updated_data = dict(person.data)
            updated_data.update(card_values)
            person.data = {key: value for key, value in updated_data.items() if value}
            person.recognition_type = "individual"
            updated_count += 1
        return updated_count

    @classmethod
    def matching_roles(cls, form_values: Mapping[str, str], id_numbers: set[str]) -> list[str]:
        return [
            role
            for role, id_field in cls.ROLE_ID_FIELDS.items()
            if PersonIdentityRules.same_identity(form_values.get(id_field, ""), id_numbers)
        ]

    @staticmethod
    def beneficial_owner_list_values(card_values: Mapping[str, str]) -> dict[str, str]:
        return {
            "beneficial_owner_list_full_name": str(card_values.get("legal_representative_full_name", "") or ""),
            "beneficial_owner_list_date_of_birth": str(card_values.get("legal_representative_date_of_birth", "") or ""),
            "beneficial_owner_list_gender": str(card_values.get("legal_representative_gender", "") or ""),
            "beneficial_owner_list_identity": PersonProfileSynchronizer.representative_identity_text(card_values),
            "beneficial_owner_list_ethnicity": str(card_values.get("legal_representative_ethnicity", "") or ""),
            "beneficial_owner_list_address": PersonIdentityRules.authorization_contact_address(card_values),
        }

    @staticmethod
    def representative_identity_text(data: Mapping[str, str]) -> str:
        identity_number = str(data.get("legal_representative_id_number", "") or "").strip()
        issue_date = str(data.get("legal_representative_issue_date", "") or "").strip()
        issue_place = str(data.get("legal_representative_issue_place", "") or "").strip()
        parts = [f"CCCD số {identity_number}" if identity_number else ""]
        if issue_date:
            parts.append(f"cấp ngày {issue_date}")
        if issue_place:
            parts.append(f"nơi cấp {issue_place}")
        return ", ".join(part for part in parts if part)

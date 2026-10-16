from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
import re
from typing import Mapping

from mingo_assistant.models.form_values import (
    BUSINESS_LINE_KEY_PATTERN,
    format_form_date,
    merge_form_values,
    normalize_form_values,
    parse_form_date,
)


def _format_vnd(value: int, existing: str = "") -> str:
    digits = re.sub(r"\D", "", str(existing or ""))
    if digits and int(digits) == value:
        return existing
    return f"{max(0, value):,}".replace(",", ".")


@dataclass(frozen=True)
class Address:
    full_text: str = ""
    detail: str = ""
    ward: str = ""
    province: str = ""


@dataclass(frozen=True)
class Person:
    full_name: str = ""
    identity_number: str = ""
    date_of_birth: date | None = None
    gender: str = ""
    nationality: str = ""
    permanent_address: Address = field(default_factory=Address)
    contact_address: Address = field(default_factory=Address)


@dataclass(frozen=True)
class AuthorizedPerson:
    person: Person = field(default_factory=Person)
    phone: str = ""
    email: str = ""
    issue_date: date | None = None
    issue_place: str = ""


@dataclass(frozen=True)
class Company:
    name: str = ""
    address: Address = field(default_factory=Address)
    phone: str = ""
    email: str = ""


@dataclass(frozen=True)
class BusinessLine:
    name: str
    code: str = ""
    detail: str = ""
    is_main: bool = False
    form_index: int = 0

    @property
    def normalized_code(self) -> str:
        return re.sub(r"\D", "", self.code)[:4]

    @classmethod
    def from_form_values(cls, values: Mapping[str, str]) -> tuple["BusinessLine", ...]:
        indices = {
            int(match.group(1))
            for key in values
            if (match := re.fullmatch(r"business_line_(\d+)_(?:name|detail|code|is_main)", key))
        }
        return tuple(
            cls(
                name=str(values.get(f"business_line_{index}_name", "") or "").strip(),
                detail=str(values.get(f"business_line_{index}_detail", "") or "").strip(),
                code=str(values.get(f"business_line_{index}_code", "") or "").strip(),
                is_main=bool(str(values.get(f"business_line_{index}_is_main", "") or "").strip()),
                form_index=index,
            )
            for index in sorted(indices)
            if index > 0
        )


@dataclass(frozen=True)
class CapitalContribution:
    contributor_name: str
    amount_vnd: int
    ratio_percent: Decimal


@dataclass(frozen=True)
class OrganizationOwner:
    name: str = ""
    registration_number: str = ""
    address: Address = field(default_factory=Address)
    representative: Person = field(default_factory=Person)


@dataclass(frozen=True)
class SigningContext:
    place: str = ""
    day: str = ""
    month: str = ""
    year: str = ""
    signer_full_name: str = ""


@dataclass(frozen=True)
class RegistrationCase:
    company: Company
    legal_representative: Person
    authorized_person: AuthorizedPerson | None
    business_lines: tuple[BusinessLine, ...]
    charter_capital_vnd: int
    signing: SigningContext = field(default_factory=SigningContext)
    owner_type: str = "Cá nhân"
    organization_owner: OrganizationOwner | None = None
    legacy_form_values: Mapping[str, str] = field(default_factory=dict, repr=False)

    @classmethod
    def from_form_values(cls, values: Mapping[str, str]) -> "RegistrationCase":
        copied = {str(key): str(value or "") for key, value in values.items()}
        company = Company(
            name=copied.get("company_name", ""),
            phone=copied.get("company_phone", ""),
            email=copied.get("company_email", ""),
            address=Address(
                full_text=copied.get("company_address", ""),
                detail=copied.get("company_address_detail", ""),
                ward=copied.get("company_ward", ""),
                province=copied.get("company_province", ""),
            ),
        )
        legal_representative = Person(
            full_name=copied.get("legal_representative_full_name", ""),
            identity_number=copied.get("legal_representative_id_number", ""),
            date_of_birth=parse_form_date(copied.get("legal_representative_date_of_birth", "")),
            gender=copied.get("legal_representative_gender", ""),
            nationality=copied.get("legal_representative_nationality", ""),
            permanent_address=Address(
                full_text=copied.get("legal_representative_permanent_address", ""),
                detail=copied.get("legal_representative_address_detail", ""),
                ward=copied.get("legal_representative_ward", ""),
                province=copied.get("legal_representative_province", ""),
            ),
            contact_address=Address(
                full_text=copied.get("legal_representative_contact_address", ""),
            ),
        )
        authorized = None
        if copied.get("authorized_person_full_name") or copied.get("authorized_person_id_number"):
            authorized = AuthorizedPerson(
                person=Person(
                    full_name=copied.get("authorized_person_full_name", ""),
                    identity_number=copied.get("authorized_person_id_number", ""),
                    date_of_birth=parse_form_date(copied.get("authorized_person_date_of_birth", "")),
                    gender=copied.get("authorized_person_gender", ""),
                    nationality=copied.get("authorized_person_nationality", ""),
                    contact_address=Address(full_text=copied.get("authorized_person_contact_address", "")),
                ),
                phone=copied.get("authorized_person_phone", ""),
                email=copied.get("authorized_person_email", ""),
                issue_date=parse_form_date(copied.get("authorized_person_issue_date", "")),
                issue_place=copied.get("authorized_person_issue_place", ""),
            )
        organization_owner = None
        if copied.get("owner_type", "Cá nhân") == "Tổ chức":
            organization_owner = OrganizationOwner(
                name=copied.get("organization_owner_name", ""),
                registration_number=copied.get("organization_owner_registration_number", ""),
                address=Address(
                    full_text=copied.get("organization_owner_address", ""),
                    detail=copied.get("organization_owner_address_detail", ""),
                    ward=copied.get("organization_owner_ward", ""),
                    province=copied.get("organization_owner_province", ""),
                ),
                representative=Person(
                    full_name=copied.get("organization_owner_representative_full_name", ""),
                    identity_number=copied.get("organization_owner_representative_identity", ""),
                ),
            )
        capital_digits = re.sub(r"\D", "", copied.get("charter_capital_number", ""))
        return cls(
            company=company,
            legal_representative=legal_representative,
            authorized_person=authorized,
            business_lines=BusinessLine.from_form_values(copied),
            charter_capital_vnd=int(capital_digits or 0),
            signing=SigningContext(
                place=copied.get("document_place", ""),
                day=copied.get("document_day", ""),
                month=copied.get("document_month", ""),
                year=copied.get("document_year", ""),
                signer_full_name=copied.get("signer_full_name", ""),
            ),
            owner_type=copied.get("owner_type", "Cá nhân"),
            organization_owner=organization_owner,
            legacy_form_values=copied,
        )

    def to_form_values(self, base: Mapping[str, str] | None = None) -> dict[str, str]:
        """Project typed fields back onto a lossless legacy-compatible map."""

        source = self.legacy_form_values if base is None else normalize_form_values(base)
        values = merge_form_values(
            source,
            {},
            replaced_key_patterns=(BUSINESS_LINE_KEY_PATTERN,),
        )
        values.update({
            "company_name": self.company.name,
            "company_address": self.company.address.full_text,
            "company_address_detail": self.company.address.detail,
            "company_ward": self.company.address.ward,
            "company_province": self.company.address.province,
            "company_phone": self.company.phone,
            "company_email": self.company.email,
            "legal_representative_full_name": self.legal_representative.full_name,
            "legal_representative_id_number": self.legal_representative.identity_number,
            "legal_representative_date_of_birth": format_form_date(
                self.legal_representative.date_of_birth
            ),
            "legal_representative_gender": self.legal_representative.gender,
            "legal_representative_nationality": self.legal_representative.nationality,
            "legal_representative_permanent_address": (
                self.legal_representative.permanent_address.full_text
            ),
            "legal_representative_address_detail": (
                self.legal_representative.permanent_address.detail
            ),
            "legal_representative_ward": self.legal_representative.permanent_address.ward,
            "legal_representative_province": (
                self.legal_representative.permanent_address.province
            ),
            "legal_representative_contact_address": (
                self.legal_representative.contact_address.full_text
            ),
            "charter_capital_number": _format_vnd(
                self.charter_capital_vnd,
                values.get("charter_capital_number", ""),
            ),
            "owner_type": self.owner_type,
            "document_place": self.signing.place,
            "document_day": self.signing.day,
            "document_month": self.signing.month,
            "document_year": self.signing.year,
            "signer_full_name": self.signing.signer_full_name,
        })
        authorized = self.authorized_person
        values.update({
            "authorized_person_full_name": authorized.person.full_name if authorized else "",
            "authorized_person_id_number": authorized.person.identity_number if authorized else "",
            "authorized_person_date_of_birth": (
                format_form_date(authorized.person.date_of_birth) if authorized else ""
            ),
            "authorized_person_gender": authorized.person.gender if authorized else "",
            "authorized_person_nationality": authorized.person.nationality if authorized else "",
            "authorized_person_contact_address": (
                authorized.person.contact_address.full_text if authorized else ""
            ),
            "authorized_person_phone": authorized.phone if authorized else "",
            "authorized_person_email": authorized.email if authorized else "",
            "authorized_person_issue_date": (
                format_form_date(authorized.issue_date) if authorized else ""
            ),
            "authorized_person_issue_place": authorized.issue_place if authorized else "",
        })
        organization = self.organization_owner
        values.update({
            "organization_owner_name": organization.name if organization else "",
            "organization_owner_registration_number": (
                organization.registration_number if organization else ""
            ),
            "organization_owner_address": organization.address.full_text if organization else "",
            "organization_owner_address_detail": organization.address.detail if organization else "",
            "organization_owner_ward": organization.address.ward if organization else "",
            "organization_owner_province": organization.address.province if organization else "",
            "organization_owner_representative_full_name": (
                organization.representative.full_name if organization else ""
            ),
            "organization_owner_representative_identity": (
                organization.representative.identity_number if organization else ""
            ),
        })
        for output_index, line in enumerate(self.business_lines, start=1):
            index = line.form_index if line.form_index > 0 else output_index
            values[f"business_line_{index}_name"] = line.name
            values[f"business_line_{index}_detail"] = line.detail
            values[f"business_line_{index}_code"] = line.code
            values[f"business_line_{index}_is_main"] = "X" if line.is_main else ""
        return values

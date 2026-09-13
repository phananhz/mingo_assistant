from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
import re
from typing import Mapping


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
class RegistrationCase:
    company: Company
    legal_representative: Person
    authorized_person: AuthorizedPerson | None
    business_lines: tuple[BusinessLine, ...]
    charter_capital_vnd: int
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
            gender=copied.get("legal_representative_gender", ""),
            nationality=copied.get("legal_representative_nationality", ""),
            permanent_address=Address(
                full_text=copied.get("legal_representative_permanent_address", ""),
                detail=copied.get("legal_representative_address_detail", ""),
                ward=copied.get("legal_representative_ward", ""),
                province=copied.get("legal_representative_province", ""),
            ),
        )
        authorized = None
        if copied.get("authorized_person_full_name") or copied.get("authorized_person_id_number"):
            authorized = AuthorizedPerson(
                person=Person(
                    full_name=copied.get("authorized_person_full_name", ""),
                    identity_number=copied.get("authorized_person_id_number", ""),
                    contact_address=Address(full_text=copied.get("authorized_person_contact_address", "")),
                ),
                phone=copied.get("authorized_person_phone", ""),
                email=copied.get("authorized_person_email", ""),
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
            owner_type=copied.get("owner_type", "Cá nhân"),
            organization_owner=organization_owner,
            legacy_form_values=copied,
        )

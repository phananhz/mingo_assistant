"""Typed, lossless projection for dependent-unit dossier form values."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Mapping

from mingo_assistant.domains.business_registration.models import (
    Address,
    AuthorizedPerson,
    BusinessLine,
    Person,
    SigningContext,
)
from mingo_assistant.models.form_values import (
    BUSINESS_LINE_KEY_PATTERN,
    format_form_date,
    merge_form_values,
    normalize_form_values,
    parse_form_date,
)


@dataclass(frozen=True)
class IdentityDocument:
    person_type: str = ""
    identity_number: str = ""
    passport_number: str = ""
    passport_issue_date: date | None = None
    passport_issue_place: str = ""


@dataclass(frozen=True)
class ParentEntity:
    entity_type: str = ""
    name: str = ""
    registration_number: str = ""
    branch_name: str = ""
    branch_number: str = ""


@dataclass(frozen=True)
class LegalRepresentative:
    person: Person = field(default_factory=Person)
    position: str = ""
    document: IdentityDocument = field(default_factory=IdentityDocument)


@dataclass(frozen=True)
class DependentUnitManager:
    person: Person = field(default_factory=Person)
    document: IdentityDocument = field(default_factory=IdentityDocument)
    phone: str = ""
    email: str = ""
    foreign_address_detail: str = ""
    foreign_country: str = ""


@dataclass(frozen=True)
class DependentUnitCase:
    parent: ParentEntity = field(default_factory=ParentEntity)
    name: str = ""
    english_name: str = ""
    short_name: str = ""
    business_code: str = ""
    address: Address = field(default_factory=Address)
    phone: str = ""
    email: str = ""
    manager: DependentUnitManager = field(default_factory=DependentUnitManager)
    legal_representative: LegalRepresentative = field(default_factory=LegalRepresentative)
    authorized_person: AuthorizedPerson | None = None
    business_lines: tuple[BusinessLine, ...] = ()
    signing: SigningContext = field(default_factory=SigningContext)
    supplemental_registration_content: str = ""
    termination_reason: str = ""
    legacy_form_values: Mapping[str, str] = field(default_factory=dict, repr=False)

    @classmethod
    def from_form_values(cls, values: Mapping[str, str]) -> "DependentUnitCase":
        copied = normalize_form_values(values)
        authorized = None
        if copied.get("authorized_person_full_name") or copied.get("authorized_person_id_number"):
            authorized = AuthorizedPerson(
                person=Person(
                    full_name=copied.get("authorized_person_full_name", ""),
                    identity_number=copied.get("authorized_person_id_number", ""),
                    date_of_birth=parse_form_date(copied.get("authorized_person_date_of_birth", "")),
                    gender=copied.get("authorized_person_gender", ""),
                    nationality=copied.get("authorized_person_nationality", ""),
                    contact_address=Address(
                        full_text=copied.get("authorized_person_contact_address", ""),
                    ),
                ),
                phone=copied.get("authorized_person_phone", ""),
                email=copied.get("authorized_person_email", ""),
                issue_date=parse_form_date(copied.get("authorized_person_issue_date", "")),
                issue_place=copied.get("authorized_person_issue_place", ""),
            )
        return cls(
            parent=ParentEntity(
                entity_type=copied.get("parent_entity_type", ""),
                name=copied.get("parent_entity_name", ""),
                registration_number=copied.get("parent_entity_registration_number", ""),
                branch_name=copied.get("parent_entity_branch_name", ""),
                branch_number=copied.get("parent_entity_branch_number", ""),
            ),
            name=copied.get("location_business_name", ""),
            english_name=copied.get("location_business_english_name", ""),
            short_name=copied.get("location_business_short_name", ""),
            business_code=copied.get("location_business_code", ""),
            address=Address(
                full_text=copied.get("location_full_address", ""),
                detail=copied.get("location_address_detail", ""),
                ward=copied.get("location_ward", ""),
                province=copied.get("location_province", ""),
            ),
            phone=copied.get("location_phone", ""),
            email=copied.get("location_email", ""),
            manager=DependentUnitManager(
                person=Person(
                    full_name=copied.get("location_manager_full_name", ""),
                    identity_number=copied.get("location_manager_id_number", ""),
                    date_of_birth=parse_form_date(copied.get("location_manager_date_of_birth", "")),
                    gender=copied.get("location_manager_gender", ""),
                    nationality=copied.get("location_manager_nationality", ""),
                    permanent_address=Address(
                        detail=copied.get("location_manager_address_detail", ""),
                        ward=copied.get("location_manager_ward", ""),
                        province=copied.get("location_manager_province", ""),
                    ),
                ),
                document=IdentityDocument(
                    person_type=copied.get("location_manager_person_type", ""),
                    identity_number=copied.get("location_manager_id_number", ""),
                    passport_number=copied.get("location_manager_passport_number", ""),
                    passport_issue_date=parse_form_date(
                        copied.get("location_manager_passport_issue_date", "")
                    ),
                    passport_issue_place=copied.get(
                        "location_manager_passport_issue_place", ""
                    ),
                ),
                phone=copied.get("location_manager_phone", ""),
                email=copied.get("location_manager_email", ""),
                foreign_address_detail=copied.get(
                    "location_manager_foreign_address_detail", ""
                ),
                foreign_country=copied.get("location_manager_foreign_country", ""),
            ),
            legal_representative=LegalRepresentative(
                person=Person(
                    full_name=copied.get("legal_representative_full_name", ""),
                    identity_number=copied.get("legal_representative_id_number", ""),
                    date_of_birth=parse_form_date(
                        copied.get("legal_representative_date_of_birth", "")
                    ),
                    gender=copied.get("legal_representative_gender", ""),
                    nationality=copied.get("legal_representative_nationality", ""),
                    permanent_address=Address(
                        full_text=copied.get(
                            "legal_representative_permanent_address", ""
                        ),
                    ),
                    contact_address=Address(
                        full_text=copied.get("legal_representative_contact_address", ""),
                    ),
                ),
                position=copied.get("legal_representative_position", ""),
                document=IdentityDocument(
                    person_type=copied.get("legal_representative_person_type", ""),
                    identity_number=copied.get("legal_representative_id_number", ""),
                    passport_number=copied.get("legal_representative_passport_number", ""),
                    passport_issue_date=parse_form_date(
                        copied.get("legal_representative_passport_issue_date", "")
                    ),
                    passport_issue_place=copied.get(
                        "legal_representative_passport_issue_place", ""
                    ),
                ),
            ),
            authorized_person=authorized,
            business_lines=BusinessLine.from_form_values(copied),
            signing=SigningContext(
                place=copied.get("document_place", ""),
                day=copied.get("document_day", ""),
                month=copied.get("document_month", ""),
                year=copied.get("document_year", ""),
                signer_full_name=copied.get("signer_full_name", ""),
            ),
            supplemental_registration_content=copied.get(
                "supplemental_registration_content", ""
            ),
            termination_reason=copied.get("termination_reason", ""),
            legacy_form_values=copied,
        )

    def to_form_values(self, base: Mapping[str, str] | None = None) -> dict[str, str]:
        source = self.legacy_form_values if base is None else normalize_form_values(base)
        values = merge_form_values(
            source,
            {},
            replaced_key_patterns=(BUSINESS_LINE_KEY_PATTERN,),
        )
        manager = self.manager
        representative = self.legal_representative
        values.update({
            "parent_entity_type": self.parent.entity_type,
            "parent_entity_name": self.parent.name,
            "parent_entity_registration_number": self.parent.registration_number,
            "parent_entity_branch_name": self.parent.branch_name,
            "parent_entity_branch_number": self.parent.branch_number,
            "location_business_name": self.name,
            "location_business_english_name": self.english_name,
            "location_business_short_name": self.short_name,
            "location_business_code": self.business_code,
            "location_full_address": self.address.full_text,
            "location_address_detail": self.address.detail,
            "location_ward": self.address.ward,
            "location_province": self.address.province,
            "location_phone": self.phone,
            "location_email": self.email,
            "location_manager_full_name": manager.person.full_name,
            "location_manager_person_type": manager.document.person_type,
            "location_manager_id_number": manager.document.identity_number,
            "location_manager_date_of_birth": format_form_date(
                manager.person.date_of_birth
            ),
            "location_manager_gender": manager.person.gender,
            "location_manager_nationality": manager.person.nationality,
            "location_manager_address_detail": manager.person.permanent_address.detail,
            "location_manager_ward": manager.person.permanent_address.ward,
            "location_manager_province": manager.person.permanent_address.province,
            "location_manager_passport_number": manager.document.passport_number,
            "location_manager_passport_issue_date": format_form_date(
                manager.document.passport_issue_date
            ),
            "location_manager_passport_issue_place": (
                manager.document.passport_issue_place
            ),
            "location_manager_phone": manager.phone,
            "location_manager_email": manager.email,
            "location_manager_foreign_address_detail": manager.foreign_address_detail,
            "location_manager_foreign_country": manager.foreign_country,
            "legal_representative_full_name": representative.person.full_name,
            "legal_representative_person_type": representative.document.person_type,
            "legal_representative_id_number": representative.document.identity_number,
            "legal_representative_date_of_birth": format_form_date(
                representative.person.date_of_birth
            ),
            "legal_representative_gender": representative.person.gender,
            "legal_representative_nationality": representative.person.nationality,
            "legal_representative_permanent_address": (
                representative.person.permanent_address.full_text
            ),
            "legal_representative_contact_address": (
                representative.person.contact_address.full_text
            ),
            "legal_representative_position": representative.position,
            "legal_representative_passport_number": (
                representative.document.passport_number
            ),
            "legal_representative_passport_issue_date": format_form_date(
                representative.document.passport_issue_date
            ),
            "legal_representative_passport_issue_place": (
                representative.document.passport_issue_place
            ),
            "document_place": self.signing.place,
            "document_day": self.signing.day,
            "document_month": self.signing.month,
            "document_year": self.signing.year,
            "signer_full_name": self.signing.signer_full_name,
            "supplemental_registration_content": (
                self.supplemental_registration_content
            ),
            "termination_reason": self.termination_reason,
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
        for output_index, line in enumerate(self.business_lines, start=1):
            index = line.form_index if line.form_index > 0 else output_index
            values[f"business_line_{index}_name"] = line.name
            values[f"business_line_{index}_detail"] = line.detail
            values[f"business_line_{index}_code"] = line.code
            values[f"business_line_{index}_is_main"] = "X" if line.is_main else ""
        return values

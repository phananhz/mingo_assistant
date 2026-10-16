"""Typed, lossless state and migrations for business-amendment dossiers."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import re
from typing import Any, Mapping

from mingo_assistant.domains.business_registration.models import Address, SigningContext
from mingo_assistant.models.form_values import (
    format_form_date,
    normalize_form_values,
    parse_form_date,
)


AMENDMENT_SCHEMA_VERSION = 4
AMENDMENT_LINE_KINDS = ("add", "remove", "detail")
CHANGE_SELECTION_KEYS = (
    "change_name_selected",
    "change_address_selected",
    "change_capital_selected",
    "change_business_lines_selected",
    "change_tax_selected",
    "change_beneficial_selected",
    "change_members_selected",
    "change_supplemental_selected",
    "change_correction_selected",
)
AMENDMENT_LINE_KEY_PATTERN = re.compile(
    r"^amendment_line_(?:add|remove|detail)_(?:\d+_(?:name|detail|code|main|note)|row_count)$"
)


def _selected(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "x", "true", "yes", "có"}


def _schema_version(values: Mapping[str, str], explicit: int | None) -> int:
    if explicit is not None:
        return max(explicit, 0)
    try:
        return max(int(values.get("amendment_schema_version", 0) or 0), 0)
    except (TypeError, ValueError):
        return 0


def _compact_line_rows(values: Mapping[str, str]) -> dict[str, str]:
    """Compact only legacy industry rows, retaining every entered subfield."""

    result = normalize_form_values(values)
    for kind in AMENDMENT_LINE_KINDS:
        prefix = f"amendment_line_{kind}_"
        rows: dict[int, dict[str, str]] = {}
        for key, value in result.items():
            match = re.fullmatch(
                rf"{prefix}(\d+)_(name|detail|code|main|note)",
                key,
            )
            if match:
                rows.setdefault(int(match.group(1)), {})[match.group(2)] = value
        for key in tuple(result):
            if key.startswith(prefix):
                result.pop(key)
        entered = [
            row
            for _, row in sorted(rows.items())
            if any(str(value).strip() for value in row.values())
        ]
        for index, row in enumerate(entered, 1):
            for suffix, value in row.items():
                result[f"{prefix}{index}_{suffix}"] = value
        result[f"{prefix}row_count"] = str(len(entered))
    return result


def migrate_business_amendment_form_values(
    values: Mapping[Any, Any] | None,
    *,
    from_version: int | None = None,
) -> dict[str, str]:
    """Migrate one in-memory snapshot to v4 without mutating its source.

    Versions 0-3 used pre-created empty industry rows. Versions 0-2 could also
    store the share-capital choice under ``change_shares_selected``. Unknown
    keys deliberately survive so newer or dossier-specific fields stay intact.
    """

    source = normalize_form_values(values)
    version = _schema_version(source, from_version)
    migrated = dict(source)
    if version < AMENDMENT_SCHEMA_VERSION:
        migrated = _compact_line_rows(migrated)
    if version < 3 and _selected(migrated.get("change_shares_selected")):
        migrated["change_capital_selected"] = "X"
    migrated.pop("change_shares_selected", None)
    migrated["amendment_schema_version"] = str(AMENDMENT_SCHEMA_VERSION)
    return migrated


@dataclass(frozen=True)
class AmendmentLineChange:
    kind: str
    name: str = ""
    detail: str = ""
    code: str = ""
    is_main: bool = False
    note: str = ""

    def __post_init__(self) -> None:
        if self.kind not in AMENDMENT_LINE_KINDS:
            raise ValueError(f"Unsupported amendment line kind: {self.kind}")


@dataclass(frozen=True)
class AmendmentRepresentative:
    full_name: str = ""
    position: str = ""
    date_of_birth: date | None = None
    gender: str = ""
    nationality: str = ""
    identity_number: str = ""
    passport_number: str = ""
    issue_date: date | None = None
    issue_place: str = ""
    permanent_address: Address = field(default_factory=Address)
    contact_address: Address = field(default_factory=Address)


@dataclass(frozen=True)
class BusinessAmendmentCase:
    company_name: str = ""
    registration_number: str = ""
    representative: AmendmentRepresentative = field(
        default_factory=AmendmentRepresentative
    )
    signing: SigningContext = field(default_factory=SigningContext)
    selected_changes: frozenset[str] = frozenset()
    line_changes: tuple[AmendmentLineChange, ...] = ()
    legacy_form_values: Mapping[str, str] = field(default_factory=dict, repr=False)

    @classmethod
    def from_form_values(
        cls,
        values: Mapping[Any, Any] | None,
        *,
        from_version: int | None = None,
    ) -> "BusinessAmendmentCase":
        migrated = migrate_business_amendment_form_values(
            values,
            from_version=from_version,
        )
        line_changes: list[AmendmentLineChange] = []
        for kind in AMENDMENT_LINE_KINDS:
            indices = sorted({
                int(match.group(1))
                for key in migrated
                if (match := re.fullmatch(
                    rf"amendment_line_{kind}_(\d+)_(?:name|detail|code|main|note)",
                    key,
                ))
            })
            for index in indices:
                prefix = f"amendment_line_{kind}_{index}_"
                raw_name = migrated.get(prefix + "name", "")
                name, separator, embedded_detail = raw_name.partition("\n")
                detail = migrated.get(prefix + "detail", "")
                if not detail and separator:
                    detail = embedded_detail
                line_changes.append(AmendmentLineChange(
                    kind=kind,
                    name=name,
                    detail=detail,
                    code=migrated.get(prefix + "code", ""),
                    is_main=_selected(migrated.get(prefix + "main")),
                    note=migrated.get(prefix + "note", ""),
                ))
        return cls(
            company_name=migrated.get("parent_entity_name", ""),
            registration_number=migrated.get(
                "parent_entity_registration_number",
                "",
            ),
            representative=AmendmentRepresentative(
                full_name=migrated.get("legal_representative_full_name", ""),
                position=migrated.get("legal_representative_position", ""),
                date_of_birth=parse_form_date(
                    migrated.get("legal_representative_date_of_birth", "")
                ),
                gender=migrated.get("legal_representative_gender", ""),
                nationality=migrated.get("legal_representative_nationality", ""),
                identity_number=migrated.get("legal_representative_id_number", ""),
                passport_number=migrated.get(
                    "legal_representative_passport_number",
                    "",
                ),
                issue_date=parse_form_date(
                    migrated.get("legal_representative_issue_date", "")
                ),
                issue_place=migrated.get("legal_representative_issue_place", ""),
                permanent_address=Address(
                    full_text=migrated.get(
                        "legal_representative_permanent_address",
                        "",
                    )
                ),
                contact_address=Address(
                    full_text=migrated.get(
                        "legal_representative_contact_address",
                        "",
                    )
                ),
            ),
            signing=SigningContext(
                place=migrated.get("document_place", ""),
                day=migrated.get("document_day", ""),
                month=migrated.get("document_month", ""),
                year=migrated.get("document_year", ""),
                signer_full_name=migrated.get(
                    "signer_full_name",
                    migrated.get("legal_representative_full_name", ""),
                ),
            ),
            selected_changes=frozenset(
                key for key in CHANGE_SELECTION_KEYS if _selected(migrated.get(key))
            ),
            line_changes=tuple(line_changes),
            legacy_form_values=migrated,
        )

    def to_form_values(
        self,
        base: Mapping[Any, Any] | None = None,
    ) -> dict[str, str]:
        source = self.legacy_form_values if base is None else normalize_form_values(base)
        values = migrate_business_amendment_form_values(source)
        for key in tuple(values):
            if AMENDMENT_LINE_KEY_PATTERN.match(key):
                values.pop(key)
        for key in CHANGE_SELECTION_KEYS:
            values[key] = "X" if key in self.selected_changes else ""
        representative = self.representative
        values.update({
            "parent_entity_name": self.company_name,
            "parent_entity_registration_number": self.registration_number,
            "company_name": self.company_name,
            "legal_representative_full_name": representative.full_name,
            "legal_representative_position": representative.position,
            "legal_representative_date_of_birth": format_form_date(
                representative.date_of_birth
            ),
            "legal_representative_gender": representative.gender,
            "legal_representative_nationality": representative.nationality,
            "legal_representative_id_number": representative.identity_number,
            "legal_representative_passport_number": representative.passport_number,
            "legal_representative_issue_date": format_form_date(
                representative.issue_date
            ),
            "legal_representative_issue_place": representative.issue_place,
            "legal_representative_permanent_address": (
                representative.permanent_address.full_text
            ),
            "legal_representative_contact_address": (
                representative.contact_address.full_text
            ),
            "document_place": self.signing.place,
            "document_day": self.signing.day,
            "document_month": self.signing.month,
            "document_year": self.signing.year,
            "signer_full_name": self.signing.signer_full_name,
        })
        counts = {kind: 0 for kind in AMENDMENT_LINE_KINDS}
        for line in self.line_changes:
            counts[line.kind] += 1
            prefix = f"amendment_line_{line.kind}_{counts[line.kind]}_"
            values[prefix + "name"] = "\n".join(
                part for part in (line.name, line.detail) if part
            )
            values[prefix + "detail"] = line.detail
            values[prefix + "code"] = line.code
            if line.kind == "remove":
                values[prefix + "note"] = line.note
            else:
                values[prefix + "main"] = "X" if line.is_main else ""
        for kind, count in counts.items():
            values[f"amendment_line_{kind}_row_count"] = str(count)
        values["amendment_schema_version"] = str(AMENDMENT_SCHEMA_VERSION)
        return values

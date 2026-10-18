"""Typed, lossless state for household-business registration dossiers."""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Mapping

from mingo_assistant.models.form_values import normalize_form_values

HOUSEHOLD_BUSINESS_SCHEMA_VERSION = 1
MEMBER_KEY = re.compile(r"^household_member_(\d+)_(full_name|date_of_birth|id_number|gender|nationality|ethnicity|permanent_address|current_address)$")


@dataclass(frozen=True)
class HouseholdMember:
    full_name: str = ""
    date_of_birth: str = ""
    id_number: str = ""
    gender: str = ""
    nationality: str = ""
    ethnicity: str = ""
    permanent_address: str = ""
    current_address: str = ""


@dataclass(frozen=True)
class HouseholdBusinessCase:
    business_name: str = ""
    owner_name: str = ""
    subject_type: str = "individual"
    members: tuple[HouseholdMember, ...] = ()
    legacy_form_values: Mapping[str, str] = field(default_factory=dict, repr=False)

    @classmethod
    def from_form_values(cls, values: Mapping[Any, Any] | None) -> "HouseholdBusinessCase":
        source = normalize_form_values(values)
        rows: dict[int, dict[str, str]] = {}
        for key, value in source.items():
            match = MEMBER_KEY.fullmatch(key)
            if match:
                rows.setdefault(int(match.group(1)), {})[match.group(2)] = value
        members = tuple(HouseholdMember(**row) for _, row in sorted(rows.items()) if any(str(value).strip() for value in row.values()))
        return cls(
            business_name=source.get("household_business_name", ""),
            owner_name=source.get("household_owner_full_name", ""),
            subject_type=source.get("household_subject_type", "individual") or "individual",
            members=members,
            legacy_form_values=source,
        )

    def to_form_values(self, base: Mapping[Any, Any] | None = None) -> dict[str, str]:
        result = normalize_form_values(base if base is not None else self.legacy_form_values)
        for key in tuple(result):
            if MEMBER_KEY.fullmatch(key):
                result.pop(key)
        result.update({
            "household_schema_version": str(HOUSEHOLD_BUSINESS_SCHEMA_VERSION),
            "household_business_name": self.business_name,
            "household_owner_full_name": self.owner_name,
            "household_subject_type": self.subject_type,
        })
        for index, member in enumerate(self.members, 1):
            prefix = f"household_member_{index}_"
            for name in HouseholdMember.__dataclass_fields__:
                result[prefix + name] = str(getattr(member, name))
        result["household_member_row_count"] = str(len(self.members))
        return result

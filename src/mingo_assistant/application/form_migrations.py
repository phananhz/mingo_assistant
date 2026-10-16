"""Workflow-aware, in-memory migrations for persisted form snapshots."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from mingo_assistant.domains.business_amendment import (
    AMENDMENT_SCHEMA_VERSION,
    migrate_business_amendment_form_values,
)
from mingo_assistant.models.form_values import normalize_form_values


BUSINESS_AMENDMENT_CASE_TYPE = "Doanh nghiệp - Thay đổi nội dung ĐKDN"
REGISTRATION_CASE_TYPES = frozenset({
    "TNHH một thành viên",
    "TNHH hai thành viên (Cá nhân)",
    "TNHH hai thành viên trở lên",
    "TNHH hai thành viên trở lên (thành viên là cá nhân)",
})
DEPENDENT_UNIT_CASE_TYPES = frozenset({
    "Địa điểm kinh doanh - Lập mới",
    "Địa điểm kinh doanh - Thay đổi nội dung kinh doanh",
    "Địa điểm kinh doanh - Chấm dứt hoạt động",
})


@dataclass(frozen=True)
class FormMigrationResult:
    values: dict[str, str]
    version: int


def migrate_form_values(
    case_type: str,
    values: Mapping[Any, Any] | None,
    *,
    from_version: int = 0,
) -> FormMigrationResult:
    """Return a migrated copy for a known workflow without writing to disk."""

    version = max(int(from_version or 0), 0)
    if case_type == BUSINESS_AMENDMENT_CASE_TYPE:
        return FormMigrationResult(
            values=migrate_business_amendment_form_values(
                values,
                from_version=version,
            ),
            version=AMENDMENT_SCHEMA_VERSION,
        )
    if case_type in REGISTRATION_CASE_TYPES | DEPENDENT_UNIT_CASE_TYPES:
        return FormMigrationResult(
            values=normalize_form_values(values),
            version=1,
        )
    return FormMigrationResult(
        values=normalize_form_values(values),
        version=version,
    )

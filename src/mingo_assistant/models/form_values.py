"""Compatibility helpers for versioned, lossless form-value snapshots."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Mapping, Pattern, Sequence


LEGACY_FORM_SCHEMA_VERSION = 0


def parse_form_date(value: object) -> date | None:
    """Parse supported complete dates while leaving partial input to the base map."""

    text = str(value or "").strip()
    for pattern in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def format_form_date(value: date | None) -> str:
    return value.strftime("%d/%m/%Y") if value else ""

# These namespaces are rebuilt from the current registration workspace state.
# Removing only these known dynamic keys prevents deleted rows from returning,
# while unrelated legacy or future keys remain untouched.
BUSINESS_LINE_KEY_PATTERN = re.compile(r"^business_line_\d+_")

REGISTRATION_DYNAMIC_KEY_PATTERNS: tuple[Pattern[str], ...] = (
    BUSINESS_LINE_KEY_PATTERN,
    re.compile(r"^person_\d+_"),
    re.compile(r"^member_\d+_"),
    re.compile(r"^beneficial_owner_row_\d+_"),
    re.compile(r"^beneficial_owner_list_\d+_"),
)


def normalize_form_values(values: Mapping[Any, Any] | None) -> dict[str, str]:
    """Return the on-disk string map without discarding unknown keys."""

    return {
        str(key): str(value if value is not None else "")
        for key, value in (values or {}).items()
    }


def merge_form_values(
    original: Mapping[Any, Any] | None,
    current: Mapping[Any, Any] | None,
    *,
    replaced_key_patterns: Sequence[Pattern[str]] = (),
) -> dict[str, str]:
    """Overlay current UI state while retaining fields unknown to that UI.

    Known dynamic namespaces are removed before the overlay so deleting a row
    in the current UI also deletes its persisted keys. Every other unknown key
    survives an open/edit/save round trip.
    """

    merged = normalize_form_values(original)
    if replaced_key_patterns:
        for key in tuple(merged):
            if any(pattern.match(key) for pattern in replaced_key_patterns):
                merged.pop(key)
    merged.update(normalize_form_values(current))
    return merged

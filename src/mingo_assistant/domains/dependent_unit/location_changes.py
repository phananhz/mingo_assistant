"""Entered-data rules shared by the location-update form and Word exporter."""
from __future__ import annotations

import re
from typing import Mapping


UPDATE_LABOR_INPUT_KEY = "location_update_tax_labor_count_entered"
UPDATE_LEGACY_LABOR_KEY = "location_update_legacy_tax_labor_count"


def normalize_location_update_tax_values(values: Mapping[str, str]) -> dict[str, str]:
    """Do not treat the former creation default as a confirmed tax change.

    Old update dossiers did not record whether ``1`` came from the user or
    from the creation form. Retain that ambiguous value as metadata, but ask
    for explicit entry before using it again. Never mutate the saved input.
    This migration is only for the location-update workflow, not creation.
    """
    result = dict(values)
    labor = str(result.get("tax_labor_count", "") or "").strip()
    if labor == "1" and result.get(UPDATE_LABOR_INPUT_KEY) != "1":
        result.setdefault(UPDATE_LEGACY_LABOR_KEY, result["tax_labor_count"])
        result["tax_labor_count"] = ""
    return result


LOCATION_CHANGE_FIELDS: dict[str, tuple[str, ...]] = {
    "change_name_selected": (
        "new_location_business_name", "new_location_business_english_name", "new_location_business_short_name",
    ),
    "change_address_selected": (
        "new_location_address_detail", "new_location_ward", "new_location_province", "new_location_phone",
        "new_location_fax", "new_location_email", "new_location_website",
    ),
    "change_business_lines_selected": (),
    "change_manager_selected": (
        "location_manager_full_name", "location_manager_date_of_birth", "location_manager_gender",
        "location_manager_id_number", "location_manager_address_detail", "location_manager_ward",
        "location_manager_province", "location_manager_nationality", "location_manager_phone", "location_manager_email",
    ),
    "change_tax_selected": (
        "tax_accountant_full_name", "tax_accountant_date_of_birth", "tax_accountant_gender",
        "tax_accountant_id_number", "tax_accountant_phone", "tax_notification_address_detail",
        "tax_notification_ward", "tax_notification_province", "tax_notification_phone", "tax_notification_email",
        "tax_financial_year_start", "tax_financial_year_end", "tax_labor_count",
    ),
    "change_supplemental_selected": (
        "supplemental_registration_content", "supplemental_registration_content_1",
        "supplemental_registration_content_2", "supplemental_registration_content_3",
    ),
}


def location_change_has_data(section: str, values: Mapping[str, str]) -> bool:
    """Checkboxes open editors; only nonblank editable values keep sections."""
    if section == "change_business_lines_selected":
        return any(
            str(value or "").strip()
            for key, value in values.items()
            if re.fullmatch(r"business_line_\d+_(?:name|detail|code)", key)
        )
    return any(str(values.get(key, "") or "").strip() for key in LOCATION_CHANGE_FIELDS.get(section, ()))


def entered_location_changes(values: Mapping[str, str]) -> tuple[str, ...]:
    """Return supported sections in template order, excluding retired correction."""
    return tuple(section for section in LOCATION_CHANGE_FIELDS if location_change_has_data(section, values))

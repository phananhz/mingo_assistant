"""Serialize and restore business-amendment workspace state."""
from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from mingo_assistant.domains.business_amendment import AMENDMENT_SCHEMA_VERSION
from mingo_assistant.services.documents.business_amendment_generator import inferred_change_selections

if TYPE_CHECKING:
    from mingo_assistant.models.case import CaseSummary
    from mingo_assistant.ui.views.business_amendment_workspace import BusinessAmendmentWorkspace


class AmendmentFormState:
    """Keep case migration and form serialization outside widget construction."""

    SCHEMA_VERSION = str(AMENDMENT_SCHEMA_VERSION)

    def __init__(self, owner: "BusinessAmendmentWorkspace") -> None:
        self.owner = owner

    def restore(self, case: "CaseSummary | None") -> None:
        owner = self.owner
        today = datetime.now()
        values = {
            "document_day": f"{today.day:02d}",
            "document_month": f"{today.month:02d}",
            "document_year": str(today.year),
        }
        if case:
            values.update({
                "parent_entity_name": case.company_name,
                "legal_representative_full_name": case.owner,
            })
            values.update(owner._legacy_values)
            legacy_share_selected = values.get("change_shares_selected", "").lower() in {
                "1", "x", "true", "yes", "có",
            }
            if values.get("amendment_schema_version") not in {"3", self.SCHEMA_VERSION} and legacy_share_selected:
                values["change_capital_selected"] = "X"
            for selection in inferred_change_selections(values):
                values[selection] = "X"
        owner._ensure_amendment_line_rows(values)
        for key, value in values.items():
            owner._set_field(key, value)
        owner._refresh_capital_inputs()
        owner._refresh_share_inputs()
        owner._refresh_amendment_line_numbers()
        if not owner._field_value("document_place"):
            owner._sync_document_place_from_registration_office()
        owner._restore_people(values)
        try:
            restored = json.loads(values.get("amendment_selected_organization", "{}"))
            owner._selected_update_organization = dict(restored) if isinstance(restored, dict) else {}
        except (ValueError, TypeError):
            owner._selected_update_organization = {}
        owner._refresh_update_organization_selector()
        for key, form in owner.amendment_change_forms.items():
            form.setVisible(owner.fields[key].isChecked())

    def serialize(self) -> dict[str, str]:
        owner = self.owner
        values = dict(owner._legacy_values)
        values.update({key: owner._field_value(key) for key in owner.fields})
        for kind, table in owner.amendment_line_tables.items():
            prefix = f"amendment_line_{kind}_"
            for key in list(values):
                if key.startswith(prefix):
                    values.pop(key)
            for index, row in enumerate(table.snapshot_rows(), 1):
                for suffix, value in row.items():
                    values[f"{prefix}{index}_{suffix}"] = value
                values[f"{prefix}{index}_name"] = "\n".join(
                    part for part in (row.get("name", ""), row.get("detail", "")) if part
                )
            values[f"amendment_line_{kind}_row_count"] = str(table.rowCount())
        owner._store_people_values(values)
        values.pop("change_shares_selected", None)
        values["amendment_schema_version"] = self.SCHEMA_VERSION
        values["company_name"] = values.get("parent_entity_name", "")
        values["signer_full_name"] = values.get("legal_representative_full_name", "")
        values["amendment_representative_company_code"] = owner._representative_company_code
        values["amendment_selected_organization"] = json.dumps(
            owner._selected_update_organization,
            ensure_ascii=False,
        )
        values["document_place_date"] = (
            f"{values.get('document_place', '')}, "
            f"ngày {values.get('document_day', '')} "
            f"tháng {values.get('document_month', '')} "
            f"năm {values.get('document_year', '')}"
        ).lstrip(", ")
        return values

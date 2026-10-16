from __future__ import annotations

import unittest

from mingo_assistant.models.case import CaseSummary
from mingo_assistant.models.form_values import (
    LEGACY_FORM_SCHEMA_VERSION,
    REGISTRATION_DYNAMIC_KEY_PATTERNS,
    merge_form_values,
)


class FormValuesSchemaTest(unittest.TestCase):
    def test_legacy_case_defaults_to_unversioned_without_losing_unknown_values(self) -> None:
        case = CaseSummary.from_dict({
            "id": "legacy",
            "form_values": {"custom_old_field": "KEEP", "nullable_old_field": None},
        })

        self.assertEqual(LEGACY_FORM_SCHEMA_VERSION, case.form_schema_version)
        self.assertEqual("KEEP", case.form_values["custom_old_field"])
        self.assertEqual("", case.form_values["nullable_old_field"])

    def test_schema_version_survives_case_round_trip(self) -> None:
        case = CaseSummary.from_dict({
            "id": "versioned",
            "form_schema_version": "4",
            "form_values": {"amendment_schema_version": "4"},
        })

        restored = CaseSummary.from_dict(case.to_dict())

        self.assertEqual(4, restored.form_schema_version)
        self.assertEqual("4", restored.form_values["amendment_schema_version"])

    def test_overlay_preserves_unknown_keys_and_replaces_dynamic_namespaces(self) -> None:
        merged = merge_form_values(
            {
                "custom_old_field": "KEEP",
                "business_line_8_name": "OLD LINE",
                "person_3_name": "OLD PERSON",
            },
            {
                "company_name": "CÔNG TY TEST",
                "business_line_1_name": "CURRENT LINE",
            },
            replaced_key_patterns=REGISTRATION_DYNAMIC_KEY_PATTERNS,
        )

        self.assertEqual("KEEP", merged["custom_old_field"])
        self.assertEqual("CURRENT LINE", merged["business_line_1_name"])
        self.assertNotIn("business_line_8_name", merged)
        self.assertNotIn("person_3_name", merged)


if __name__ == "__main__":
    unittest.main()

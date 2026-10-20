from __future__ import annotations

from unittest import TestCase

from mingo_assistant.domains.dependent_unit.location_changes import (
    LOCATION_CHANGE_FIELDS, UPDATE_LABOR_INPUT_KEY, UPDATE_LEGACY_LABOR_KEY,
    entered_location_changes, location_change_has_data, normalize_location_update_tax_values,
)


class LocationChangeRulesTests(TestCase):
    def test_legacy_labor_default_is_not_a_tax_change_and_original_is_preserved(self):
        original = {"tax_labor_count": "1", "change_tax_selected": "X"}
        values = normalize_location_update_tax_values(original)
        self.assertEqual("", values["tax_labor_count"])
        self.assertEqual("1", values[UPDATE_LEGACY_LABOR_KEY])
        self.assertEqual((), entered_location_changes(values))
        self.assertEqual({"tax_labor_count": "1", "change_tax_selected": "X"}, original)
        self.assertEqual(values, normalize_location_update_tax_values(values))

    def test_confirmed_one_and_other_entered_labor_counts_are_preserved(self):
        for values in ({"tax_labor_count": "1", UPDATE_LABOR_INPUT_KEY: "1"},
                       {"tax_labor_count": "0"}, {"tax_labor_count": "25"}):
            with self.subTest(values=values):
                self.assertEqual(values, normalize_location_update_tax_values(values))

    def test_selection_and_noneditable_tax_symbols_are_not_entered_data(self):
        values = {section: "X" for section in LOCATION_CHANGE_FIELDS}
        values.update({"change_correction_selected": "X", "tax_accounting_dependent_x": "X",
                       "business_line_1_is_main": "X", "business_line_1_number": "1"})
        self.assertEqual((), entered_location_changes(values))

    def test_partial_data_keeps_a_collapsed_section(self):
        values = {"change_address_selected": "", "new_location_phone": "0901000001"}
        self.assertEqual(("change_address_selected",), entered_location_changes(values))
        self.assertTrue(location_change_has_data("change_address_selected", values))

    def test_zero_is_data_but_whitespace_is_not(self):
        self.assertTrue(location_change_has_data("change_tax_selected", {"tax_labor_count": "0"}))
        self.assertFalse(location_change_has_data("change_tax_selected", {"tax_labor_count": " \n\t"}))

    def test_business_lines_and_legacy_supplemental_values_are_supported(self):
        values = {"business_line_15_code": "6201", "supplemental_registration_content_2": "UPDATE"}
        self.assertEqual(
            ("change_business_lines_selected", "change_supplemental_selected"), entered_location_changes(values),
        )

from __future__ import annotations

from pathlib import Path
import unittest

from mingo_assistant.services.business_lines.industry_lookup import IndustryCatalog
from mingo_assistant.services.business_lines.legacy_industry_lookup import (
    LEGACY_INDUSTRY_LOOKUP_CASE_TYPES,
    dossier_can_use_legacy_industry_lookup,
    load_legacy_industry_catalog,
)
from mingo_assistant.ui.styles import stylesheet_for_theme


class LegacyIndustryLookupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]
        cls.legacy_catalog = load_legacy_industry_catalog(cls.project_root)
        cls.current_catalog = IndustryCatalog.load_from_project(cls.project_root)

    def test_legacy_catalog_contains_only_464_unique_level4_codes(self) -> None:
        rows = self.legacy_catalog.display_rows
        codes = [row.levels[3] for row in rows]

        self.assertTrue(self.legacy_catalog.is_available)
        self.assertEqual(len(rows), 464)
        self.assertEqual(len(codes), len(set(codes)))
        self.assertTrue(all(code.isdigit() and len(code) == 4 for code in codes))
        self.assertTrue(all(row.levels[:3] == ["", "", ""] for row in rows))
        self.assertTrue(all(row.levels[4] == "" for row in rows))

    def test_legacy_catalog_has_known_official_rows_and_search(self) -> None:
        by_code = {row.levels[3]: row for row in self.legacy_catalog.display_rows}

        self.assertEqual(by_code["0111"].name, "Trồng lúa")
        self.assertEqual(by_code["7222"].name, "Nghiên cứu khoa học và phát triển công nghệ trong lĩnh vực khoa học nhân văn")
        self.assertEqual(by_code["9900"].name, "Hoạt động của các tổ chức và cơ quan quốc tế")
        self.assertIn("7222", [row.levels[3] for row in self.legacy_catalog.filter_rows("nhân văn")])

    def test_current_and_legacy_catalogs_are_distinct_datasets(self) -> None:
        self.assertNotEqual(self.current_catalog.source_path, self.legacy_catalog.source_path)
        self.assertEqual(len(self.current_catalog.display_rows), 495)
        self.assertEqual(len(self.legacy_catalog.display_rows), 464)

    def test_no_dossier_is_allowed_to_use_legacy_catalog(self) -> None:
        self.assertEqual(LEGACY_INDUSTRY_LOOKUP_CASE_TYPES, frozenset())
        for case_type in (
            "tnhh_mot_thanh_vien",
            "tnhh_hai_thanh_vien",
            "co_phan",
            "business_amendment",
            "dependent_unit",
        ):
            self.assertFalse(dossier_can_use_legacy_industry_lookup(case_type))

    def test_legacy_table_selection_has_readable_contrast_in_supported_layouts(self) -> None:
        expected_colors = {
            "default": ("#d9ebff", "#0f172a"),
            "liquid_glass": ("#ebe8f8", "#243247"),
        }
        for layout, (background, text) in expected_colors.items():
            stylesheet = stylesheet_for_theme("rose", layout=layout)
            self.assertIn("QTableWidget#LegacyIndustryTable::item:selected", stylesheet)
            self.assertIn(f"background: {background}", stylesheet)
            self.assertIn(f"color: {text}", stylesheet)


if __name__ == "__main__":
    unittest.main()

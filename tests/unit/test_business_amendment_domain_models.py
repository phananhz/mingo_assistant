from __future__ import annotations

from dataclasses import replace
from datetime import date
import unittest

from mingo_assistant.application.form_migrations import migrate_form_values
from mingo_assistant.domains.business_amendment import (
    AmendmentLineChange,
    BusinessAmendmentCase,
    migrate_business_amendment_form_values,
)


class BusinessAmendmentDomainModelTest(unittest.TestCase):
    def test_v2_migration_compacts_rows_and_maps_share_selection_losslessly(self) -> None:
        source = {
            "amendment_schema_version": "2",
            "change_shares_selected": "X",
            "change_capital_selected": "",
            "amendment_line_add_1_name": "",
            "amendment_line_add_4_name": "Ngành thử nghiệm",
            "amendment_line_add_4_detail": "Chi tiết giữ nguyên",
            "amendment_line_add_4_code": "6201",
            "future_template_exception": "KEEP",
        }

        migrated = migrate_business_amendment_form_values(source)

        self.assertEqual("2", source["amendment_schema_version"])
        self.assertIn("change_shares_selected", source)
        self.assertEqual("4", migrated["amendment_schema_version"])
        self.assertEqual("X", migrated["change_capital_selected"])
        self.assertNotIn("change_shares_selected", migrated)
        self.assertEqual("Ngành thử nghiệm", migrated["amendment_line_add_1_name"])
        self.assertEqual("Chi tiết giữ nguyên", migrated["amendment_line_add_1_detail"])
        self.assertEqual("1", migrated["amendment_line_add_row_count"])
        self.assertEqual("KEEP", migrated["future_template_exception"])

    def test_typed_round_trip_preserves_passport_dates_lines_and_unknown_fields(self) -> None:
        values = {
            "amendment_schema_version": "3",
            "parent_entity_name": "CÔNG TY TNHH TEST",
            "parent_entity_registration_number": "0101234567",
            "legal_representative_full_name": "FOREIGN REPRESENTATIVE",
            "legal_representative_date_of_birth": "1990-02-03",
            "legal_representative_passport_number": "P1234567",
            "legal_representative_issue_date": "04-05-2025",
            "change_name_selected": "X",
            "change_business_lines_selected": "X",
            "amendment_line_add_2_name": "Lập trình máy vi tính\nChi tiết phần mềm",
            "amendment_line_add_2_code": "6201",
            "amendment_line_add_2_main": "X",
            "tax_custom_future_field": "KEEP",
        }

        dossier = BusinessAmendmentCase.from_form_values(values)
        restored = dossier.to_form_values()

        self.assertEqual(date(1990, 2, 3), dossier.representative.date_of_birth)
        self.assertEqual(date(2025, 5, 4), dossier.representative.issue_date)
        self.assertEqual("P1234567", dossier.representative.passport_number)
        self.assertEqual(1, len(dossier.line_changes))
        self.assertEqual("Chi tiết phần mềm", dossier.line_changes[0].detail)
        self.assertTrue(dossier.line_changes[0].is_main)
        self.assertEqual("03/02/1990", restored["legal_representative_date_of_birth"])
        self.assertEqual("04/05/2025", restored["legal_representative_issue_date"])
        self.assertEqual("X", restored["change_business_lines_selected"])
        self.assertEqual("Lập trình máy vi tính\nChi tiết phần mềm", restored["amendment_line_add_1_name"])
        self.assertEqual("KEEP", restored["tax_custom_future_field"])

    def test_typed_edit_replaces_owned_line_namespace_but_keeps_base_exceptions(self) -> None:
        dossier = BusinessAmendmentCase.from_form_values({
            "parent_entity_name": "TÊN CŨ",
            "change_business_lines_selected": "X",
            "amendment_line_remove_1_name": "Ngành cũ",
        })
        changed = replace(
            dossier,
            company_name="TÊN MỚI",
            line_changes=(
                AmendmentLineChange(
                    kind="detail",
                    name="Ngành được sửa",
                    detail="Nội dung sau sửa",
                    code="8299",
                ),
            ),
        )

        restored = changed.to_form_values(base={
            "amendment_schema_version": "4",
            "amendment_line_add_9_name": "Dòng đã xóa",
            "direct_non_yellow_mapping": "KEEP",
        })

        self.assertEqual("TÊN MỚI", restored["parent_entity_name"])
        self.assertNotIn("amendment_line_add_9_name", restored)
        self.assertEqual("Ngành được sửa\nNội dung sau sửa", restored["amendment_line_detail_1_name"])
        self.assertEqual("KEEP", restored["direct_non_yellow_mapping"])

    def test_registry_migrates_known_workflows_and_leaves_unknown_version_unchanged(self) -> None:
        registration = migrate_form_values(
            "TNHH một thành viên",
            {"company_name": "TEST", "future_key": 7},
            from_version=0,
        )
        amendment = migrate_form_values(
            "Doanh nghiệp - Thay đổi nội dung ĐKDN",
            {"change_shares_selected": "X"},
            from_version=0,
        )
        unknown = migrate_form_values(
            "Workflow tương lai",
            {"future_key": "KEEP"},
            from_version=7,
        )

        self.assertEqual(1, registration.version)
        self.assertEqual("7", registration.values["future_key"])
        self.assertEqual(4, amendment.version)
        self.assertEqual("X", amendment.values["change_capital_selected"])
        self.assertEqual(7, unknown.version)
        self.assertEqual({"future_key": "KEEP"}, unknown.values)


if __name__ == "__main__":
    unittest.main()

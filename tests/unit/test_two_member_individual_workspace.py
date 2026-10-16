from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit

from mingo_assistant.models.case import CaseSummary
from mingo_assistant.repositories.case_repository import CaseRepository
from mingo_assistant.services.documents.business_registration_variants import (
    TWO_MEMBER_INDIVIDUAL_CASE_TYPE,
    TWO_MEMBER_INDIVIDUAL_VARIANT,
)
from mingo_assistant.ui.views.business_registration_workspace import (
    BusinessRegistrationWorkspace,
    MEMBER_CAPITAL_SECTION_TITLE,
    MEMBER_SECTION_TITLE,
)


class TwoMemberIndividualWorkspaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_member_list_is_first_tab_and_syncs_first_member_for_file1(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = BusinessRegistrationWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
                template_variant=TWO_MEMBER_INDIVIDUAL_VARIANT,
            )
            try:
                self.assertEqual(MEMBER_SECTION_TITLE, next(iter(workspace.form_sections)))
                tabs = list(workspace.form_sections)
                capital_tab = "V\u1ed1n \u0111i\u1ec1u l\u1ec7 v\u00e0 v\u1ed1n g\u00f3p"
                self.assertEqual(MEMBER_CAPITAL_SECTION_TITLE, tabs[tabs.index(capital_tab) + 1])
                self.assertEqual(2, len(workspace.company_member_rows))
                self.assertNotIn("beneficial_owner_full_name", workspace.fields)
                workspace._set_field("member_1_full_name", "NGUY\u1ec4N V\u0102N M\u1eaaU")
                workspace._set_field("member_1_id_number", "001090000001")
                workspace._set_field("member_1_date_of_birth", "01/02/1990")
                workspace._set_field("member_1_gender", "Nam")
                workspace._set_field("member_1_permanent_address", "S\u1ed1 1 ph\u1ed1 M\u1eabu, H\u00e0 N\u1ed9i")
                workspace._set_field("member_2_full_name", "TR\u1ea6N TH\u1eca B\u00ccNH")
                workspace._set_field("member_2_id_number", "001091000002")
                values = workspace.form_values()
                self.assertEqual("2", values["member_count"])
                self.assertEqual("NGUY\u1ec4N V\u0102N M\u1eaaU", values["beneficial_owner_full_name"])
                self.assertEqual("001090000001", values["beneficial_owner_id_number"])
                workspace._set_field("charter_capital_number", "1.000.000")
                workspace._set_field("member_1_capital_amount", "400.000")
                self.app.processEvents()
                self.assertEqual("600.000", workspace._field_value("member_2_capital_amount"))
                self.assertEqual("40%", workspace._field_value("member_1_capital_ratio"))
                self.assertEqual("60%", workspace._field_value("member_2_capital_ratio"))
                self.assertEqual("Ti\u1ec1n m\u1eb7t", workspace._field_value("member_1_capital_asset_type"))
                workspace._set_field("member_1_capital_asset_type", "Quy\u1ec1n s\u1eed d\u1ee5ng tài s\u1ea3n")
                workspace._set_field("member_1_capital_deadline", "Hoàn thành trong 30 ngày")
                values = workspace.form_values()
                self.assertEqual("Quy\u1ec1n s\u1eed d\u1ee5ng tài s\u1ea3n", values["member_1_capital_asset_type"])
                self.assertEqual("Hoàn thành trong 30 ngày", values["member_1_capital_deadline"])
                workspace._show_next_company_member_row()
                self.assertEqual(3, len(workspace.company_member_rows))
            finally:
                workspace.deleteLater()

    def test_two_member_capital_and_beneficial_owners_restore_from_saved_form_values(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = BusinessRegistrationWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
                template_variant=TWO_MEMBER_INDIVIDUAL_VARIANT,
            )
            try:
                self.assertEqual("", workspace._field_value("charter_capital_number"))
                self.assertIsInstance(workspace.fields["legal_representative_position"], QLineEdit)
                self.assertEqual("", workspace._field_value("legal_representative_position"))

                workspace._set_field("legal_representative_position", "Ch\u1ee7 t\u1ecbch c\u00f4ng ty")
                workspace._set_field("charter_capital_number", "1.000.000")
                workspace._set_field("member_1_capital_amount", "400.000")
                workspace._set_field("member_1_capital_asset_type", "Quy\u1ec1n s\u1eed d\u1ee5ng t\u00e0i s\u1ea3n")
                workspace._set_field("member_1_capital_deadline", "Ho\u00e0n th\u00e0nh trong 30 ng\u00e0y")
                workspace._set_field("member_1_full_name", "NGUY\u1ec4N V\u0102N M\u1eaaU")
                workspace._set_field("member_1_id_number", "001090000001")
                workspace._set_field("member_2_full_name", "TR\u1ea6N TH\u1eca B\u00ccNH")
                workspace._set_field("member_2_id_number", "001091000002")
                self.app.processEvents()
                self.assertEqual("600.000", workspace._field_value("member_2_capital_amount"))

                owner_row = workspace.two_member_beneficial_owner_rows[0]
                owner_row.member_selector.setCurrentIndex(owner_row.member_selector.findData("member:1"))
                self.assertEqual("NGUY\u1ec4N V\u0102N M\u1eaaU", workspace._field_value("beneficial_owner_row_1_full_name"))
                self.assertEqual("", workspace._field_value("beneficial_owner_row_1_capital_total"))
                workspace._show_next_two_member_beneficial_owner_row([])
                self.assertEqual(2, len(workspace.two_member_beneficial_owner_rows))
                second_owner_row = workspace.two_member_beneficial_owner_rows[1]
                second_owner_row.member_selector.setCurrentIndex(second_owner_row.member_selector.findData("member:2"))
                workspace._set_field("beneficial_owner_row_2_related_group", "Nh\u00f3m li\u00ean quan")

                saved_case = workspace.build_case_summary()
            finally:
                workspace.deleteLater()

            reopened = BusinessRegistrationWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                case=saved_case,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
                template_variant=TWO_MEMBER_INDIVIDUAL_VARIANT,
            )
            try:
                self.assertEqual("1.000.000", reopened._field_value("charter_capital_number"))
                self.assertEqual("400.000", reopened._field_value("member_1_capital_amount"))
                self.assertEqual("600.000", reopened._field_value("member_2_capital_amount"))
                self.assertEqual("Quy\u1ec1n s\u1eed d\u1ee5ng t\u00e0i s\u1ea3n", reopened._field_value("member_1_capital_asset_type"))
                self.assertEqual("Ho\u00e0n th\u00e0nh trong 30 ng\u00e0y", reopened._field_value("member_1_capital_deadline"))
                self.assertEqual("Ch\u1ee7 t\u1ecbch c\u00f4ng ty", reopened._field_value("legal_representative_position"))
                self.assertEqual(2, len(reopened.two_member_beneficial_owner_rows))
                self.assertEqual("member:2", reopened.two_member_beneficial_owner_rows[1].member_selector.currentData())
                self.assertEqual("Nh\u00f3m li\u00ean quan", reopened._field_value("beneficial_owner_row_2_related_group"))
            finally:
                reopened.deleteLater()

    def test_existing_case_auto_saves_capital_and_member_contributions(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            initial = BusinessRegistrationWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
                template_variant=TWO_MEMBER_INDIVIDUAL_VARIANT,
            )
            try:
                initial_case = initial.build_case_summary()
            finally:
                initial.deleteLater()

            saved_cases = []
            editing = BusinessRegistrationWorkspace(
                on_back=lambda: None,
                on_save=saved_cases.append,
                case=initial_case,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
                template_variant=TWO_MEMBER_INDIVIDUAL_VARIANT,
            )
            try:
                editing._set_field("charter_capital_number", "1000000000")
                for index in range(2, 7):
                    editing._set_field(f"asset_contribution_{index}_amount", "0")
                editing._set_field("charter_capital_number", "2000000000")
                editing._set_field("member_1_capital_amount", "280000000")
                for _ in range(30):
                    if saved_cases:
                        break
                    QTest.qWait(100)
                self.assertTrue(saved_cases)
                saved_case = saved_cases[-1]
                self.assertEqual("2.000.000.000", saved_case.form_values["charter_capital_number"])
                self.assertEqual("280.000.000", saved_case.form_values["member_1_capital_amount"])
                self.assertEqual("1.720.000.000", saved_case.form_values["member_2_capital_amount"])
            finally:
                editing.deleteLater()

            repository = CaseRepository(Path(temp_dir) / "cases.json")
            repository.save_case(saved_case)
            persisted_case = repository.get_case(saved_case.id)
            self.assertIsNotNone(persisted_case)
            reopened = BusinessRegistrationWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                case=persisted_case,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
                template_variant=TWO_MEMBER_INDIVIDUAL_VARIANT,
            )
            try:
                self.assertEqual("2.000.000.000", reopened._field_value("charter_capital_number"))
                self.assertEqual("280.000.000", reopened._field_value("member_1_capital_amount"))
                self.assertEqual("1.720.000.000", reopened._field_value("member_2_capital_amount"))
            finally:
                reopened.deleteLater()

    def test_legacy_two_member_case_restores_its_capital_fields(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        legacy_case = CaseSummary(
            id="two-member-existing-case",
            company_name="CÔNG TY MẪU",
            case_type=TWO_MEMBER_INDIVIDUAL_CASE_TYPE,
            owner="",
            updated_at="15/09/2026",
            status="Đã tạo hồ sơ",
            condition="Đủ dữ liệu",
            members=2,
            capital="350.000.000",
            form_values={
                "charter_capital_number": "350.000.000",
                "member_1_full_name": "PHẠM THÀNH LONG",
                "member_1_capital_amount": "125.000.000",
                "member_1_capital_ratio": "35,71%",
                "member_2_full_name": "BÙI VĂN THẮNG",
                "member_2_capital_amount": "225.000.000",
                "member_2_capital_ratio": "64,29%",
                "custom_old_field": "KEEP OLD",
            },
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = BusinessRegistrationWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                case=legacy_case,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
            )
            try:
                self.assertEqual(TWO_MEMBER_INDIVIDUAL_VARIANT, workspace.template_variant)
                self.assertEqual("350.000.000", workspace._field_value("charter_capital_number"))
                self.assertEqual("125.000.000", workspace._field_value("member_1_capital_amount"))
                self.assertEqual("225.000.000", workspace._field_value("member_2_capital_amount"))
                migrated = workspace.build_case_summary()
                self.assertEqual(1, migrated.form_schema_version)
                self.assertEqual("KEEP OLD", migrated.form_values["custom_old_field"])
            finally:
                workspace.deleteLater()
    def test_legacy_workspace_has_no_member_list_tab(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = BusinessRegistrationWorkspace(
                on_back=lambda: None,
                on_save=lambda case: None,
                bundle_root=project_root,
                default_export_root=Path(temp_dir),
            )
            try:
                self.assertNotIn(MEMBER_SECTION_TITLE, workspace.form_sections)
                self.assertEqual([], workspace.company_member_rows)
                self.assertIn("beneficial_owner_full_name", workspace.fields)
            finally:
                workspace.deleteLater()


if __name__ == "__main__":
    unittest.main()

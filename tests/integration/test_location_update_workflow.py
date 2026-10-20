"""Persist and reopen an update dossier before exporting real Word templates."""
from __future__ import annotations

import hashlib
import os
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from docx import Document
from PySide6.QtWidgets import QApplication

from mingo_assistant.application.cases import CaseUseCases
from mingo_assistant.repositories.case_repository import CaseRepository
from mingo_assistant.services.documents.dependent_unit_generator import DependentUnitTemplateGenerator
from mingo_assistant.ui.views.location_business_update_workspace import LocationBusinessUpdateWorkspace


class LocationUpdateWorkflowIntegrationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_collapsed_populated_section_survives_disk_round_trip_and_exports(self):
        project = Path(__file__).resolve().parents[2]
        templates = project / "assets/templates/word/dependent_units/ddkd_update"
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in templates.iterdir() if p.is_file()}
        with TemporaryDirectory() as temporary, patch.dict(os.environ, {"APPDATA": temporary}):
            working = Path(temporary)
            cases = CaseUseCases(CaseRepository(working / "cases.json"))
            workspace = LocationBusinessUpdateWorkspace(
                on_back=lambda: None, on_save=cases.save, bundle_root=project, default_export_root=working,
            )
            try:
                workspace.fields["new_location_business_name"].setText("ĐỊA ĐIỂM KINH DOANH KIỂM THỬ")
                workspace.fields["change_name_selected"].setChecked(False)
                case = workspace.build_case_summary()
                cases.save(case)
            finally:
                workspace.close()
                workspace.deleteLater()
                self.app.processEvents()

            loaded = CaseUseCases(CaseRepository(working / "cases.json")).get(case.id)
            reopened = LocationBusinessUpdateWorkspace(
                on_back=lambda: None, on_save=cases.save, case=loaded,
                bundle_root=project, default_export_root=working,
            )
            try:
                self.assertFalse(reopened.fields["change_name_selected"].isChecked())
                self.assertFalse(reopened.change_option_indicators["change_name_selected"].isHidden())
                self.assertTrue(reopened.change_option_indicators["change_tax_selected"].isHidden())
                self.assertEqual("", reopened.fields["tax_labor_count"].text())
                generator = DependentUnitTemplateGenerator(templates, working)
                result = generator.generate(reopened.form_values(), "Integration", working / "export")
                notification = next(p.output_path for p in result.generated if p.source_name == "Thong bao thay doi.docx")
                text = "\n".join(p.text for p in generator._iter_paragraphs(Document(notification)))
                folded = generator._fold(text)
                self.assertIn("ĐỊA ĐIỂM KINH DOANH KIỂM THỬ", text)
                self.assertIn("dang ky thay doi ten dia diem kinh doanh", folded)
                # Keep empty children of the populated name block.
                self.assertIn("ten dia diem kinh doanh viet tat", folded)
                for heading in ("dang ky thay doi dia chi dia diem kinh doanh",
                                "dang ky thay doi thong tin dang ky thue", "de nghi hieu dinh"):
                    self.assertNotIn(heading, folded)
            finally:
                reopened.close()
                reopened.deleteLater()
                self.app.processEvents()
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in templates.iterdir() if p.is_file()}
        self.assertEqual(before, after)

    def test_old_saved_auto_labor_is_not_restored_or_exported_as_a_tax_change(self):
        project = Path(__file__).resolve().parents[2]
        templates = project / "assets/templates/word/dependent_units/ddkd_update"
        with TemporaryDirectory() as temporary, patch.dict(os.environ, {"APPDATA": temporary}):
            working = Path(temporary)
            options = dict(on_back=lambda: None, on_save=lambda case: None,
                           bundle_root=project, default_export_root=working)
            fresh = LocationBusinessUpdateWorkspace(**options)
            try:
                case = fresh.build_case_summary()
            finally:
                fresh.deleteLater()
            values = dict(case.form_values)
            values.pop("location_update_tax_labor_count_entered", None)
            values.update(tax_labor_count="1", new_location_phone="0901000001", change_tax_selected="X")
            repository = CaseRepository(working / "cases.json")
            cases = CaseUseCases(repository)
            cases.save(replace(case, form_values=values))
            reopened = LocationBusinessUpdateWorkspace(case=cases.get(case.id), **options)
            try:
                self.assertEqual("", reopened.fields["tax_labor_count"].text())
                self.assertTrue(reopened.change_option_indicators["change_tax_selected"].isHidden())
                generator = DependentUnitTemplateGenerator(templates, working)
                result = generator.generate(reopened.form_values(), "Legacy", working / "export")
                path = next(p.output_path for p in result.generated if p.source_name == "Thong bao thay doi.docx")
                folded = generator._fold("\n".join(p.text for p in generator._iter_paragraphs(Document(path))))
                self.assertIn("dang ky thay doi dia chi", folded)
                self.assertNotIn("dang ky thay doi thong tin dang ky thue", folded)
                cases.save(reopened.build_case_summary())
            finally:
                reopened.deleteLater()
                self.app.processEvents()
            saved = CaseUseCases(CaseRepository(working / "cases.json")).get(case.id)
            self.assertEqual("", saved.form_values["tax_labor_count"])
            self.assertEqual("1", saved.form_values["location_update_legacy_tax_labor_count"])

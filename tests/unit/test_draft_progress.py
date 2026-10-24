from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PySide6.QtGui import QCloseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from mingo_assistant.app.paths import AppPaths
from mingo_assistant.repositories.case_repository import CaseRepository
from mingo_assistant.ui.main_window import MainWindow
from mingo_assistant.ui.routing.workspace_registry import WORKSPACE_ROUTES, route_for_case_type
from mingo_assistant.ui.views.business_registration_workspace import BusinessRegistrationWorkspace
from mingo_assistant.ui.views.location_business_update_workspace import LocationBusinessUpdateWorkspace
from mingo_assistant.ui.views.draft_progress import PROGRESS_KEY, checkpoint_scan
from mingo_assistant.services.documents.business_registration_variants import TWO_MEMBER_INDIVIDUAL_VARIANT


ROOT = Path(__file__).resolve().parents[2]


class DraftProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = CaseRepository(self.root / "cases.json")
        self.repo._write_cases([])
        self.workspaces = []

    def tearDown(self):
        for w in self.workspaces:
            w.draft_progress.stop()
            w.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()

    def workspace(self, cls=BusinessRegistrationWorkspace, case=None, **kwargs):
        w = cls(
            on_back=lambda: None, on_save=self.repo.save_case, case=case,
            bundle_root=ROOT, default_export_root=self.root / "output", **kwargs,
        )
        w.enable_draft_progress()
        self.workspaces.append(w)
        return w

    def test_all_workflows_no_empty_draft_then_roundtrip_raw_edits_with_own_route(self):
        for route in WORKSPACE_ROUTES:
            with self.subTest(route=route.key):
                w = self.workspace(route.workspace_class)
                w.draft_progress.flush(force=True)
                self.assertIsNone(self.repo.get_case(w.case_id))
                # Merely opening optional sections is not entered dossier data.
                for key, widget in w.fields.items():
                    if key.startswith("change_") and key.endswith("_selected"):
                        widget.setChecked(True)
                w.draft_progress.flush()
                self.assertIsNone(self.repo.get_case(w.case_id))
                if route.key == "tax_template":
                    w.raw_ocr_text.setPlainText("Dữ liệu quét thử")
                    w.draft_progress.flush()
                    saved = self.repo.get_case(w.case_id)
                    self.assertIs(route_for_case_type(saved.case_type), route)
                    w.draft_progress.stop()
                    reopened = self.workspace(route.workspace_class, saved)
                    self.assertEqual("Dữ liệu quét thử", reopened.raw_ocr_text.toPlainText())
                    continue
                key = "company_phone" if "company_phone" in w.fields else "parent_entity_name"
                w._set_field(key, "090123")
                w.draft_progress.flush()
                saved = self.repo.get_case(w.case_id)
                self.assertEqual("Bản nháp", saved.status)
                self.assertIsNone(saved.warning)
                self.assertIs(route_for_case_type(saved.case_type), route)
                w.draft_progress.stop()
                reopened = self.workspace(route.workspace_class, saved)
                self.assertEqual("090123", reopened._field_value(key))
                self.assertEqual(saved.id, reopened.case_id)
                reopened._set_field(key, "090456")
                reopened.draft_progress.flush()
                self.assertEqual("090456", self.repo.get_case(saved.id).form_values[key])

    def test_two_member_draft_preserves_incomplete_ratio_input(self):
        w = self.workspace(template_variant=TWO_MEMBER_INDIVIDUAL_VARIANT)
        w.draft_progress.flush()
        self.assertIsNone(w.case)
        w._set_field("member_1_full_name", "THÀNH VIÊN A")
        w._set_field("charter_capital_number", "100000000")
        w._set_field("member_1_capital_ratio", "30")
        w.draft_progress.flush()
        saved = self.repo.get_case(w.case_id)
        w.draft_progress.stop()
        restored = self.workspace(case=saved)
        self.assertEqual(TWO_MEMBER_INDIVIDUAL_VARIANT, restored.template_variant)
        self.assertEqual("THÀNH VIÊN A", restored._field_value("member_1_full_name"))
        self.assertEqual(w._field_value("member_1_capital_ratio"), restored._field_value("member_1_capital_ratio"))

    def test_unconfirmed_cccd_erc_brc_edits_and_selected_person_survive(self):
        for document_type in ("cccd", "erc", "brc"):
            with self.subTest(document_type=document_type):
                w = self.workspace()
                person = w.ocr_people[0]
                person.front_path = str(self.root / f"{document_type}.pdf")
                person.back_path = str(self.root / "back.jpg")
                person.document_type = document_type
                person.recognition_type = "individual" if document_type == "cccd" else "organization"
                person.recognition_saved = False
                if document_type == "cccd":
                    person.data = {"legal_representative_full_name": "TÊN OCR SAI"}
                else:
                    person.organization_data = {"organization_owner_name": "TÊN OCR SAI"}
                w._refresh_selected_person_images()
                field = w.ocr_card_fields["legal_representative_full_name"] if document_type == "cccd" else w.organization_card_fields["organization_owner_name"]
                field.setText("ĐANG SỬA DỞ")
                w.raw_ocr_text.setPlainText("Nội dung đã nhận diện còn thiếu dấu")
                w.scan_document_type_input.setCurrentIndex(w.scan_document_type_input.findData(document_type))
                w._select_form_section(min(1, w.form_stack.count() - 1))
                w.draft_progress.flush()
                saved = self.repo.get_case(w.case_id)
                w.draft_progress.stop()
                restored = self.workspace(case=saved)
                person = restored.ocr_people[0]
                self.assertFalse(person.recognition_saved)
                self.assertEqual({}, person.saved_data)
                self.assertEqual({}, person.saved_organization_data)
                self.assertEqual([], restored.organization_profiles)
                data = person.data if document_type == "cccd" else person.organization_data
                key = "legal_representative_full_name" if document_type == "cccd" else "organization_owner_name"
                self.assertEqual("ĐANG SỬA DỞ", data[key])
                self.assertEqual("Nội dung đã nhận diện còn thiếu dấu", restored.raw_ocr_text.toPlainText())
                self.assertEqual(document_type, restored.scan_document_type_input.currentData())
                self.assertEqual(w.form_stack.currentIndex(), restored.form_stack.currentIndex())

    def test_running_scan_checkpoint_is_saved_before_scanner_and_restored_interrupted(self):
        w = self.workspace()
        w.ocr_people[0].front_path = str(self.root / "first.pdf")
        w.ocr_people[0].recognition_type = "organization"
        w.ocr_people[0].organization_data = {"organization_owner_name": "ĐÃ QUÉT ERC"}
        w._refresh_selected_person_images()
        w._add_ocr_person()
        w.ocr_people[1].front_path = str(self.root / "cccd.jpg")
        w.draft_progress.begin_scan(1)
        w._update_ocr_progress(42, "Đang đọc QR", "2 giây")
        # Read from a new repository while the original editor is still scanning.
        saved = CaseRepository(self.repo.data_file).get_case(w.case_id)
        state = json.loads(saved.form_values[PROGRESS_KEY])
        self.assertEqual("running", state["scans"]["1"]["state"])
        w.draft_progress.stop()  # deliberately no save/close callback
        restored = self.workspace(case=saved)
        self.assertEqual(1, restored.current_person_index)
        self.assertEqual("ĐÃ QUÉT ERC", restored.ocr_people[0].organization_data["organization_owner_name"])
        self.assertEqual("interrupted", restored.draft_progress.scans["1"]["state"])
        self.assertEqual(42, restored.ocr_progress.value())
        self.assertIn("gián đoạn", restored.ocr_status_label.text())
        self.assertEqual(str(self.root / "cccd.jpg"), restored.ocr_people[1].front_path)

    def test_checkpoint_decorator_saves_completion_and_unsaved_result(self):
        w = self.workspace()
        w.ocr_people[0].front_path = "cccd.jpg"

        @checkpoint_scan
        def scanner(owner):
            self.assertIsNotNone(self.repo.get_case(owner.case_id))
            owner._update_ocr_progress(100, "Đã quét", "1 giây")
            owner.ocr_people[0].recognition_type = "individual"
            owner._update_cccd_result_fields({"legal_representative_full_name": "KẾT QUẢ"})

        scanner(w)
        saved = self.repo.get_case(w.case_id)
        state = json.loads(saved.form_values[PROGRESS_KEY])
        self.assertEqual("complete", state["scans"]["0"]["state"])
        self.assertEqual("KẾT QUẢ", state["people"][0]["data"]["legal_representative_full_name"])
        self.assertFalse(state["people"][0]["recognition_saved"])

    def test_editing_signal_saves_without_manual_click_and_does_not_duplicate(self):
        w = self.workspace()
        w.fields["company_name"].setText("NHÁP TỰ LƯU")
        QTest.qWait(50)
        self.assertEqual("NHÁP TỰ LƯU", self.repo.get_case(w.case_id).company_name)
        w.fields["company_name"].setText("NHÁP TIẾP TỤC")
        QTest.qWait(50)
        self.assertEqual(1, len(self.repo.list_cases()))
        self.assertEqual("NHÁP TIẾP TỤC", self.repo.get_case(w.case_id).company_name)

    def test_export_metadata_preserved_on_edits_but_no_downgrade_after_success(self):
        w = self.workspace()
        w._set_field("company_name", "CÔNG TY TEST")
        w.draft_progress.flush()
        exported = replace(w.case, status="Đã tạo hồ sơ", export_dir="folder", exported_at="date", generated_documents=["a.docx"], export_versions=[{"name": "v1"}])
        self.repo.save_case(exported)
        w.case = exported
        w.draft_progress.accept_export()
        w.draft_progress.flush()
        self.assertEqual("Đã tạo hồ sơ", self.repo.get_case(w.case_id).status)
        w._set_field("company_phone", "012345")
        w.draft_progress.flush()
        saved = self.repo.get_case(w.case_id)
        self.assertEqual("Bản nháp", saved.status)
        self.assertEqual(exported.export_versions, saved.export_versions)
        self.assertEqual(exported.generated_documents, saved.generated_documents)
        self.assertEqual("folder", saved.export_dir)

    def test_write_failure_is_visible_and_retry_saves_same_case(self):
        w = self.workspace()
        w._set_field("company_name", "TEST")
        with patch.object(w.draft_progress, "save", side_effect=OSError("disk full")):
            with self.assertLogs("mingo_assistant.ui.views.draft_progress", level="ERROR"):
                w.draft_progress._safe_flush()
        self.assertIsNone(w.case)
        self.assertIn("Không thể", w.draft_progress.notice.text())
        w.draft_progress.flush()
        self.assertEqual(1, len(self.repo.list_cases()))

    def test_tax_labor_count_alone_is_data_but_section_and_engine_choices_are_not(self):
        w = self.workspace(LocationBusinessUpdateWorkspace)
        w.fields["change_tax_selected"].setChecked(True)
        w.scan_document_type_input.setCurrentIndex(2)
        w.draft_progress.flush()
        self.assertIsNone(w.case)
        w._set_field("tax_labor_count", "7")
        w.draft_progress.flush()
        saved = self.repo.get_case(w.case_id)
        self.assertEqual("7", saved.form_values["tax_labor_count"])
        w.draft_progress.stop()
        restored = self.workspace(LocationBusinessUpdateWorkspace, saved)
        self.assertEqual("7", restored._field_value("tax_labor_count"))
        self.assertTrue(restored.fields["change_tax_selected"].isChecked())
        self.assertFalse(restored.change_forms["change_tax_selected"].isHidden())

    def test_back_flushes_last_input_to_list_and_empty_editor_closes_without_draft(self):
        paths = AppPaths(ROOT, self.root / "navigation-data", self.root / "navigation-docs")
        window = MainWindow(app_paths=paths)
        try:
            window._open_case_workspace(None)
            empty = window.current_workspace
            with patch.object(window, "isVisible", return_value=True), patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
                event = QCloseEvent()
                window.closeEvent(event)
                self.assertTrue(event.isAccepted())
            self.assertIsNone(window.case_use_cases.get(empty.case_id))
            window._open_case_workspace(None)
            w = window.current_workspace
            w._set_field("company_name", "GÕ XONG BẤM QUAY LẠI NGAY")
            # Do not process queued autosave events before invoking Back.
            w.on_back()
            self.assertIs(window.business_page, window.stack.currentWidget())
            self.assertEqual("Bản nháp", window.case_use_cases.get(w.case_id).status)
            self.assertTrue(any(case.id == w.case_id for case in window.cases))
            self.assertFalse(w.draft_progress.timer.isActive())
            with patch.object(QMessageBox, "question") as ask:
                window.closeEvent(QCloseEvent())
                ask.assert_not_called()
        finally:
            window.current_workspace.draft_progress.stop()
            window.deleteLater()

    def test_close_save_failure_keeps_editor_open(self):
        paths = AppPaths(ROOT, self.root / "failure-data", self.root / "failure-docs")
        window = MainWindow(app_paths=paths)
        window._open_case_workspace(None)
        w = window.current_workspace
        try:
            w._set_field("company_name", "KHÔNG ĐƯỢC MẤT")
            with patch.object(window, "isVisible", return_value=True), \
                    patch.object(QMessageBox, "question", return_value=QMessageBox.Yes), \
                    patch.object(QMessageBox, "critical") as critical, \
                    patch.object(w.draft_progress, "save", side_effect=OSError("disk full")):
                event = QCloseEvent()
                window.closeEvent(event)
                self.assertFalse(event.isAccepted())
                critical.assert_called_once()
            self.assertTrue(w.draft_progress.timer.isActive())
            self.assertEqual("KHÔNG ĐƯỢC MẤT", w._field_value("company_name"))
        finally:
            w.draft_progress.stop()
            window.deleteLater()

    def test_close_confirmation_cancel_yes_and_no_empty_draft(self):
        paths = AppPaths(ROOT, self.root / "appdata", self.root / "docs")
        window = MainWindow(app_paths=paths)
        window._open_case_workspace(None)
        w = window.current_workspace
        try:
            with patch.object(window, "isVisible", return_value=True), patch.object(QMessageBox, "question", return_value=QMessageBox.No) as ask:
                event = QCloseEvent()
                window.closeEvent(event)
                self.assertFalse(event.isAccepted())
                ask.assert_called_once()
            self.assertIsNone(window.case_use_cases.get(w.case_id))
            w._set_field("company_name", "KHÔI PHỤC SAU THOÁT")
            with patch.object(window, "isVisible", return_value=True), patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
                event = QCloseEvent()
                window.closeEvent(event)
                self.assertTrue(event.isAccepted())
            saved = window.case_use_cases.get(w.case_id)
            self.assertEqual("Bản nháp", saved.status)
            self.assertEqual("KHÔI PHỤC SAU THOÁT", saved.company_name)
        finally:
            w.draft_progress.stop()
            window.deleteLater()


if __name__ == "__main__":
    unittest.main()

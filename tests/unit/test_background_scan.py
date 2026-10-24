from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication, QEvent, QThread, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget
from shiboken6 import isValid

from mingo_assistant.app.paths import AppPaths
from mingo_assistant.repositories.case_repository import CaseRepository
from mingo_assistant.services.organization_documents import DocumentTypeMismatchError
from mingo_assistant.services.organization_documents.organization_document_service import OrganizationDocumentResult
from mingo_assistant.services.qr.scanner import IdentityScanResult
from mingo_assistant.ui.main_window import MainWindow
from mingo_assistant.ui.views.business_registration_workspace import BusinessRegistrationWorkspace
from mingo_assistant.ui.views.business_amendment_workspace import BusinessAmendmentWorkspace
from mingo_assistant.ui.views.location_business_workspace import LocationBusinessWorkspace
from mingo_assistant.ui.views.draft_progress import PROGRESS_KEY


ROOT = Path(__file__).resolve().parents[2]


class BackgroundScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = CaseRepository(self.root / "cases.json")
        self.repo._write_cases([])
        self.widgets = []
        self.messages = [patch.object(QMessageBox, name, return_value=QMessageBox.Yes) for name in ("critical", "warning", "information", "question")]
        self.mocks = [message.start() for message in self.messages]

    def tearDown(self):
        for widget in self.widgets:
            if not isValid(widget):
                continue
            for thread in widget.findChildren(QThread):
                if thread.isRunning():
                    thread.requestInterruption()
                    self.until(lambda: not thread.isRunning())
            for timer in widget.findChildren(QTimer):
                timer.stop()
            widget.hide()
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        self.app.processEvents()
        for message in self.messages:
            message.stop()
        self.temp.cleanup()

    def until(self, predicate, timeout=4000):
        start = time.monotonic()
        while not predicate() and (time.monotonic() - start) * 1000 < timeout:
            QTest.qWait(10)
        self.assertTrue(predicate(), "Background job did not finish in time")

    def workspace(self, cls=BusinessRegistrationWorkspace):
        w = cls(on_back=lambda: None, on_save=self.repo.save_case, bundle_root=ROOT, default_export_root=self.root)
        w.enable_draft_progress()
        self.widgets.append(w)
        return w

    @staticmethod
    def result():
        return OrganizationDocumentResult({
            "organization_owner_name": "CÔNG TY TNHH KIỂM THỬ",
            "organization_owner_registration_number": "0312345678",
        }, "chữ nguồn OCR", "text")

    def test_scan_runs_off_gui_thread_and_does_not_confirm_profile(self):
        w = self.workspace()
        threads, calls, ticks = [], [], []
        def extract(path, progress_callback=None):
            calls.append(path)
            threads.append(QThread.currentThread())
            progress_callback(35, "Đang đọc")
            time.sleep(.15)
            return self.result()
        w.organization_document_service.extract_pdf = extract
        timer = QTimer(w)
        timer.timeout.connect(lambda: ticks.append(True))
        timer.start(10)
        w.ocr_people[0].front_path = "fixture.pdf"
        w._run_document_scan()
        self.assertIsNotNone(w._scan_thread)
        self.assertFalse(w.isEnabled())
        w._run_document_scan()  # ignores rapid double-click / reentrant calls
        self.until(lambda: w._scan_thread is None)
        self.assertEqual(1, len(calls))
        self.assertIsNot(threads[0], self.app.thread())
        self.assertGreater(len(ticks), 3)
        self.assertTrue(w.isEnabled())
        self.assertFalse(w.ocr_people[0].recognition_saved)
        saved = self.repo.get_case(w.case_id)
        state = json.loads(saved.form_values[PROGRESS_KEY])
        self.assertEqual("complete", state["scans"]["0"]["state"])
        self.assertEqual("CÔNG TY TNHH KIỂM THỬ", state["people"][0]["organization_data"]["organization_owner_name"])

    def test_amendment_background_result_keeps_review_metadata(self):
        w = self.workspace(BusinessAmendmentWorkspace)
        w.organization_document_service.extract_pdf = lambda *args, **kwargs: self.result()
        w.ocr_people[0].front_path = "fixture.pdf"
        w._run_document_scan()
        self.until(lambda: w._scan_thread is None)
        data = w.ocr_people[0].organization_data
        self.assertEqual("", data["amendment_recognition_confirmed"])
        self.assertEqual("fixture.pdf", data["amendment_source_pdf"])
        self.assertFalse(w.organization_review_checkbox.isChecked())

    def test_identity_background_scan_keeps_partial_edits_unconfirmed(self):
        w = self.workspace()
        w.ocr_people[0].front_path = "identity.jpg"
        w.scan_document_type_input.setCurrentIndex(w.scan_document_type_input.findData("cccd"))
        w.ocr_service.scan_identity = lambda *args, **kwargs: IdentityScanResult("031234567890|123456789|NGUYỄN VĂN TEST|01011990|Nam|Số 18 đường Tân Phú|01012025", "qr", "identity.jpg")
        w._run_document_scan()
        self.until(lambda: w._scan_thread is None)
        self.assertEqual("031234567890", w.ocr_people[0].data["legal_representative_id_number"])
        self.assertFalse(w.ocr_people[0].recognition_saved)

    def test_auto_certificate_photo_applies_correct_card_and_keeps_original_path(self):
        for cls, kind, values in (
            (BusinessRegistrationWorkspace, "erc", self.result().values),
            (LocationBusinessWorkspace, "brc", {"location_business_name": "ĐỊA ĐIỂM KIỂM THỬ", "location_business_code": "00012"}),
        ):
            w = self.workspace(cls)
            w.ocr_people[0].front_path = "photo.jpg"
            w.ocr_service.scan_qr = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("no QR"))
            result = OrganizationDocumentResult(values, "text", "ocr", document_type=kind)
            with patch("mingo_assistant.ui.views.business_registration.scan_worker.read_certificate", return_value=result):
                w._run_document_scan()
                self.until(lambda: w._scan_thread is None)
            person = w.ocr_people[0]
            self.assertEqual(kind, person.document_type)
            self.assertEqual("photo.jpg", person.front_path)
            self.assertFalse(person.recognition_saved)
            self.assertEqual(1, w.recognition_result_stack.currentIndex())
            self.assertEqual("complete", w.draft_progress.scans["0"]["state"])

    def test_errors_reenable_editor_and_preserve_preexisting_fields(self):
        for error in (RuntimeError("engine unavailable"), DocumentTypeMismatchError("Sai loại tài liệu")):
            w = self.workspace()
            w._set_field("company_name", "GIỮ DỮ LIỆU NHÁP")
            def extract(*args, **kwargs):
                raise error
            w.organization_document_service.extract_pdf = extract
            w.ocr_people[0].front_path = "fixture.pdf"
            w._run_document_scan()
            self.until(lambda: w._scan_thread is None)
            self.assertTrue(w.isEnabled())
            self.assertEqual("GIỮ DỮ LIỆU NHÁP", self.repo.get_case(w.case_id).company_name)
            self.assertEqual("interrupted", w.draft_progress.scans["0"]["state"])

    def test_confirmed_close_waits_for_cancellation_and_preserves_draft(self):
        window = MainWindow(app_paths=AppPaths(ROOT, self.root / "data", self.root / "docs"))
        self.widgets.append(window)
        window._open_case_workspace(None)
        w = window.current_workspace
        def extract(path, progress_callback=None):
            time.sleep(.10)
            progress_callback(45, "Đang đọc")
            return self.result()
        w.organization_document_service.extract_pdf = extract
        w.ocr_people[0].front_path = "fixture.pdf"
        w._run_document_scan()
        window.show()
        self.app.processEvents()
        event = QCloseEvent()
        window.closeEvent(event)
        self.assertFalse(event.isAccepted())
        self.assertTrue(window._close_requested)
        self.until(lambda: w._scan_thread is None and not window.isVisible())
        saved = window.case_use_cases.get(w.case_id)
        self.assertEqual("Bản nháp", saved.status)
        self.assertEqual("interrupted", json.loads(saved.form_values[PROGRESS_KEY])["scans"]["0"]["state"])

    def test_duplicate_deferred_close_callbacks_are_safe_after_native_window_is_deleted(self):
        window = MainWindow(app_paths=AppPaths(ROOT, self.root / "data", self.root / "docs"))
        self.widgets.append(window)
        window._finish_deferred_close()
        window._finish_deferred_close()
        self.assertTrue(window._deferred_close_scheduled)
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        self.assertFalse(isValid(window))
        with patch("sys.excepthook") as uncaught:
            window._complete_deferred_close()
            window._finish_deferred_close()
            window._release_retired_views()
            self.app.processEvents()
        uncaught.assert_not_called()

    def test_removed_workspace_stays_alive_until_job_exits_and_discards_stale_result(self):
        window = MainWindow(app_paths=AppPaths(ROOT, self.root / "data", self.root / "docs"))
        self.widgets.append(window)
        window._open_case_workspace(None)
        w = window.current_workspace
        def extract(path, progress_callback=None):
            time.sleep(.10)
            progress_callback(45, "Đang đọc")
            return self.result()
        w.organization_document_service.extract_pdf = extract
        w.ocr_people[0].front_path = "fixture.pdf"
        w._run_document_scan()
        window._show_transient_view("current_documents_view", QWidget())
        self.assertTrue(isValid(w))
        self.until(lambda: not isValid(w))
        self.assertIsNone(window.current_workspace)
        saved = window.case_use_cases.get(w.case_id)
        self.assertEqual("", json.loads(saved.form_values[PROGRESS_KEY])["people"][0]["recognition_type"])

    def test_export_thread_is_not_destroyed_when_its_view_is_removed(self):
        window = MainWindow(app_paths=AppPaths(ROOT, self.root / "data", self.root / "docs"))
        self.widgets.append(window)
        window._open_case_workspace(None)
        w = window.current_workspace
        worker_threads = []
        class SlowGenerator:
            def __init__(self, **kwargs):
                pass
            def validate_templates(self, values):
                return []
            def generate(self, *args, **kwargs):
                worker_threads.append(QThread.currentThread())
                time.sleep(.1)
                raise RuntimeError("Synthetic export failure")
        w._validation_issues = lambda values: []
        w._document_generator_class = lambda: SlowGenerator
        w._set_field("company_name", "HỒ SƠ KIỂM THỬ TÁC VỤ WORD")
        w._export_documents()
        self.assertIsNotNone(w._export_thread)
        window._show_transient_view("current_documents_view", QWidget())
        self.assertTrue(isValid(w))
        self.until(lambda: not isValid(w))
        self.assertEqual(1, len(worker_threads))
        self.assertIsNot(worker_threads[0], self.app.thread())

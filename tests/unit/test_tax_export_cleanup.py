from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from mingo_assistant.application.registration import RegistrationExportPlanner
from mingo_assistant.services.documents.document_file_access import ensure_documents_closed
from mingo_assistant.ui.views.tax_commitment_workspace import TaxCommitmentWorkspace


CHECKER = "mingo_assistant.ui.views.tax_commitment_workspace.ensure_documents_closed"


class TaxExportCleanupTests(TestCase):
    @staticmethod
    def holder():
        return SimpleNamespace(
            export_planner=RegistrationExportPlanner(),
            _version_word_files=TaxCommitmentWorkspace._version_word_files,
        )

    def test_checks_old_word_files_before_deleting_only_this_cases_old_version(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            case_root = root / "case-a"
            old = case_root / "bản 1" / "company"
            latest = case_root / "bản 2" / "company"
            other = root / "case-b" / "bản 1"
            notes = case_root / "notes"
            for folder in (old, latest, other, notes):
                folder.mkdir(parents=True)
            old_doc = old / "Commitment.docx"
            old_doc.write_bytes(b"old")
            (old / "~$Commitment.docx").write_bytes(b"lock")
            new_doc = latest / "Commitment.docx"
            new_doc.write_bytes(b"new")
            other_doc = other / "Commitment.docx"
            other_doc.write_bytes(b"other")
            holder = self.holder()

            def check(files):
                self.assertEqual([old_doc], files)
                self.assertTrue(old_doc.exists())
                self.assertEqual(b"new", new_doc.read_bytes())

            with patch(CHECKER, side_effect=check) as checker:
                failures = TaxCommitmentWorkspace._remove_previous_export_versions(
                    holder, case_root, latest
                )
            checker.assert_called_once()
            self.assertEqual([], failures)
            self.assertFalse(old.parent.exists())
            self.assertEqual(b"new", new_doc.read_bytes())
            self.assertEqual(b"other", other_doc.read_bytes())
            self.assertTrue(notes.exists())

    def test_open_file_preserves_entire_old_version_and_new_export(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "bản 1"
            latest = root / "bản 2"
            old.mkdir()
            latest.mkdir()
            old_doc = old / "Commitment.docx"
            new_doc = latest / "Commitment.docx"
            old_doc.write_bytes(b"old")
            new_doc.write_bytes(b"new")
            holder = self.holder()
            with patch(CHECKER, side_effect=OSError("Word file is open")):
                failures = TaxCommitmentWorkspace._remove_previous_export_versions(
                    holder, root, latest
                )
            self.assertEqual([old], failures)
            self.assertEqual(b"old", old_doc.read_bytes())
            self.assertEqual(b"new", new_doc.read_bytes())

    def test_export_outside_case_root_does_not_close_or_delete_anything(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "case-a" / "bản 1"
            old.mkdir(parents=True)
            holder = self.holder()
            with patch(CHECKER) as checker:
                failures = TaxCommitmentWorkspace._remove_previous_export_versions(
                    holder, root / "case-a", root / "case-b" / "bản 2"
                )
            checker.assert_not_called()
            self.assertEqual([], failures)
            self.assertTrue(old.exists())

    def test_open_old_file_stops_export_before_generation_and_asks_user_to_close(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "bản 1"
            old.mkdir()
            (old / "Commitment.docx").write_bytes(b"old")
            holder = self.holder()
            holder._export_thread = None
            holder.form_values = lambda: {}
            holder._validation_issues = lambda values: []
            holder._template_and_export_dirs = lambda: (root, root)
            holder._case_export_dir = lambda export_root, values: root
            with patch(CHECKER, side_effect=OSError("Please close this Word file")), \
                    patch("mingo_assistant.ui.views.tax_commitment_workspace.QMessageBox.warning") as warning, \
                    patch("mingo_assistant.ui.views.business_registration_workspace.BusinessRegistrationWorkspace._export_documents") as export:
                TaxCommitmentWorkspace._export_documents(holder)
            warning.assert_called_once()
            export.assert_not_called()
            self.assertTrue((old / "Commitment.docx").exists())
        app.processEvents()

    def test_real_windows_open_handle_blocks_export_without_changing_file(self):
        import ctypes
        import sys
        from ctypes import wintypes

        if sys.platform != "win32":
            self.skipTest("Windows file sharing check")
        with TemporaryDirectory() as directory:
            file = Path(directory) / "Commitment.docx"
            file.write_bytes(b"important content")
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            create = kernel.CreateFileW
            create.argtypes = (
                wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
            )
            create.restype = wintypes.HANDLE
            close = kernel.CloseHandle
            close.argtypes = (wintypes.HANDLE,)
            close.restype = wintypes.BOOL
            handle = create(str(file), 0x80000000, 1, None, 3, 0x80, None)
            self.assertNotEqual(ctypes.c_void_p(-1).value, handle)
            try:
                with self.assertRaisesRegex(OSError, "Word"):
                    ensure_documents_closed([file])
                self.assertEqual(b"important content", file.read_bytes())
            finally:
                close(handle)
            ensure_documents_closed([file])
            self.assertEqual(b"important content", file.read_bytes())

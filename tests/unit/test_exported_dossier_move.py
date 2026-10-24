from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch
import json
import base64
import shutil
import subprocess

from PySide6.QtWidgets import QApplication

from mingo_assistant.models.case import CaseSummary
from mingo_assistant.repositories.case_repository import CaseRepository
from mingo_assistant.services.documents.exported_dossier_move import move_exported_dossier
from mingo_assistant.services.documents.open_document_closer import close_open_documents
from mingo_assistant.ui.views.business_registration_documents import BusinessRegistrationDocumentsView


UI = "mingo_assistant.ui.views.business_registration_documents"
SERVICE = "mingo_assistant.services.documents.exported_dossier_move"
CLOSER = "mingo_assistant.services.documents.open_document_closer"


class ExportedDossierMoveTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.destination = self.root / "destination"
        self.destination.mkdir()
        self.versions = []
        for index in (1, 2):
            folder = self.root / "original" / f"bản {index}"
            folder.mkdir(parents=True)
            (folder / "Notice.docx").write_bytes(f"version-{index}".encode())
            (folder / "Authorization.docx").write_bytes(f"authorization-{index}".encode())
            self.versions.append({"name": f"bản {index}", "export_dir": str(folder),
                                  "documents": ["Notice.docx", "Authorization.docx"]})
        self.case = CaseSummary(
            id="move-test", company_name="Company", case_type="Other workflow", owner="", updated_at="",
            status="Đã tạo hồ sơ", condition="", members=1, capital="",
            export_dir=str(self.root / "original"), export_versions=self.versions,
        )
        self.repository = CaseRepository(self.root / "cases.json")
        self.repository.save_case(self.case)
        self.view = None
        self.closer_patch = patch(f"{SERVICE}.close_open_documents")
        self.closer = self.closer_patch.start()

    def tearDown(self):
        self.closer_patch.stop()
        if self.view:
            self.view.close()
            self.view.deleteLater()
            self.app.processEvents()
        self.temporary.cleanup()

    def make_view(self, on_save=None):
        self.view = BusinessRegistrationDocumentsView(
            self.case, lambda: None, lambda: None, on_save=on_save or self.repository.save_case,
        )
        return self.view

    def perform_move(self):
        with patch(f"{UI}.QFileDialog.getExistingDirectory", return_value=str(self.destination)), \
                patch(f"{UI}.QMessageBox.information") as information:
            self.view.move_button.click()
        information.assert_called_once()

    def test_move_selected_history_version_preserves_other_versions_and_default_settings(self):
        settings = self.root / "settings.json"
        settings.write_text('{"default_export_root": "unchanged"}', encoding="utf-8")
        original_settings = settings.read_bytes()
        latest_before = deepcopy(self.versions[1])
        view = self.make_view()
        view.version_button_group.button(1).setChecked(True)
        source = Path(self.versions[0]["export_dir"])
        (source / "Notice.docx").write_bytes(b"edited-in-Word-after-export")
        self.perform_move()
        target = self.destination / "Company - bản 1"
        self.assertEqual({"Notice.docx", "Authorization.docx"}, {p.name for p in target.iterdir()})
        self.assertEqual(b"edited-in-Word-after-export", (target / "Notice.docx").read_bytes())
        self.assertEqual([], list(source.glob("*.docx")))
        saved = self.repository.get_case(self.case.id)
        self.assertEqual(self.case.export_dir, saved.export_dir)
        self.assertEqual(latest_before, saved.export_versions[1])
        self.assertEqual(str(target), saved.export_versions[0]["export_dir"])
        self.assertEqual(original_settings, settings.read_bytes())
        self.assertEqual(1, view.version_button_group.checkedId())
        self.assertEqual(target, view.displayed_versions[0]["files"][0].parent)
        self.closer.assert_called_once()

    def test_latest_only_moves_without_version_selector_and_reopens_from_new_path(self):
        self.case = replace(self.case, case_type="TNHH một thành viên")
        self.repository.save_case(self.case)
        view = self.make_view()
        self.assertEqual(-1, view.version_button_group.checkedId())
        self.perform_move()
        target = self.destination / "Company - bản 2"
        self.assertEqual(b"version-2", (target / "Notice.docx").read_bytes())
        self.assertFalse((Path(self.versions[1]["export_dir"]) / "Notice.docx").exists())
        saved = self.repository.get_case(self.case.id)
        self.assertEqual(str(target), saved.export_dir)
        self.assertEqual(["Notice.docx", "Authorization.docx"], saved.generated_documents)
        with patch(f"{UI}.QDesktopServices.openUrl") as opener:
            view._open_export_folder()
        self.assertEqual(target, Path(opener.call_args.args[0].toLocalFile()))
        reopened = BusinessRegistrationDocumentsView(saved, lambda: None, lambda: None, on_save=self.repository.save_case)
        self.assertEqual(target, reopened.displayed_versions[0]["files"][0].parent)
        reopened.deleteLater()

    def test_legacy_case_without_version_metadata_is_relocated_and_persisted(self):
        folder = Path(self.versions[0]["export_dir"])
        self.case = replace(self.case, export_dir=str(folder), export_versions=[], generated_documents=["Notice.docx", "Authorization.docx"])
        self.repository.save_case(self.case)
        self.make_view()
        self.perform_move()
        saved = self.repository.get_case(self.case.id)
        self.assertEqual(1, len(saved.export_versions))
        self.assertTrue(all(path.is_file() for path in self.view.displayed_versions[0]["files"]))
        self.assertFalse((folder / "Notice.docx").exists())

    def test_cancel_never_closes_documents_or_moves_files(self):
        view = self.make_view()
        with patch(f"{UI}.QFileDialog.getExistingDirectory", return_value=""), \
                patch(f"{UI}.QMessageBox.information") as information:
            view.move_button.click()
        self.assertEqual([], list(self.destination.iterdir()))
        self.closer.assert_not_called()
        information.assert_not_called()

    def test_existing_destination_is_not_overwritten(self):
        occupied = self.destination / "Company"
        occupied.mkdir()
        (occupied / "Notice.docx").write_bytes(b"keep")
        files = list(Path(self.versions[0]["export_dir"]).glob("*.docx"))
        target = move_exported_dossier(files, self.destination, "Company", lambda path: None)
        self.assertEqual("Company (2)", target.name)
        self.assertEqual(b"keep", (occupied / "Notice.docx").read_bytes())
        self.assertTrue(all(not file.exists() for file in files))

    def test_save_failure_rolls_back_files_and_keeps_the_old_case(self):
        view = self.make_view(on_save=Mock(side_effect=OSError("cannot save metadata")))
        before = self.repository.get_case(self.case.id).to_dict()
        with patch(f"{UI}.QFileDialog.getExistingDirectory", return_value=str(self.destination)), \
                patch(f"{UI}.QMessageBox.warning") as warning:
            view.move_button.click()
        warning.assert_called_once()
        self.assertEqual([], list(self.destination.iterdir()))
        self.assertEqual(before, self.repository.get_case(self.case.id).to_dict())
        self.assertEqual(before, view.case.to_dict())
        self.assertTrue(all(path.is_file() for path in view.displayed_versions[-1]["files"]))

    def test_move_failure_rolls_back_previous_files_and_never_commits(self):
        files = list(Path(self.versions[0]["export_dir"]).glob("*.docx"))
        actual_move = shutil.move
        commit = Mock()
        calls = 0
        def fail_second(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise PermissionError("file locked")
            return actual_move(source, target)
        with patch(f"{SERVICE}.shutil.move", side_effect=fail_second):
            with self.assertRaises(PermissionError):
                move_exported_dossier(files, self.destination, "Company", commit)
        commit.assert_not_called()
        self.assertTrue(all(path.is_file() for path in files))
        self.assertEqual([], list(self.destination.iterdir()))

    def test_cross_volume_partial_copy_failure_removes_partial_target_only(self):
        files = list(Path(self.versions[0]["export_dir"]).glob("*.docx"))
        def fail_copy(source, target):
            Path(target).write_bytes(b"partial")
            raise OSError("disk full")
        with patch(f"{SERVICE}.shutil.move", side_effect=fail_copy):
            with self.assertRaises(OSError):
                move_exported_dossier(files, self.destination, "Company", Mock())
        self.assertTrue(all(path.is_file() for path in files))
        self.assertEqual([], list(self.destination.iterdir()))

    def test_close_failure_leaves_files_and_paths_untouched(self):
        self.closer.side_effect = OSError("cannot save open document")
        files = list(Path(self.versions[0]["export_dir"]).glob("*.docx"))
        with self.assertRaises(OSError):
            move_exported_dossier(files, self.destination, "Company", Mock())
        self.assertTrue(all(path.is_file() for path in files))
        self.assertEqual([], list(self.destination.iterdir()))

    def test_missing_displayed_file_aborts_before_closing_or_moving(self):
        view = self.make_view()
        (Path(self.versions[1]["export_dir"]) / "Notice.docx").unlink()
        with patch(f"{UI}.QFileDialog.getExistingDirectory", return_value=str(self.destination)), \
                patch(f"{UI}.QMessageBox.warning") as warning:
            view.move_button.click()
        warning.assert_called_once()
        self.closer.assert_not_called()
        self.assertEqual([], list(self.destination.iterdir()))

    def test_empty_view_disables_move_and_does_not_open_picker(self):
        self.case = replace(self.case, export_dir="", export_versions=[])
        view = self.make_view()
        self.assertFalse(view.move_button.isEnabled())
        with patch(f"{UI}.QFileDialog.getExistingDirectory") as picker, patch(f"{UI}.QMessageBox.warning"):
            view._move_selected_version()
        picker.assert_not_called()

    def test_duplicate_names_are_rejected_before_moving(self):
        files = [Path(version["export_dir"]) / "Notice.docx" for version in self.versions]
        with self.assertRaises(ValueError):
            move_exported_dossier(files, self.destination, "Company", Mock())
        self.closer.assert_not_called()

    def test_document_closer_saves_before_move_and_unrelated_source_files_stay(self):
        folder = Path(self.versions[0]["export_dir"])
        selected = folder / "Notice.docx"
        other = folder / "Authorization.docx"
        def close_and_save(files):
            self.assertEqual([selected], files)
            selected.write_bytes(b"saved-before-close")
        self.closer.side_effect = close_and_save
        target = move_exported_dossier([selected], self.destination, "Selected", Mock())
        self.assertEqual(b"saved-before-close", (target / selected.name).read_bytes())
        self.assertFalse(selected.exists())
        self.assertTrue(other.is_file())


class OpenDocumentCloserTests(TestCase):
    def test_only_explicit_paths_are_sent_to_hidden_office_closer(self):
        files = [Path("tmp/only-this.docx")]
        with patch(f"{CLOSER}.sys.platform", "win32"), \
                patch(f"{CLOSER}.subprocess.run", return_value=Mock(returncode=0)) as run:
            close_open_documents(files)
        self.assertEqual([str(files[0].resolve())], json.loads(run.call_args.kwargs["input"]))
        self.assertEqual(0x08000000, run.call_args.kwargs["creationflags"])
        self.assertEqual(30, run.call_args.kwargs["timeout"])
        script = base64.b64decode(run.call_args.args[0][-1]).decode("utf-16-le")
        self.assertIn("$targets.Contains", script)
        self.assertNotIn("Stop-Process", script)
        self.assertNotIn(".Quit(", script)
        self.assertNotIn("taskkill", script)

    def test_office_failure_and_timeout_are_reported_before_move(self):
        with patch(f"{CLOSER}.sys.platform", "win32"), \
                patch(f"{CLOSER}.subprocess.run", return_value=Mock(returncode=1, stderr="read only")):
            with self.assertRaises(OSError):
                close_open_documents([Path("test.docx")])
        with patch(f"{CLOSER}.sys.platform", "win32"), \
                patch(f"{CLOSER}.subprocess.run", side_effect=subprocess.TimeoutExpired("office", 30)):
            with self.assertRaises(OSError):
                close_open_documents([Path("test.docx")])

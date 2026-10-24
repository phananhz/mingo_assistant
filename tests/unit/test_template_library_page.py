from pathlib import Path
from unittest import TestCase, skipUnless
from unittest.mock import patch
from tempfile import TemporaryDirectory
import shutil

from PySide6.QtWidgets import QApplication, QBoxLayout

from mingo_assistant.ui.styles import stylesheet_for_theme
from mingo_assistant.ui.views.template_library_catalog import TEMPLATE_GROUPS
from mingo_assistant.ui.views.template_library_page import TemplateLibraryPage


SOURCE_ROOT = Path(__file__).resolve().parents[2] / "TemplatesBefore/8. Biểu mẫu/8. Biểu mẫu"


class TemplateLibraryPageTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.page = TemplateLibraryPage()

    def tearDown(self):
        self.page.close()
        self.page.deleteLater()
        self.app.processEvents()

    def test_catalog_counts_formats_and_unique_ids(self):
        self.assertEqual(["dkdn", "tax"], [group.id for group in TEMPLATE_GROUPS])
        self.assertEqual([7, 10], [len(group.items) for group in TEMPLATE_GROUPS])
        items = [item for group in TEMPLATE_GROUPS for item in group.items]
        self.assertEqual(17, len({item.id for item in items}))
        self.assertEqual(2, sum(item.format_label == "DOC" for item in items))

    def test_dkdn_download_preserves_original_bytes_and_cancel_does_nothing(self):
        template = self.page.selected_template
        source = self.page.files.source(template.id)
        original = source.read_bytes()
        with TemporaryDirectory() as directory:
            target = Path(directory) / template.filename
            with patch("mingo_assistant.ui.views.template_library_page.QFileDialog.getSaveFileName", return_value=(str(target), "")), patch("mingo_assistant.ui.views.template_library_page.QMessageBox.information"):
                self.page.download_button.click()
            self.assertEqual(original, target.read_bytes())
        self.assertEqual(original, source.read_bytes())
        with patch("mingo_assistant.ui.views.template_library_page.QFileDialog.getSaveFileName", return_value=("", "")), patch.object(self.page.files, "download") as download:
            self.page.download_button.click()
            download.assert_not_called()

    def test_preview_opens_isolated_copy_and_tax_download_is_unavailable(self):
        source = self.page.files.source(self.page.selected_template.id)
        with patch("mingo_assistant.ui.views.template_library_page.QDesktopServices.openUrl", return_value=True) as opener:
            self.page.preview_button.click()
            preview = Path(opener.call_args.args[0].toLocalFile())
        try:
            self.assertNotEqual(source, preview)
            self.assertEqual(source.read_bytes(), preview.read_bytes())
        finally:
            preview.chmod(0o666)
            shutil.rmtree(preview.parent)
        self.page.select_group("tax")
        self.assertFalse(self.page.preview_button.isHidden())
        self.assertTrue(self.page.download_button.isHidden())
        with patch.object(self.page.files, "preview_copy") as preview_copy, patch("mingo_assistant.ui.views.template_library_page.QFileDialog.getSaveFileName") as dialog:
            self.page._download_template()
            preview_copy.assert_not_called()
            dialog.assert_not_called()

    def test_all_dkdn_assets_match_originals_and_cannot_overwrite_source(self):
        for template in TEMPLATE_GROUPS[0].items:
            source = self.page.files.source(template.id)
            self.assertTrue(source.is_file())
            if SOURCE_ROOT.is_dir():
                self.assertEqual((SOURCE_ROOT / template.folder / template.filename).read_bytes(), source.read_bytes())
            with self.assertRaises(ValueError):
                self.page.files.download(template.id, source)
        with self.assertRaises(ValueError):
            self.page.files.source("tax-24")

    def test_missing_asset_and_unavailable_viewer_show_errors(self):
        with patch.object(self.page.files, "preview_copy", side_effect=FileNotFoundError("missing")), patch("mingo_assistant.ui.views.template_library_page.QMessageBox.warning") as warning:
            self.page.preview_button.click()
            warning.assert_called_once()
        with patch.object(self.page.files, "preview_copy", return_value=Path("sample.docx")), patch("mingo_assistant.ui.views.template_library_page.QDesktopServices.openUrl", return_value=False), patch("mingo_assistant.ui.views.template_library_page.QMessageBox.warning") as warning:
            self.page.preview_button.click()
            warning.assert_called_once()

    @skipUnless(SOURCE_ROOT.is_dir(), "Original private template inbox is not part of the repository")
    def test_frontend_catalog_matches_all_supplied_filenames_without_copying_files(self):
        actual = {path.relative_to(SOURCE_ROOT).as_posix() for path in SOURCE_ROOT.rglob("*") if path.is_file()}
        catalog = {f"{item.folder}/{item.filename}" for group in TEMPLATE_GROUPS for item in group.items}
        self.assertEqual(actual, catalog)

    def test_switching_groups_shows_their_files_and_enables_tax_preparation(self):
        self.assertEqual("dkdn", self.page.current_group_id)
        self.assertEqual(7, self.page.template_list.count())
        self.page.group_buttons["tax"].click()
        self.assertEqual(10, self.page.template_list.count())
        self.assertIn("Biểu mẫu Thuế", self.page.detail_folder.text())
        self.assertTrue(self.page.use_template_button.isEnabled())
        self.assertTrue(self.page.group_buttons["tax"].isChecked())
        self.assertFalse(self.page.group_buttons["dkdn"].isChecked())
        self.page.group_buttons["dkdn"].click()
        self.assertEqual(7, self.page.template_list.count())

    def test_search_works_with_accents_without_accents_and_original_filename(self):
        for query in ("cổ phần", "co phan", "MS 4", "3. MS4_Thanh lap CTCP.docx"):
            with self.subTest(query=query):
                self.page.search_input.setText(query)
                self.assertEqual(1, self.page.template_list.count())
                self.assertEqual("dkdn-04", self.page.selected_template.id)
        self.page.search_input.setText("MS12")
        self.assertEqual("dkdn-12", self.page.selected_template.id)

    def test_empty_search_clears_stale_details_and_switching_group_resets_filter(self):
        self.page.search_input.setText("nothing matches 999")
        self.assertEqual(0, self.page.template_list.count())
        self.assertIsNone(self.page.selected_template)
        self.assertFalse(self.page.empty_state.isHidden())
        self.assertEqual("—", self.page.detail_filename.text())
        self.page.group_buttons["tax"].click()
        self.assertEqual("", self.page.search_input.text())
        self.assertEqual(10, self.page.template_list.count())
        self.assertTrue(self.page.empty_state.isHidden())

    def test_selecting_doc_file_shows_its_original_name_and_format(self):
        self.page.select_group("tax")
        self.page.search_input.setText("uy quyen giai the")
        self.assertEqual(1, self.page.template_list.count())
        self.assertEqual("Giay uy quyen giai the (Thue).doc", self.page.detail_filename.text())
        self.assertEqual("WORD · DOC", self.page.format_label.text())
        self.assertTrue(self.page.use_template_button.isEnabled())

    def test_narrow_layout_stacks_details_and_wide_layout_places_them_beside_list(self):
        self.page.resize(1100, 800)
        self.page.show()
        self.app.processEvents()
        self.assertEqual(QBoxLayout.LeftToRight, self.page.body_layout.direction())
        self.page.resize(560, 800)
        self.app.processEvents()
        self.assertEqual(QBoxLayout.TopToBottom, self.page.body_layout.direction())
        self.assertLessEqual(self.page.minimumSizeHint().width(), 560)

    def test_category_buttons_and_search_stay_compact_in_wide_layout(self):
        self.page.resize(1366, 900)
        self.page.show()
        self.app.processEvents()
        for button in self.page.group_buttons.values():
            self.assertEqual(40, button.height())
            self.assertLess(button.width(), 300)
            self.assertNotIn("\n", button.text())
        self.assertEqual(40, self.page.search_input.height())
        self.assertLess(self.page.template_list.item(0).sizeHint().height(), 82)

    def test_library_uses_shared_theme_instead_of_local_palette_overrides(self):
        self.assertEqual("", self.page.template_list.styleSheet())
        self.assertEqual("", self.page.use_template_button.styleSheet())
        previous_style = self.app.styleSheet()
        try:
            for appearance in ("light", "dark"):
                css = stylesheet_for_theme("rose", layout="liquid_glass", appearance_mode=appearance)
                self.app.setStyleSheet(css)
                self.page.show()
                self.app.processEvents()
                self.assertIn("background: #6750a4; color: white;", css)
                self.assertTrue(self.page.group_buttons["dkdn"].isChecked())
                self.assertIsNotNone(self.page.selected_template)
        finally:
            self.app.setStyleSheet(previous_style)

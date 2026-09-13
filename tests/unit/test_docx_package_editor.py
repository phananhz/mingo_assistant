from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

from mingo_assistant.services.documents.package_editor import DocxPackageEditor


class DocxPackageEditorTests(unittest.TestCase):
    def test_rewrites_only_word_xml_parts_and_keeps_other_entries(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.docx"
            with zipfile.ZipFile(path, "w") as package:
                package.writestr("word/document.xml", b"<root>[name]</root>")
                package.writestr("docProps/core.xml", b"<root>[keep]</root>")

            changed = DocxPackageEditor.rewrite_xml_parts(
                path,
                lambda _, data: data.replace(b"[name]", b"TEST"),
            )

            self.assertTrue(changed)
            with zipfile.ZipFile(path) as package:
                self.assertEqual(package.read("word/document.xml"), b"<root>TEST</root>")
                self.assertEqual(package.read("docProps/core.xml"), b"<root>[keep]</root>")

    def test_unchanged_package_is_not_replaced_when_requested(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.docx"
            with zipfile.ZipFile(path, "w") as package:
                package.writestr("word/document.xml", b"<root/>")
            before = path.stat().st_mtime_ns

            changed = DocxPackageEditor.rewrite_xml_parts(
                path,
                lambda _, data: data,
                replace_only_if_changed=True,
            )

            self.assertFalse(changed)
            self.assertEqual(path.stat().st_mtime_ns, before)


if __name__ == "__main__":
    unittest.main()

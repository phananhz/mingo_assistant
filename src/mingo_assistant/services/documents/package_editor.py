from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from tempfile import NamedTemporaryFile
import zipfile


class DocxPackageEditor:
    """Atomic ZIP-package operations used by DOCX renderers."""

    @staticmethod
    def word_xml_parts(docx_path: Path) -> Iterator[tuple[str, bytes]]:
        with zipfile.ZipFile(docx_path, "r") as package:
            for item in package.infolist():
                if item.filename.startswith("word/") and item.filename.endswith(".xml"):
                    yield item.filename, package.read(item.filename)

    @staticmethod
    def rewrite_xml_parts(
        docx_path: Path,
        transform: Callable[[str, bytes], bytes],
        *,
        replace_only_if_changed: bool = False,
    ) -> bool:
        temporary_file = NamedTemporaryFile(delete=False, suffix=".docx", dir=docx_path.parent)
        temporary_path = Path(temporary_file.name)
        temporary_file.close()
        changed = False
        try:
            with (
                zipfile.ZipFile(docx_path, "r") as source_zip,
                zipfile.ZipFile(temporary_path, "w", zipfile.ZIP_DEFLATED) as target_zip,
            ):
                for item in source_zip.infolist():
                    data = source_zip.read(item.filename)
                    if item.filename.startswith("word/") and item.filename.endswith(".xml"):
                        replaced = transform(item.filename, data)
                        changed = changed or replaced != data
                        data = replaced
                    target_zip.writestr(item, data)
            if changed or not replace_only_if_changed:
                temporary_path.replace(docx_path)
            else:
                temporary_path.unlink(missing_ok=True)
            return changed
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise


from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from mingo_assistant.services.documents.template_manifest import TemplateManifest
from mingo_assistant.services.documents.template_repository import BusinessRegistrationTemplateRepository


class DocumentTemplateBoundaryTests(unittest.TestCase):
    def test_manifest_exposes_template_and_part_without_document_dependency(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "template_manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "templates": {
                            "sample.docx": {
                                "mode": "copy",
                                "word/document.xml": {"highlighted_fields": {"0": "company_name"}},
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            manifest = TemplateManifest(path)

            self.assertEqual(manifest.template("sample.docx")["mode"], "copy")
            self.assertEqual(
                manifest.part("sample.docx", "word/document.xml")["highlighted_fields"]["0"],
                "company_name",
            )

    def test_repository_selects_exactly_one_charter_for_owner_type(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            names = (
                "1. Giấy đề nghị.docx",
                BusinessRegistrationTemplateRepository.PERSONAL_CHARTER_TEMPLATE,
                BusinessRegistrationTemplateRepository.ORGANIZATION_CHARTER_TEMPLATE,
            )
            for name in names:
                (root / name).touch()
            repository = BusinessRegistrationTemplateRepository(root)

            individual = [path.name for path in repository.selected({"owner_type": "Cá nhân"})]
            organization = [path.name for path in repository.selected({"owner_type": "Tổ chức"})]

            self.assertIn(repository.PERSONAL_CHARTER_TEMPLATE, individual)
            self.assertNotIn(repository.ORGANIZATION_CHARTER_TEMPLATE, individual)
            self.assertIn(repository.ORGANIZATION_CHARTER_TEMPLATE, organization)
            self.assertNotIn(repository.PERSONAL_CHARTER_TEMPLATE, organization)


if __name__ == "__main__":
    unittest.main()

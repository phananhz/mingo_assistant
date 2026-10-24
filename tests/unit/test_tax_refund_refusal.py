from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4
from zipfile import ZipFile

from lxml import etree
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QLineEdit

from mingo_assistant.app.paths import AppPaths
from mingo_assistant.models.case import CaseSummary
from mingo_assistant.repositories.case_repository import CaseRepository
from mingo_assistant.services.documents.tax_refund_refusal_generator import (
    TaxRefundRefusalGenerator,
)
from mingo_assistant.ui.main_window import MainWindow
from mingo_assistant.ui.views.tax_commitment_workspace import TaxCommitmentWorkspace
from mingo_assistant.ui.views.tax_refund_refusal_workspace import TaxRefundRefusalWorkspace
from mingo_assistant.ui.views.tax_template_workspace import TAX_TEMPLATE_CASE_TYPE


ROOT = Path(__file__).resolve().parents[2]
VALUES = {
    "tax_receiving_authority": "Thuế cơ sở 1 Thành phố Hồ Chí Minh",
    "tax_company_name": "CÔNG TY CỔ PHẦN KIỂM THỬ",
    "tax_registration_number": "0312345678",
    "tax_taxpayer": "NGUYỄN VĂN A",
    "tax_taxpayer_position": "Chủ tịch Hội đồng quản trị",
}


class TaxRefundRefusalTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_route_has_optional_position_without_fields_from_other_templates(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repo = CaseRepository(root / "cases.json")
            repo._write_cases([])
            window = MainWindow(
                app_paths=AppPaths(ROOT, root, root / "exports"), case_repository=repo
            )
            try:
                window._open_tax_template_workspace("tax-refund")
                workspace = window.current_workspace
                self.assertIsInstance(workspace, TaxRefundRefusalWorkspace)
                self.assertIsInstance(workspace.fields["tax_taxpayer_position"], QLineEdit)
                self.assertEqual("erc", workspace.scan_document_type_input.currentData())
                self.assertNotIn("tax_signing_place", workspace.fields)
                self.assertNotIn("tax_business_industry", workspace.fields)
                window.current_workspace.on_back()
                window._open_tax_template_workspace("tax-commitment")
                self.assertIs(type(window.current_workspace), TaxCommitmentWorkspace)
                self.assertNotIn("tax_taxpayer_position", window.current_workspace.fields)
            finally:
                window.hide()
                window.close()
                window.deleteLater()
                self.app.processEvents()

    def test_generator_fills_only_green_fields_and_clears_optional_sample_position(self):
        with TemporaryDirectory() as directory:
            generator = TaxRefundRefusalGenerator(
                ROOT / "assets/templates/library/tax", directory
            )
            for position in (VALUES["tax_taxpayer_position"], "", None):
                with self.subTest(position=position):
                    values = dict(VALUES)
                    if position is None:
                        values.pop("tax_taxpayer_position")
                    else:
                        values["tax_taxpayer_position"] = position
                    result = generator.generate(values, "QA")
                    with ZipFile(generator.template_dir / generator.FILENAME) as source, \
                            ZipFile(result.generated[0].output_path) as output:
                        for name in source.namelist():
                            if name != "word/document.xml":
                                self.assertEqual(source.read(name), output.read(name))
                        original = etree.fromstring(source.read("word/document.xml"))
                        generated = etree.fromstring(output.read("word/document.xml"))
                        runs = generated.xpath(
                            "//w:r[w:rPr/w:highlight[@w:val='green']]",
                            namespaces=generator.NS,
                        )
                        expected = [values[key] for key in generator.REQUIRED_KEYS]
                        expected.append(position or "")
                        self.assertEqual(expected, [
                            "".join(run.xpath("w:t/text()", namespaces=generator.NS))
                            for run in runs
                        ])
                        for document in (original, generated):
                            for run in document.xpath(
                                "//w:r[w:rPr/w:highlight[@w:val='green']]",
                                namespaces=generator.NS,
                            ):
                                for child in list(run):
                                    if child.tag != generator.W + "rPr":
                                        run.remove(child)
                        self.assertEqual(etree.tostring(original), etree.tostring(generated))
            with self.assertRaises(ValueError):
                generator.generate({}, "Missing required values")

    def test_erc_save_restore_export_without_position_and_case_independence(self):
        with TemporaryDirectory() as directory, patch.object(
            QMessageBox, "information"
        ), patch.object(QMessageBox, "warning"):
            repo = CaseRepository(Path(directory) / "cases.json")
            repo._write_cases([])
            workspaces = []

            def create(case=None):
                if case is None:
                    case = CaseSummary.from_dict({
                        "id": str(uuid4()), "case_type": TAX_TEMPLATE_CASE_TYPE,
                        "form_values": {"tax_template_id": "tax-refund"},
                    })
                workspace = TaxRefundRefusalWorkspace(
                    on_back=lambda: None, on_save=repo.save_case, bundle_root=ROOT,
                    default_export_root=Path(directory) / "exports", case=case,
                )
                workspaces.append(workspace)
                workspace.enable_draft_progress()
                return workspace

            try:
                workspace = create()
                recognized = {
                    "organization_owner_name": VALUES["tax_company_name"],
                    "organization_owner_registration_number": VALUES["tax_registration_number"],
                    "organization_owner_issue_date": "01/02/2020",
                    "organization_owner_issue_place": "Sở Tài chính Thành phố Hồ Chí Minh",
                    "organization_owner_address_full": "12 Đường Kiểm Thử, Thành phố Hồ Chí Minh",
                    "tax_legal_representatives": "NGUYỄN VĂN A\nTRẦN THỊ B",
                }
                workspace._apply_organization_values_to_current_person(recognized, "ERC test", "text")
                workspace._update_organization_result_fields(recognized)
                workspace._save_organization_profile()
                workspace.taxpayer.setCurrentText(VALUES["tax_taxpayer"])
                workspace._set_field("tax_receiving_authority", VALUES["tax_receiving_authority"])
                workspace._set_field("tax_taxpayer_position", VALUES["tax_taxpayer_position"])
                workspace.draft_progress.flush()
                reopened = create(repo.get_case(workspace.case_id))
                self.assertEqual(
                    VALUES["tax_taxpayer_position"], reopened.form_values()["tax_taxpayer_position"]
                )
                other = create()
                self.assertEqual("", other.form_values()["tax_taxpayer_position"])
                self.assertNotEqual(
                    reopened._case_export_folder_name(reopened.form_values()),
                    other._case_export_folder_name(other.form_values()),
                )
                reopened._set_field("tax_taxpayer_position", "")
                self.assertEqual([], reopened._validation_issues(reopened.form_values()))
                reopened._export_documents()
                for _ in range(500):
                    QTest.qWait(10)
                    if reopened._export_thread is None:
                        break
                self.assertIsNone(reopened._export_thread)
                saved = repo.get_case(reopened.case_id)
                self.assertEqual("Đã tạo hồ sơ", saved.status)
                self.assertEqual("tax-refund", saved.form_values["tax_template_id"])
                self.assertEqual("", saved.form_values["tax_taxpayer_position"])
                self.assertEqual(1, len(saved.generated_documents))
                self.assertTrue(list(Path(saved.export_dir).rglob("*.docx")))
            finally:
                for workspace in workspaces:
                    workspace.draft_progress.stop()
                    workspace.deleteLater()
                self.app.processEvents()

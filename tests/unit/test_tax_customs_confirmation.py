from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4
from zipfile import ZipFile

from lxml import etree
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from mingo_assistant.app.paths import AppPaths
from mingo_assistant.models.case import CaseSummary
from mingo_assistant.repositories.case_repository import CaseRepository
from mingo_assistant.services.documents.tax_customs_confirmation_generator import TaxCustomsConfirmationGenerator
from mingo_assistant.ui.main_window import MainWindow
from mingo_assistant.ui.views.tax_authorization_close_workspace import TaxAuthorizationCloseWorkspace
from mingo_assistant.ui.views.tax_customs_confirmation_workspace import TaxCustomsConfirmationWorkspace
from mingo_assistant.ui.views.tax_template_workspace import TAX_TEMPLATE_CASE_TYPE


ROOT = Path(__file__).resolve().parents[2]
PROFILE = {
    "id": "recipient-a", "authorized_person_full_name": "NGUYỄN VĂN B",
    "authorized_person_phone": "0901234567", "authorized_person_id_number": "079123456789",
}
OTHER_PROFILE = dict(PROFILE, id="recipient-b", authorized_person_full_name="TRẦN THỊ C")
VALUES = {
    "tax_company_name": "CÔNG TY TNHH KIỂM THỬ", "tax_registration_number": "0312345678",
    "tax_address": "12 Đường Kiểm Thử, Lâm Đồng, Việt Nam",
    "tax_receiving_authority": "Chi cục Hải quan khu vực II",
    "tax_signing_place": "Tỉnh Lâm Đồng", "tax_taxpayer": "NGUYỄN VĂN A", **PROFILE,
}


class TaxCustomsConfirmationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_catalog_reuses_profile_dropdown_with_only_recipient_name_and_phone(self):
        with TemporaryDirectory() as directory, patch.object(
            MainWindow, "_load_authorized_person", return_value={"__profiles": [PROFILE]}
        ):
            root = Path(directory)
            repo = CaseRepository(root / "cases.json")
            repo._write_cases([])
            window = MainWindow(app_paths=AppPaths(ROOT, root, root / "exports"), case_repository=repo)
            try:
                window._open_tax_template_workspace("tax-customs")
                workspace = window.current_workspace
                self.assertIsInstance(workspace, TaxCustomsConfirmationWorkspace)
                self.assertEqual("erc", workspace.scan_document_type_input.currentData())
                self.assertIn(workspace.SECTION_TITLE, workspace.form_sections)
                selector = workspace.person_fill_selectors["authorized_person"]
                selector.setCurrentIndex(selector.findData("authorized_profile:0"))
                self.assertEqual(PROFILE["authorized_person_full_name"], workspace._field_value("authorized_person_full_name"))
                self.assertEqual(PROFILE["authorized_person_phone"], workspace._field_value("authorized_person_phone"))
                for key in ("authorized_person_id_number", "authorized_person_issue_date", "authorized_person_email", "tax_business_industry"):
                    self.assertNotIn(key, workspace.fields)
            finally:
                window.hide()
                window.close()
                window.deleteLater()
                self.app.processEvents()

    def test_generator_fills_recipient_and_both_authorities_preserving_all_fixed_content(self):
        with TemporaryDirectory() as directory:
            generator = TaxCustomsConfirmationGenerator(ROOT / "assets/templates/library/tax", directory)
            result = generator.generate(VALUES, "QA")
            with ZipFile(generator.template_dir / generator.FILENAME) as source, \
                    ZipFile(result.generated[0].output_path) as output:
                for name in source.namelist():
                    if name != "word/document.xml":
                        self.assertEqual(source.read(name), output.read(name))
                original = etree.fromstring(source.read("word/document.xml"))
                generated = etree.fromstring(output.read("word/document.xml"))
                runs = generated.xpath("//w:r[w:rPr/w:highlight[@w:val='green']]", namespaces=generator.NS)
                self.assertEqual([
                    "CÔNG TY TNHH", "KIỂM THỬ", "Lâm Đồng", VALUES["tax_receiving_authority"],
                    VALUES["tax_company_name"], VALUES["tax_registration_number"], VALUES["tax_address"],
                    VALUES["tax_receiving_authority"], PROFILE["authorized_person_full_name"],
                    PROFILE["authorized_person_phone"], VALUES["tax_taxpayer"],
                ], ["".join(run.xpath("w:t/text()", namespaces=generator.NS)) for run in runs])
                for document in (original, generated):
                    for run in document.xpath("//w:r[w:rPr/w:highlight]", namespaces=generator.NS):
                        for node in run.xpath("w:t|w:br", namespaces=generator.NS):
                            run.remove(node)
                self.assertEqual(etree.tostring(original), etree.tostring(generated))
            for key in ("authorized_person_full_name", "authorized_person_phone"):
                with self.assertRaises(ValueError):
                    generator.generate(dict(VALUES, **{key: ""}), "Missing recipient")

    def test_erc_and_profile_snapshot_restore_export_without_mutating_other_dossiers(self):
        with TemporaryDirectory() as directory, patch.object(QMessageBox, "information"), \
                patch.object(QMessageBox, "warning"):
            repo = CaseRepository(Path(directory) / "cases.json")
            repo._write_cases([])
            defaults = {"__profiles": [deepcopy(PROFILE), deepcopy(OTHER_PROFILE)]}
            before = deepcopy(defaults)
            workspaces = []

            def create(case=None, profiles=None, authorization=False):
                if case is None:
                    case = CaseSummary.from_dict({
                        "id": str(uuid4()), "case_type": TAX_TEMPLATE_CASE_TYPE,
                        "form_values": {"tax_template_id": "tax-authorization-close" if authorization else "tax-customs"},
                    })
                cls = TaxAuthorizationCloseWorkspace if authorization else TaxCustomsConfirmationWorkspace
                workspace = cls(
                    on_back=lambda: None, on_save=repo.save_case, bundle_root=ROOT,
                    default_export_root=Path(directory) / "exports", case=case,
                    authorized_person_defaults=profiles if profiles is not None else defaults,
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
                    "organization_owner_issue_place": "Sở Tài chính Lâm Đồng",
                    "organization_owner_address_full": VALUES["tax_address"],
                    "tax_legal_representatives": "NGUYỄN VĂN A\nTRẦN THỊ B",
                }
                workspace._apply_organization_values_to_current_person(recognized, "ERC test", "text")
                workspace._update_organization_result_fields(recognized)
                workspace._save_organization_profile()
                workspace.taxpayer.setCurrentText(VALUES["tax_taxpayer"])
                selector = workspace.person_fill_selectors["authorized_person"]
                selector.setCurrentIndex(selector.findData("authorized_profile:0"))
                workspace._set_field("authorized_person_phone", "0909999999")
                for key in ("tax_receiving_authority", "tax_signing_place"):
                    workspace._set_field(key, VALUES[key])
                workspace.draft_progress.flush()
                reopened = create(repo.get_case(workspace.case_id), {"__profiles": [OTHER_PROFILE, dict(PROFILE, authorized_person_phone="0900000000")]})
                self.assertEqual("0909999999", reopened._field_value("authorized_person_phone"))
                self.assertEqual("authorized_profile:1", reopened.person_fill_selectors["authorized_person"].currentData())
                self.assertEqual(before, defaults)
                other = create(authorization=True)
                self.assertEqual("", other._field_value("authorized_person_full_name"))
                self.assertIn("authorized_person_id_number", other.fields)
                self.assertNotEqual(
                    reopened._case_export_folder_name(reopened.form_values()),
                    other._case_export_folder_name(other.form_values()),
                )
                self.assertEqual([], reopened._validation_issues(reopened.form_values()))
                self.assertTrue(reopened._validation_issues(dict(reopened.form_values(), authorized_person_phone="")))
                reopened._export_documents()
                for _ in range(500):
                    QTest.qWait(10)
                    if reopened._export_thread is None:
                        break
                self.assertIsNone(reopened._export_thread)
                saved = repo.get_case(reopened.case_id)
                self.assertEqual("Đã tạo hồ sơ", saved.status)
                self.assertEqual("tax-customs", saved.form_values["tax_template_id"])
                self.assertTrue(list(Path(saved.export_dir).rglob("*.docx")))
            finally:
                for workspace in workspaces:
                    workspace.draft_progress.stop()
                    workspace.deleteLater()
                self.app.processEvents()

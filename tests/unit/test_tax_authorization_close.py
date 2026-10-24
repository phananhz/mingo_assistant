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
from mingo_assistant.services.documents.tax_authorization_close_generator import (
    TaxAuthorizationCloseGenerator,
)
from mingo_assistant.ui.main_window import MainWindow
from mingo_assistant.ui.views.tax_authorization_close_workspace import TaxAuthorizationCloseWorkspace
from mingo_assistant.ui.views.tax_template_workspace import TAX_TEMPLATE_CASE_TYPE


ROOT = Path(__file__).resolve().parents[2]
PROFILE = {
    "id": "authorized-a", "authorized_person_full_name": "NGUYỄN VĂN B",
    "authorized_person_id_number": "079123456789", "authorized_person_issue_date": "01/02/2023",
    "authorized_person_issue_place": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "authorized_person_contact_address": "Địa chỉ profile không thay chữ cố định trong mẫu",
    "authorized_person_phone": "0901234567", "authorized_person_email": "person@example.com",
}
OTHER_PROFILE = dict(PROFILE, id="authorized-b", authorized_person_full_name="TRẦN THỊ C")
VALUES = {
    **PROFILE, "tax_company_name": "CÔNG TY TNHH KIỂM THỬ",
    "tax_registration_number": "0312345678", "tax_address": "12 Đường Kiểm Thử, Lâm Đồng, Việt Nam",
    "tax_taxpayer": "NGUYỄN VĂN A", "tax_receiving_authority": "Thuế cơ sở kiểm thử",
    "tax_signing_place": "Tỉnh Lâm Đồng",
}


class TaxAuthorizationCloseTests(TestCase):
    WORKSPACE_CLASS = TaxAuthorizationCloseWorkspace
    GENERATOR_CLASS = TaxAuthorizationCloseGenerator
    TEMPLATE_ID = "tax-authorization-close"
    TEMPLATE_RELATIVE_DIR = "assets/templates/word/tax/authorization_close"

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_catalog_routes_to_combined_section_and_shared_profile_selector(self):
        with TemporaryDirectory() as directory, patch.object(
            MainWindow, "_load_authorized_person", return_value={"__profiles": [PROFILE]}
        ):
            root = Path(directory)
            repo = CaseRepository(root / "cases.json")
            repo._write_cases([])
            window = MainWindow(app_paths=AppPaths(ROOT, root, root / "exports"), case_repository=repo)
            try:
                window._open_tax_template_workspace(self.TEMPLATE_ID)
                workspace = window.current_workspace
                self.assertIsInstance(workspace, self.WORKSPACE_CLASS)
                self.assertIn(workspace.SECTION_TITLE, workspace.form_sections)
                self.assertNotIn("tax_business_industry", workspace.fields)
                selector = workspace.person_fill_selectors["authorized_person"]
                selector.setCurrentIndex(selector.findData("authorized_profile:0"))
                self.assertEqual(PROFILE["authorized_person_full_name"], workspace._field_value("authorized_person_full_name"))
                self.assertEqual("erc", workspace.scan_document_type_input.currentData())
            finally:
                window.hide()
                window.close()
                window.deleteLater()
                self.app.processEvents()

    def test_generator_changes_only_yellow_and_green_regions(self):
        with TemporaryDirectory() as directory:
            generator = self.GENERATOR_CLASS(
                ROOT / self.TEMPLATE_RELATIVE_DIR, directory
            )
            for email in (PROFILE["authorized_person_email"], ""):
                with self.subTest(email=email):
                    values = dict(VALUES, authorized_person_email=email)
                    result = generator.generate(values, "QA")
                    with ZipFile(generator.template_dir / generator.FILENAME) as source, \
                            ZipFile(result.generated[0].output_path) as output:
                        for name in source.namelist():
                            if name != "word/document.xml":
                                self.assertEqual(source.read(name), output.read(name))
                        original = etree.fromstring(source.read("word/document.xml"))
                        generated = etree.fromstring(output.read("word/document.xml"))
                        runs = generated.xpath("//w:r[w:rPr/w:highlight]", namespaces=generator.NS)
                        expected = [values.get(key, "") for key in generator.KEYS]
                        expected[12] = "Lâm Đồng"
                        self.assertEqual(expected, [
                            "".join(run.xpath("w:t/text()", namespaces=generator.NS)) for run in runs
                        ])
                        for document in (original, generated):
                            # This row intentionally removes excess padding;
                            # all non-whitespace text and formatting stay protected.
                            for paragraph in document.xpath("//w:p", namespaces=generator.NS):
                                if "Cấp ngày" in "".join(paragraph.xpath(".//w:t/text()", namespaces=generator.NS)):
                                    for text in paragraph.xpath("w:r/w:t", namespaces=generator.NS):
                                        if text.text and text.text.isspace():
                                            text.text = " "
                            for run in document.xpath("//w:r[w:rPr/w:highlight]", namespaces=generator.NS):
                                for child in list(run):
                                    if child.tag != generator.W + "rPr":
                                        run.remove(child)
                        self.assertEqual(etree.tostring(original), etree.tostring(generated))
            with self.assertRaises(ValueError):
                generator.generate({}, "Missing values")

    def test_long_issuing_authority_reclaims_padding_without_shrinking_or_losing_text(self):
        with TemporaryDirectory() as directory:
            generator = self.GENERATOR_CLASS(ROOT / self.TEMPLATE_RELATIVE_DIR, directory)
            issuer = "Cục Cảnh sát Quản lý Hành chính về Trật tự Xã hội"
            values = dict(VALUES, authorized_person_issue_date="12/06/2021", authorized_person_issue_place=issuer)
            result = generator.generate(values, "Long issuer")
            with ZipFile(result.generated[0].output_path) as package:
                xml = etree.fromstring(package.read("word/document.xml"))
                row = next(
                    paragraph for paragraph in xml.xpath("//w:p", namespaces=generator.NS)
                    if "Cấp ngày" in "".join(paragraph.xpath(".//w:t/text()", namespaces=generator.NS))
                )
                text = "".join(row.xpath(".//w:t/text()", namespaces=generator.NS))
                self.assertIn("Cấp ngày : 12/06/2021   Nơi Cấp: " + issuer, text)
                self.assertFalse(row.xpath(".//w:br", namespaces=generator.NS))
                self.assertEqual({"26"}, set(row.xpath(".//w:r/w:rPr/w:sz/@w:val", namespaces=generator.NS)))

    def test_profile_snapshot_and_erc_restore_export_and_case_independence(self):
        with TemporaryDirectory() as directory, patch.object(QMessageBox, "information"), \
                patch.object(QMessageBox, "warning"):
            repo = CaseRepository(Path(directory) / "cases.json")
            repo._write_cases([])
            defaults = {"__profiles": [deepcopy(PROFILE), deepcopy(OTHER_PROFILE)]}
            before = deepcopy(defaults)
            workspaces = []

            def create(case=None, profiles=None):
                if case is None:
                    case = CaseSummary.from_dict({
                        "id": str(uuid4()), "case_type": TAX_TEMPLATE_CASE_TYPE,
                        "form_values": {"tax_template_id": self.TEMPLATE_ID},
                    })
                workspace = self.WORKSPACE_CLASS(
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
                    "tax_legal_representatives": "NGUYỄN VĂN A\nTRẦN THỊ A",
                }
                workspace._apply_organization_values_to_current_person(recognized, "ERC test", "text")
                workspace._update_organization_result_fields(recognized)
                workspace._save_organization_profile()
                self.assertEqual(2, workspace.taxpayer.count())
                workspace.taxpayer.setCurrentText(VALUES["tax_taxpayer"])
                selector = workspace.person_fill_selectors["authorized_person"]
                selector.setCurrentIndex(selector.findData("authorized_profile:0"))
                workspace._set_field("authorized_person_phone", "0909999999")
                workspace._set_field("tax_receiving_authority", VALUES["tax_receiving_authority"])
                workspace._set_field("tax_signing_place", VALUES["tax_signing_place"])
                workspace.draft_progress.flush()
                changed_profiles = {"__profiles": [OTHER_PROFILE, dict(PROFILE, authorized_person_phone="0900000000")]}
                reopened = create(repo.get_case(workspace.case_id), changed_profiles)
                self.assertEqual("0909999999", reopened._field_value("authorized_person_phone"))
                self.assertEqual("authorized_profile:1", reopened.person_fill_selectors["authorized_person"].currentData())
                self.assertEqual("authorized-a", reopened.form_values()["tax_authorized_profile_id"])
                removed_profile = create(repo.get_case(workspace.case_id), {"__profiles": [OTHER_PROFILE]})
                self.assertEqual("", removed_profile.person_fill_selectors["authorized_person"].currentData())
                self.assertEqual(PROFILE["authorized_person_full_name"], removed_profile._field_value("authorized_person_full_name"))
                self.assertEqual("0909999999", removed_profile._field_value("authorized_person_phone"))
                self.assertEqual(before, defaults)
                other = create()
                self.assertEqual("", other._field_value("authorized_person_full_name"))
                self.assertNotEqual(
                    reopened._case_export_folder_name(reopened.form_values()),
                    other._case_export_folder_name(other.form_values()),
                )
                self.assertEqual([], reopened._validation_issues(reopened.form_values()))
                reopened._export_documents()
                for _ in range(500):
                    QTest.qWait(10)
                    if reopened._export_thread is None:
                        break
                self.assertIsNone(reopened._export_thread)
                saved = repo.get_case(reopened.case_id)
                self.assertEqual("Đã tạo hồ sơ", saved.status)
                self.assertEqual(self.TEMPLATE_ID, saved.form_values["tax_template_id"])
                self.assertTrue(list(Path(saved.export_dir).rglob("*.docx")))
            finally:
                for workspace in workspaces:
                    workspace.draft_progress.stop()
                    workspace.deleteLater()
                self.app.processEvents()

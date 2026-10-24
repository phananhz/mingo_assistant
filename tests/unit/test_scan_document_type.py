from copy import copy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import fitz
from PySide6.QtWidgets import QApplication

from mingo_assistant.services.ocr.scan_input import certificate_pdf, identity_images
from mingo_assistant.services.organization_documents.location_certificate_service import LocationCertificateService
from mingo_assistant.services.organization_documents.organization_document_service import (
    DocumentTypeMismatchError, OrganizationDocumentService,
)
from mingo_assistant.ui.views.business_registration_workspace import BusinessRegistrationWorkspace
from mingo_assistant.ui.views.business_amendment_workspace import BusinessAmendmentWorkspace
from mingo_assistant.ui.views.location_business_workspace import LocationBusinessWorkspace
from tests.unit.test_location_certificate_ocr_quality import ERC_TEXT, NOISY_BRC


class ScanDocumentTypeTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_dropdown_routes_explicit_types_and_preserves_automatic_mode(self):
        with TemporaryDirectory() as directory:
            for workspace_class, expected in (
                (BusinessRegistrationWorkspace, "erc"), (LocationBusinessWorkspace, "brc"),
                (BusinessAmendmentWorkspace, "erc"),
            ):
                workspace = workspace_class(
                    on_back=lambda: None, on_save=lambda case: None,
                    bundle_root=Path(__file__).resolve().parents[2], default_export_root=Path(directory),
                )
                try:
                    combo = workspace.scan_document_type_input
                    self.assertEqual(["auto", "cccd", "erc", "brc"], [combo.itemData(i) for i in range(combo.count())])
                    self.assertEqual("auto", combo.currentData())
                    person = workspace.ocr_people[workspace.current_person_index]
                    with patch.object(workspace, "_scan_organization_document") as organization, \
                            patch.object(workspace, "_run_qr_scan") as identity, \
                            patch("mingo_assistant.ui.views.business_registration_workspace.QMessageBox.warning") as warning:
                        person.front_path = "card.pdf"
                        combo.setCurrentIndex(combo.findData("cccd"))
                        workspace._run_document_scan()
                        identity.assert_called_once_with("card.pdf")
                        organization.assert_not_called()
                        person.front_path = "certificate.jpg"
                        combo.setCurrentIndex(combo.findData(expected))
                        workspace._run_document_scan()
                        organization.assert_called_once_with("certificate.jpg")
                        organization.reset_mock()
                        combo.setCurrentIndex(combo.findData("brc" if expected == "erc" else "erc"))
                        workspace._run_document_scan()
                        warning.assert_called_once()
                        organization.assert_not_called()
                        combo.setCurrentIndex(0)
                        person.front_path = "certificate.pdf"
                        workspace._run_document_scan()
                        organization.assert_called_once_with("certificate.pdf")
                        with patch.object(workspace.organization_document_service, "extract_pdf", return_value="auto") as automatic, \
                                patch.object(workspace.organization_document_service, "extract_pdf_as", return_value="manual") as manual:
                            self.assertEqual("auto", workspace._extract_selected_organization_document("certificate.pdf"))
                            automatic.assert_called_once()
                            manual.assert_not_called()
                            combo.setCurrentIndex(combo.findData(expected))
                            self.assertEqual("manual", workspace._extract_selected_organization_document("certificate.pdf"))
                            manual.assert_called_once_with("certificate.pdf", expected, None)
                finally:
                    workspace.deleteLater()
                    self.app.processEvents()

    def test_manual_type_override_is_per_scan_and_keeps_workflow_guard(self):
        service = OrganizationDocumentService()
        with patch.object(OrganizationDocumentService, "extract_pdf", autospec=True) as extract:
            extract.side_effect = lambda scanner, path, callback: scanner._validate_expected_document_type(NOISY_BRC)
            self.assertEqual("erc", service.extract_pdf_as("certificate.pdf", "erc"))
        self.assertFalse(hasattr(service, "_explicit_document_type"))
        with patch.object(OrganizationDocumentService, "extract_pdf", side_effect=RuntimeError("unreadable")):
            with self.assertRaises(RuntimeError):
                service.extract_pdf_as("certificate.pdf", "erc")
        self.assertFalse(hasattr(service, "_explicit_document_type"))
        with self.assertRaises(DocumentTypeMismatchError):
            service._validate_expected_document_type(NOISY_BRC)
        with self.assertRaises(DocumentTypeMismatchError):
            service.extract_pdf_as("certificate.pdf", "brc")

    def test_manual_parsers_can_read_fields_when_certificate_heading_is_missing(self):
        for original, text in ((OrganizationDocumentService(), ERC_TEXT), (LocationCertificateService(), NOISY_BRC)):
            scanner = copy(original)
            scanner._explicit_document_type = original.DOCUMENT_TYPE
            text = "\n".join(text.splitlines()[1:])
            if scanner.DOCUMENT_TYPE == "erc":
                self.assertFalse(original._is_business_certificate(text))
                result = scanner._extract_supported_document(text, "text")
                self.assertEqual("0312345678", result.values["organization_owner_registration_number"])
            else:
                self.assertEqual({}, original._parse_certificate(text))
                self.assertEqual("00003", scanner._parse_certificate(text)["location_business_code"])
                self.assertEqual({}, scanner._parse_certificate("unrelated document"))

    def test_format_adapters_create_readable_files_and_remove_temporary_copies(self):
        with TemporaryDirectory() as directory:
            pdf = Path(directory) / "identity.pdf"
            with fitz.open() as document:
                document.new_page(width=100, height=150)
                document.new_page(width=100, height=150)
                document.save(pdf)
            with identity_images([str(pdf)]) as images:
                self.assertEqual(2, len(images))
                self.assertTrue(all(Path(path).is_file() for path in images))
                image = Path(directory) / "certificate.png"
                image.write_bytes(Path(images[0]).read_bytes())
            self.assertTrue(all(not Path(path).exists() for path in images))
            with certificate_pdf(str(image)) as adapted:
                with fitz.open(adapted) as document:
                    self.assertEqual(1, document.page_count)
            self.assertFalse(Path(adapted).exists())
            self.assertTrue(pdf.is_file())
            self.assertTrue(image.is_file())

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import MagicMock, patch

import cv2
import fitz
import numpy as np
from PIL import Image, ImageDraw
from PySide6.QtWidgets import QApplication

from mingo_assistant.core.cancellation import ScanCancelledError
from mingo_assistant.services.ocr.certificate_photo import geometry_variant, _deskew, _page_quad
from mingo_assistant.services.ocr.certificate_scan import _orient_and_probe, read_certificate
from mingo_assistant.services.ocr.scan_input import certificate_pdf
from mingo_assistant.services.ocr.vietnamese_line_refiner import VietnameseLineRefiner
from mingo_assistant.services.organization_documents.organization_document_service import OrganizationDocumentService
from mingo_assistant.services.organization_documents.location_certificate_service import LocationCertificateService
from mingo_assistant.services.qr.scanner import IdentityScanResult
from mingo_assistant.ui.views.business_registration.scan_worker import DocumentScanWorker, ScanRequest
from tests.unit.test_location_certificate_ocr_quality import ERC_TEXT, NOISY_BRC


class CertificatePhotoTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root / "giấy chứng nhận.png"
        Image.new("RGB", (600, 900), "white").save(self.image)

    def pdf_pixels(self, path):
        with fitz.open(path) as document:
            pixmap = document[0].get_pixmap(alpha=False)
            return np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, 3)

    def test_exif_rotation_alpha_and_source_are_preserved(self):
        photo = self.root / "phone.jpg"
        image = Image.new("RGB", (900, 600), "white")
        ImageDraw.Draw(image).rectangle((0, 0, 150, 150), fill="red")
        exif = Image.Exif()
        exif[274] = 6  # right-angle camera rotation
        image.save(photo, exif=exif)
        original = sha256(photo.read_bytes()).hexdigest()
        with certificate_pdf(str(photo)) as adapted:
            pixels = self.pdf_pixels(adapted)
            self.assertGreater(pixels.shape[0], pixels.shape[1])
            self.assertGreater(pixels[25, -25, 0], 200)
            self.assertLess(pixels[25, -25, 1], 80)
        self.assertFalse(Path(adapted).exists())
        self.assertEqual(original, sha256(photo.read_bytes()).hexdigest())
        Image.new("RGBA", (600, 900), (0, 0, 0, 0)).save(self.image)
        with certificate_pdf(str(self.image)) as adapted:
            self.assertTrue(np.all(self.pdf_pixels(adapted)[200, 200] > 245))

    def test_tiff_keeps_all_pages_and_bounds_render_size(self):
        photo = self.root / "pages.tiff"
        Image.new("RGB", (1000, 1400), "white").save(
            photo, save_all=True, append_images=[Image.new("RGB", (1400, 1000), "white")],
        )
        with certificate_pdf(str(photo)) as adapted, fitz.open(adapted) as document:
            self.assertEqual(2, len(document))
            self.assertGreater(document[0].rect.height, document[0].rect.width)
            self.assertLess(document[1].rect.height, document[1].rect.width)
        Image.new("RGB", (4000, 2000), "white").save(self.image)
        with certificate_pdf(str(self.image)) as adapted, fitz.open(adapted) as document:
            xref = document[0].get_images()[0][0]
            self.assertLessEqual(max(fitz.Pixmap(document, xref).width, fitz.Pixmap(document, xref).height), 3600)

    def test_many_frames_and_oversized_photos_fail_without_touching_original(self):
        photo = self.root / "many.tiff"
        Image.new("RGB", (10, 10)).save(photo, save_all=True, append_images=[Image.new("RGB", (10, 10)) for _ in range(12)])
        with self.assertRaisesRegex(ValueError, "12 trang"), certificate_pdf(str(photo)):
            pass
        with patch("mingo_assistant.services.ocr.scan_input.Image.open") as open_image:
            source = open_image.return_value.__enter__.return_value
            source.n_frames, source.width, source.height = 1, 8000, 7000
            with self.assertRaisesRegex(ValueError, "48 megapixel"), certificate_pdf(str(self.image)):
                pass

    def test_pdf_with_text_bypasses_photo_conversion_and_ocr_probe(self):
        service = OrganizationDocumentService()
        pdf = self.root / "text.pdf"
        pdf.touch()
        with patch.object(service, "extract_pdf", return_value="direct") as extract, \
                patch("mingo_assistant.services.ocr.scan_input.Image.open") as image, \
                patch("mingo_assistant.services.ocr.certificate_scan._orient_and_probe") as probe:
            self.assertEqual("direct", read_certificate(service, str(pdf)))
            extract.assert_called_once_with(str(pdf), progress_callback=None)
            image.assert_not_called()
            probe.assert_not_called()

    def test_rotation_probe_is_bounded_and_stops_when_title_is_found(self):
        service = OrganizationDocumentService()
        with certificate_pdf(str(self.image)) as pdf, \
                patch.object(service, "_get_legacy_engine"), \
                patch.object(service, "_extract_page_with_ocr", side_effect=["noise", ERC_TEXT]) as ocr:
            text = _orient_and_probe(service, pdf, None)
            self.assertEqual(ERC_TEXT, text)
            self.assertEqual(2, ocr.call_count)
            with fitz.open(pdf) as document:
                self.assertEqual(90, document[0].rotation)
        with certificate_pdf(str(self.image)) as pdf, \
                patch.object(service, "_get_legacy_engine"), \
                patch.object(service, "_extract_page_with_ocr", return_value="") as ocr:
            self.assertEqual("", _orient_and_probe(service, pdf, None))
            self.assertEqual(4, ocr.call_count)

    def test_photo_early_read_is_reused_and_state_does_not_leak(self):
        for service, text in ((OrganizationDocumentService(), ERC_TEXT), (LocationCertificateService(), NOISY_BRC)):
            with self.subTest(kind=service.DOCUMENT_TYPE), \
                    patch("mingo_assistant.services.ocr.certificate_scan._orient_and_probe", return_value=text), \
                    patch.object(type(service), "_extract_first_page_for_type_detection") as second_probe, \
                    patch.object(type(service), "_safe_ocr_pass", return_value=text):
                result = read_certificate(service, str(self.image), service.DOCUMENT_TYPE)
                self.assertEqual(service.DOCUMENT_TYPE, result.document_type)
                self.assertFalse(hasattr(service, "_photo_input"))
                self.assertFalse(hasattr(service, "_photo_probe"))
                second_probe.assert_not_called()

    def test_auto_photo_wrong_workflow_fails_before_full_ocr(self):
        service = OrganizationDocumentService()
        with patch("mingo_assistant.services.ocr.certificate_scan._orient_and_probe", return_value=NOISY_BRC), \
                patch.object(service, "extract_pdf") as full:
            with self.assertRaisesRegex(ValueError, "Sai loại tài liệu"):
                read_certificate(service, str(self.image), auto_photo=True)
            full.assert_not_called()

    def test_inconclusive_auto_does_not_run_full_certificate_ocr(self):
        service = OrganizationDocumentService()
        with patch("mingo_assistant.services.ocr.certificate_scan._orient_and_probe", return_value="unrelated"), \
                patch.object(service, "extract_pdf") as full:
            self.assertIsNone(read_certificate(service, str(self.image), auto_photo=True))
            full.assert_not_called()

    def test_cancellation_propagates_and_temp_file_is_removed(self):
        service = OrganizationDocumentService()
        paths = []
        def cancel(scanner, path, callback):
            paths.append(path)
            raise ScanCancelledError()
        with patch("mingo_assistant.services.ocr.certificate_scan._orient_and_probe", side_effect=cancel):
            with self.assertRaises(ScanCancelledError):
                read_certificate(service, str(self.image))
        self.assertTrue(paths)
        self.assertFalse(Path(paths[0]).exists())

    def test_cancel_during_photo_preparation_does_not_start_ocr(self):
        service = OrganizationDocumentService()
        def cancel(*args):
            raise ScanCancelledError()
        with patch("mingo_assistant.services.ocr.certificate_scan._orient_and_probe") as probe:
            with self.assertRaises(ScanCancelledError):
                read_certificate(service, str(self.image), callback=cancel)
            probe.assert_not_called()

    def test_perspective_candidate_is_additional_and_preserves_color(self):
        canvas = np.full((1300, 1000, 3), 30, dtype=np.uint8)
        points = np.int32([[130, 90], [880, 140], [840, 1180], [90, 1210]])
        cv2.fillConvexPoly(canvas, points, (240, 250, 250))
        cv2.putText(canvas, "DOC TEST 123", (220, 350), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (10, 10, 10), 2)
        cv2.circle(canvas, (780, 1000), 25, (20, 30, 200), -1)
        self.assertIsNotNone(_page_quad(canvas))
        ok, data = cv2.imencode(".png", canvas)
        self.assertTrue(ok)
        original = data.tobytes()
        variant = geometry_variant(original)
        self.assertIsNotNone(variant)
        corrected = cv2.imdecode(np.frombuffer(variant, np.uint8), cv2.IMREAD_COLOR)
        self.assertLess(corrected.shape[0], canvas.shape[0])
        self.assertTrue(np.any((corrected[:, :, 2] > 170) & (corrected[:, :, 1] < 60)))
        self.assertTrue(np.array_equal(canvas, cv2.imdecode(np.frombuffer(original, np.uint8), 1)))

    def test_no_page_or_weak_skew_evidence_does_not_crop_or_rotate(self):
        for canvas in (np.full((600, 900, 3), 255, np.uint8), np.zeros((600, 900, 3), np.uint8)):
            self.assertIsNone(_page_quad(canvas))
            self.assertIs(canvas, _deskew(canvas))
            _, data = cv2.imencode(".png", canvas)
            self.assertIsNone(geometry_variant(data.tobytes()))

    def test_deskew_uses_consistent_baselines_and_expands_instead_of_clipping(self):
        paper = np.full((650, 900, 3), 255, np.uint8)
        for y in range(100, 570, 45):
            cv2.line(paper, (100, y), (780, y), (0, 0, 0), 2)
        rotated = cv2.warpAffine(paper, cv2.getRotationMatrix2D((450, 325), 3, 1), (900, 650), borderValue=(255, 255, 255))
        corrected = _deskew(rotated)
        self.assertGreater(corrected.shape[0], rotated.shape[0])
        edges = cv2.Canny(cv2.cvtColor(corrected, cv2.COLOR_BGR2GRAY), 60, 160)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 1800, 55, minLineLength=300, maxLineGap=14)
        self.assertIsNotNone(lines)
        slopes = [abs(float(np.degrees(np.arctan2(y2 - y1, x2 - x1)))) for x1, y1, x2, y2 in lines[:, 0]]
        self.assertLess(float(np.median(slopes)), .6)

    def test_padded_photo_reread_aligns_names_after_unrepaired_label_words(self):
        original = "Tên công ty vit bng ting Vit: CÔNG TY TNHH GIÅI PHÁP SÓ MINH AN"
        candidate = "Tên công ty viết bằng tiếng Việt: CÔNG TY TNHH GIẢI PHÁP SỐ MINH AN"
        actual = VietnameseLineRefiner.restore_accents(original, candidate, allow_letter_repairs=False, advance_unmatched=True)
        self.assertEqual("Tên công ty vit bng ting Vit: CÔNG TY TNHH GIẢI PHÁP SỐ MINH AN", actual)
        self.assertNotEqual(actual, VietnameseLineRefiner.restore_accents(original, candidate, allow_letter_repairs=False))

    def test_photo_spacing_uses_image_evidence_without_changing_identifiers(self):
        safe = VietnameseLineRefiner._safe_photo_spacing
        self.assertTrue(safe("Số 128duong Nguyễn Thị Định", "Số 128 đường Nguyễn Thị Định"))
        self.assertTrue(safe("79/J4 đường D18", "79/J4 đường D18"))
        for original, candidate in (
            ("79/J4 đường D18", "79 J4 đường D18"),
            ("128A đường D18", "128 A đường D18"),
            ("07-02 đường D18", "0702 đường D18"),
            ("128 đường D18", "129 đường D18"),
            ("Số 128 đường Nguyn", "Số 128 đường Nguyễn"),
        ):
            self.assertFalse(safe(original, candidate))

    def test_photo_uncertainty_requests_reread_without_mutating_foreign_names_or_house_numbers(self):
        service = OrganizationDocumentService()
        original = "CÔNG TY TNHH GIÅI PHÁP SÓ MINH AN"
        self.assertGreater(service._field_quality("organization_owner_name", original), .90)
        service._photo_input = True
        self.assertLess(service._field_quality("organization_owner_name", original), .80)
        self.assertLess(service._field_quality("organization_owner_address_detail", "Số 128duong Nguyễn Thị Định"), .80)
        self.assertGreater(service._field_quality("organization_owner_address_detail", "Số 128A đường D18"), .85)

    def test_photo_address_letter_repair_requires_independent_probe_and_crop_agreement(self):
        refiner = VietnameseLineRefiner(self.root)
        original = "Số 128 đường Nguyn Thị Đnh, Phường Bình Trưng,"
        candidate = "Số 128 đường Nguyễn Thị Định, Phường Bình Trưng,"
        refiner.address_candidates = {0: candidate}
        lines = [(None, original, .92)]
        self.assertEqual(lines, refiner.corroborate_photo_addresses(lines, "unrelated text"))
        self.assertEqual(candidate, refiner.corroborate_photo_addresses(lines, "Số 128duongNguyenThiDinh, PhuongBinhTrung,")[0][1])
        refiner.address_candidates = {0: candidate.replace("128", "129")}
        self.assertEqual(lines, refiner.corroborate_photo_addresses(lines, candidate.replace("128", "129")))

    def test_enhanced_geometry_runs_for_photos_only_and_retains_original_variants(self):
        service = OrganizationDocumentService()
        with certificate_pdf(str(self.image)) as pdf, fitz.open(pdf) as document, \
                patch.object(service, "_get_legacy_engine"), \
                patch.object(service, "_extract_page_with_ocr", return_value=ERC_TEXT) as ocr, \
                patch("mingo_assistant.services.ocr.certificate_photo.geometry_variant", return_value=b"geometry") as geometry:
            service._extract_with_ocr(document, None, enhanced=True)
            geometry.assert_not_called()
            self.assertEqual(2, ocr.call_count)
            ocr.reset_mock()
            service._photo_input = True
            service._extract_with_ocr(document, None, enhanced=True)
            geometry.assert_called_once()
            self.assertEqual(3, ocr.call_count)

    def run_worker(self, kind="auto", explicit="auto", identity=None, service=None):
        worker = DocumentScanWorker(ScanRequest(str(self.image), kind, explicit), identity or MagicMock(), service or OrganizationDocumentService())
        payloads = []
        worker.finished.connect(payloads.append)
        worker.run()
        self.assertEqual(1, len(payloads))
        return payloads[0]

    def test_auto_worker_keeps_fast_qr_without_certificate_probe(self):
        identity = MagicMock()
        identity.scan_qr.return_value = "031234567890|123456789|TEST|01011990|Nam|Ha Noi|01012025"
        with patch("mingo_assistant.ui.views.business_registration.scan_worker.read_certificate") as read:
            payload = self.run_worker(identity=identity)
            self.assertEqual("cccd", payload["kind"])
            self.assertEqual("qr", payload["result"].method)
            read.assert_not_called()
            identity.scan_identity.assert_not_called()

    def test_auto_worker_routes_certificate_photo_not_identity_ocr(self):
        identity = MagicMock()
        identity.scan_qr.side_effect = RuntimeError("no identity QR")
        result = MagicMock(document_type="erc")
        with patch("mingo_assistant.ui.views.business_registration.scan_worker.read_certificate", return_value=result):
            payload = self.run_worker(identity=identity)
            self.assertEqual("erc", payload["kind"])
            self.assertIs(result, payload["result"])
            identity.scan_identity.assert_not_called()

    def test_explicit_identity_never_probes_certificate_and_auto_inconclusive_falls_back(self):
        identity = MagicMock()
        identity.scan_qr.side_effect = RuntimeError("no QR")
        identity.scan_identity.return_value = IdentityScanResult("cccd text", "ocr", str(self.image))
        with patch("mingo_assistant.ui.views.business_registration.scan_worker.read_certificate", return_value=None) as read:
            payload = self.run_worker(kind="cccd", explicit="cccd", identity=identity)
            self.assertEqual("ocr", payload["result"].method)
            read.assert_not_called()
            payload = self.run_worker(identity=identity)
            self.assertEqual("cccd", payload["kind"])
            read.assert_called_once()

    def test_auto_unknown_photo_error_explains_manual_dropdown_instead_of_calling_it_invalid_cccd(self):
        identity = MagicMock()
        identity.scan_qr.side_effect = RuntimeError("no QR")
        identity.scan_identity.side_effect = RuntimeError("unreadable")
        with patch("mingo_assistant.ui.views.business_registration.scan_worker.read_certificate", return_value=None):
            payload = self.run_worker(identity=identity)
            self.assertIn("Loại tài liệu", payload["error"])
            self.assertIn("ERC", payload["error"])

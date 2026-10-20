from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import MagicMock, patch

import cv2
import fitz
import numpy as np

from mingo_assistant.services.ocr.vietnamese_document_ocr import VietnameseDocumentOcr
from mingo_assistant.services.organization_documents.organization_document_service import OrganizationDocumentService


class VietnameseDocumentOcrTests(TestCase):
    def test_quick_scan_preserves_pixel_resolution_of_small_physical_page(self) -> None:
        service = OrganizationDocumentService()
        service._legacy_engine = MagicMock()
        with fitz.open() as document:
            document.new_page(width=259.5, height=395.5)
            with patch.object(service, "_extract_page_with_ocr", return_value="certificate") as ocr:
                self.assertEqual("certificate", service._extract_first_page_for_type_detection(document, None))

        image = cv2.imdecode(np.frombuffer(ocr.call_args.args[1], dtype=np.uint8), cv2.IMREAD_COLOR)
        # At the old 3.1x cap this page was only 805px wide, too small to
        # separate the address's letters from the security pattern.
        self.assertGreater(image.shape[1], 1400)
        self.assertGreater(image.shape[0], 1500)
        self.assertLess(image.shape[0], 1600)

    def test_quick_background_cleanup_lightens_yellow_but_preserves_dark_ink(self) -> None:
        image = np.full((60, 120, 3), 255, dtype=np.uint8)
        image[10:50, 10:100] = (80, 180, 190)
        image[25:30, 20:80] = (25, 25, 25)
        _, encoded = cv2.imencode(".png", image)

        cleaned = OrganizationDocumentService._suppress_certificate_background(encoded.tobytes())
        gray = cv2.imdecode(np.frombuffer(cleaned, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)

        self.assertGreater(int(gray[15, 15]), int(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)[15, 15]))
        self.assertEqual(25, int(gray[27, 25]))

    def test_quick_background_cleanup_keeps_monochrome_and_invalid_inputs(self) -> None:
        image = np.full((40, 80, 3), 255, dtype=np.uint8)
        image[10:20, 20:60] = (25, 25, 25)
        _, encoded = cv2.imencode(".png", image)
        for original in (encoded.tobytes(), b"not-an-image"):
            with self.subTest(valid=original != b"not-an-image"):
                self.assertEqual(original, OrganizationDocumentService._suppress_certificate_background(original))

    def test_complete_primary_erc_does_not_run_second_full_ocr_engine(self) -> None:
        text = (
            "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP\n"
            "Mã số doanh nghiệp: 0312345678\n"
            "Tên công ty viết bằng tiếng Việt: CÔNG TY TNHH KIỂM THỬ\n"
            "2. Địa chỉ trụ sở chính: Số 12 đường Nguyễn Thị Định, Việt Nam\n"
        )
        service = OrganizationDocumentService(bundle_root=Path(__file__).resolve().parents[2])
        module = "mingo_assistant.services.organization_documents.organization_document_service"
        with TemporaryDirectory() as directory:
            path = Path(directory) / "scan.pdf"
            path.touch()
            with patch(f"{module}.fitz.open"), \
                    patch(f"{module}.extract_certificate_text", return_value=""), \
                    patch.object(service, "_extract_first_page_for_type_detection", return_value=text.split("Mã số", 1)[0]), \
                    patch.object(service, "_extract_with_ocr", return_value=text) as ocr:
                result = service.extract_pdf(path)

        ocr.assert_called_once()
        self.assertEqual(("pdf_text", "ppocr_v6"), result.processing_route)

    def test_erc_stops_after_first_page_when_required_fields_are_complete(self) -> None:
        text = (
            "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP\n"
            "Mã số doanh nghiệp: 0312345678\n"
            "Tên công ty viết bằng tiếng Việt: CÔNG TY TNHH KIỂM THỬ\n"
            "2. Địa chỉ trụ sở chính: Số 12 đường Nguyễn Thị Định, Việt Nam\n"
        )
        for complete_first_page in (True, False):
            with self.subTest(complete_first_page=complete_first_page):
                service = OrganizationDocumentService()
                service._legacy_engine = MagicMock()
                first, second = MagicMock(), MagicMock()
                for page in (first, second):
                    page.rect.width, page.rect.height = 600, 800
                    page.get_pixmap.return_value.tobytes.return_value = b"page"
                document = MagicMock()
                document.page_count = 2
                document.__iter__.return_value = iter([first, second])
                caption, address = text.split("2. Địa chỉ", 1)
                readings = [text] if complete_first_page else [caption, "2. Địa chỉ" + address]
                with patch.object(service, "_extract_page_with_ocr", side_effect=readings) as ocr:
                    result = service._extract_with_ocr(document, None)

                self.assertEqual(1 if complete_first_page else 2, ocr.call_count)
                if complete_first_page:
                    second.get_pixmap.assert_not_called()
                else:
                    second.get_pixmap.assert_called_once()
                self.assertIn("Nguyễn Thị Định", result)

    def test_bundled_ppocrv6_models_are_detected(self) -> None:
        project_root = Path(__file__).resolve().parents[2]

        ocr = VietnameseDocumentOcr(project_root)

        self.assertTrue(ocr.is_available)

    def test_missing_models_are_reported_without_initializing_engine(self) -> None:
        ocr = VietnameseDocumentOcr(Path("missing-project-root"))

        self.assertFalse(ocr.is_available)
        with self.assertRaises(FileNotFoundError):
            ocr.recognize(b"not-an-image")

    def test_organization_pdf_retries_legacy_ocr_when_v6_misses_certificate_labels(self) -> None:
        with TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "certificate.pdf"
            pdf_path.touch()
            service = OrganizationDocumentService(bundle_root=Path(__file__).resolve().parents[2])
            legacy_text = "\n".join((
                "GIAY CHUNG NHAN DANG KY DOANH NGHIEP",
                "Ma so doanh nghiep: 0123456789",
                "1. Ten cong ty",
                "Ten cong ty viet bang tieng Viet: CONG TY TNHH KIEM THU",
                "2. Dia chi tru so chinh: 1 DUONG MAU, VIET NAM",
            ))
            with patch("mingo_assistant.services.organization_documents.organization_document_service.fitz.open") as open_pdf:
                open_pdf.return_value.__enter__.return_value.__iter__.return_value = iter(())
                with patch.object(
                    service,
                    "_extract_with_ocr",
                    side_effect=("unrecognized OCR text", legacy_text, legacy_text),
                ) as ocr:
                    result = service.extract_pdf(pdf_path)

        self.assertEqual("0123456789", result.values["organization_owner_registration_number"])
        self.assertEqual(2, ocr.call_count)
        self.assertTrue(ocr.call_args.kwargs["use_legacy"])

    def test_certificate_accepts_common_ocr_errors_in_registration_label(self) -> None:
        service = OrganizationDocumentService()
        for label in ("Mã s doanh nghip", "Ma s6 doanh nghiep", "Mã số doanh nghiệp"):
            with self.subTest(label=label):
                text = "\n".join((
                    "GIÁY CHÚNG NHN ĐĂNG KÝ DOANH NGHIĘP",
                    f"{label}: 3703192163",
                    "1. Tên công ty",
                    "Tên công ty viết bằng tiếng Việt: CÔNG TY TNHH KIỂM THỬ",
                    "2. Địa chỉ trụ sở chính: 1 ĐƯỜNG MẪU, VIỆT NAM",
                ))
                result = service._extract_supported_document(text, "ocr")

                self.assertIsNotNone(result)
                self.assertEqual("3703192163", result.values["organization_owner_registration_number"])

    def test_partial_v6_result_retries_legacy_and_prefers_complete_result(self) -> None:
        with TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "certificate.pdf"
            pdf_path.touch()
            service = OrganizationDocumentService(bundle_root=Path(__file__).resolve().parents[2])
            header = "\n".join((
                "GIAY CHUNG NHAN DANG KY DOANH NGHIEP",
                "Ma so doanh nghiep: 0123456789",
                "1. Ten cong ty",
                "Ten cong ty viet bang tieng Viet: CONG TY TNHH KIEM THU",
            ))
            with patch("mingo_assistant.services.organization_documents.organization_document_service.fitz.open") as open_pdf:
                open_pdf.return_value.__enter__.return_value.__iter__.return_value = iter(())
                with patch.object(
                    service,
                    "_extract_with_ocr",
                    side_effect=(
                        header,
                        header + "\n2. Dia chi tru so chinh: 1 DUONG MAU, VIET NAM",
                        header + "\n2. Dia chi tru so chinh: 1 DUONG MAU, VIET NAM",
                    ),
                ) as ocr:
                    result = service.extract_pdf(pdf_path)

        self.assertTrue(result.values["organization_owner_address_detail"])
        self.assertEqual(2, ocr.call_count)
        self.assertTrue(ocr.call_args.kwargs["use_legacy"])

    def test_enhanced_pass_runs_when_both_standard_engines_miss_a_core_field(self) -> None:
        with TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "certificate.pdf"
            pdf_path.touch()
            service = OrganizationDocumentService(bundle_root=Path(__file__).resolve().parents[2])
            partial = "\n".join((
                "GIAY CHUNG NHAN DANG KY DOANH NGHIEP",
                "Ma so doanh nghiep: 0123456789",
                "1. Ten cong ty",
                "Ten cong ty viet bang tieng Viet: CONG TY TNHH KIEM THU",
            ))
            complete = partial + "\n2. Dia chi tru so chinh: 1 DUONG MAU, VIET NAM"
            with patch("mingo_assistant.services.organization_documents.organization_document_service.fitz.open") as open_pdf:
                open_pdf.return_value.__enter__.return_value.__iter__.return_value = iter(())
                with patch.object(
                    service,
                    "_extract_with_ocr",
                    side_effect=(partial, partial, complete),
                ) as ocr:
                    result = service.extract_pdf(pdf_path)

        self.assertTrue(result.values["organization_owner_address_detail"])
        self.assertEqual(3, ocr.call_count)
        self.assertTrue(ocr.call_args.kwargs["enhanced"])
        self.assertIn("ppocr_v6_enhanced", result.processing_route)

    def test_merges_best_fields_from_different_ocr_engines(self) -> None:
        service = OrganizationDocumentService()
        ppocr = service._document_result(
            {
                "organization_owner_name": "CÔNG TY TNHH KIỂM THỬ",
                "organization_owner_registration_number": "0312345678",
                "organization_owner_address_detail": "1 TEST",
                "organization_owner_email": "contact@example.com",
            },
            "ppocr text",
            "ocr",
            source="ppocr_v6",
        )
        rapidocr = service._document_result(
            {
                "organization_owner_name": "CONG TY TNHH KIEM THU",
                "organization_owner_registration_number": "O312345678",
                "organization_owner_address_detail": "Số 1 đường Mẫu, Phường 5, Thành phố Hồ Chí Minh",
                "organization_owner_email": "contact example.com",
            },
            "rapidocr text",
            "ocr",
            source="rapidocr",
        )

        result = service._merge_results(ppocr, rapidocr)

        self.assertIsNotNone(result)
        self.assertEqual("0312345678", result.values["organization_owner_registration_number"])
        self.assertEqual(
            "Số 1 đường Mẫu, Phường 5, Thành phố Hồ Chí Minh",
            result.values["organization_owner_address_detail"],
        )
        self.assertEqual("contact@example.com", result.values["organization_owner_email"])
        self.assertEqual("ppocr_v6", result.field_sources["organization_owner_registration_number"])
        self.assertEqual("rapidocr", result.field_sources["organization_owner_address_detail"])
        self.assertGreater(result.quality_score, ppocr.quality_score)

    def test_enhanced_preprocessing_returns_readable_png(self) -> None:
        image = np.full((180, 500), 225, dtype=np.uint8)
        cv2.putText(image, "MA SO DOANH NGHIEP: 0312345678", (12, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 135, 1)
        success, encoded = cv2.imencode(".png", image)
        self.assertTrue(success)

        processed = OrganizationDocumentService._preprocess_for_ocr(encoded.tobytes())
        decoded = cv2.imdecode(np.frombuffer(processed, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)

        self.assertIsNotNone(decoded)
        self.assertEqual(image.shape, decoded.shape)
        self.assertGreater(float(decoded.std()), float(image.std()))

    def test_enhanced_preprocessing_produces_complementary_scan_variants(self) -> None:
        image = np.full((240, 700), 235, dtype=np.uint8)
        gradient = np.tile(np.linspace(0, 30, image.shape[1], dtype=np.uint8), (image.shape[0], 1))
        image = cv2.subtract(image, gradient)
        cv2.putText(
            image,
            "DIA CHI TRU SO CHINH: 12 NGUYEN THI DINH",
            (10, 125),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.72,
            115,
            1,
        )
        success, encoded = cv2.imencode(".png", image)
        self.assertTrue(success)

        variants = OrganizationDocumentService._preprocess_variants_for_ocr(encoded.tobytes())

        self.assertEqual(2, len(variants))
        for variant in variants:
            decoded = cv2.imdecode(np.frombuffer(variant, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            self.assertIsNotNone(decoded)
            self.assertEqual(image.shape, decoded.shape)

    def test_enhanced_variant_ranking_prefers_document_anchors_and_accents(self) -> None:
        service = OrganizationDocumentService()
        incomplete = "GIAY CHUNG NHAN\nCONG TY TNHH KIEM THU"
        complete = (
            "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP\n"
            "Mã số doanh nghiệp: 0312345678\n"
            "Tên công ty: CÔNG TY TNHH KIỂM THỬ\n"
            "Địa chỉ trụ sở chính: 12 Nguyễn Thị Định"
        )

        self.assertGreater(service._ocr_text_quality(complete), service._ocr_text_quality(incomplete))

    def test_enhanced_pass_retains_each_image_variant_for_field_level_merge(self) -> None:
        service = OrganizationDocumentService()
        service._legacy_engine = MagicMock()
        page = MagicMock()
        page.rect.width = 600
        page.rect.height = 800
        page.get_pixmap.return_value.tobytes.return_value = b"rendered-page"
        document = MagicMock()
        document.page_count = 1
        document.__iter__.return_value = iter([page])
        weak = "GIAY CHUNG NHAN"
        strong = (
            "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP\n"
            "Mã số doanh nghiệp: 0312345678\nĐịa chỉ trụ sở chính: Hà Nội"
        )

        with patch.object(
            service,
            "_preprocess_variants_for_ocr",
            return_value=[b"contrast", b"binary"],
        ), patch.object(
            service,
            "_extract_page_with_ocr",
            side_effect=[weak, strong],
        ):
            selected = service._extract_with_ocr(document, None, enhanced=True)

        self.assertEqual(strong, selected)
        self.assertEqual((weak, strong), service._last_enhanced_text_candidates)

    def test_address_cleanup_preserves_detail_and_removes_administrative_suffix(self) -> None:
        service = OrganizationDocumentService()
        cases = (
            (
                "Ô 17 Lô I37 Đuòng DE1, Khu TĐC M Phưóc 3, Phưòng Thói Hòa, Thành ph Hồ Chí Minh, Vit Nam",
                "Ô 17 Lô I37 đường DE1, Khu TĐC Mỹ Phước 3",
            ),
            (
                "Nhà xưởng số 15 đường Tien Phong 13 (nhà xưởng, khu sản xuất loại 2, lô TR-A-04) "
                "khu công nghiệp BW Supply Chain City, Phường Bình Dương, Thành phố Hồ Chí Minh, Việt Nam",
                "Nhà xưởng số 15 đường Tiên Phong 13 (nhà xưởng, khu sản xuất loại 2, lô TR-A-04) "
                "khu công nghiệp BW Supply Chain City",
            ),
            (
                "204/3 Trn Bá Giao, Phung 5, Qun Gò Váp, Thành phó Hò Chi Minh, Vit Nam",
                "204/3 Trần Bá Giao",
            ),
        )
        for raw_address, expected_detail in cases:
            with self.subTest(raw_address=raw_address):
                values = service._organization_address_values(raw_address)
                self.assertEqual(expected_detail, values["organization_owner_address_detail"])

    def test_domain_phrases_repair_real_erc_ocr_damage(self) -> None:
        service = OrganizationDocumentService()

        self.assertEqual(
            "CÔNG TY TNHH TRANG TRÍ NỘI THẤT HP",
            service._restore_vietnamese_phrases(
                "CÔNG TY TNHH TRANG TRÍ NI THÁT HP"
            ),
        )
        self.assertEqual(
            "CÔNG TY TNHH THƯƠNG MẠI NÔNG SẢN THANH HOA",
            service._restore_vietnamese_phrases(
                "CÔNG TY TNHH THƯƠNG MẠI NÔNG SÅN THANH HOA"
            ),
        )

    def test_fuzzy_certificate_labels_keep_v6_name_and_address_available(self) -> None:
        service = OrganizationDocumentService()
        text = "\n".join((
            "GIÁY CHÚNG NHĂN DĂNG KÝ DOANH NGHIP",
            "Mã só doanh nghip: 0314690354",
            "1. Tên công ty",
            "Tên công ty vit băng ting Vit: CÔNG TY TNHH TRANG TRÍ NOI THÁT HP",
            "2. Đa chi tru s chính",
            "204/3 Trn Bá Giao, Phung 5, Qun Gò Váp, Thành phó Hò Chi Minh, Vit Nam",
            "Dięn thoai: 0819902610",
        ))

        result = service._extract_supported_document(text, "ocr", source="ppocr_v6")

        self.assertIsNotNone(result)
        self.assertEqual("CÔNG TY TNHH TRANG TRÍ NỘI THẤT HP", result.values["organization_owner_name"])
        self.assertEqual("204/3 Trần Bá Giao", result.values["organization_owner_address_detail"])

    def test_erc_quality_penalizes_missing_letters_and_glued_words(self) -> None:
        service = OrganizationDocumentService()

        correct = service._field_quality(
            "organization_owner_address_detail",
            "Số 757D, đường Nguyễn Thị Định, phường Bình Trưng",
        )
        missing_letters = service._field_quality(
            "organization_owner_address_detail",
            "Số 757D, đường Nguyn Th Đnh, phường Bình Trưng",
        )
        glued_words = service._field_quality(
            "organization_owner_address_detail",
            "Số 15 ThanhphoHaNoi",
        )

        self.assertGreater(correct, missing_letters)
        self.assertLess(missing_letters, 0.80)
        self.assertLess(glued_words, 0.80)

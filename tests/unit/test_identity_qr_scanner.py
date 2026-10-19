from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from mingo_assistant.services.ocr.ocr_service import OcrService
from mingo_assistant.services.qr import IdentityQrScanner


class IdentityQrScannerTests(unittest.TestCase):
    def test_legacy_ocr_service_is_a_compatible_qr_scanner(self) -> None:
        self.assertIsInstance(OcrService(), IdentityQrScanner)

    def test_bundle_root_controls_offline_qr_model_location(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            scanner = IdentityQrScanner(root)

            self.assertEqual(scanner._resource_root(), root)
            with self.assertRaises(FileNotFoundError):
                scanner.scan_qr(root / "missing-card.png")

    def test_scan_identity_tries_back_side_when_front_qr_is_unreadable(self) -> None:
        payload = "012345678901|000000000|NGUYEN VAN TEST|01011990|Nam|Ha Noi|01012024"
        with TemporaryDirectory() as temp_dir:
            front = Path(temp_dir) / "front.jpg"
            back = Path(temp_dir) / "back.jpg"
            front.touch()
            back.touch()
            scanner = IdentityQrScanner()

            with patch.object(scanner, "scan_qr", side_effect=[RuntimeError("no QR"), payload]) as scan_qr:
                result = scanner.scan_identity([front, back])

        self.assertEqual(result.method, "qr")
        self.assertEqual(result.raw_text, payload)
        self.assertEqual(result.source_path, str(back))
        self.assertEqual(scan_qr.call_count, 2)

    def test_scan_identity_falls_back_to_combined_ocr_for_both_sides(self) -> None:
        with TemporaryDirectory() as temp_dir:
            front = Path(temp_dir) / "front.jpg"
            back = Path(temp_dir) / "back.jpg"
            front.touch()
            back.touch()
            scanner = IdentityQrScanner()

            with (
                patch.object(scanner, "scan_qr", side_effect=RuntimeError("no QR")),
                patch.object(
                    scanner,
                    "_recognize_identity_text",
                    side_effect=[
                        "CAN CUOC CONG DAN\nSo: 012345678901\nHo va ten: NGUYEN VAN TEST",
                        "Noi cu tru: Ha Noi",
                    ],
                ),
            ):
                result = scanner.scan_identity([front, back])

        self.assertEqual(result.method, "ocr")
        self.assertIn("--- scan 1 ---\nCAN CUOC CONG DAN", result.raw_text)
        self.assertIn("--- scan 2 ---\nNoi cu tru: Ha Noi", result.raw_text)

    def test_scan_identity_rejects_non_identity_ocr_text(self) -> None:
        with TemporaryDirectory() as temp_dir:
            image = Path(temp_dir) / "not-an-id.jpg"
            image.touch()
            scanner = IdentityQrScanner()

            with (
                patch.object(scanner, "scan_qr", side_effect=RuntimeError("no QR")),
                patch.object(scanner, "_recognize_identity_text", return_value="INVOICE\nTOTAL: 100000"),
            ):
                with self.assertRaisesRegex(RuntimeError, "không phải CCCD"):
                    scanner.scan_identity([image])

    def test_qr_payload_validation_rejects_unrelated_codes(self) -> None:
        scanner = IdentityQrScanner()

        self.assertEqual(scanner._normalize_cccd_qr_payload("https://example.com"), "")
        self.assertEqual(scanner._normalize_cccd_qr_payload("123|short|payload"), "")
        self.assertTrue(
            scanner._normalize_cccd_qr_payload(
                "012345678901|000000000|NGUYEN VAN TEST|01011990|Nam|Ha Noi|01012024"
            )
        )


if __name__ == "__main__":
    unittest.main()

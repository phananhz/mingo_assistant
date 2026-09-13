from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

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


if __name__ == "__main__":
    unittest.main()

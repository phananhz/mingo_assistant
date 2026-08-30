from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable


class OcrService:
    """Offline QR reader for Vietnamese citizen identity cards.

    The class name is retained temporarily so existing UI code keeps working;
    all OCR engines and image-to-text processing have been removed.
    """

    def __init__(self) -> None:
        self._wechat_detector: Any | None = None
        self._wechat_checked = False

    def scan_qr(
        self,
        image_path: str | Path,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> str:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy ảnh: {path}")

        if progress_callback:
            progress_callback(10, "Đang đọc ảnh CCCD")
        image = self._read_image_for_cv(path)
        if image is None:
            raise RuntimeError("Không thể đọc ảnh. Hãy kiểm tra định dạng file ảnh.")

        candidates = self._qr_scan_candidates(image)
        if progress_callback:
            progress_callback(25, "Đang quét QR bằng bộ nhận diện nâng cao")
        value = self._scan_qr_with_wechat([image, *candidates])
        if value:
            if progress_callback:
                progress_callback(95, "Đã tìm thấy mã QR")
            return value

        if progress_callback:
            progress_callback(65, "Đang thử bộ giải mã QR dự phòng")
        value = self._scan_qr_with_zxing(candidates)
        if value:
            if progress_callback:
                progress_callback(95, "Đã tìm thấy mã QR")
            return value

        if progress_callback:
            progress_callback(72, "Đang thử bộ giải mã ZBar")
        value = self._scan_qr_with_pyzbar(candidates)
        if value:
            if progress_callback:
                progress_callback(95, "Đã tìm thấy mã QR")
            return value

        try:
            import cv2
        except Exception as exc:
            raise RuntimeError("Máy chưa có OpenCV để quét QR.") from exc

        detector = cv2.QRCodeDetectorAruco() if hasattr(cv2, "QRCodeDetectorAruco") else cv2.QRCodeDetector()
        total = max(1, len(candidates))
        for index, candidate in enumerate(candidates, start=1):
            if progress_callback:
                progress_callback(70 + int(((index - 1) / total) * 22), f"Đang quét QR {index}/{total}")
            value = self._detect_qr_value(detector, candidate)
            if value:
                if progress_callback:
                    progress_callback(95, "Đã tìm thấy mã QR")
                return value

        raise RuntimeError(
            "Không tìm thấy mã QR có thể đọc được. Hãy dùng ảnh gốc, chụp rõ góc phải trên CCCD "
            "và tránh ảnh chụp màn hình đã bị nén."
        )

    def _read_image_for_cv(self, image_path: Path) -> Any | None:
        """Read image paths containing Vietnamese/Unicode characters on Windows."""
        try:
            import cv2
            import numpy as np
        except Exception:
            return None

        try:
            image_bytes = np.fromfile(str(image_path), dtype=np.uint8)
            if image_bytes.size:
                image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
                if image is not None:
                    return image
        except (OSError, ValueError):
            pass

        try:
            from PySide6.QtGui import QImage, QImageReader

            reader = QImageReader(str(image_path))
            reader.setAutoTransform(True)
            qt_image = reader.read()
            if qt_image.isNull():
                return None
            qt_image = qt_image.convertToFormat(QImage.Format.Format_RGBA8888)
            rgba = np.frombuffer(qt_image.bits(), dtype=np.uint8).reshape((qt_image.height(), qt_image.bytesPerLine()))
            rgba = rgba[:, : qt_image.width() * 4].reshape((qt_image.height(), qt_image.width(), 4)).copy()
            return cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
        except Exception:
            return None

    def _qr_scan_candidates(self, image: Any) -> list[Any]:
        try:
            import cv2
        except Exception:
            return [image]

        height, width = image.shape[:2]
        base = image
        if max(height, width) < 1800:
            scale = 1800 / max(height, width)
            base = cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_CUBIC)
        base_height, base_width = base.shape[:2]
        crop_boxes = [
            (0.55, 0.00, 1.00, 0.45),
            (0.68, 0.00, 1.00, 0.36),
            (0.50, 0.00, 1.00, 0.60),
            (0.00, 0.00, 1.00, 1.00),
        ]
        candidates: list[Any] = []
        for left, top, right, bottom in crop_boxes:
            crop = base[int(base_height * top) : int(base_height * bottom), int(base_width * left) : int(base_width * right)]
            if crop.size:
                candidates.extend(self._qr_variants(crop))
        return candidates or [base]

    def _qr_variants(self, image: Any) -> list[Any]:
        try:
            import cv2
        except Exception:
            return [image]

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return [
            image,
            gray,
            cv2.createCLAHE(clipLimit=2.4, tileGridSize=(8, 8)).apply(gray),
            cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        ]

    def _scan_qr_with_wechat(self, candidates: list[Any]) -> str:
        detector = self._get_wechat_detector()
        if detector is None:
            return ""
        for candidate in candidates:
            try:
                values, _ = detector.detectAndDecode(candidate)
            except Exception:
                continue
            for value in values:
                if value:
                    return str(value).strip()
        return ""

    def _get_wechat_detector(self) -> Any | None:
        if self._wechat_checked:
            return self._wechat_detector
        self._wechat_checked = True
        try:
            import cv2
            model_dir = self._resource_root() / "assets" / "qr_models" if getattr(sys, "frozen", False) else Path("assets") / "qr_models"
            model_files = [
                model_dir / "detect.prototxt",
                model_dir / "detect.caffemodel",
                model_dir / "sr.prototxt",
                model_dir / "sr.caffemodel",
            ]
            if not all(path.exists() for path in model_files):
                return None
            self._wechat_detector = cv2.wechat_qrcode_WeChatQRCode(*(str(path) for path in model_files))
        except Exception:
            self._wechat_detector = None
        return self._wechat_detector

    def _resource_root(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys._MEIPASS)
        return Path(__file__).resolve().parents[4]

    def _scan_qr_with_zxing(self, candidates: list[Any]) -> str:
        try:
            import zxingcpp
        except Exception:
            return ""
        for candidate in candidates:
            try:
                codes = zxingcpp.read_barcodes(
                    candidate,
                    formats=zxingcpp.BarcodeFormat.QRCode,
                    try_rotate=True,
                    try_downscale=False,
                )
            except Exception:
                continue
            for code in codes:
                value = getattr(code, "text", "")
                if value:
                    return str(value).strip()
        return ""

    def _scan_qr_with_pyzbar(self, candidates: list[Any]) -> str:
        try:
            from pyzbar.pyzbar import ZBarSymbol, decode
        except Exception:
            return ""
        for candidate in candidates:
            try:
                codes = decode(candidate, symbols=[ZBarSymbol.QRCODE])
            except Exception:
                continue
            for code in codes:
                value = getattr(code, "data", b"")
                if isinstance(value, bytes):
                    value = value.decode("utf-8", errors="replace")
                if value:
                    return str(value).strip()
        return ""
    def _detect_qr_value(self, detector: Any, image: Any) -> str:
        try:
            value, _, _ = detector.detectAndDecode(image)
            if value:
                return value.strip()
        except Exception:
            pass
        try:
            value, _, _ = detector.detectAndDecodeCurved(image)
            if value:
                return value.strip()
        except Exception:
            pass
        try:
            ok, values, _, _ = detector.detectAndDecodeMulti(image)
            if ok:
                for value in values:
                    if value:
                        return str(value).strip()
        except Exception:
            pass
        return ""



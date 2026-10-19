from __future__ import annotations

import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class IdentityScanResult:
    """Text recognized from a CCCD image and the method that produced it."""

    raw_text: str
    method: str
    source_path: str


class IdentityQrScanner:
    """Offline CCCD scanner: QR first, then local OCR as a fallback."""

    def __init__(self, bundle_root: Path | None = None) -> None:
        self._bundle_root = bundle_root
        self._wechat_detector: Any | None = None
        self._wechat_checked = False
        self._identity_ocr_engine: Any | None = None

    def scan_identity(
        self,
        image_paths: Iterable[str | Path],
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> IdentityScanResult:
        """Scan all supplied card sides, preferring the authoritative QR payload."""
        paths: list[Path] = []
        seen: set[str] = set()
        for raw_path in image_paths:
            path = Path(raw_path)
            key = str(path.resolve()) if path.exists() else str(path)
            if key not in seen:
                paths.append(path)
                seen.add(key)
        if not paths:
            raise FileNotFoundError("Chưa có ảnh CCCD để quét.")
        missing = [path for path in paths if not path.exists()]
        if len(missing) == len(paths):
            raise FileNotFoundError(f"Không tìm thấy ảnh: {missing[0]}")

        valid_paths = [path for path in paths if path.exists()]
        qr_errors: list[str] = []
        for index, path in enumerate(valid_paths):
            if progress_callback:
                progress_callback(5 + index * 25, f"Đang tìm QR trên ảnh {index + 1}/{len(valid_paths)}")
            try:
                value = self.scan_qr(path)
            except Exception as exc:
                qr_errors.append(str(exc))
                continue
            if progress_callback:
                progress_callback(72, "Đã đọc được QR CCCD")
            return IdentityScanResult(value, "qr", str(path))

        recognized_pages: list[str] = []
        recognized_source = ""
        for index, path in enumerate(valid_paths):
            if progress_callback:
                progress_callback(
                    72 + int((index / max(1, len(valid_paths))) * 23),
                    f"Không đọc được QR, đang OCR ảnh {index + 1}/{len(valid_paths)}",
                )
            try:
                text = self._recognize_identity_text(path)
            except Exception:
                continue
            if text.strip():
                if not recognized_source:
                    recognized_source = str(path)
                recognized_pages.append(f"--- scan {index + 1} ---\n{text.strip()}")

        if recognized_pages:
            recognized_text = "\n".join(recognized_pages)
            if not self._looks_like_identity_ocr_text(recognized_text):
                raise RuntimeError(
                    "Tài liệu ảnh không phải CCCD/Căn cước hoặc không đủ rõ để xác minh loại tài liệu."
                )
            if progress_callback:
                progress_callback(96, "Đã nhận diện CCCD bằng OCR")
            return IdentityScanResult(recognized_text, "ocr", recognized_source)

        detail = qr_errors[-1] if qr_errors else "Không đọc được nội dung ảnh."
        raise RuntimeError(
            "Không đọc được QR hoặc chữ trên CCCD. Hãy dùng ảnh gốc, chụp đủ hai mặt, "
            f"rõ nét và không bị lóa. Chi tiết: {detail}"
        )

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

    def _recognize_identity_text(self, image_path: Path) -> str:
        from mingo_assistant.services.ocr.vietnamese_document_ocr import VietnameseDocumentOcr

        if self._identity_ocr_engine is None:
            self._identity_ocr_engine = VietnameseDocumentOcr(self._resource_root())
        lines = self._identity_ocr_engine.recognize(image_path.read_bytes())
        return "\n".join(text for text, _score in lines if text.strip())

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
            (0.62, 0.00, 1.00, 0.42),
            (0.68, 0.02, 0.99, 0.36),
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
        sharpened = cv2.addWeighted(gray, 1.7, cv2.GaussianBlur(gray, (0, 0), 1.2), -0.7, 0)
        clahe = cv2.createCLAHE(clipLimit=2.4, tileGridSize=(8, 8)).apply(gray)
        otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        adaptive = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            7,
        )

        def enlarged(source: Any, scale: float) -> Any:
            height, width = source.shape[:2]
            resized = cv2.resize(source, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_CUBIC)
            border = max(16, int(min(resized.shape[:2]) * 0.05))
            return cv2.copyMakeBorder(resized, border, border, border, border, cv2.BORDER_CONSTANT, value=255)

        return [
            image,
            gray,
            sharpened,
            clahe,
            otsu,
            adaptive,
            enlarged(gray, 1.5),
            enlarged(gray, 3.0),
            enlarged(adaptive, 3.0),
        ]

    def _normalize_cccd_qr_payload(self, value: Any) -> str:
        text = unicodedata.normalize("NFC", str(value or "")).replace("\x00", "").lstrip("\ufeff").strip()
        parts = [part.strip() for part in re.split(r"\|+", text) if part.strip()]
        first_digits = re.sub(r"\D", "", parts[0]) if parts else ""
        if len(parts) < 6 or not re.fullmatch(r"\d{12}", first_digits):
            return ""
        return text

    @staticmethod
    def _looks_like_identity_ocr_text(value: str) -> bool:
        normalized = unicodedata.normalize("NFD", value or "")
        folded = "".join(
            character
            for character in normalized
            if unicodedata.category(character) != "Mn"
        ).lower().replace("đ", "d")
        score = 2 if re.search(r"\b\d{12}\b", folded) else 0
        marker_groups = (
            ("can cuoc", "citizen identity", "identity card"),
            ("ho va ten", "full name"),
            ("ngay sinh", "date of birth"),
            ("gioi tinh", "sex"),
            ("quoc tich", "nationality"),
            ("noi cu tru", "thuong tru", "place of residence"),
        )
        score += sum(any(marker in folded for marker in group) for group in marker_groups)
        return score >= 3

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
                normalized = self._normalize_cccd_qr_payload(value)
                if normalized:
                    return normalized
        return ""

    def _get_wechat_detector(self) -> Any | None:
        if self._wechat_checked:
            return self._wechat_detector
        self._wechat_checked = True
        try:
            import cv2
            model_dir = self._resource_root() / "assets" / "qr_models"
            model_files = [
                model_dir / "detect.prototxt",
                model_dir / "detect.caffemodel",
                model_dir / "sr.prototxt",
                model_dir / "sr.caffemodel",
            ]
            if not all(path.exists() for path in model_files):
                return None
            detector_class = getattr(cv2, "wechat_qrcode_WeChatQRCode", None)
            if detector_class is None:
                detector_class = getattr(getattr(cv2, "wechat_qrcode", None), "WeChatQRCode", None)
            if detector_class is None:
                return None
            self._wechat_detector = detector_class(*(str(path) for path in model_files))
        except Exception:
            self._wechat_detector = None
        return self._wechat_detector

    def _resource_root(self) -> Path:
        if self._bundle_root is not None:
            return self._bundle_root
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
                    try_downscale=True,
                    try_invert=True,
                )
            except Exception:
                continue
            for code in codes:
                normalized = self._normalize_cccd_qr_payload(getattr(code, "text", ""))
                if normalized:
                    return normalized
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
                normalized = self._normalize_cccd_qr_payload(value)
                if normalized:
                    return normalized
        return ""

    def _detect_qr_value(self, detector: Any, image: Any) -> str:
        try:
            value, _, _ = detector.detectAndDecode(image)
            normalized = self._normalize_cccd_qr_payload(value)
            if normalized:
                return normalized
        except Exception:
            pass
        try:
            value, _, _ = detector.detectAndDecodeCurved(image)
            normalized = self._normalize_cccd_qr_payload(value)
            if normalized:
                return normalized
        except Exception:
            pass
        try:
            ok, values, _, _ = detector.detectAndDecodeMulti(image)
            if ok:
                for value in values:
                    normalized = self._normalize_cccd_qr_payload(value)
                    if normalized:
                        return normalized
        except Exception:
            pass
        return ""


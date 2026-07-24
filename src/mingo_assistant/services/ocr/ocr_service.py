from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class OcrService:
    """OCR wrapper with EasyOCR primary engine and PaddleOCR fallback."""

    def __init__(self, lang: str = "vi", engine: str = "easyocr") -> None:
        self.lang = lang
        self.engine = engine
        self._ocr: Any | None = None
        self._easyocr_reader: Any | None = None

    def extract_text(self, image_path: str | Path) -> str:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy ảnh: {path}")

        qr_text = self.extract_qr_text(path)
        if self.engine == "easyocr":
            lines = self._run_easyocr(path)
        else:
            ocr = self._get_ocr()
            result = self._run_ocr(ocr, str(path))
            lines = self._collect_text_lines(result)
        if qr_text:
            lines.insert(0, f"QR_DATA: {qr_text}")
        return "\n".join(line for line in lines if line.strip())

    def set_engine(self, engine: str) -> None:
        if engine not in {"easyocr", "paddleocr"}:
            raise ValueError(f"Unsupported OCR engine: {engine}")
        self.engine = engine

    def _run_easyocr(self, image_path: Path) -> list[str]:
        reader = self._get_easyocr_reader()
        image = self._read_image_for_cv(image_path)
        source = image if image is not None else str(image_path)
        results = reader.readtext(source, detail=1, paragraph=False)
        lines: list[str] = []
        for item in results:
            if len(item) >= 2 and isinstance(item[1], str):
                text = item[1].strip()
                if self._looks_like_text(text):
                    lines.append(text)
        return self._dedupe_keep_order(lines)

    def _get_easyocr_reader(self) -> Any:
        if self._easyocr_reader is not None:
            return self._easyocr_reader

        import easyocr

        self._easyocr_reader = easyocr.Reader(["vi", "en"], gpu=False, verbose=False)
        return self._easyocr_reader

    def _read_image_for_cv(self, image_path: Path) -> Any | None:
        try:
            import cv2
            import numpy as np
        except Exception:
            return None

        try:
            image_bytes = np.fromfile(str(image_path), dtype=np.uint8)
            return cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
        except Exception:
            return None

    def extract_qr_text(self, image_path: str | Path) -> str:
        try:
            import cv2
            import numpy as np
        except Exception:
            return ""

        image = self._read_image_for_cv(Path(image_path))
        if image is None:
            return ""

        detector = cv2.QRCodeDetector()
        for candidate in self._qr_candidates(image):
            data, _, _ = detector.detectAndDecode(candidate)
            if data:
                return data.strip()

            try:
                retval, decoded_info, _, _ = detector.detectAndDecodeMulti(candidate)
            except Exception:
                continue
            if retval:
                text = "\n".join(item.strip() for item in decoded_info if item and item.strip())
                if text:
                    return text
        return ""

    def _qr_candidates(self, image: Any) -> list[Any]:
        try:
            import cv2
        except Exception:
            return [image]

        candidates = [image]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        candidates.append(gray)
        height, width = image.shape[:2]
        if max(height, width) < 1600:
            scale = 1600 / max(height, width)
            size = (int(width * scale), int(height * scale))
            resized = cv2.resize(image, size, interpolation=cv2.INTER_CUBIC)
            candidates.append(resized)
            candidates.append(cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY))
        return candidates

    def _get_ocr(self) -> Any:
        if self._ocr is not None:
            return self._ocr

        # Paddle 3.x CPU on Windows can fail in oneDNN/PIR for OCR graphs.
        # These flags must be set before importing PaddleOCR/Paddle.
        os.environ.setdefault("FLAGS_use_mkldnn", "0")
        os.environ.setdefault("FLAGS_use_onednn", "0")
        os.environ.setdefault("FLAGS_enable_pir_api", "0")
        os.environ.setdefault("OMP_NUM_THREADS", "1")

        from paddleocr import PaddleOCR

        options = {
            "lang": self.lang,
            "device": "cpu",
            "enable_hpi": False,
            "enable_mkldnn": False,
            "cpu_threads": 4,
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
        }
        try:
            self._ocr = PaddleOCR(**options)
        except TypeError:
            self._ocr = PaddleOCR(use_angle_cls=True, lang=self.lang)
        return self._ocr

    def _run_ocr(self, ocr: Any, image_path: str) -> Any:
        if hasattr(ocr, "predict"):
            return ocr.predict(image_path)
        return ocr.ocr(image_path, cls=True)

    def _collect_text_lines(self, result: Any) -> list[str]:
        lines: list[str] = []
        self._walk_result(result, lines)
        return self._dedupe_keep_order(lines)

    def _walk_result(self, value: Any, lines: list[str]) -> None:
        if value is None:
            return
        if isinstance(value, str):
            if self._looks_like_text(value):
                lines.append(value.strip())
            return
        if isinstance(value, dict):
            for key in ("rec_text", "text", "transcription"):
                item = value.get(key)
                if isinstance(item, str) and self._looks_like_text(item):
                    lines.append(item.strip())
            for key in ("rec_texts", "texts"):
                items = value.get(key)
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, str) and self._looks_like_text(item):
                            lines.append(item.strip())
            for item in value.values():
                if isinstance(item, (dict, list, tuple)):
                    self._walk_result(item, lines)
            return
        if isinstance(value, (list, tuple)):
            if len(value) >= 2 and isinstance(value[1], (list, tuple)) and value[1]:
                text = value[1][0]
                if isinstance(text, str) and self._looks_like_text(text):
                    lines.append(text.strip())
            for item in value:
                self._walk_result(item, lines)

    def _looks_like_text(self, text: str) -> bool:
        clean = text.strip()
        if len(clean) < 2:
            return False
        return any(char.isalpha() or char.isdigit() for char in clean)

    def _dedupe_keep_order(self, lines: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for line in lines:
            normalized = " ".join(line.split())
            key = normalized.lower()
            if key not in seen:
                seen.add(key)
                result.append(normalized)
        return result

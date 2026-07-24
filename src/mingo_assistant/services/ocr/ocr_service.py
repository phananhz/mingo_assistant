from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable


class OcrService:
    """OCR wrapper with EasyOCR primary engine and PaddleOCR fallback."""

    def __init__(self, lang: str = "vi", engine: str = "easyocr") -> None:
        self.lang = lang
        self.engine = engine
        self._ocr: Any | None = None
        self._easyocr_reader: Any | None = None

    def extract_text(self, image_path: str | Path, progress_callback: Callable[[int, str], None] | None = None) -> str:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy ảnh: {path}")

        if self.engine == "easyocr":
            lines = self._run_easyocr(path, progress_callback=progress_callback)
        else:
            if progress_callback:
                progress_callback(20, "Dang khoi tao PaddleOCR")
            ocr = self._get_ocr()
            if progress_callback:
                progress_callback(45, "Dang nhan dien van ban")
            result = self._run_ocr(ocr, str(path))
            lines = self._collect_text_lines(result)
            if progress_callback:
                progress_callback(90, "Dang tong hop ket qua")
        return "\n".join(line for line in lines if line.strip())

    def set_engine(self, engine: str) -> None:
        if engine not in {"easyocr", "paddleocr"}:
            raise ValueError(f"Unsupported OCR engine: {engine}")
        self.engine = engine

    def _run_easyocr(self, image_path: Path, progress_callback: Callable[[int, str], None] | None = None) -> list[str]:
        reader = self._get_easyocr_reader()
        image = self._read_image_for_cv(image_path)
        lines: list[str] = []
        sources = self._easyocr_sources(image) if image is not None else [str(image_path)]
        total = max(1, len(sources))
        if progress_callback:
            progress_callback(10, "Dang cat vung chu tren CCCD")
        for index, source in enumerate(sources, start=1):
            if progress_callback:
                percent = 10 + int(((index - 1) / total) * 80)
                progress_callback(percent, f"Dang nhan dien vung {index}/{total}")
            results = reader.readtext(source, detail=1, paragraph=False)
            for item in self._sort_ocr_results(results):
                if len(item) >= 2 and isinstance(item[1], str):
                    confidence = float(item[2]) if len(item) >= 3 and isinstance(item[2], (int, float)) else 1.0
                    text = self._clean_ocr_line(item[1])
                    if confidence < 0.18 and not self._is_high_value_cccd_line(text):
                        continue
                    if self._looks_like_text(text):
                        lines.append(text)
            if progress_callback:
                percent = 10 + int((index / total) * 80)
                progress_callback(percent, f"Da xu ly vung {index}/{total}")
        if progress_callback:
            progress_callback(92, "Dang gop ket qua OCR")
        return self._dedupe_keep_order(lines)

    def _easyocr_sources(self, image: Any) -> list[Any]:
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
            (0.28, 0.08, 0.92, 0.92),
            (0.28, 0.18, 0.92, 0.72),
            (0.28, 0.54, 0.92, 0.94),
        ]
        candidates: list[Any] = []
        for left, top, right, bottom in crop_boxes:
            crop = base[int(base_height * top) : int(base_height * bottom), int(base_width * left) : int(base_width * right)]
            if crop.size:
                candidates.extend(self._crop_variants(crop))

        return candidates or [base]

    def _crop_variants(self, crop: Any) -> list[Any]:
        try:
            import cv2
        except Exception:
            return [crop]

        variants = [crop]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        variants.append(cv2.createCLAHE(clipLimit=2.4, tileGridSize=(8, 8)).apply(gray))
        return variants

    def _sort_ocr_results(self, results: Any) -> list[Any]:
        if not isinstance(results, list):
            return []

        def key(item: Any) -> tuple[int, int]:
            if not isinstance(item, (list, tuple)) or not item:
                return (0, 0)
            box = item[0]
            if not isinstance(box, (list, tuple)) or not box:
                return (0, 0)
            xs: list[float] = []
            ys: list[float] = []
            for point in box:
                if isinstance(point, (list, tuple)) and len(point) >= 2:
                    xs.append(float(point[0]))
                    ys.append(float(point[1]))
            return (int(min(ys) if ys else 0), int(min(xs) if xs else 0))

        return sorted(results, key=key)

    def _clean_ocr_line(self, text: str) -> str:
        replacements = {
            "Â«": "<",
            "«": "<",
            "»": "<",
            "|": " ",
        }
        result = text.strip()
        for source, target in replacements.items():
            result = result.replace(source, target)
        return " ".join(result.split())

    def _is_high_value_cccd_line(self, text: str) -> bool:
        folded = text.lower()
        if any(marker in folded for marker in ["full name", "date of birth", "place of", "idvnm"]):
            return True
        return any(char.isdigit() for char in text)

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

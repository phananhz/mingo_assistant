"""Offline PP-OCRv6 recognition for Vietnamese business documents.

The project bundles the detector and recognizer as ONNX files.  RapidOCR
provides the stable image preprocessing and DB postprocessing we already use,
while this adapter supplies the newer local PP-OCRv6 model paths.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


class VietnameseDocumentOcr:
    """Run the bundled PP-OCRv6 models without downloading anything at runtime."""

    _MODEL_DIR = ("assets", "models", "ocr")
    _DETECTOR = "PP-OCRv6_det_small.onnx"
    _RECOGNIZER = "PP-OCRv6_rec_medium.onnx"
    _CLASSIFIER = "ch_ppocr_mobile_v2.0_cls_mobile.onnx"

    def __init__(self, bundle_root: Path) -> None:
        self.model_dir = bundle_root.joinpath(*self._MODEL_DIR)
        self._engine: Any | None = None

    @property
    def is_available(self) -> bool:
        return all(
            (self.model_dir / model_name).is_file()
            for model_name in (self._DETECTOR, self._RECOGNIZER, self._CLASSIFIER)
        )

    def recognize(self, image: bytes) -> list[tuple[str, float]]:
        """Return recognized lines and their confidence scores in reading order."""
        engine = self._get_engine()
        result, _elapsed = engine(image, text_score=0.25)
        return [
            (str(line[1]).strip(), float(line[2]))
            for line in result or []
            if len(line) >= 3 and str(line[1]).strip()
        ]

    def _get_engine(self) -> Any:
        if self._engine is not None:
            return self._engine
        if not self.is_available:
            raise FileNotFoundError("Thiếu bộ model PP-OCRv6 cục bộ.")

        from rapidocr_onnxruntime import RapidOCR

        self._engine = RapidOCR(
            det_model_path=str(self.model_dir / self._DETECTOR),
            rec_model_path=str(self.model_dir / self._RECOGNIZER),
            cls_model_path=str(self.model_dir / self._CLASSIFIER),
            text_score=0.25,
        )
        return self._engine

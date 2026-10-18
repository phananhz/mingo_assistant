"""Runtime verification for the portable Windows build.

This module is intentionally callable from the frozen, windowed executable so
the release script can prove that lazy OCR imports, native DLLs, and bundled
model files all work after PyInstaller extraction.
"""
from __future__ import annotations

import importlib
import json
import sys
import traceback
from pathlib import Path
from typing import Any


OCR_MODELS = (
    "ch_ppocr_mobile_v2.0_cls_mobile.onnx",
    "PP-OCRv6_det_small.onnx",
    "PP-OCRv6_rec_medium.onnx",
    "vietocr_vgg_transformer.pth",
)

QR_MODELS = (
    "detect.prototxt",
    "detect.caffemodel",
    "sr.prototxt",
    "sr.caffemodel",
)


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[3]


def _check_file(path: Path) -> dict[str, Any]:
    return {"path": str(path), "exists": path.is_file(), "size": path.stat().st_size if path.is_file() else 0}


def run_portable_self_test(report_path: str | Path) -> int:
    report_file = Path(report_path).resolve()
    report_file.parent.mkdir(parents=True, exist_ok=True)
    root = _bundle_root()
    report: dict[str, Any] = {"ok": False, "frozen": bool(getattr(sys, "frozen", False)), "bundle_root": str(root)}

    try:
        imports = {}
        for module_name in (
            "cv2",
            "numpy",
            "onnxruntime",
            "rapidocr_onnxruntime",
            "torch",
            "torchvision",
            "vietocr",
            "zxingcpp",
            "pyzbar.pyzbar",
        ):
            importlib.import_module(module_name)
            imports[module_name] = True
        report["imports"] = imports

        model_files = [
            *(_check_file(root / "assets" / "models" / "ocr" / name) for name in OCR_MODELS),
            *(_check_file(root / "assets" / "qr_models" / name) for name in QR_MODELS),
        ]
        report["model_files"] = model_files
        if not all(item["exists"] and item["size"] > 0 for item in model_files):
            raise RuntimeError("The portable package is missing one or more OCR/QR model files.")

        import cv2
        import numpy as np

        from mingo_assistant.services.ocr.vietnamese_document_ocr import VietnameseDocumentOcr
        from mingo_assistant.services.ocr.vietnamese_line_refiner import VietnameseLineRefiner
        from mingo_assistant.services.qr.scanner import IdentityQrScanner

        image = np.full((320, 1200, 3), 255, dtype=np.uint8)
        cv2.putText(image, "OCR 123", (55, 215), cv2.FONT_HERSHEY_SIMPLEX, 4.2, (0, 0, 0), 10, cv2.LINE_AA)
        encoded_ok, encoded = cv2.imencode(".png", image)
        if not encoded_ok:
            raise RuntimeError("Could not create the OCR self-test image.")

        ocr = VietnameseDocumentOcr(root)
        lines = ocr.recognize(encoded.tobytes())
        report["rapidocr"] = {"available": ocr.is_available, "lines": lines}
        if not lines:
            raise RuntimeError("RapidOCR loaded but returned no text for its self-test image.")

        refiner = VietnameseLineRefiner(ocr.model_dir)
        predictor = refiner._load()
        report["vietocr"] = {"weights": _check_file(refiner.weights), "predictor": type(predictor).__name__}

        qr_scanner = IdentityQrScanner(root)
        report["qr"] = {
            "wechat_available": qr_scanner._get_wechat_detector() is not None,
            "zxingcpp_available": imports["zxingcpp"],
            "pyzbar_available": imports["pyzbar.pyzbar"],
        }
        report["ok"] = True
    except BaseException as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["traceback"] = traceback.format_exc()
    finally:
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return 0 if report["ok"] else 1

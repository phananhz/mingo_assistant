"""One local entry point for photo/PDF certificate scans, shared by UI workers."""
from __future__ import annotations

from copy import copy
from dataclasses import replace
from pathlib import Path

import fitz

from mingo_assistant.core.cancellation import ScanCancelledError
from mingo_assistant.services.ocr.scan_input import certificate_pdf
from mingo_assistant.services.qr.scanner import IdentityQrScanner


def _orient_and_probe(scanner, pdf_path, callback):
    best = ((), 0, "")
    with fitz.open(pdf_path) as document:
        page = document[0]
        engine = scanner._get_legacy_engine()
        # Try right-angle rotations only when the first reading is inconclusive.
        for index, rotation in enumerate((0, 90, 270, 180)):
            scanner._progress(callback, 8 + index, "Đang kiểm tra hướng ảnh và loại tài liệu")
            page.set_rotation(rotation)
            scale = 2000 / max(page.rect.width, page.rect.height)
            image = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).tobytes("png")
            text = scanner._extract_page_with_ocr(engine, scanner._suppress_certificate_background(image), use_legacy=True)
            detected = scanner.detect_document_type(text)
            rank = (detected in {"erc", "brc"}, *scanner._ocr_text_quality(text))
            if rank > best[0]:
                best = rank, rotation, text
            if detected or IdentityQrScanner._looks_like_identity_ocr_text(text):
                best = rank, rotation, text
                break
        page.set_rotation(best[1])
        if best[1]:
            document.saveIncr()
    return best[2]


def read_certificate(service, path, selected="auto", callback=None, *, auto_photo=False):
    """None means photo classification was inconclusive; explicit mode still OCRs it.

    All state/candidates are per scan. No path-based cache can survive edits to a
    user's file, and no photo transform ever changes an embedded-text PDF.
    """
    is_photo = Path(path).suffix.lower() != ".pdf"
    scanner = copy(service) if is_photo else service
    with certificate_pdf(str(path), progress_callback=callback) as pdf_path:
        if is_photo:
            scanner._photo_input = True
            with fitz.open(pdf_path) as document:
                images = document[0].get_images()
                scanner._photo_low_resolution = bool(images and max(images[0][2:4]) < 2200)
            try:
                text = _orient_and_probe(scanner, pdf_path, callback)
            except ScanCancelledError:
                raise
            except Exception:
                # Optional early OCR/orientation failure is not a wrong-type verdict.
                text = ""
            detected = scanner.detect_document_type(text)
            if auto_photo and not detected:
                return None
            if selected not in {"erc", "brc"}:
                scanner._validate_expected_document_type(text)
            scanner._photo_probe = (pdf_path, text)
        if selected in {"erc", "brc"}:
            result = scanner.extract_pdf_as(pdf_path, selected, callback)
        else:
            result = scanner.extract_pdf(pdf_path, progress_callback=callback)
        if is_photo and scanner._photo_low_resolution:
            result = replace(result, warnings=list(dict.fromkeys(result.warnings + [
                "Ảnh tài liệu có độ phân giải thấp. Cần đối chiếu tên, địa chỉ và dấu tiếng Việt; nên dùng ảnh gốc rõ nét hơn nếu có.",
            ])))
        return result

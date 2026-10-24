"""Run only document/engine code off the GUI thread; emit plain result objects."""
from __future__ import annotations

from dataclasses import dataclass
from copy import copy
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot

from mingo_assistant.core.cancellation import ScanCancelledError
from mingo_assistant.services.ocr.scan_input import identity_images
from mingo_assistant.services.ocr.certificate_scan import read_certificate
from mingo_assistant.services.organization_documents import DocumentTypeMismatchError
from mingo_assistant.services.qr.scanner import IdentityScanResult


@dataclass(frozen=True)
class ScanRequest:
    path: str
    kind: str
    explicit_type: str
    back_path: str = ""


class DocumentScanWorker(QObject):
    progress = Signal(int, str)
    finished = Signal(object)

    def __init__(self, request: ScanRequest, identity_service, organization_service):
        super().__init__()
        self.request = request
        self.identity_service = identity_service
        # Per-document candidate buffers must not leak to a later scan.
        self.organization_service = copy(organization_service)

    def _progress(self, percent, status):
        if QThread.currentThread().isInterruptionRequested():
            raise ScanCancelledError()
        self.progress.emit(percent, status)

    @Slot()
    def run(self):
        try:
            self._progress(0, "Đang chuẩn bị quét tài liệu")
            request = self.request
            result = None
            kind = request.kind
            if kind == "auto" and Path(request.path).suffix.lower() != ".pdf":
                # Keep the fast, authoritative CCCD QR path. A certificate photo
                # without a valid identity QR must not enter CCCD-only OCR.
                self._progress(3, "Đang kiểm tra QR và loại tài liệu ảnh")
                try:
                    value = self.identity_service.scan_qr(request.path)
                    result = IdentityScanResult(value, "qr", request.path)
                except ScanCancelledError:
                    raise
                except Exception:
                    result = read_certificate(self.organization_service, request.path, callback=self._progress, auto_photo=True)
                    if result is not None:
                        kind = result.document_type
                if result is None or isinstance(result, IdentityScanResult):
                    kind = "cccd"
            if result is None and kind == "cccd":
                paths = list(dict.fromkeys(path for path in (request.path, request.back_path) if path))
                with identity_images(paths) as images:
                    try:
                        result = self.identity_service.scan_identity(images, progress_callback=self._progress)
                    except ScanCancelledError:
                        raise
                    except Exception as exc:
                        if request.kind == "auto":
                            raise RuntimeError(
                                "Chưa tự xác định được loại tài liệu ảnh. Hãy chọn CCCD, ERC hoặc BRC "
                                "trong mục Loại tài liệu rồi quét lại, hoặc dùng ảnh rõ nét hơn."
                            ) from exc
                        raise
            elif result is None:
                result = read_certificate(self.organization_service, request.path, request.explicit_type, self._progress)
            payload = {"result": result, "kind": kind}
        except ScanCancelledError:
            payload = {"cancelled": True}
        except DocumentTypeMismatchError as exc:
            payload = {"error": str(exc), "mismatch": True}
        except Exception as exc:
            payload = {"error": str(exc)}
        self.finished.emit(payload)

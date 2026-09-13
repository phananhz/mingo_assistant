"""Compatibility import for the former, inaccurately named QR service."""
from __future__ import annotations

from mingo_assistant.services.qr import IdentityQrScanner


class OcrService(IdentityQrScanner):
    """Deprecated compatibility alias; use :class:`IdentityQrScanner`."""

"""Cooperative cancellation; never terminate an OCR/native inference thread."""


class ScanCancelledError(Exception):
    pass

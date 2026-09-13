from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from mingo_assistant.core.errors import ConfigurationError, FileSystemError


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


class WindowsDpapiProtector:
    """Windows user-scoped encryption without an application-owned key."""

    @staticmethod
    def _blob(data: bytes) -> tuple[_DataBlob, ctypes.Array]:
        buffer = ctypes.create_string_buffer(data)
        blob = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
        return blob, buffer

    def protect(self, plaintext: bytes) -> bytes:
        if os.name != "nt":
            raise ConfigurationError("Windows DPAPI chỉ khả dụng trên Windows")
        input_blob, input_buffer = self._blob(plaintext)
        output_blob = _DataBlob()
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        if not crypt32.CryptProtectData(
            ctypes.byref(input_blob),
            "Min Assistant local data",
            None,
            None,
            None,
            0,
            ctypes.byref(output_blob),
        ):
            raise ctypes.WinError()
        try:
            return ctypes.string_at(output_blob.pbData, output_blob.cbData)
        finally:
            kernel32.LocalFree(output_blob.pbData)
            del input_buffer

    def unprotect(self, ciphertext: bytes) -> bytes:
        if os.name != "nt":
            raise ConfigurationError("Windows DPAPI chỉ khả dụng trên Windows")
        input_blob, input_buffer = self._blob(ciphertext)
        output_blob = _DataBlob()
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        if not crypt32.CryptUnprotectData(
            ctypes.byref(input_blob),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(output_blob),
        ):
            raise ctypes.WinError()
        try:
            return ctypes.string_at(output_blob.pbData, output_blob.cbData)
        finally:
            kernel32.LocalFree(output_blob.pbData)
            del input_buffer


class DpapiJsonStorage:
    """Opt-in encrypted JSON adapter; existing repositories remain plaintext."""

    HEADER = b"MINASSISTANT-DPAPI-v1\n"

    def __init__(self, path: Path, protector: WindowsDpapiProtector | None = None) -> None:
        self.path = path
        self.protector = protector or WindowsDpapiProtector()

    def read(self) -> Any:
        encoded = self.path.read_bytes()
        if not encoded.startswith(self.HEADER):
            raise ConfigurationError("Tệp không phải định dạng DPAPI của Min Assistant")
        ciphertext = base64.b64decode(encoded[len(self.HEADER) :], validate=True)
        plaintext = self.protector.unprotect(ciphertext)
        return json.loads(plaintext.decode("utf-8"))

    def write(self, payload: Any) -> None:
        plaintext = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        encoded = self.HEADER + base64.b64encode(self.protector.protect(plaintext))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="wb",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(encoded)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, self.path)
            temporary_path = None
        except OSError as exc:
            raise FileSystemError(self.path, "Không thể ghi dữ liệu DPAPI") from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass


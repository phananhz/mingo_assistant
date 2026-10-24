"""Check office-file availability without opening an application or closing files."""
from __future__ import annotations

import ctypes
import sys
from collections.abc import Sequence
from ctypes import wintypes
from pathlib import Path


def ensure_documents_closed(files: Sequence[Path]) -> None:
    """Require exclusive read access; never change or close a user's document."""
    if sys.platform != "win32" or not files:
        return
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = (
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    )
    create.restype = wintypes.HANDLE
    close = kernel.CloseHandle
    close.argtypes = (wintypes.HANDLE,)
    close.restype = wintypes.BOOL
    invalid = ctypes.c_void_p(-1).value
    for file in files:
        # OPEN_EXISTING, GENERIC_READ, no sharing: this also detects read-only
        # documents opened in Word without creating/truncating anything.
        handle = create(str(file.resolve()), 0x80000000, 0, None, 3, 0x80, None)
        if handle == invalid:
            error = ctypes.get_last_error()
            if error in (32, 33):
                raise OSError(
                    f"File hồ sơ đang được mở hoặc sử dụng:\n{file}\n"
                    "Vui lòng tự đóng file này trong Word rồi bấm Xuất hồ sơ lại."
                )
            raise OSError(
                f"Không thể kiểm tra file hồ sơ:\n{file}\n"
                f"Lỗi Windows {error}: {ctypes.FormatError(error).strip()}"
            )
        close(handle)

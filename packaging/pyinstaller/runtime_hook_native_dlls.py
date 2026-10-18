"""Expose vendored native-library directories before NumPy/OCR imports.

Several scientific wheels ship the same MSVC DLL under different ``*.libs``
directories. PyInstaller de-duplicates the file in a one-file build, so the
copy expected beside NumPy can end up under pandas instead. Keeping these
directories in the Windows DLL search path makes the portable bundle robust
to that de-duplication.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


_DLL_DIRECTORY_HANDLES = []

if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
    root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    for relative in (
        "numpy.libs",
        "pandas.libs",
        "scipy.libs",
        "Shapely.libs",
        "sklearn/.libs",
        "torch/lib",
        "torchvision",
    ):
        directory = root / relative
        if directory.is_dir():
            _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(directory)))

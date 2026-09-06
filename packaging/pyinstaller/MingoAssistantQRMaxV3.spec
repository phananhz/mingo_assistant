# -*- mode: python ; coding: utf-8 -*-
"""Portable PyInstaller configuration for Mingo Assistant.

Run this spec from the repository root. All paths derive from the spec location,
so a fresh clone can build without the original developer's local directories.
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

PROJECT_ROOT = Path(SPECPATH).resolve().parents[1]

# Runtime data required by OCR, address normalization, business-line lookup,
# and Word document generation.
datas = [(str(PROJECT_ROOT / "assets"), "assets")]
binaries = []
hiddenimports = []

# RapidOCR and its native dependencies load models/configuration dynamically.
for package_name in (
    "numpy",
    "cv2",
    "zxingcpp",
    "pyzbar",
    "docxtpl",
    "fitz",
    "rapidocr_onnxruntime",
    "onnxruntime",
):
    package_datas, package_binaries, package_hiddenimports = collect_all(package_name)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports


a = Analysis(
    [str(PROJECT_ROOT / "src" / "mingo_assistant" / "__main__.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MingoAssistantQRMaxV3",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    # Use PyInstaller's user-specific default temp directory. The earlier spec
    # embedded a single developer's Windows user directory and was not portable.
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

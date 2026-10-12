# -*- mode: python ; coding: utf-8 -*-
"""Portable PyInstaller configuration for Min Assistant.

Run this spec from the repository root. All paths derive from the spec location,
so a fresh clone can build without the original developer's local directories.
"""
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all

PROJECT_ROOT = Path(SPECPATH).resolve().parents[1]

# Runtime data required by OCR, address normalization, business-line lookup,
# and Word document generation.
datas = [(str(PROJECT_ROOT / "assets"), "assets")]
binaries = []
hiddenimports = []

# This Python installation exposes the _tkinter extension but cannot initialize
# Tcl while PyInstaller analyzes it. Its automatic hook therefore registers the
# runtime hook without collecting the script libraries, causing a one-file EXE
# to fail during extraction with ``_tcl_data not found``. Bundle the three
# standard library trees explicitly so the runtime hook always has its data.
PYTHON_TCL_ROOT = Path(sys.base_prefix) / "tcl"
for source_name, destination in (
    ("tcl8.6", "_tcl_data"),
    ("tk8.6", "_tk_data"),
    ("tcl8", "tcl8"),
):
    source_path = PYTHON_TCL_ROOT / source_name
    if source_path.is_dir():
        datas.append((str(source_path), destination))

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
    # VietOCR is imported lazily by the Vietnamese line-refinement pass.
    "vietocr",
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
    name="MinAssistant",
    icon=str(PROJECT_ROOT / "assets" / "branding" / "min-assistant.ico"),
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

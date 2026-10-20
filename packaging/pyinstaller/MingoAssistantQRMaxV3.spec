# -*- mode: python ; coding: utf-8 -*-
"""Portable PyInstaller configuration for Min Assistant.

Run this spec from the repository root. All paths derive from the spec location,
so a fresh clone can build without the original developer's local directories.
"""
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all, collect_data_files

import cv2

if not hasattr(cv2, "wechat_qrcode_WeChatQRCode"):
    raise RuntimeError("Portable QR build requires OpenCV Contrib; another cv2 distribution is shadowing it.")

PROJECT_ROOT = Path(SPECPATH).resolve().parents[1]

REQUIRED_PORTABLE_ASSETS = (
    "assets/models/ocr/ch_ppocr_mobile_v2.0_cls_mobile.onnx",
    "assets/models/ocr/PP-OCRv6_det_small.onnx",
    "assets/models/ocr/PP-OCRv6_rec_medium.onnx",
    "assets/models/ocr/vietocr_vgg_transformer.pth",
    "assets/qr_models/detect.prototxt",
    "assets/qr_models/detect.caffemodel",
    "assets/qr_models/sr.prototxt",
    "assets/qr_models/sr.caffemodel",
)
missing_assets = [relative for relative in REQUIRED_PORTABLE_ASSETS if not (PROJECT_ROOT / relative).is_file()]
if missing_assets:
    raise FileNotFoundError("Missing portable OCR/QR assets: " + ", ".join(missing_assets))

# Runtime data required by OCR, address normalization, business-line lookup,
# and Word document generation.
datas = [(str(PROJECT_ROOT / "assets"), "assets")]
binaries = []
hiddenimports = []
hiddenimports += [
    # These modules are imported lazily by the OCR/QR pipelines. Listing them
    # explicitly prevents an analyzer optimization from producing an EXE that
    # starts successfully but loses OCR on another computer.
    "PIL.Image",
    "onnxruntime.capi._pybind_state",
    "rapidocr_onnxruntime",
    "torch",
    "torchvision",
    "vietocr.tool.translate",
    "zxingcpp",
    "pyzbar.pyzbar",
]

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
):
    package_datas, package_binaries, package_hiddenimports = collect_all(package_name)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

# The offline predictor imports translate/model code explicitly. Keep its
# configuration data, without collecting training/augmentation CLI modules
# that are not part of scanning and pull in unrelated dependencies.
datas += collect_data_files("vietocr")


a = Analysis(
    [str(PROJECT_ROOT / "src" / "mingo_assistant" / "__main__.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(PROJECT_ROOT / "packaging" / "pyinstaller" / "runtime_hook_native_dlls.py")],
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

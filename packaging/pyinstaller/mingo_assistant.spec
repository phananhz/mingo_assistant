from pathlib import Path

from PyInstaller.utils.hooks import collect_all


PROJECT_ROOT = Path(SPECPATH).parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

datas = [(str(PROJECT_ROOT / "assets"), "assets")]
binaries = []
hiddenimports = []

for package_name in ("numpy", "cv2", "zxingcpp", "pyzbar", "docxtpl", "fitz", "rapidocr_onnxruntime", "onnxruntime"):
    try:
        package_binaries, package_datas, package_hiddenimports = collect_all(package_name)
    except ImportError:
        continue
    binaries.extend(package_binaries)
    datas.extend(package_datas)
    hiddenimports.extend(package_hiddenimports)

analysis = Analysis(
    [str(SRC_ROOT / "mingo_assistant" / "__main__.py")],
    pathex=[str(SRC_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    name="MinAssistant",
    icon=str(PROJECT_ROOT / "assets" / "branding" / "min-assistant.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    exclude_binaries=True,
)
coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    name="MinAssistant",
)



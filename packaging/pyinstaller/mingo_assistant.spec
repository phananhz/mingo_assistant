from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules


PROJECT_ROOT = Path(SPECPATH).parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

datas = [(str(PROJECT_ROOT / "assets"), "assets")]
binaries = []
hiddenimports = []

for package_name in ("PySide6", "numpy", "cv2", "zxingcpp", "pyzbar", "docxtpl", "fitz"):
    try:
        package_binaries, package_datas, package_hiddenimports = collect_all(package_name)
    except ImportError:
        continue
    binaries.extend(package_binaries)
    datas.extend(package_datas)
    hiddenimports.extend(package_hiddenimports)

for package_name in ("PySide6", "numpy", "cv2", "zxingcpp", "pyzbar", "docx", "PyMuPDF"):
    try:
        hiddenimports.extend(collect_submodules(package_name))
    except ImportError:
        continue

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
    name="MingoAssistant",
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
    name="MingoAssistant",
)



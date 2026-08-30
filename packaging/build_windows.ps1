$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path
$specPath = Join-Path $projectRoot "packaging\pyinstaller\mingo_assistant.spec"
$distPath = Join-Path $projectRoot "dist"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Không tìm thấy Python. Hãy cài Python 3.12 và mở lại PowerShell."
}

python -c "import PySide6, PyInstaller; print('PySide6', PySide6.__version__); print('PyInstaller', PyInstaller.__version__)"

Write-Host "Building Mingo Assistant with PyInstaller..."
python -m PyInstaller --noconfirm --clean $specPath

$iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue
if ($null -eq $iscc) {
    Write-Warning "PyInstaller build completed. Inno Setup (iscc.exe) was not found, so installer creation was skipped."
    exit 0
}

Write-Host "Building Windows installer with Inno Setup..."
& $iscc.Source (Join-Path $projectRoot "packaging\inno_setup\MingoAssistant.iss")
Write-Host "Installer output: $(Join-Path $distPath 'installer')"

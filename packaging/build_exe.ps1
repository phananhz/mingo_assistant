$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$specPath = Join-Path $projectRoot "packaging\pyinstaller\MingoAssistantQRMaxV3.spec"
$workPath = Join-Path $projectRoot ".tmp-pyinstaller-exe-work"
$outputPath = Join-Path $projectRoot "EXE"
$exePath = Join-Path $outputPath "MinAssistant.exe"
$selfTestRoot = Join-Path $projectRoot ".tmp-portable-self-test"
$selfTestReport = Join-Path $selfTestRoot "report.json"

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Khong tim thay Python cua du an tai: $pythonPath"
}

New-Item -ItemType Directory -Path $outputPath -Force | Out-Null

& $pythonPath -c "import PySide6, PyInstaller; print('PySide6', PySide6.__version__); print('PyInstaller', PyInstaller.__version__)"
if ($LASTEXITCODE -ne 0) {
    throw "Moi truong build chua co du PySide6 va PyInstaller."
}

Write-Host "Building Min Assistant EXE..."
& $pythonPath -m PyInstaller --noconfirm --clean `
    --workpath $workPath `
    --distpath $outputPath `
    $specPath
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE."
}
if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
    throw "Build completed but the expected EXE was not found: $exePath"
}

New-Item -ItemType Directory -Path $selfTestRoot -Force | Out-Null
Remove-Item -LiteralPath $selfTestReport -Force -ErrorAction SilentlyContinue

Write-Host "Running OCR/QR self-test inside the frozen EXE..."
$selfTestProcess = Start-Process `
    -FilePath $exePath `
    -ArgumentList @("--portable-self-test", $selfTestReport) `
    -WindowStyle Hidden `
    -PassThru
if (-not $selfTestProcess.WaitForExit(240000)) {
    Stop-Process -Id $selfTestProcess.Id -Force -ErrorAction SilentlyContinue
    throw "Portable OCR/QR self-test timed out after 240 seconds."
}
if (-not (Test-Path -LiteralPath $selfTestReport -PathType Leaf)) {
    throw "The frozen EXE did not create its OCR/QR self-test report."
}
$selfTestResult = Get-Content -LiteralPath $selfTestReport -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $selfTestResult.ok) {
    $selfTestResult | ConvertTo-Json -Depth 8
    throw "Portable OCR/QR self-test failed inside the frozen EXE."
}

$exeHash = (Get-FileHash -LiteralPath $exePath -Algorithm SHA256).Hash
$exeSize = (Get-Item -LiteralPath $exePath).Length
Write-Host "Portable self-test passed. RapidOCR lines:" (($selfTestResult.rapidocr.lines | ForEach-Object { $_[0] }) -join " | ")
Write-Host "EXE size: $exeSize bytes"
Write-Host "EXE SHA256: $exeHash"
Write-Host "EXE output: $exePath"

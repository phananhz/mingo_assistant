param([string]$OpenCvRoot = "", [string]$AuthorizedProfilesFile = "")

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$specPath = Join-Path $projectRoot "packaging\pyinstaller\MingoAssistantQRMaxV3.spec"
$workPath = Join-Path $projectRoot ".tmp-pyinstaller-exe-work"
$outputPath = Join-Path $projectRoot "EXE"
$exePath = Join-Path $outputPath "MinAssistant.exe"
$selfTestRoot = Join-Path $projectRoot ".tmp-portable-self-test"
$selfTestReport = Join-Path $selfTestRoot "report.json"
$privateProfileRoot = Join-Path $projectRoot ".tmp-release-private"
$privateProfileResource = Join-Path $privateProfileRoot "authorized_person_seed.json"

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Khong tim thay Python cua du an tai: $pythonPath"
}

if ($OpenCvRoot) {
    $opencvDependencyRoot = (Resolve-Path -LiteralPath $OpenCvRoot).Path
    if (-not (Test-Path -LiteralPath (Join-Path $opencvDependencyRoot "cv2\cv2.pyd") -PathType Leaf)) {
        throw "OpenCvRoot must contain a complete OpenCV Contrib installation."
    }
    $env:PYTHONPATH = $opencvDependencyRoot + [IO.Path]::PathSeparator + $env:PYTHONPATH
}

New-Item -ItemType Directory -Path $outputPath -Force | Out-Null

& $pythonPath -c "import PySide6, PyInstaller; print('PySide6', PySide6.__version__); print('PyInstaller', PyInstaller.__version__)"
if ($LASTEXITCODE -ne 0) {
    throw "Moi truong build chua co du PySide6 va PyInstaller."
}

& $pythonPath -c "import cv2; assert hasattr(cv2, 'wechat_qrcode_WeChatQRCode'), 'OpenCV Contrib is missing or shadowed by another OpenCV distribution'; print('OpenCV Contrib', cv2.__version__, cv2.__file__)"
if ($LASTEXITCODE -ne 0) {
    throw "Build requires OpenCV Contrib with WeChat QR. Repair conflicting cv2 packages or supply -OpenCvRoot."
}

if (-not $AuthorizedProfilesFile) {
    $AuthorizedProfilesFile = Join-Path $env:APPDATA "Min Assistant\authorized_person.json"
    if (-not (Test-Path -LiteralPath $AuthorizedProfilesFile -PathType Leaf)) {
        $AuthorizedProfilesFile = Join-Path $env:APPDATA "Mingo Assistant\authorized_person.json"
    }
}
if (-not (Test-Path -LiteralPath $AuthorizedProfilesFile -PathType Leaf)) {
    throw "No real authorized profiles found. Supply -AuthorizedProfilesFile; do not ship sample profiles."
}
$previousProfileResource = $env:MIN_ASSISTANT_AUTHORIZED_PROFILES
$profilePreparationPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = (Join-Path $projectRoot "src") + [IO.Path]::PathSeparator + $env:PYTHONPATH
    $profileSummaryJson = & $pythonPath -m mingo_assistant.application.profile_bundle `
        --source $AuthorizedProfilesFile `
        --defaults (Join-Path $projectRoot "assets\defaults\authorized_person_profiles.json") `
        --output $privateProfileResource
    if ($LASTEXITCODE -ne 0) { throw "Preparing authorized-person release profiles failed; EXE build aborted." }
    $profileSummary = $profileSummaryJson | ConvertFrom-Json
    $env:MIN_ASSISTANT_AUTHORIZED_PROFILES = $privateProfileResource
    Write-Host "Bundling authorized-person profiles:" $profileSummary.profiles
    Write-Host "WARNING: This personal EXE contains private profile data. Distribute only to intended recipients."
    Write-Host "Building Min Assistant EXE..."
    & $pythonPath -m PyInstaller --noconfirm --clean `
        --workpath $workPath `
        --distpath $outputPath `
        $specPath
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed with exit code $LASTEXITCODE." }
} finally {
    $env:PYTHONPATH = $profilePreparationPythonPath
    $env:MIN_ASSISTANT_AUTHORIZED_PROFILES = $previousProfileResource
}
if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
    throw "Build completed but the expected EXE was not found: $exePath"
}

New-Item -ItemType Directory -Path $selfTestRoot -Force | Out-Null
Remove-Item -LiteralPath $selfTestReport -Force -ErrorAction SilentlyContinue

Write-Host "Running OCR/QR self-test inside the frozen EXE..."
$previousPath = $env:PATH
$previousPythonPath = $env:PYTHONPATH
$previousPythonHome = $env:PYTHONHOME
try {
    # Only this child process is isolated; do not modify machine/user settings.
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    $env:PYTHONPATH = $null
    $env:PYTHONHOME = $null
    $selfTestProcess = Start-Process `
        -FilePath $exePath `
        -WorkingDirectory $selfTestRoot `
        -ArgumentList @("--portable-self-test", ('"' + $selfTestReport + '"')) `
        -WindowStyle Hidden `
        -PassThru
    if (-not $selfTestProcess.WaitForExit(240000)) {
        Stop-Process -Id $selfTestProcess.Id -Force -ErrorAction SilentlyContinue
        throw "Portable OCR/QR self-test timed out after 240 seconds."
    }
    if ($selfTestProcess.ExitCode -ne 0) {
        throw "Portable self-test exited with code $($selfTestProcess.ExitCode). See $selfTestReport"
    }
} finally {
    $env:PATH = $previousPath
    $env:PYTHONPATH = $previousPythonPath
    $env:PYTHONHOME = $previousPythonHome
}
if (-not (Test-Path -LiteralPath $selfTestReport -PathType Leaf)) {
    throw "The frozen EXE did not create its OCR/QR self-test report."
}
$selfTestResult = Get-Content -LiteralPath $selfTestReport -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $selfTestResult.ok -or -not $selfTestResult.frozen) {
    $selfTestResult | ConvertTo-Json -Depth 8
    throw "Portable OCR/QR self-test failed inside the frozen EXE."
}
if ($selfTestResult.authorized_profiles.profiles -ne $profileSummary.profiles -or
    $selfTestResult.authorized_profiles.bundle_sha256 -ne $profileSummary.sha256 -or
    -not $selfTestResult.authorized_profiles.autofill_verified) {
    throw "The frozen EXE did not load and autofill the exact authorized-person profile bundle."
}

$exeHash = (Get-FileHash -LiteralPath $exePath -Algorithm SHA256).Hash
$exeSize = (Get-Item -LiteralPath $exePath).Length
Write-Host "Portable self-test passed. RapidOCR lines:" (($selfTestResult.rapidocr.lines | ForEach-Object { $_[0] }) -join " | ")
Write-Host "EXE size: $exeSize bytes"
Write-Host "EXE SHA256: $exeHash"
Write-Host "EXE output: $exePath"

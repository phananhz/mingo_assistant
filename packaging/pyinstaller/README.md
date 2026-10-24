# Windows packaging

From the repository root on Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-build.txt
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m unittest discover -s tests\unit
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean `
  --workpath build\pyinstaller `
  --distpath dist `
  packaging\pyinstaller\MingoAssistantQRMaxV3.spec
```

The resulting executable is `dist\MinAssistant.exe`. Build output and releases remain local and are intentionally ignored by Git.

## Verified portable release

Prefer the release script: it builds `EXE\MinAssistant.exe` and runs the
OCR/QR/PDF/form-to-Word self-test inside the actual frozen executable.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_exe.ps1
```

The build machine must already have the four OCR models and four WeChat QR
model files listed in `MingoAssistantQRMaxV3.spec`. They are embedded, together
with RapidOCR's own models, native libraries, templates and lookup datasets.
Recipients need only the EXE; they do not need the build environment or a
separate Python, OpenCV, QR, or OCR installation.

OpenCV wheels share the `cv2` namespace. Installing a plain/headless wheel
after Contrib can silently remove WeChat support. The release script and spec
reject that state. If the source app is holding its OpenCV DLL open, prepare
an isolated build dependency instead of stopping it or changing file ACLs:

```powershell
.\.venv\Scripts\python.exe -m pip install --no-deps --target .tmp-portable-self-test/build-deps opencv-contrib-python==4.10.0.84
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_exe.ps1 -OpenCvRoot .tmp-portable-self-test/build-deps
```

Use a fresh target directory or reuse the already verified installation.
The override affects packaging only; this directory is not needed beside the
distributed EXE.

The frozen test runs from a separate working directory with only Windows
system folders on `PATH`, without `PYTHONPATH`/`PYTHONHOME`, with temporary
app data, and with Python socket connections blocked. It performs actual
PP-OCRv6, RapidOCR and VietOCR inference, decodes a synthetic CCCD QR with all
three engines, reads text PDFs for ERC/BRC and exports a location-update DOCX.
This verifies the bundled runtime, but does not replace a clean-machine test
on the recipient's Windows hardware. Report: `.tmp-portable-self-test/report.json`.

## Authorized-person profiles in personal releases

`build_exe.ps1` prepares the real profiles from
`%APPDATA%\Min Assistant\authorized_person.json` (or the former Mingo Assistant
folder) and embeds a private seed resource in the EXE. An explicit source can
be supplied with `-AuthorizedProfilesFile`. Missing, incomplete or sample-only
data aborts the release instead of silently shipping placeholders.

The seed is staged under ignored `.tmp-release-private/`, never written into
tracked default assets. On a new machine it initializes the editable local
profiles once. Existing local profiles and intentional deletions are retained.
The frozen self-test verifies the exact seed hash, profile count and dropdown
autofill with fresh app data. Source-only PyInstaller builds without the seed
cannot pass this personal-release gate.

These personalized EXEs contain personal information. Distribute them only to
the intended recipients; do not upload the seed, local profiles or EXE to Git.

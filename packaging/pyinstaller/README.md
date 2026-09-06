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

The resulting executable is `dist\MingoAssistantQRMaxV3.exe`. Build output and releases remain local and are intentionally ignored by Git.

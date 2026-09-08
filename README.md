# Min Assistant

á»¨ng dá»¥ng desktop Windows há»— trá»£ táº¡o há»“ sÆ¡ tá»« giáº¥y tá» cÃ¡ nhÃ¢n: OCR áº£nh/PDF, trÃ­ch xuáº¥t dá»¯ liá»‡u cÃ³ cáº¥u trÃºc, kiá»ƒm tra dá»¯ liá»‡u, Ä‘iá»n máº«u Word vÃ  xuáº¥t bá»™ há»“ sÆ¡.

YÃªu cáº§u dá»± Ã¡n Ä‘áº§y Ä‘á»§ náº±m táº¡i [YEU_CAU_PHAT_TRIEN_UNG_DUNG.md](YEU_CAU_PHAT_TRIEN_UNG_DUNG.md).

## Cáº¥u trÃºc chÃ­nh

```text
src/mingo_assistant/       Source á»©ng dá»¥ng
docs/                      TÃ i liá»‡u phÃ¢n tÃ­ch, kiáº¿n trÃºc, hÆ°á»›ng dáº«n
assets/templates/word/     Máº«u Word .docx
assets/samples/            Dá»¯ liá»‡u máº«u dÃ¹ng test OCR vÃ  táº¡o há»“ sÆ¡
data/                      Dá»¯ liá»‡u runtime local, khÃ´ng commit dá»¯ liá»‡u tháº­t
exports/                   Káº¿t quáº£ xuáº¥t há»“ sÆ¡, khÃ´ng commit
tests/                     Unit test, integration test, fixtures
scripts/                   Script há»— trá»£ dev/build/import
packaging/                 Cáº¥u hÃ¬nh Ä‘Ã³ng gÃ³i Windows
```

Hiá»‡n táº¡i má»›i dá»±ng khung dá»± Ã¡n, chÆ°a cÃ³ code nghiá»‡p vá»¥.

## Cháº¡y giao diá»‡n hiá»‡n táº¡i

```powershell
$env:PYTHONPATH = "src"
python -m mingo_assistant
```

Náº¿u terminal chÆ°a nháº­n `python`, dÃ¹ng trá»±c tiáº¿p Python 3.12:

```powershell
$env:PYTHONPATH = "src"
& "C:\Users\duyle\AppData\Local\Programs\Python\Python312\python.exe" -m mingo_assistant
```



## Build Windows EXE

A fresh clone can produce a Windows EXE by installing both dependency files and using the portable PyInstaller spec:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-build.txt
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean packaging\pyinstaller\MingoAssistantQRMaxV3.spec
```

See [packaging/pyinstaller/README.md](packaging/pyinstaller/README.md) for the full test and build steps.

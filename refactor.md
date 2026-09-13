# Min Assistant - Refactor handoff

Cap nhat: 2026-09-13

## 1. Muc dich cua tai lieu

Tai lieu nay ghi lai dung trang thai refactor hien tai de co the dung tai day va
tiep tuc phat trien tinh nang, hoac quay lai refactor sau nay ma khong phai khao
sat lai tu dau.

Refactor da duoc thuc hien theo huong tang dan, giu cac API/ham tuong thich o
nhung diem co nguy co cao. Du an van co the tiep tuc phat trien neu khong thuc
hien them cac muc con lai trong tai lieu nay.

## 2. Moc ban dau va trang thai Git

- Commit ban dau: `36800ba94356610b99c31b546ad1c54c073e1541`.
- Truoc khi refactor, local va `origin/main` cung o commit tren.
- Toan bo thay doi refactor hien tai van chua commit va chua push.
- Thu muc `TemplatesBefore/` la du lieu untracked cua nguoi dung, khong bi sua.
- Baseline truoc refactor: 111 unit test dat, compile dat, build PyInstaller va
  startup smoke test dat.

Khong duoc dung `git reset --hard`, `git clean` hoac xoa workspace neu chua sao
luu, vi cac thay doi refactor va file moi hien chua nam trong commit.

## 3. Cac rang buoc bat buoc phai giu

- Ba ho so nguoi duoc uy quyen co dinh phai luon co khi su dung app.
- Khong lam thay doi hanh vi UI, luong lap ho so, du lieu case va thu muc export.
- Giu tuong thich voi JSON case cu va du lieu AppData cu.
- Khong lam thay doi bo cuc, noi dung bao ve, bang, bookmark, checkbox, font,
  chu ky va ngat trang cua cac mau DOCX.
- Khi sua CCCD da nhan dien, phai dong bo dung nguoi theo CCCD cu/moi tren cac
  vai tro lien quan; khong duoc sua nham nguoi khac.
- App va viec quet QR phai tiep tuc hoat dong offline.
- Che do source va EXE dong goi phai tim thay cung mot bo tai nguyen.

## 4. Phan da refactor

### 4.1 Du lieu ba ho so co dinh va bao mat fixture

- Chuyen ba ho so co dinh ra khoi ma UI sang
  `assets/defaults/authorized_person_profiles.json`.
- Them `AuthorizedPersonRepository`; hop nhat ho so co dinh voi ho so local.
- Ho so co dinh van hien trong app va khong the bi xoa boi UI hien tai.
- Thay du lieu ca nhan that bi lap lai trong test bang du lieu gia.
- Khong sua lich su Git va khong sua noi dung cac Word template.

### 4.2 Composition root va application boundaries

- Them `AppContainer` lam noi khoi tao va chia se dependency.
- Them `AppPaths` cho duong dan source/frozen va duong dan du lieu local.
- Them use case cho case va ho so nguoi duoc uy quyen.
- Them core data errors co kieu ro rang.
- MainWindow khong con tu doc/ghi kho ho so nguoi duoc uy quyen truc tiep.
- Van giu cac ham delegate/compatibility can thiet cho code va test cu.

### 4.3 Domain dang ky doanh nghiep

- Them cac model khong phu thuoc PySide cho nguoi, dia chi, doanh nghiep, nganh
  nghe, von gop, chu so huu to chuc, nguoi duoc uy quyen va case dang ky.
- Them projection tu `form_values` cu; khong thay doi payload dang luu.
- Tien VND dung integer/Decimal, khong dung float.
- Tach validation bat buoc va validation nganh nghe ra khoi widget.
- Ket qua validation tach rieng error va warning.

### 4.4 BusinessRegistrationWorkspace

- Them `RegistrationViewModel` quan ly ban sao form state, domain projection va
  validation.
- Them `RegistrationExportPlanner` cho thu muc export va version ho so.
- Them `RegistrationValueComposer` cho gia tri mac dinh/phat sinh cua form,
  ghep dia chi, noi ky, von bang so/chu va tom tat nganh nghe.
- Tach parse/format/doc tien VND sang formatter thuan Python.
- Cac method cu tren workspace duoc giu lai duoi dang delegate de han che thay
  doi signal, preview, save va test regression.

### 4.5 Dong bo nguoi va vai tro

- Them `PersonIdentityRules` cho quy tac so khop CCCD cu/moi va fallback thong
  tin lien he uy quyen.
- Them `PersonRoleMapper` de map du lieu CCCD vao cac truong vai tro.
- Them `PersonProfileSynchronizer` de dong bo nguoi trong case, cac role va
  beneficial-owner fields theo dung identity.
- Giu dung chuoi identity legacy nhu `CCCD so ...`, ngay cap va noi cap.
- Workspace tiep tuc cung cap cac method compatibility cu.

### 4.6 DOCX boundaries

- Them `TemplateManifest` co cache.
- Them `TemplateRepository` de chon template theo loai chu so huu.
- Them `DocxPackageEditor` de doc/ghi ZIP/XML theo cach atomic.
- Them `DocumentValueFormatter` cho ngay, dia chi, tinh/thanh, tien, thanh vien
  va nganh nghe.
- Them `DocumentContextBuilder` cho viec tao gia tri placeholder/template target.
- Generator dang ky doanh nghiep va don vi phu thuoc cung dung boundary manifest
  da tach.
- Khong viet lai engine thay placeholder va cac post-processor XML co rui ro cao.

### 4.7 Dia gioi hanh chinh

- Bo hai bang province-merger bi lap trong AddressParser va DOCX generator.
- Them `AdministrativePlaceMatcher.canonical_province_name`, lay ten chuan tu
  asset dia gioi hanh chinh chinh thuc dang duoc dong goi.
- Formatter DOCX nhan resolver qua dependency thay vi giu mot ban do rieng.

### 4.8 QR scanner

- Tach `IdentityQrScanner` sang `services/qr/scanner.py`.
- Giu `OcrService` lam compatibility subclass de import cu van hoat dong.
- Scanner nhan `bundle_root` va nap cac model offline tu `assets/qr_models`.
- AppContainer khoi tao scanner moi; chuoi fallback reader hien tai duoc giu.

### 4.9 Persistence va an toan du lieu local

- Case JSON moi co schema version 1, nhung van doc duoc payload list legacy.
- JSON hong duoc sao chep thanh file `.corrupt-*.bak` truoc khi bao loi.
- Read path khong ghi de hoac xoa file JSON hong.
- Case hong hien loi chan startup; profile local hong fallback ve ba ho so co
  dinh va hien canh bao.
- Them `QLockFile` theo user de ngan hai instance cung ghi JSON.
- Them DPAPI JSON adapter va atomic write lam nen tang, nhung chua bat mac dinh.

### 4.10 Engineering va test automation

- Them cau hinh Ruff Python 3.12, chi bat nhom loi correctness/fatal.
- Them GitHub Actions tren Windows cho compile, Ruff, unit va integration test.
- Them Dependabot cho pip va GitHub Actions.
- Them integration flow du lieu gia: tao case -> luu -> nap lai -> validate ->
  tao nam loai DOCX that.
- Them integration flow QR gia -> parse CCCD -> chuan hoa dia chi.

## 5. Ket qua kiem tra da xac nhan

- `compileall`: dat.
- Ruff correctness lint: dat.
- Unit test: 150 test duoc discover va full suite khong co failure.
- Integration test: 2/2 dat.
- Cac nhom test dia chi/DOCX, QR/CCCD/container, person-role va application
  boundary da dat sau khi tach code.
- Tao thu 5 loai DOCX voi du lieu gia: 5/5 file tao thanh cong, khong co
  placeholder chua resolve trong ket qua kiem tra cau truc.
- Ban EXE da smoke-test day du truoc do:
  `dist/final-refactor/MinAssistant.exe`, 244,930,765 bytes,
  SHA-256 `3302fb6767f521aa4376659394154c43bacd3c3a9cfb75f019a86fe13697f84e`.
- Ban build moi nhat da dong goi thanh cong:
  `dist/refactor-continuation/MinAssistant.exe`, 244,939,800 bytes,
  SHA-256 `171AD9B602BA658E2E2677149251454D65EF8FA66DDD446909AFBC9441CDA953`.

Luu y: ban `refactor-continuation` moi chi duoc xac nhan build va hash tai thoi
diem viet tai lieu; chua hoan tat archive-content check va isolated-AppData
startup smoke test cua chinh artifact nay.

## 6. Da lam nhung chua xac minh day du

### 6.1 Kiem tra DOCX truc quan

- Da tao du 5 file DOCX voi du lieu gia va kiem tra cau truc thanh cong.
- Da thu render bang LibreOffice 26.8 tai
  `C:\Program Files\LibreOffice\program\soffice.exe`, nhung tien trinh headless bi
  treo/timeout.
- Da thu Microsoft Word COM hidden conversion, cung bi treo/timeout.
- Chi cac process do lan kiem tra tao ra bi dung; cac phien Word co san cua
  nguoi dung khong bi dong.
- Vi vay chua co ket luan page-by-page ve bo cuc truc quan cua 5 DOCX.

### 6.2 DPAPI

- Boundary va test nen tang da co.
- Chua noi DPAPI vao repository dang su dung, vi chua co migration plaintext ->
  encrypted co rollback va bao dam khong mat du lieu.

### 6.3 QR thuc te

- Parser, normalization, dependency wiring va fallback orchestration co test.
- Chua test lai day du bang camera/anh CCCD that tren ban EXE moi nhat.

## 7. Phan chua refactor

- `BusinessRegistrationWorkspace` van la file lon, con nhieu khoi tao widget,
  signal wiring, UI state va luong preview/export trong cung lop.
- `DocxTemplateGenerator` van lon; placeholder engine, XML post-processors,
  bang, checkbox, bookmark, font va page-break logic chua duoc tach vat ly.
- `MainWindow` van con nhieu trach nhiem shell/navigation, case lifecycle,
  settings va dieu phoi UI.
- Mot so compatibility delegate co the duoc thu gon ve sau, nhung chi khi tat ca
  caller va regression test da chuyen sang boundary moi.
- Chua co bo golden-file hoac rendered-image regression cho tung trang DOCX.
- Chua co bo sample anh QR/MRZ offline dai dien cho day du fallback reader.
- Chua thuc hien migration DPAPI cho du lieu dang ton tai.
- Chua chia commit theo phase va chua push len GitHub.

Day la technical debt, khong phai dieu kien bat buoc de tiep tuc xay dung tinh
nang tren code hien tai.

## 8. Thu tu de tiep tuc refactor sau nay

1. Sao luu workspace, `.git`, `TemplatesBefore/`, AppData va thu muc export.
2. Chay lai compile, Ruff, 150 unit test va 2 integration test de dat baseline.
3. Smoke-test `dist/refactor-continuation/MinAssistant.exe` voi AppData tam; kiem
   tra archive co du profile mac dinh, administrative assets, business lines,
   QR models, branding va 5 template DOCX.
4. Giai quyet render DOCX; tao anh/PDF cua 5 bo ho so va so san page-by-page
   truoc khi tach them generator.
5. Neu tach tiep workspace, chi tach tung section/controller nho va giu method
   delegate cho den khi caller cu khong con.
6. Neu tach tiep DOCX generator, uu tien mot nhom pure formatting/context moi
   lan; khong viet lai dong loat XML pipeline.
7. Chi bat DPAPI sau khi co migration mot lan, backup, rollback va test doc ca
   plaintext lan encrypted.
8. Test source va EXE tren may Windows that sau moi moc co thay doi resource,
   QR native dependency hoac template.

## 9. Lenh kiem tra de dung lam baseline

Chay tu thu muc goc du an bang PowerShell:

```powershell
$env:PYTHONPATH='src'
$env:PYTHONIOENCODING='utf-8'
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\ruff.exe check src tests
.\.venv\Scripts\python.exe -m unittest discover -s tests\unit
.\.venv\Scripts\python.exe -m unittest discover -s tests\integration
git diff --check
git status --short
```

Build dung spec chinh cua du an:

```powershell
.\.venv\Scripts\pyinstaller.exe --noconfirm --distpath dist\refactor-check packaging\pyinstaller\MingoAssistantQRMaxV3.spec
```

## 10. Backup de khoi phuc dung trang thai

Muon khoi phuc day du nhu luc backup, can sao luu khi app da dong:

- Toan bo workspace, bao gom `.git`, file uncommitted/untracked va
  `TemplatesBefore/`.
- `%APPDATA%\Min Assistant`.
- `%APPDATA%\Mingo Assistant` neu con du lieu legacy.
- `%USERPROFILE%\Documents\Min Assistant` hoac thu muc export tuy chinh trong
  settings.

Chi sao luu repository/Git se khong sao luu case, profile, settings trong
AppData va cac ho so Word da export. Neu sao luu va khoi phuc day du cac muc tren
vao dung duong dan, du an va du lieu se tro lai trang thai tai thoi diem backup.

## 11. Tai lieu lien quan

- Audit chi tiet: `docs/REFACTOR_ARCHITECTURE_AUDIT.md`.
- PyInstaller spec: `packaging/pyinstaller/MingoAssistantQRMaxV3.spec`.
- Tai nguyen profile co dinh:
  `assets/defaults/authorized_person_profiles.json`.

# Min Assistant

Ứng dụng desktop Windows chạy offline, hỗ trợ quét QR/OCR CCCD, chuẩn hóa địa chỉ, quản lý case, lập hồ sơ đăng ký doanh nghiệp và xuất bộ hồ sơ Word.

Đây là tài liệu bàn giao kỹ thuật. Mỗi phiên phát triển mới phải đọc file này, sau đó kiểm tra `git status --short` trước khi sửa mã.

## Nguyên tắc dự án

- Thương hiệu hiện tại là **Min Assistant**.
- Không commit CCCD, hồ sơ thực tế, ảnh giấy tờ hoặc export của khách hàng.
- Không sửa template DOCX, mapping field hoặc layout ngoài phạm vi yêu cầu.
- Khi CCCD đã lưu được sửa, đồng bộ mọi tham chiếu cùng người trong case bằng CCCD cũ/mới; không ảnh hưởng người khác.
- Unit test hoặc thay placeholder không chứng minh layout Word đúng. Khi template/mapping thay đổi, phải kiểm tra DOCX trực quan.

## Kiến trúc hiện tại

```text
PySide6 UI
  -> application/              Điều phối dependency và workflow
  -> services/ + repositories/ Nghiệp vụ, OCR, DOCX, case/profile
  -> infrastructure/           Filesystem và JSON atomic
```

| Khu vực | Trách nhiệm |
| --- | --- |
| `src/mingo_assistant/app/` | Khởi động, đường dẫn runtime, settings và migration Mingo -> Min. |
| `application/` | Dependency/workflow cấp ứng dụng. |
| `models/` | `CaseSummary`, `OcrPerson` và dữ liệu nghiệp vụ. |
| `repositories/` | Lưu case JSON, xóa mềm, khôi phục, thùng rác. |
| `services/ocr/` | QR/OCR CCCD và parser thẻ. |
| `services/normalization/` | Chuẩn hóa địa chỉ hành chính. |
| `services/documents/` | Sinh, kiểm tra và hậu xử lý DOCX. |
| `services/business_lines/` | Danh mục ngành nghề. |
| `services/personal_profiles.py` | Hồ sơ cá nhân/tổ chức local. |
| `infrastructure/storage/` | Đọc JSON và ghi atomic. |
| `ui/main_window.py` | Điều hướng, danh sách case, hồ sơ ủy quyền, settings. |
| `ui/views/business_registration_workspace.py` | Workspace hồ sơ thành lập; tách dần theo section khi mở rộng. |
| `ui/views/business_registration/` | Schema field, component và worker export DOCX. |

## Template Word: quy ước bắt buộc

### 1. Thư mục nguồn

Đặt toàn bộ template mới tại:

```text
TemplatesBefore/
```

Đây là inbox nguồn của người dùng. Giữ nguyên file gốc, tên file, cấu trúc và layout; không chỉnh trực tiếp hoặc move file trong thư mục này.

### 2. Thư mục ứng dụng thực sự nạp

```text
assets/templates/word/business_registration/
```

`AppPaths.template_dir` và `DocxTemplateGenerator` chỉ đọc template runtime tại đây. Khi người dùng yêu cầu tích hợp template mới:

1. Đọc toàn bộ template trong `TemplatesBefore/`: placeholder, bảng, header/footer, checkbox, Word field và vùng được bảo vệ.
2. Đối chiếu `template_manifest.json` cùng mapping trong `services/documents/docx_generator.py`.
3. Copy template gốc sang `assets/templates/word/business_registration/`; không move và không ghi đè nguồn.
4. Cập nhật manifest/mapping tối thiểu cần thiết, bảo toàn layout và vùng protected.
5. Xuất hồ sơ thử, kiểm tra placeholder chưa điền và render DOCX để QA trực quan khi layout bị ảnh hưởng.
6. Thêm regression test cho mapping/trường mới.

Quy tắc DOCX:

- Không điền chéo vào vùng chủ sở hữu tổ chức hoặc section được yêu cầu giữ nguyên.
- Không bình thường hóa paragraph/run/table style của mẫu nếu không có yêu cầu rõ.
- Tên ngành, mô tả ngành và mã ngành là các dữ liệu riêng.
- Mapping CCCD phải đồng bộ giữa OCR, profile, workspace và DOCX, gồm `issue_date` và `issue_place`.

## Thay đổi đăng ký doanh nghiệp

Mục **2. Thủ tục thay đổi ĐKDN** mở thẳng `BusinessAmendmentWorkspace` với bốn
tab riêng: cơ quan/thời gian ký, doanh nghiệp, người đại diện và nội dung thay đổi.
PDF được nhận diện bằng `BusinessAmendmentDocumentService`, chỉ lấy tên doanh nghiệp
và mã số doanh nghiệp/mã số thuế ở phần nhận diện tổ chức; người dùng đối chiếu,
sửa và xác nhận trước khi áp dụng. Cơ quan tiếp nhận, nơi/ngày ký được nhập tại tab
tương ứng. Dữ liệu doanh nghiệp hiện tại và dữ liệu sau
thay đổi được lưu riêng trong mỗi hồ sơ.

`BusinessAmendmentTemplateGenerator` điền các vị trí vàng đã kiểm tra trong
`assets/templates/word/business_amendment/Thong bao thay doi.docx`, giữ nguyên
định dạng, các phần cố định và toàn bộ nội dung ngoài vị trí nhập. Ngoại lệ theo
yêu cầu: fax/website trong thay đổi địa chỉ được điền nếu có dữ liệu, giữ định dạng
không bôi vàng; để trống sẽ giữ nguyên dấu chấm của mẫu. Bản đồ vị trí
được ràng buộc với SHA-256 của mẫu; khi mẫu thay đổi cần cập nhật bản đồ trước
khi xuất. Mục B/C và ô đánh dấu chưa vàng giữ nguyên. Ba bảng ngành nghề cho phép
thêm/xóa dòng và lưu số dòng theo từng hồ sơ. Word nhân bản dòng dữ liệu của mẫu
để giữ định dạng và màu vàng, đánh STT liên tục và ghi X cho ngành chính đã chọn. Danh sách
thành viên/chủ sở hữu hưởng lợi gửi kèm chưa được tạo bởi chức năng này.

Giao diện ngành nghề tái sử dụng panel tra cứu và bộ dựng dòng của hồ sơ đăng ký
doanh nghiệp. Adapter riêng cho mỗi bảng bổ sung/bỏ/sửa chi tiết giữ các trường
`amendment_line_*`; tên và chi tiết được ghép vào ô Word khi xuất. Các workspace
đăng ký doanh nghiệp và thay đổi địa điểm kinh doanh giữ nguyên code và dữ liệu.
Ba bảng được chia thành ba tab. Nút tra cứu ở mỗi tab mở cửa sổ chọn ngành riêng,
ghi rõ bảng nhận dữ liệu; thêm thành công sẽ đóng cửa sổ và hiển thị dòng vừa thêm.
Hồ sơ mới không tạo sẵn dòng nhập ở cả ba bảng. Người dùng thêm dòng bằng tra cứu
hoặc nút thêm dòng trống, không giới hạn số ngành; xóa dòng cuối cùng trả bảng về rỗng.
Danh sách dài hiển thị theo trang 50 dòng để không tạo hàng nghìn bộ ô nhập cùng lúc;
việc lưu và xuất Word luôn dùng toàn bộ danh sách, kể cả các trang không đang mở.
Mỗi bảng trong mẫu Word giữ một hàng tiêu đề và một hàng dữ liệu trống. Khi xuất,
chỉ nhân bản hàng cho ngành đã nhập; bảng không có dữ liệu giữ một hàng trống.
Hồ sơ amendment version 4 lưu được số dòng bằng 0; khi mở bản cũ, chỉ bỏ dòng
template rỗng và giữ mọi dòng đã có dữ liệu, kể cả thông tin đang nhập dở.

Hồ sơ và phiên bản xuất được phân biệt bằng mã hồ sơ; dữ liệu cũ bị ẩn vẫn được
bảo toàn khi lưu lại. Nguồn trong `TemplatesBefore/` được giữ nguyên.

Phần vốn tự định dạng dấu chấm và tạo dòng diễn giải VNĐ/bằng chữ chỉ đọc cho
vốn đã đăng ký và vốn sau thay đổi. Hai bảng giống mẫu chỉ cho nhập Vốn tư nhân
và Đồng Việt Nam, tỷ lệ cố định 100%, tổng tự tính; các hàng còn lại giữ số 0.
Thời điểm/hình thức thay đổi vốn là văn bản tự nhập. Checkbox Có/Không hiển thị
ngoại tệ chỉ lưu lựa chọn trên màn hình, chưa xử lý vào Word.

## Dữ liệu runtime

```text
%APPDATA%\Min Assistant\
  settings.json
  cases.json
  personal_profiles.json
  authorized_person.json

Documents\Min Assistant\
  Bộ hồ sơ Word đã xuất
```

Dữ liệu cũ `%APPDATA%\Mingo Assistant` được copy một lần khi thư mục Min chưa tồn tại. Mở rộng JSON phải có version/migration, không phá dữ liệu cũ.

## Chạy và kiểm tra

Chạy source:

```powershell
$env:PYTHONPATH = "src"
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe -m mingo_assistant
```

Unit test Qt offscreen:

```powershell
$env:PYTHONPATH = "src"
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m unittest discover -s tests\unit
```

Build EXE:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-build.txt
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean `
  --workpath build\pyinstaller `
  --distpath dist `
  packaging\pyinstaller\MingoAssistantQRMaxV3.spec
```

Kết quả source test, build EXE, commit và push phải được báo riêng. Khi release: test -> build -> smoke test -> hash/version -> kiểm tra Git -> commit/push nếu được yêu cầu.

## Quy tắc phát triển

1. Logic/mapping mới vào `services/` hoặc `application/`, không nhét thêm vào `MainWindow`.
2. Widget PySide ở `ui/`; section có state/workflow riêng thì tách khỏi workspace.
3. Persistence qua repository/infrastructure, không ghi JSON trực tiếp từ widget.
4. Viết regression test trước khi thay OCR, DOCX hoặc đồng bộ CCCD.
5. Tách commit UI, template, migration dữ liệu và release thành phạm vi rõ ràng.

## Checklist bàn giao

```text
[ ] git status --short đã kiểm tra
[ ] py_compile đạt
[ ] unit test offscreen đạt
[ ] DOCX đã kiểm tra placeholder và layout nếu có thay đổi template
[ ] không có dữ liệu CCCD thật trong diff
[ ] chỉ báo build/smoke/hash khi thực sự đã chạy
[ ] báo riêng commit hash và push result
```

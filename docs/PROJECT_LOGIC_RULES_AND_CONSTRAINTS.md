# Logic, quy tắc và ràng buộc của Min Assistant

> Cập nhật: 16/10/2026
> Phạm vi: mô tả hành vi runtime, ranh giới kiến trúc, hợp đồng dữ liệu và các
> quy tắc bắt buộc khi bảo trì hoặc phát triển thêm tính năng.

## 1. Mục đích của tài liệu

Tài liệu này trả lời bốn câu hỏi:

1. Ứng dụng đang chạy theo luồng nào?
2. Mỗi lớp/module chịu trách nhiệm gì?
3. Những quy tắc nghiệp vụ và tương thích nào không được phá vỡ?
4. Khi thêm workflow, trường dữ liệu hoặc mẫu Word mới thì phải thay đổi và
   kiểm tra những gì?

Đây là tài liệu mô tả **code đang chạy**, không phải PRD cho chức năng chưa có.
Khi tài liệu này khác với code, cần kiểm tra test và hành vi runtime trước khi
quyết định bên nào đúng; không được tự động sửa code chỉ để khớp tài liệu.

Các tài liệu liên quan:

- `docs/ARCHITECTURE.md`: kiến trúc tổng quan.
- `docs/FORM_VALUES_SCHEMA.md`: version và nhóm khóa của `form_values`.
- `docs/DOCX_GENERATION_BOUNDARIES.md`: ranh giới hệ thống sinh Word.
- `docs/MAINTENANCE_ROADMAP.md`: lịch sử bảo trì và bằng chứng kiểm tra.
- `docs/INDUSTRY_TABLE_LOGIC_NOTE.md`: logic bảng ngành nghề.

## 2. Các bất biến quan trọng nhất

Những nguyên tắc dưới đây có mức ưu tiên cao hơn việc làm code ngắn hoặc tổng
quát hơn:

1. **Mỗi loại hồ sơ có nghiệp vụ riêng.** Không gom các workflow vào một thuật
   toán chung nếu việc đó làm mất quy tắc về trường bắt buộc, checkbox, CCCD,
   hộ chiếu, người ký, bảng ngành nghề hoặc cách điền Word.
2. **Màu vàng không phải luật toàn cục.** Một vị trí hợp lệ có thể là highlight
   vàng, shading, placeholder, ô bảng, symbol hoặc mapping trực tiếp không tô
   màu. Nguồn sự thật là mapping/manifest và regression test của generator đó.
3. **Không xóa mapping chỉ vì template không bôi vàng.** Có những mẫu người
   dùng quên highlight nhưng code vẫn phải điền đúng vị trí đã được xác nhận.
4. **Không thay đổi template nguồn trong một đợt refactor code.** Template,
   mapping, code sinh Word và dữ liệu form là bốn lớp riêng; thay lớp nào phải
   kiểm tra đúng lớp đó.
5. **Không làm mất dữ liệu hồ sơ cũ.** Khóa chưa được UI hoặc typed model hiện
   tại nhận diện phải sống qua chu trình mở → sửa → lưu.
6. **Danh sách động do UI sở hữu phải được thay toàn bộ.** Nếu người dùng xóa
   một dòng ngành nghề/thành viên, các khóa của dòng đó không được quay lại từ
   map legacy.
7. **OCR là dữ liệu gợi ý cần đối chiếu.** OCR/QR không được âm thầm ghi đè dữ
   liệu người dùng đã xác nhận hoặc đồng bộ nhầm sang một người khác.
8. **Lưu file phải an toàn khi ứng dụng bị ngắt.** JSON được ghi qua file tạm,
   `fsync` và `os.replace`; không ghi đè trực tiếp file chính từng phần.
9. **Unit test không chứng minh bố cục Word đúng.** Thay đổi có thể ảnh hưởng
   layout phải sinh file mới, render và kiểm tra trang.
10. **Git, build và release là các cổng độc lập.** Test đạt không có nghĩa EXE
    đã build; build đạt không có nghĩa đã smoke-test; cũng không đồng nghĩa code
    đã commit hoặc push.

## 3. Công nghệ và đặc tính vận hành

- Ngôn ngữ: Python 3.12.
- UI desktop: PySide6/Qt.
- Môi trường chính: Windows, chạy offline.
- Lưu hồ sơ: JSON cục bộ, không dùng SQLite làm kho chính.
- Tài liệu: DOCX, thao tác bằng `python-docx` và XML package khi cần.
- OCR/QR: service cục bộ, model nằm trong runtime assets.
- Đóng gói: PyInstaller theo script/spec trong `packaging/`.
- Test UI: Qt offscreen với `QT_QPA_PLATFORM=offscreen`.

Ứng dụng ưu tiên khả năng chạy offline và bảo toàn dữ liệu cục bộ. Không được
thêm phụ thuộc cloud, telemetry hoặc gửi tài liệu ra ngoài nếu chưa có yêu cầu
và cơ chế đồng ý rõ ràng.

## 4. Luồng khởi động

```text
python -m mingo_assistant
  -> src/mingo_assistant/__main__.py
  -> app/main.py::main()
  -> AppPaths
  -> SingleInstanceGuard
  -> AppContainer.build()
  -> MainWindow
  -> workspace registry
  -> workspace theo case_type
```

### 4.1 `AppPaths`

`AppPaths` phân biệt hai nhóm đường dẫn:

- `bundle_root`: mã nguồn/assets khi chạy source hoặc `_MEIPASS` khi chạy bản
  PyInstaller.
- `user_data_root`: `%APPDATA%\Min Assistant`.
- `documents_root`: mặc định là `Documents\Min Assistant`.

Các file runtime chính:

```text
%APPDATA%\Min Assistant\
  settings.json
  cases.json
  authorized_person.json
  personal_profiles.json
```

Nếu thư mục `Min Assistant` chưa tồn tại nhưng `%APPDATA%\Mingo Assistant` có
dữ liệu cũ, ứng dụng thử copy toàn bộ một lần để giữ dữ liệu khi đổi tên sản
phẩm. Lỗi copy không làm ứng dụng crash tại bước lấy đường dẫn.

### 4.2 `SingleInstanceGuard`

Ứng dụng có guard để tránh hai tiến trình cùng thao tác kho dữ liệu local. Không
nên bỏ guard chỉ để thuận tiện debug vì hai tiến trình có thể ghi đè `cases.json`
theo thứ tự không xác định.

### 4.3 `AppContainer`

`AppContainer` là composition root. Nó tạo và truyền dependency thay vì để
workspace tự khởi tạo service tùy ý. Các dependency chính gồm:

- `CaseRepository` và `CaseUseCases`.
- `AuthorizedPersonProfileRepository` và use case tương ứng.
- `IndustryCatalog`.
- `AdministrativePlaceMatcher` và `AddressParser`.
- `IdentityQrScanner` và `IdCardParser`.
- `OrganizationDocumentService`.
- `PersonalProfileRepository`.
- `RegistrationOfficeCatalog`.
- `RegistrationValidator`, export planner và value composer.
- `PersonRoleMapper` và `PersonProfileSynchronizer`.

Quy tắc: dependency dùng chung cấp tiến trình phải được nối tại container hoặc
application service; không tạo thêm một bản repository/catalog khác trong từng
widget nếu không có lý do nghiệp vụ.

## 5. Hướng phụ thuộc kiến trúc

```text
PySide6 UI
  -> application
  -> domains + models
  -> services
  -> repositories
  -> infrastructure
  -> filesystem local
```

### 5.1 UI

UI chịu trách nhiệm:

- Hiển thị field, bảng, modal và trạng thái tiến trình.
- Nhận input người dùng.
- Gọi use case/service.
- Chuyển dữ liệu giữa widget và `form_values`.
- Hiển thị validation/error theo ngữ cảnh.

UI không nên:

- Tự ghi JSON.
- Tự sửa XML DOCX.
- Chứa thuật toán OCR hoặc parser phức tạp.
- Chứa registry `if case_type` dài.
- Trở thành nơi sở hữu duy nhất của quy tắc có thể test độc lập.

### 5.2 Application

Application layer điều phối use case và phụ thuộc:

- CRUD/xóa mềm/khôi phục hồ sơ.
- Ghép và chuẩn hóa giá trị trước khi lưu/xuất.
- Lập kế hoạch phiên bản export.
- Mapping vai trò người.
- Migration theo workflow.

Application không nên biết chi tiết run/paragraph/XML của Word.

### 5.3 Domain và model

Domain/model chứa kiểu dữ liệu và quy tắc có thể chạy không cần Qt:

- `RegistrationCase`, `Company`, `Person`, `Address`, `BusinessLine`.
- `DependentUnitCase`, `ParentEntity`, `IdentityDocument`.
- `BusinessAmendmentCase`, `AmendmentLineChange`.
- Validation và định dạng tiền có tính nghiệp vụ.

Typed model hiện là projection hai chiều trên nền `dict[str, str]`; chưa thay
định dạng JSON. Đây là chủ ý để tương thích với UI/generator cũ.

### 5.4 Services

Services chứa OCR, parser, danh mục, normalization, template repository và
generator DOCX. Service dùng chung chỉ chứa cơ chế thực sự dùng chung; hook hoặc
mapping riêng phải ở service/generator của workflow tương ứng.

### 5.5 Repository và infrastructure

Repository chuyển giữa model và storage. Infrastructure cung cấp primitive
ghi/đọc file, phục hồi file hỏng và DPAPI. Repository không chứa logic widget
hoặc logic bố cục Word.

## 6. `CaseSummary` và hợp đồng dữ liệu hồ sơ

`CaseSummary` là aggregate persisted cấp hồ sơ. Các nhóm field:

### 6.1 Metadata hiển thị

- `id`: định danh ổn định của hồ sơ.
- `company_name`: tên hiển thị trên danh sách.
- `case_type`: khóa điều hướng workflow.
- `owner`: người ký/người ủy quyền dùng để hiển thị.
- `updated_at`, `status`, `condition`, `warning`.
- `members`, `capital`.

### 6.2 Metadata export

- `export_dir`: thư mục export gần nhất.
- `exported_at`: thời điểm export gần nhất.
- `generated_documents`: tên file của lần export gần nhất.
- `export_versions`: lịch sử các version export.

### 6.3 Xóa mềm

- `is_deleted`.
- `deleted_at`.

Xóa từ danh sách chỉ đánh dấu xóa mềm. Xóa vĩnh viễn và xóa toàn bộ thùng rác
mới loại phần tử khỏi JSON.

### 6.4 Dữ liệu form

- `form_values: dict[str, str]`.
- `form_schema_version: int`.

`form_values` là ranh giới tương thích giữa:

```text
widget UI <-> JSON local <-> typed projection <-> DOCX generator
```

Không đổi toàn bộ `form_values` sang schema mới trong một lần. Thay đổi format
phải có adapter/migration và test mở–lưu hồ sơ cũ.

## 7. Lưu trữ JSON và phục hồi lỗi

`CaseRepository` lưu payload:

```json
{
  "schema_version": 1,
  "cases": []
}
```

Repository vẫn đọc được dạng legacy là một JSON array thuần. Nếu file không tồn
tại, repository tạo file và hiện tại seed các hồ sơ demo. Nếu JSON lỗi cú pháp
hoặc sai cấu trúc:

1. Không ghi đè file lỗi.
2. Copy file sang `*.corrupt-<timestamp>.bak` bên cạnh.
3. Ném `CorruptDataError` có `backup_path`.
4. UI quyết định cách cảnh báo người dùng.

### 7.1 Ghi atomic

`write_json_atomic()`:

1. Tạo file tạm cùng thư mục với file đích.
2. Ghi UTF-8, `ensure_ascii=False`, indent 2.
3. `flush()`.
4. `os.fsync()`.
5. `os.replace()` file tạm vào file đích.
6. Cố dọn file tạm nếu có lỗi.

Không thay bằng `Path.write_text()` trực tiếp cho dữ liệu quan trọng.

## 8. Schema version và migration

### 8.1 Nguyên tắc chung

- Hồ sơ không có `form_schema_version` được coi là version `0`.
- Chỉ đọc danh sách không tự rewrite hồ sơ.
- Migration chạy trên bản copy trong bộ nhớ.
- Hồ sơ được nâng version khi mở/lưu qua workflow tương ứng.
- Key chưa biết phải được giữ.
- Case type chưa biết không bị tự động nâng version.

### 8.2 Version hiện tại

| Workflow | Version |
| --- | ---: |
| Đăng ký doanh nghiệp | 1 |
| Đơn vị phụ thuộc: lập/thay đổi/chấm dứt | 1 |
| Thay đổi nội dung ĐKDN | 4 |

### 8.3 Merge lossless

Typed adapter ghi các field nó sở hữu lên một map nền. Hai nhóm key được xử lý
khác nhau:

- Key tĩnh/không nhận diện: giữ nguyên.
- Namespace động do UI sở hữu: xóa toàn bộ namespace cũ rồi ghi snapshot mới.

Namespace động quan trọng:

- `business_line_<n>_*`.
- `person_<n>_*`.
- `member_<n>_*`.
- `beneficial_owner_row_<n>_*`.
- `beneficial_owner_list_<n>_*`.
- `amendment_line_{add,remove,detail}_<n>_*`.

Nếu chỉ overlay từng key mà không thay namespace, dòng người dùng đã xóa sẽ
quay lại từ dữ liệu legacy.

### 8.4 Migration thay đổi ĐKDN

Migration v0–v3 lên v4:

- Thu gọn các dòng ngành nghề rỗng được tạo sẵn ở version cũ.
- Giữ đủ `name`, `detail`, `code`, `main`, `note` của dòng có dữ liệu.
- Chuyển `change_shares_selected` cũ sang `change_capital_selected` khi phù hợp.
- Xóa key legacy đã được thay thế rõ ràng.
- Giữ mọi key khác, kể cả key thuế/tổ chức/template tương lai.

## 9. Điều hướng và lifecycle UI

`ui/routing/workspace_registry.py` ánh xạ `case_type` sang:

- `workspace_class`.
- `return_target`.
- `nav_key`.
- cờ `dependent`.

Các route chính:

| Route | Case type | Workspace |
| --- | --- | --- |
| Đăng ký doanh nghiệp | Các alias TNHH đang hỗ trợ | `BusinessRegistrationWorkspace` |
| Thay đổi ĐKDN | `Doanh nghiệp - Thay đổi nội dung ĐKDN` | `BusinessAmendmentWorkspace` |
| Lập ĐĐKD | `Địa điểm kinh doanh - Lập mới` | `LocationBusinessWorkspace` |
| Thay đổi ĐĐKD | `Địa điểm kinh doanh - Thay đổi nội dung kinh doanh` | `LocationBusinessUpdateWorkspace` |
| Chấm dứt ĐĐKD | `Địa điểm kinh doanh - Chấm dứt hoạt động` | `LocationBusinessTerminationWorkspace` |

Thêm workflow mới phải thêm route vào registry, không thêm chuỗi
`if case.case_type == ...` vào `MainWindow`.

`MainWindow._show_transient_view()` quản lý workspace và màn hình documents:

1. Gỡ view tạm hiện tại khỏi stack.
2. Gọi `deleteLater()`.
3. Đặt reference cũ về `None`.
4. Thêm view mới vào stack.
5. Chuyển current widget.
6. Ẩn sidebar phù hợp với chế độ layout.

Mục tiêu là tránh tích lũy widget và signal khi người dùng mở/sửa/Back nhiều lần.

## 10. Luồng chung của một hồ sơ

```text
Chọn thủ tục
  -> tạo/mở workspace
  -> nạp CaseSummary.form_values
  -> restore widget + dữ liệu OCR/PDF liên quan
  -> người dùng nhập/đối chiếu
  -> validate
  -> build CaseSummary
  -> CaseUseCases.save()
  -> CaseRepository.save_case()
  -> atomic JSON
```

Luồng export:

```text
form_values hiện tại
  -> validation nghiệp vụ
  -> validate template/hash/manifest
  -> tạo thư mục version mới
  -> DocxExportWorker
  -> generator workflow
  -> GenerationResult
  -> cập nhật export_dir/exported_at/generated_documents/export_versions
  -> lưu lại CaseSummary
  -> mở màn hình documents
```

Lưu nháp và export là hai hành động khác nhau. Export không được dựa vào state
UI chưa serialize; lưu nháp không được giả vờ rằng file Word đã được sinh.

## 11. OCR, QR và dữ liệu người

### 11.1 Nguyên tắc nhận diện

- QR/OCR tạo dữ liệu có cấu trúc nhưng không phải nguồn tuyệt đối.
- Field có trạng thái cần xác nhận phải được người dùng xác nhận trước export.
- Lỗi parse không được làm mất input thủ công đã có.
- Đường dẫn ảnh/raw text/metadata nguồn thuộc hồ sơ, không được ghi vào source.

### 11.2 Mapping vai trò

`PersonRoleMapper` chuyển một bản ghi CCCD đã chuẩn hóa sang vai trò:

- người đại diện pháp luật;
- người nộp hồ sơ;
- người được ủy quyền;
- thành viên;
- chủ sở hữu hưởng lợi.

Mapping địa chỉ có quy tắc riêng. Ví dụ vai trò người nộp có thể tách địa chỉ
thành chi tiết/phường/tỉnh; người được ủy quyền ưu tiên địa chỉ liên lạc hợp lệ.

### 11.3 Đồng bộ theo định danh

`PersonProfileSynchronizer` chỉ cập nhật người/role có số định danh khớp sau khi
loại ký tự không phải số. Không đồng bộ chỉ dựa trên vị trí dòng UI.

Khi người nộp và người được ủy quyền là hai người khác nhau, logic bảo vệ tránh
sao chép nhầm cùng phone/email giữa hai vai trò.

### 11.4 CCCD và hộ chiếu

Các workflow đơn vị phụ thuộc giữ đồng thời dữ liệu CCCD và hộ chiếu trong typed
projection. Model không tự xóa một loại giấy tờ theo `person_type`; validation
của workflow quyết định field nào bắt buộc. Quy tắc này tránh mất dữ liệu hồ sơ
cũ khi UI hoặc loại người thay đổi.

## 12. Workflow đăng ký doanh nghiệp

### 12.1 Dữ liệu chính

- Thông tin doanh nghiệp và địa chỉ.
- Người đại diện pháp luật.
- Người được ủy quyền/người nộp hồ sơ.
- Chủ sở hữu cá nhân hoặc tổ chức.
- Vốn điều lệ và nguồn/tài sản góp vốn.
- Ngành nghề kinh doanh.
- Thông tin ký.
- Metadata OCR và profile trong hồ sơ.

### 12.2 Validation

Validation domain kiểm tra field bắt buộc, trạng thái xác nhận địa chỉ CCCD và
ngành nghề chính. Khi có ngành nghề, phải có ít nhất một dòng được chọn là ngành
chính theo contract hiện tại.

### 12.3 Chủ sở hữu cá nhân/tổ chức

Template điều lệ được chọn theo `owner_type`. Không điền đồng thời cả template
cá nhân và tổ chức. Các mapping của chủ sở hữu tổ chức, người đại diện tổ chức
và giấy đăng ký tổ chức phải ở đúng generator/workflow.

### 12.4 Công ty hai thành viên cá nhân

Workflow hai thành viên dùng generator riêng:

- Danh sách thành viên là namespace động.
- Vốn góp từng thành viên và tổng vốn phải sống qua reopen.
- Danh sách chủ sở hữu hưởng lợi có projection riêng.
- Các File 1–6 có mapping/bảng/chữ ký khác nhau.
- Không áp layout hoặc quy tắc File 1 cho File 3/4/6 nếu chưa kiểm tra.

## 13. Workflow thay đổi nội dung ĐKDN

### 13.1 Các nhóm thay đổi

Workflow hiện quản lý các nhóm:

- tên doanh nghiệp;
- địa chỉ trụ sở;
- vốn điều lệ/phần vốn/cổ phần;
- ngành nghề kinh doanh;
- thông tin thuế;
- thông báo chủ sở hữu hưởng lợi.

Các nhóm thành viên, bổ sung/cập nhật và hiệu đính có thể xuất hiện trong UI
nhưng template hiện tại có giới hạn riêng; không suy diễn rằng tất cả nhóm đã
được xuất Word đầy đủ chỉ vì có checkbox.

### 13.2 Suy luận nhóm được chọn

Khi mở hồ sơ cũ, hệ thống có thể suy luận một nhóm là active nếu các field của
nhóm đã có dữ liệu. Riêng nhóm chủ sở hữu hưởng lợi không được suy luận từ giá
trị mặc định của dropdown; cần lựa chọn rõ ràng.

### 13.3 Dòng ngành nghề thay đổi

Ba loại dòng độc lập:

- `add`: bổ sung.
- `remove`: bỏ ngành nghề.
- `detail`: sửa chi tiết.

Dòng có `name`, `detail`, `code` và `main` hoặc `note` tùy loại. Row count không
phải giới hạn nghiệp vụ; số dòng mẫu chỉ là số dòng có sẵn trong template.

### 13.4 Template Form 12

`BusinessAmendmentTemplateGenerator`:

- Kiểm tra tên file và SHA-256 của template khóa.
- Có bản đồ slot đã rà soát.
- Chỉ điền nhóm change đang active.
- Giữ phần cố định và định dạng template.
- Có ngoại lệ được duyệt cho fax/website không bôi vàng.

Không chuyển generator này sang kế thừa pipeline thành lập doanh nghiệp. Hai
workflow có nghiệp vụ và cấu trúc template khác nhau.

## 14. Workflow đơn vị phụ thuộc/địa điểm kinh doanh

Ba thủ tục là ba workspace riêng:

1. Lập địa điểm kinh doanh.
2. Thay đổi nội dung địa điểm kinh doanh.
3. Chấm dứt hoạt động địa điểm kinh doanh.

Không flatten thành một form chung nếu việc đó làm mờ quy tắc khác nhau.

### 14.1 Dữ liệu dùng chung

- Doanh nghiệp hoặc chi nhánh chủ quản.
- Tên/mã/địa chỉ/liên hệ của địa điểm.
- Người đứng đầu.
- Người đại diện pháp luật.
- Người được ủy quyền.
- Ngành nghề.
- Thông tin ký.

### 14.2 Người đứng đầu là người nước ngoài

Workflow phải giữ:

- `person_type`.
- số CCCD nếu có;
- số hộ chiếu;
- ngày/nơi cấp hộ chiếu;
- địa chỉ trong nước;
- địa chỉ và quốc gia ở nước ngoài.

Không dùng validation của công dân Việt Nam để xóa hộ chiếu hoặc địa chỉ nước
ngoài.

### 14.3 Thay đổi địa điểm kinh doanh

Workflow update có các ràng buộc riêng:

- Nội dung đăng ký bổ sung có thể nhiều dòng.
- Checkbox/mapping thông báo thay đổi thuộc generator đơn vị phụ thuộc.
- Template thông báo hiện có guard số highlight đã rà soát.
- Không xóa highlight trống không liên quan.
- Bảng ngành nghề phải có 4 cột, STT liên tục và dấu `X` đúng ngành chính.
- Text STT/`X` cần màu đen rõ để không kế thừa màu ẩn từ template.

Con số highlight là thuộc tính của đúng phiên bản template, không phải hằng số
nghiệp vụ vĩnh viễn. Chỉ đổi guard sau khi template được thay có chủ ý và XML đã
được đếm/rà lại.

### 14.4 Chấm dứt hoạt động

Workflow termination sở hữu mã địa điểm, lý do chấm dứt, thông tin giấy chứng
nhận và thông tin ký. Không ép các field này vào create/update nếu template và
nghiệp vụ không dùng.

## 15. Kiến trúc sinh DOCX

### 15.1 Các lớp dùng chung

- `DocxTemplateEngine`: cơ chế trung lập.
- `DocumentContextBuilder`: lấy giá trị theo target.
- `DocumentValueFormatter`: format ngày, tiền, địa chỉ, ngành nghề.
- `template_repository.py`: chọn template.
- `template_manifest.py`: đọc manifest.
- `package_editor.py`: chỉnh package/XML khi `python-docx` không đủ.
- `GenerationResult`: kết quả chuẩn của một lần sinh.

Engine chung được phép chứa:

- duyệt paragraph/table;
- thay run highlight theo manifest;
- giữ symbol checkbox;
- dựng bảng ngành nghề bốn cột;
- giữ geometry/format cơ bản;
- helper xử lý run/XML không phụ thuộc một hồ sơ cụ thể.

Engine chung không được chứa:

- tên field chỉ có ở một workflow;
- cách chọn bộ hồ sơ;
- quy tắc CCCD/hộ chiếu riêng;
- người ký riêng;
- hash hoặc slot của một template cụ thể;
- quyết định nghiệp vụ về field nào bắt buộc.

### 15.2 Generator workflow

- `business_registration_generator.py`: đăng ký doanh nghiệp.
- `two_member_individual_generator.py`: TNHH hai thành viên cá nhân.
- `dependent_unit_generator.py`: lập/thay đổi đơn vị phụ thuộc.
- `location_termination_generator.py`: chấm dứt địa điểm.
- `business_amendment_generator.py`: thay đổi ĐKDN.
- `docx_generator.py`: facade tương thích cho import cũ.

Facade không phải nơi đưa implementation mới vào.

### 15.3 `GenerationResult`

Generator trả:

- `output_dir`.
- danh sách `GeneratedDocument(source_name, output_path)`.
- danh sách template bị skip.
- dictionary placeholder/target chưa xử lý.

UI phải phân biệt `template_issues`, lỗi runtime và kết quả thành công; không coi
việc tạo được một vài file là toàn bộ bộ hồ sơ đã thành công.

## 16. Quy tắc màu vàng, shading và mapping trực tiếp

Đây là ràng buộc dễ bị hiểu sai nhất.

### 16.1 Màu vàng chỉ là một cơ chế

Một vị trí có thể được điền qua:

- run highlight vàng;
- paragraph highlight;
- shading nhìn giống màu vàng;
- placeholder text;
- cell trong bảng;
- symbol checkbox;
- XML target;
- mapping trực tiếp theo paragraph/run/cell;
- hậu xử lý riêng của generator.

Do đó không được viết rule toàn cục kiểu:

```text
nếu không bôi vàng => không được thay
```

### 16.2 Nguồn sự thật theo thứ tự

1. Quy tắc nghiệp vụ đã được xác nhận.
2. Generator/mapping riêng của workflow.
3. Manifest của đúng template.
4. Regression test.
5. Bản render của tài liệu sinh mới.
6. Màu/highlight của template là bằng chứng hỗ trợ, không phải nguồn duy nhất.

### 16.3 Ngoại lệ đã biết

- Fax/website của form thay đổi ĐKDN có vị trí không highlight.
- Một số field giới tính/địa chỉ trong hồ sơ thành lập dùng mapping trực tiếp.
- Một số ô của đơn vị phụ thuộc dùng shading thay vì highlight.
- Bảng ngành nghề được dựng theo cấu trúc bảng, không chỉ theo run vàng.

Khi phát hiện một vị trí người dùng quên bôi vàng, cần bổ sung mapping và test
cho đúng template; không tự tô màu toàn bộ hoặc thay mọi đoạn trống.

## 17. Template source, runtime và vùng protected

```text
TemplatesBefore/          mẫu nguồn/inbox do người dùng cung cấp
assets/templates/word/    mẫu runtime ứng dụng thực sự nạp
```

Quy tắc:

- Không sửa hoặc di chuyển `TemplatesBefore/` trong bảo trì thông thường.
- Không ghi đè template runtime nếu yêu cầu chỉ là refactor code.
- Không cập nhật SHA để “làm test xanh” khi template đổi ngoài dự kiến.
- Không normalize toàn bộ run/paragraph/table/header/footer/section.
- Chỉ thay node/field thuộc mapping của template đó.
- Giữ page break, bookmark, checkbox, tab stop, font và protected region.
- Lỗi có sẵn trong template nguồn phải được báo riêng với regression mới.

## 18. Bảng ngành nghề

Nguồn dữ liệu chuẩn là:

```text
business_line_<n>_name
business_line_<n>_detail
business_line_<n>_code
business_line_<n>_is_main
```

Quy tắc output:

- STT hiển thị liên tục theo danh sách output, không nhất thiết bằng index key
  legacy.
- Cột tên có thể ghép tên và nội dung chi tiết nhiều dòng.
- Mã ngành nằm đúng cột mã.
- Cột ngành chính chỉ có `X` khi `is_main` được chọn.
- Không giữ các dòng mẫu rỗng chỉ để đủ số hàng ban đầu.
- Không để STT hoặc `X` kế thừa màu chữ khiến chúng vô hình.
- Geometry bốn cột của template phải được giữ.

Khi lỗi output, phải trace cả chuỗi:

```text
checkbox UI
  -> form_values(..._is_main)
  -> formatter/business_lines()
  -> writer bảng DOCX
```

Không sửa renderer trước khi chắc chắn flag không bị mất ở bước serialize.

## 19. Export và version tài liệu

Mỗi lần export tạo một version riêng thay vì ghi đè bộ hồ sơ cũ. Planner tạo
tên thư mục an toàn và workspace lưu metadata vào `export_versions`.

Sau khi generator thành công:

1. Lấy danh sách file thực sự được sinh từ `GenerationResult.generated`.
2. Ghi `exported_at`.
3. Ghi `export_dir` gần nhất.
4. Append version mới vào `export_versions`.
5. Lưu lại `CaseSummary`.

Nếu validation/template/generator lỗi, không cập nhật metadata như thể export
đã thành công.

Export chạy qua worker để không chặn UI. Worker phải luôn trả một trong ba dạng:

- `{"template_issues": ...}`;
- `{"error": ...}`;
- `{"result": GenerationResult}`.

## 20. Bảo mật và dữ liệu nhạy cảm

### 20.1 Dữ liệu không được đưa vào Git

- CCCD/hộ chiếu thật.
- Ảnh giấy tờ.
- Hồ sơ khách hàng.
- Raw OCR có thông tin cá nhân.
- File Word xuất thực tế.
- Token, mật khẩu hoặc khóa bí mật.

### 20.2 DPAPI

`DpapiJsonStorage` là adapter mã hóa tùy chọn theo Windows user:

- Dùng `CryptProtectData`/`CryptUnprotectData`.
- Không lưu application-owned encryption key.
- Có header định dạng riêng.
- Ghi file theo cơ chế atomic.

Repository hồ sơ hiện tại vẫn là JSON plaintext local; không được mô tả rằng
toàn bộ dữ liệu đã mã hóa chỉ vì adapter DPAPI tồn tại.

Test DPAPI phải chạy trong Windows user context thật. Một sandbox không truy cập
được DPAPI có thể trả `WinError 2`; cần chạy riêng ngoài sandbox trước khi kết
luận code hỏng.

## 21. Xử lý lỗi và thông báo

- Lỗi filesystem phải được bọc bằng error có path và mô tả hành động.
- File JSON hỏng phải được backup trước khi báo lỗi.
- Template sai hash/manifest phải fail closed, không đoán vị trí rồi xuất.
- Validation nghiệp vụ phải trả danh sách vấn đề cụ thể.
- Exception trong worker phải được chuyển về payload lỗi, không làm mất thread
  hoặc treo nút export.
- UI không nên nuốt lỗi và báo “thành công” nếu chỉ một phần quy trình đạt.

## 22. Quy tắc thêm workflow mới

Thứ tự khuyến nghị:

1. Định nghĩa `case_type` ổn định.
2. Xác định schema `form_values` và version đầu tiên.
3. Tạo typed model/adapter nếu dữ liệu không còn đơn giản.
4. Xác định migration từ version cũ hoặc version 0.
5. Tạo workspace riêng hoặc composition từ section dùng chung.
6. Thêm route vào `workspace_registry.py`.
7. Tạo template folder runtime riêng.
8. Kiểm kê từng tài liệu trong bộ hồ sơ.
9. Viết generator/mapping riêng.
10. Chỉ đưa cơ chế thực sự trung lập xuống `DocxTemplateEngine`.
11. Viết validation domain/workflow.
12. Viết test round-trip dữ liệu.
13. Viết test generator và protected region.
14. Test Back/Save/Export/reopen.
15. Sinh mới DOCX đại diện và render nếu layout bị tác động.

Không copy một workspace/generator rồi đổi vài tên mà chưa kiểm tra các quy tắc
ẩn của bộ hồ sơ gốc.

## 23. Quy tắc sửa workflow đang có

Trước khi sửa:

- Xác định case type và workspace.
- Xác định generator và template thực sự được dùng.
- Xác định field nằm ở widget, `form_values`, typed model hay formatter.
- Tìm test hồi quy hiện có.
- Kiểm tra working tree để không ghi đè thay đổi khác.

Trong khi sửa:

- Giữ thay đổi nhỏ theo một trách nhiệm.
- Không đổi template và code cùng lúc nếu không cần.
- Bảo toàn unknown keys.
- Không xóa trực tiếp dữ liệu legacy chưa hiểu.
- Không generic hóa quy tắc đặc thù.
- Không thay source template để che lỗi generator.

Sau khi sửa:

- Chạy test mục tiêu.
- Chạy `scripts/verify.py` trước commit.
- Chạy `git diff --check`.
- Kiểm tra không có dữ liệu thật trong diff.
- Nếu ảnh hưởng DOCX: kiểm tra placeholder/unresolved.
- Nếu ảnh hưởng layout: render và xem từng trang đại diện.
- Nếu ảnh hưởng persistence: mở/lưu lại case version cũ.

## 24. Ma trận bằng chứng kiểm tra

| Loại thay đổi | Bằng chứng tối thiểu |
| --- | --- |
| Domain/formatter thuần Python | Unit test + Ruff + mypy |
| Serialization/migration | Round-trip + unknown-key preservation + case cũ |
| Repository/storage | Unit test lỗi đọc/ghi + atomic/recovery test |
| UI/workspace | Qt offscreen + reopen + Back/Save |
| Routing/lifecycle | Mở liên tiếp + stack không tăng + deferred delete |
| OCR/mapping người | Dữ liệu nhiều người + identity match + không cross-copy |
| Generator DOCX | Targeted test + template validation + unresolved check |
| Mapping/template/layout | Sinh file mới + render trực quan |
| Packaging | Build EXE + archive inspection + smoke launch |
| Git/release | Status/diff riêng; chỉ commit/push khi được yêu cầu |

## 25. Lệnh kiểm tra chuẩn

Cổng nhanh trong lúc phát triển:

```powershell
.\.venv\Scripts\python.exe scripts\verify.py --fast
```

Cổng đầy đủ trước commit:

```powershell
.\.venv\Scripts\python.exe scripts\verify.py
```

Lệnh đầy đủ chạy:

- compile `src` và `tests`;
- Ruff;
- mypy trong phạm vi `application/`, `models/`, `domains/`;
- toàn bộ unit test;
- integration test;
- `git diff --check`.

Trước release còn cần build/package/smoke test và render DOCX nếu đường sinh tài
liệu có thay đổi. `verify.py` không thay thế các cổng trực quan hoặc packaging.

## 26. Những việc không được tự động làm

- Không commit/push/upload Git nếu người dùng chưa yêu cầu.
- Không xóa artifact/untracked folder chỉ vì chúng không nằm trong source.
- Không sửa ACL/owner rộng để vượt lỗi sandbox.
- Không reset repository hoặc template để “làm sạch” working tree.
- Không cập nhật template hash khi chưa xác nhận template mới.
- Không xóa field vì chưa thấy nó trên UI hiện tại.
- Không coi mọi vị trí không vàng là protected.
- Không coi mọi vị trí vàng là bắt buộc phải xóa/điền.
- Không suy diễn unit test đạt thành visual QA đạt.
- Không suy diễn build đạt thành release đã sẵn sàng.

## 27. Các giới hạn hiện tại cần ghi nhớ

- `form_values` vẫn là dictionary string để giữ tương thích; typed model chưa
  thay thế hoàn toàn state UI.
- Một số workspace còn lớn và chứa nhiều orchestration UI.
- Một số template có bố cục/trang trắng có sẵn từ nguồn.
- DPAPI mới là adapter tùy chọn, chưa bao phủ toàn bộ repository.
- OCR luôn cần benchmark trên giấy tờ thực tế mới trước khi đổi threshold/model.
- Mypy chưa áp lên toàn bộ PySide6 UI để tránh một đợt sửa type diện rộng.
- Render QA vẫn là bước thủ công/bán tự động khi layout thay đổi.

Các giới hạn này không phải lý do để phá tương thích. Mỗi cải tiến cần một lát
cắt nhỏ, test rõ và đường rollback an toàn.

## 28. Bản đồ file quan trọng

```text
src/mingo_assistant/
  __main__.py
  app/
    main.py
    paths.py
    container.py
    lifecycle.py
  application/
    cases.py
    registration.py
    people.py
    profiles.py
    form_migrations.py
  domains/
    business_registration/
    business_amendment/
    dependent_unit/
  models/
    case.py
    form_values.py
    business_registration.py
  repositories/
    case_repository.py
    authorized_person_repository.py
  infrastructure/
    storage/json_file.py
    security/dpapi.py
  services/
    business_lines/
    normalization/
    ocr/
    qr/
    organization_documents/
    documents/
  ui/
    main_window.py
    routing/workspace_registry.py
    dialogs/
    views/
```

## 29. Tóm tắt quyết định thiết kế

Min Assistant không coi mọi hồ sơ là cùng một form và không coi mọi template
Word là cùng một cấu trúc. Phần dùng chung chỉ cung cấp cơ chế; workflow giữ
quyền sở hữu nghiệp vụ, mapping và validation của mình.

Ranh giới ổn định hiện tại là `CaseSummary.form_values`. Typed adapter và
migration làm dữ liệu an toàn hơn nhưng vẫn giữ tương thích. Repository bảo vệ
file bằng ghi atomic và backup file hỏng. Registry tách điều hướng khỏi
`MainWindow`. Generator tách theo bộ hồ sơ, còn engine chung chỉ xử lý cơ chế
DOCX trung lập.

Khi có xung đột giữa mong muốn “code gọn hơn” và yêu cầu giữ đúng hồ sơ, ưu tiên
tính đúng của từng bộ hồ sơ, dữ liệu người dùng và độ trung thực của template.

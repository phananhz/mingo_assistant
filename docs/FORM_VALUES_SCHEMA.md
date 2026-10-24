# Bản đồ schema `form_values`

Tài liệu này mô tả dữ liệu form đang được lưu trong từng `CaseSummary`. Mục tiêu của Giai đoạn 4 là thêm kiểu dữ liệu và migration từng bước mà không đổi đột ngột định dạng JSON đang chạy.

## Hợp đồng tương thích

- `form_values` tiếp tục là `dict[str, str]` trong dữ liệu lưu trữ và giao diện hiện tại.
- `form_schema_version` nằm ở cấp `CaseSummary`; hồ sơ cũ không có trường này được đọc là phiên bản `0`.
- Khi mở rồi lưu lại, khóa chưa được UI hiện tại nhận diện phải được giữ nguyên.
- Namespace danh sách động do UI quản lý được thay toàn bộ để hàng đã xóa không xuất hiện lại: `business_line_<n>_*`, `person_<n>_*`, `member_<n>_*`, `beneficial_owner_row_<n>_*` và `beneficial_owner_list_<n>_*`.
- Migration chỉ được tăng version sau khi đã có test mở/lưu lại dữ liệu phiên bản cũ.
- Không chuyển đổi hàng loạt hồ sơ trên đĩa khi chỉ đọc danh sách. Hồ sơ được nâng version khi người dùng mở và lưu qua workflow tương ứng.

## Phiên bản hiện tại

| Workflow | `case_type` | Version mới | Trạng thái model/migration |
| --- | --- | ---: | --- |
| Thành lập công ty TNHH một thành viên | `TNHH một thành viên` | 1 | Có projection typed `RegistrationCase`; lưu trữ vẫn giữ map cũ |
| Thành lập công ty TNHH hai thành viên cá nhân | `TNHH hai thành viên (Cá nhân)` | 1 | Dùng cùng nền đăng ký doanh nghiệp; có danh sách thành viên và chủ sở hữu hưởng lợi động |
| Lập địa điểm kinh doanh | `Địa điểm kinh doanh - Lập mới` | 1 | Kế thừa nền lưu form nhưng giữ mapping địa điểm riêng |
| Thay đổi địa điểm kinh doanh | `Địa điểm kinh doanh - Thay đổi nội dung kinh doanh` | 1 | Thêm nội dung đăng ký bổ sung và dữ liệu giấy chứng nhận |
| Chấm dứt địa điểm kinh doanh | `Địa điểm kinh doanh - Chấm dứt hoạt động` | 1 | Thêm mã địa điểm, lý do chấm dứt và thông tin ký |
| Thay đổi nội dung ĐKDN | `Doanh nghiệp - Thay đổi nội dung ĐKDN` | 4 | Đã có migration dòng ngành nghề cũ và `amendment_schema_version=4` |

Các loại hồ sơ chưa triển khai đầy đủ vẫn được đọc với version `0`; không tự nâng version chỉ dựa trên tên `case_type`.

## Nhóm dữ liệu dùng chung

| Nhóm | Khóa/prefix tiêu biểu | Kiểu đích dự kiến |
| --- | --- | --- |
| Doanh nghiệp | `company_*`, `parent_entity_*` | `Company`, `Organization` |
| Người | `legal_representative_*`, `authorized_person_*`, `location_manager_*` | `Person`, `AuthorizedPerson` |
| Địa chỉ | `*_address`, `*_address_detail`, `*_ward`, `*_province` | `Address` |
| Ngành nghề | `business_line_<n>_*`, `amendment_line_<kind>_<n>_*` | `BusinessLine`, `BusinessLineChange` |
| Vốn | `charter_capital_*`, `capital_source_<n>_*`, `asset_contribution_<n>_*`, `member_<n>_capital_*` | số nguyên VNĐ và `Decimal` cho tỷ lệ |
| Ký tài liệu | `document_place`, `document_day`, `document_month`, `document_year`, `signer_full_name` | `SigningContext` |
| OCR/nguồn quét | `people_count`, `person_<n>_*`, đường dẫn mặt trước/sau và raw text | `ScannedPerson` giữ metadata nguồn |

## Adapter typed đã triển khai

`RegistrationCase.from_form_values()` hiện đọc các nhóm doanh nghiệp, địa chỉ, người đại diện pháp luật, người được ủy quyền, chủ sở hữu tổ chức, vốn điều lệ, ngành nghề và thông tin ký. Ngày đầy đủ được chuyển thành `date`, vốn điều lệ thành `int`; dữ liệu gốc vẫn được giữ trong `legacy_form_values`.

`RegistrationCase.to_form_values(base=...)` ghi các trường mà model sở hữu lên một map nền. Adapter tuân thủ các nguyên tắc:

- Không thay đổi map nguồn và giữ mọi khóa ngoài phạm vi model.
- Giữ cách định dạng vốn cũ nếu giá trị số không đổi.
- Thay toàn bộ namespace `business_line_<n>_*` để dòng đã xóa không quay lại.
- Giữ nguyên chỉ số dòng ngành nghề đã được lưu, kể cả khi chỉ số không liên tục.
- Chuẩn hóa ngày typed về `dd/mm/yyyy` khi ghi ngược.

Adapter này chưa được dùng để thay thế trực tiếp state của UI. UI vẫn lưu `dict[str, str]`; model typed hiện là ranh giới đọc/ghi có kiểm thử để các workflow được chuyển dần.

`DependentUnitCase.from_form_values()` / `to_form_values(base=...)` bao phủ phần dữ liệu chung của ba workflow địa điểm kinh doanh:

- Doanh nghiệp hoặc chi nhánh chủ quản.
- Tên, mã số, địa chỉ và thông tin liên hệ của địa điểm kinh doanh.
- Người đứng đầu với cả CCCD lẫn hộ chiếu, loại người, địa chỉ trong nước/nước ngoài.
- Người đại diện pháp luật và người được ủy quyền.
- Ngành nghề, thông tin ký, nội dung đăng ký bổ sung và lý do chấm dứt.

Adapter không tự xóa CCCD hoặc hộ chiếu dựa trên loại người. Quy tắc trường nào được dùng và bắt buộc vẫn thuộc validation của từng workflow; nhờ đó dữ liệu cũ không bị mất khi đổi phiên bản UI. Các nhóm thuế, OCR, checkbox thay đổi và dữ liệu giấy chứng nhận chưa được typed vẫn được giữ nguyên qua map nền.

`BusinessAmendmentCase.from_form_values()` / `to_form_values(base=...)` bao phủ
thông tin doanh nghiệp, người đại diện, thông tin ký, nhóm thay đổi được chọn và
ba loại dòng ngành nghề thêm/bỏ/sửa. Migration domain nâng dữ liệu phiên bản
0-3 lên phiên bản 4 trong bộ nhớ, thu gọn các dòng ngành nghề rỗng cũ và chuyển
`change_shares_selected` sang `change_capital_selected`. Migration không sửa map
nguồn, không tự ghi xuống đĩa và giữ nguyên khóa thuế, tổ chức, OCR hoặc mapping
template chưa được typed.

`application.form_migrations.migrate_form_values()` là registry theo workflow.
Các workflow đăng ký và đơn vị phụ thuộc có migration tương thích v0 -> v1
không đổi dữ liệu; hồ sơ thay đổi ĐKDN dùng migration v0-3 -> v4; case type chưa
biết được giữ nguyên version và dữ liệu.

## Khóa đặc thù theo workflow

### Thành lập doanh nghiệp

- Chọn mẫu: `registration_template_variant`, `owner_type`.
- Chủ sở hữu cá nhân/tổ chức: `beneficial_owner_*`, `organization_owner_*`.
- Danh sách thành viên: `member_count`, `member_<n>_*`.
- Chủ sở hữu hưởng lợi hai thành viên: `beneficial_owner_row_<n>_*` và projection `beneficial_owner_list_<n>_*`.
- Ngành nghề: `business_line_<n>_{name,detail,code,is_main}`.

### Đơn vị phụ thuộc

- Doanh nghiệp/chi nhánh chủ quản: `parent_entity_*`.
- Địa điểm: `location_business_*`, `location_*`.
- Người đứng đầu: `location_manager_*`; quy tắc CCCD/hộ chiếu phụ thuộc loại người.
- Thay đổi nội dung: `supplemental_registration_content*`.
- Chấm dứt: `location_business_code`, `termination_reason`.

### Thay đổi đăng ký doanh nghiệp

- Version nội bộ hiện có: `amendment_schema_version`.
- Nhóm được chọn: `change_*_selected`.
- Tên, địa chỉ, vốn/cổ phần, thuế và chủ sở hữu hưởng lợi dùng các prefix riêng.
- Ngành nghề động: `amendment_line_{add,remove,detail}_<n>_*`.
- `AmendmentFormState` giữ nguyên khóa cũ chưa nhận diện và loại bỏ khóa legacy đã được migration xử lý rõ ràng.

## Lộ trình áp dụng model

1. [Hoàn thành] Duy trì adapter hai chiều giữa `dict[str, str]` và model typed; chưa thay ngay định dạng lưu trữ.
2. [Hoàn thành] Bổ sung model theo nhóm dùng chung: người, địa chỉ, vốn, ngành nghề và thông tin ký.
3. [Hoàn thành] Thêm `from_form_values()` và `to_form_values(base=...)` theo từng workflow; `base` giữ các khóa chưa nhận diện.
4. [Hoàn thành] Viết migration theo version và test round-trip/migration dữ liệu cũ đại diện.
5. [Để sau] Chỉ chuyển toàn bộ UI sang model khi có tính năng mới cần dùng model; định dạng lưu trữ hiện tại tiếp tục tương thích.

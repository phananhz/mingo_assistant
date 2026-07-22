# Bộ mẫu hồ sơ thành lập doanh nghiệp

Thư mục này chứa bộ mẫu Word cho chức năng **Hồ sơ thành lập doanh nghiệp**.

Các vị trí cần tool tự động điền dữ liệu được đánh dấu bằng dấu ngoặc vuông `[]`.

## Danh sách file

| STT | File | Vai trò | Ghi chú |
| --- | --- | --- | --- |
| 0 | `0. Hướng dẫn ký.docx` | Hướng dẫn ký hồ sơ | Tài liệu hướng dẫn, có thể không cần điền dữ liệu |
| 1 | `1. Giấy đề nghị thành lập doanh nghiệp.docx` | Giấy đề nghị đăng ký doanh nghiệp | Mẫu chính của bộ hồ sơ |
| 2 | `2. Điều lệ Công ty.doc` | Điều lệ công ty | Đang là `.doc`, nên chuyển sang `.docx` trước khi tự động điền |
| 3 | `3. Danh sách chủ sở hữu hưởng lợi.docx` | Danh sách chủ sở hữu hưởng lợi | Mẫu danh sách thông tin chủ sở hữu hưởng lợi |
| 4 | `4. Giấy ủy quyền.doc` | Giấy ủy quyền | Đang là `.doc`, nên chuyển sang `.docx` trước khi tự động điền |

## Quy ước placeholder

Trong file Word, phần nào cần thay bằng dữ liệu thật thì đặt trong dấu `[]`.

Ví dụ:

```text
Họ và tên: [legal_representative_full_name]
Số CCCD: [legal_representative_id_number]
Tên công ty: [company_name]
Vốn điều lệ: [charter_capital_number]
```

Tool sẽ quét các nội dung nằm trong `[]` để biết vị trí nào cần điền.

## Cách đặt tên placeholder

Nên đặt tên placeholder bằng tiếng Anh không dấu, chữ thường, dùng gạch dưới `_`.

Ví dụ nên dùng:

```text
[company_name]
[company_short_name]
[company_address]
[company_phone]
[company_email]
[business_lines]

[charter_capital_number]
[charter_capital_text]

[legal_representative_full_name]
[legal_representative_id_number]
[legal_representative_date_of_birth]
[legal_representative_gender]
[legal_representative_nationality]
[legal_representative_permanent_address]
[legal_representative_position]

[member_full_name]
[member_id_number]
[member_date_of_birth]
[member_permanent_address]
[member_capital_amount]
[member_capital_ratio]

[document_place]
[document_day]
[document_month]
[document_year]
[document_place_date]
```

## Ví dụ chỉ để minh họa

Nếu cần ghi ví dụ trong tài liệu, chỉ dùng dữ liệu giả:

```text
[NGUYEN_VAN_A]
[012345678901]
[1.000.000.000_VND]
[Ha_Noi_ngay_01_thang_01_nam_2026]
```

Không dùng dữ liệu CCCD hoặc tên thật của khách hàng làm ví dụ trong tài liệu.

## Lưu ý kỹ thuật

- Không sửa mất định dạng Word khi thay placeholder.
- Không tách một placeholder thành nhiều đoạn định dạng khác nhau trong Word.
- Một dữ liệu dùng lại nhiều nơi phải dùng cùng một placeholder.
- Các file `.doc` nên chuyển sang `.docx` để xử lý bằng Python ổn định hơn.
- Không commit ảnh CCCD thật, hồ sơ thật hoặc dữ liệu khách hàng thật vào Git.

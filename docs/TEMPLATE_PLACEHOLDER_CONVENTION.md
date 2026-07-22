# Quy ước placeholder trong mẫu Word

Ứng dụng sẽ dùng placeholder để xác định các vị trí cần điền dữ liệu trong mẫu hồ sơ.

## Cú pháp được chấp nhận ở giai đoạn đầu

```text
[ten_bien]
```

Ví dụ:

```text
Họ và tên: [legal_representative_full_name]
Số CCCD: [legal_representative_id_number]
Tên công ty: [company_name]
Vốn điều lệ: [charter_capital_number]
```

## Quy tắc đặt tên biến

- Chỉ dùng chữ thường không dấu.
- Không dùng khoảng trắng.
- Dùng gạch dưới `_` để phân tách từ.
- Một dữ liệu dùng nhiều lần phải dùng cùng một tên biến.
- Không đặt tên biến bằng dữ liệu mẫu thật.

## Ví dụ nên dùng

```text
[company_name]
[company_foreign_name]
[company_short_name]
[company_type]
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

## Ví dụ chỉ dùng để minh họa

```text
[NGUYEN_VAN_A]
[1.000.000.000_VND]
[Ha_Noi_ngay_01_thang_01_nam_2026]
```

Những placeholder kiểu dữ liệu mẫu vẫn giúp tool phát hiện vùng cần thay, nhưng chưa cho biết chính xác trường dữ liệu nào cần điền. Khi chuẩn hóa mẫu chính thức, nên đổi sang dạng như `[legal_representative_full_name]`, `[charter_capital_number]`, `[document_place_date]`.

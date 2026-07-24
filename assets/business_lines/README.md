# Dữ liệu tra cứu ngành nghề kinh doanh

Chức năng tra cứu nạp dữ liệu từ file:

```text
assets/business_lines/vsic_2025.json
```

Dataset hiện tại được import từ file Word Quyết định 36/2025/QĐ-TTg:

```text
E:\36_2025_QD-TTg_675010.docx
```

Script import:

```text
scripts/import_business_lines_from_qd36_docx.py
```

Script kiểm tra số lượng trước khi ghi file:

```text
Cấp 1: 22
Cấp 2: 87
Cấp 3: 259
Cấp 4: 495
Cấp 5: 743
Tổng: 1606
```

File JSON giữ cấu trúc cây 5 cấp. Một số dòng trong bảng gốc có nhiều mã trên cùng hàng, ví dụ `619 | 6190 | 61900 | Hoạt động viễn thông khác`; script vẫn tạo đủ từng node mã ngành để tra cứu và hiển thị lại đúng dạng bảng gốc.

# Kiến trúc dự án

## Mục tiêu thiết kế

- Chạy offline trên Windows.
- Tách biệt giao diện, nghiệp vụ, lưu trữ dữ liệu, OCR và sinh tài liệu.
- Dễ thêm loại hồ sơ mới, mẫu Word mới và luồng kiểm tra dữ liệu mới.
- Không phụ thuộc vào một mẫu Word hoặc một loại giấy tờ cố định.
- Hạn chế rủi ro commit dữ liệu CCCD, database runtime và hồ sơ đã xuất.

## Các lớp chính

```text
UI
  -> Application Services
      -> Domain Models
      -> Repositories
      -> Infrastructure Services
```

## Module dự kiến

```text
src/mingo_assistant/app/                    Khởi động app, điều phối vòng đời ứng dụng
src/mingo_assistant/config/                 Cấu hình đường dẫn, app settings
src/mingo_assistant/core/                   Kiểu dùng chung, lỗi nghiệp vụ, hằng số
src/mingo_assistant/database/               Kết nối SQLite, migration, seed local
src/mingo_assistant/models/                 Entity/domain model
src/mingo_assistant/repositories/           Lớp truy cập dữ liệu
src/mingo_assistant/services/ocr/           OCR ảnh/PDF và trích xuất trường CCCD
src/mingo_assistant/services/normalization/ Chuẩn hóa tên, ngày tháng, tiền, địa chỉ
src/mingo_assistant/services/validation/    Kiểm tra lỗi/cảnh báo trước khi xuất hồ sơ
src/mingo_assistant/services/templates/     Quản lý mẫu Word và mapping biến
src/mingo_assistant/services/documents/     Sinh DOCX/PDF/ZIP từ dữ liệu và template
src/mingo_assistant/services/exporting/     Quy tắc đặt tên, thư mục xuất hồ sơ
src/mingo_assistant/services/security/      Mã hóa, khóa app, che thông tin nhạy cảm
src/mingo_assistant/services/backup/        Sao lưu và khôi phục dữ liệu local
src/mingo_assistant/ui/                     PySide6 windows, views, widgets, dialogs
src/mingo_assistant/workers/                Background tasks cho OCR và xuất hồ sơ
src/mingo_assistant/utils/                  Tiện ích kỹ thuật dùng chung
```

## Nguyên tắc mở rộng

- Thêm loại hồ sơ mới bằng metadata/template/mapping trước, chỉ thêm code khi có nghiệp vụ đặc biệt.
- OCR chỉ trả dữ liệu có cấu trúc và độ tin cậy, không tự ghi thẳng vào hồ sơ đã xác nhận.
- Sinh Word đi qua template service để giữ định dạng và hỗ trợ biến, bảng lặp, điều kiện.
- Dữ liệu cá nhân và file hồ sơ xuất ra nằm ngoài Git.

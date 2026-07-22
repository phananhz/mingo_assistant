# Bảo mật dữ liệu

Ứng dụng xử lý CCCD và thông tin cá nhân nên mặc định phải chạy theo hướng offline-first.

## Quy tắc repo

- Không commit ảnh CCCD thật.
- Không commit database runtime.
- Không commit hồ sơ Word/PDF/ZIP đã xuất.
- Không commit log chứa thông tin cá nhân.
- Chỉ commit dữ liệu mẫu đã được ẩn hoặc giả lập.

## Thư mục runtime

```text
data/app/      Database local và cấu hình người dùng
data/temp/     File tạm khi OCR hoặc tạo hồ sơ
exports/       Kết quả xuất hồ sơ
logs/          Log ứng dụng
```

Các thư mục này được giữ bằng `.gitkeep`, còn nội dung thật được ignore.

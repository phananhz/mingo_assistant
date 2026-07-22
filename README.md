# Mingo Assistant

Ứng dụng desktop Windows hỗ trợ tạo hồ sơ từ giấy tờ cá nhân: OCR ảnh/PDF, trích xuất dữ liệu có cấu trúc, kiểm tra dữ liệu, điền mẫu Word và xuất bộ hồ sơ.

Yêu cầu dự án đầy đủ nằm tại [YEU_CAU_PHAT_TRIEN_UNG_DUNG.md](YEU_CAU_PHAT_TRIEN_UNG_DUNG.md).

## Cấu trúc chính

```text
src/mingo_assistant/       Source ứng dụng
docs/                      Tài liệu phân tích, kiến trúc, hướng dẫn
assets/templates/word/     Mẫu Word .docx
assets/samples/            Dữ liệu mẫu dùng test OCR và tạo hồ sơ
data/                      Dữ liệu runtime local, không commit dữ liệu thật
exports/                   Kết quả xuất hồ sơ, không commit
tests/                     Unit test, integration test, fixtures
scripts/                   Script hỗ trợ dev/build/import
packaging/                 Cấu hình đóng gói Windows
```

Hiện tại mới dựng khung dự án, chưa có code nghiệp vụ.

## Chạy giao diện hiện tại

```powershell
$env:PYTHONPATH = "src"
python -m mingo_assistant
```

Nếu terminal chưa nhận `python`, dùng trực tiếp Python 3.12:

```powershell
$env:PYTHONPATH = "src"
& "C:\Users\duyle\AppData\Local\Programs\Python\Python312\python.exe" -m mingo_assistant
```

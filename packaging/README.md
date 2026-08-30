# Packaging

Cấu hình đóng gói Windows.

```text
pyinstaller/  Cấu hình build executable
inno_setup/   Cấu hình tạo bộ cài Windows
```

## Tạo bản phát hành

Máy build cần Python 3.12, các gói trong `requirements.txt`, PyInstaller và
Inno Setup 6. Chạy PowerShell tại thư mục gốc dự án:

```powershell
& .\packaging\build_windows.ps1
```

Script sẽ kiểm tra `PySide6` và `PyInstaller` bằng đúng Python đang dùng trước
khi build, tránh tạo ra file `.exe` thiếu thư viện giao diện.

Kết quả:

- `dist/MingoAssistant/`: thư mục ứng dụng đã đóng gói.
- `dist/installer/MingoAssistantSetup-1.0.0.exe`: bộ cài Windows nếu máy có `iscc.exe`.

Ứng dụng lưu database và cấu hình trong `%APPDATA%\Mingo Assistant`. Hồ sơ
Word/PDF/ZIP mặc định được lưu trong `Documents\Mingo Assistant`; lần chạy đầu
tiên người dùng có thể chọn thư mục khác.

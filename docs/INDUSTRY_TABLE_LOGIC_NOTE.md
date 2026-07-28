# Ghi chú logic bảng ngành nghề

Ngày lập: 2026-07-28

Mục đích: dùng làm checklist bắt buộc khi viết lại phần bảng ngành nghề trong file 1 và file 2.

## 1. Phạm vi

- File 1: `assets/templates/word/business_registration/1. Giấy đề nghị thành lập doanh nghiệp.docx`
- File 2: `assets/templates/word/business_registration/2. Điều lệ Công ty.docx`
- Code sinh DOCX: `src/mingo_assistant/services/documents/docx_generator.py`
- Code form nhập liệu: `src/mingo_assistant/ui/views/business_registration_workspace.py`
- Nguồn tra cứu: `assets/business_lines/vsic_2025.json`

## 2. Logic hiện tại được ghi nhận

1. Form có tối đa 10 dòng ngành nghề:
   - `business_line_N_name`
   - `business_line_N_code`
   - `business_line_N_is_main`
2. Khi chọn ngành từ catalog, form ghép `name` và `detail` thành một chuỗi nhiều dòng.
3. Khi sinh DOCX, generator tìm mọi bảng có header chứa `Tên ngành` và `Mã ngành`.
4. Generator đang xóa toàn bộ hàng body sau header, sau đó sao chép hàng body đầu tiên làm khuôn cho từng dòng mới.
5. Generator đang thay nội dung bằng `cell.text = ""` rồi tạo lại paragraph/run.
6. Generator đang chỉnh geometry dựa trên `tblGrid` hiện tại của template:
   - File 1: `763, 5167, 1536, 1887`, tổng `9353` DXA.
   - File 2: `1037, 5167, 1536, 1887`, tổng `9627` DXA.
7. Các hàng mới hiện được đặt căn:
   - STT: giữa
   - Tên ngành: trái
   - Mã ngành: giữa
   - Ngành chính: giữa
8. Header hiện được viết lại và đánh dấu lặp lại khi sang trang.

## 3. Nguyên nhân cần loại bỏ khi viết lại

- Không được sao chép nguyên hàng body đầu tiên vì hàng đó có thể mang theo `w:pPr`, indent, numbering, spacing, font và thuộc tính chiều cao không phù hợp.
- Không được dùng `cell.text = ""` như cơ chế chính nếu nó làm mất cấu trúc paragraph/format cần giữ; mỗi cell phải được dựng lại có chủ đích.
- Không được chỉ sửa `tcW`/`tblGrid` mà bỏ qua `tblW`, `tblLayout`, cell margin, paragraph indent và row height.
- Không được để paragraph cũ có `w:numPr`, `w:firstLine`, `w:left`, `w:right`, `w:jc=both` hoặc `w:spacing` ảnh hưởng sang nội dung mới.
- Không được đặt chiều cao cố định cho hàng body có nội dung dài.
- Line break trong cell phải là `w:br` nằm bên trong `w:r`; không được append `w:br` trực tiếp vào `w:p` vì tạo OOXML không hợp lệ và làm Word hiển thị sai.

## 4. Cấu trúc đích theo ảnh mẫu

Mỗi bảng phải có đúng 4 cột:

| Cột | Nội dung | Căn ngang | Quy tắc |
|---|---|---|---|
| 1 | STT | Giữa | số thứ tự 1..N |
| 2 | Tên ngành | Trái | tên ngành; `Chi tiết:` tiếp tục trong cùng cell |
| 3 | Mã ngành | Giữa | mã cấp 4/cấp tương ứng từ form |
| 4 | Ngành, nghề kinh doanh chính | Giữa | chỉ ghi `X` nếu dòng được chọn là ngành chính |

Geometry phải được lấy từ template gốc, giữ đúng tổng chiều rộng từng file. Mọi row body phải tự giãn theo nội dung và cho phép nội dung dài chia dòng/chia trang.

## 5. Logic viết lại bắt buộc

1. Đọc geometry gốc một lần từ bảng template.
2. Giữ nguyên header gốc về border, font, chiều cao và nội dung; chỉ sửa paragraph properties nếu cần để căn giữa đúng.
3. Xóa body rows nhưng tạo row mới từ XML tối giản, không clone paragraph formatting của hàng dữ liệu cũ.
4. Mỗi row mới phải có đúng 4 cell, `tcW` khớp `tblGrid`.
5. Mỗi cell body phải có một paragraph mới với:
   - không numbering;
   - không first-line indent;
   - left/right indent bằng 0;
   - space before/after bằng 0;
   - line spacing đơn;
   - cỡ chữ theo template body;
   - vertical alignment center.
6. Cell tên ngành phải tách phần `Chi tiết:` bằng line break trong cùng cell, không tạo bảng con hoặc paragraph thừa.
7. Không tạo row rỗng giả khi hồ sơ không có ngành; chỉ tạo một row trống nếu template nghiệp vụ bắt buộc phải có vùng nhập.
8. Header phải có `tblHeader` để lặp lại khi sang trang.
9. Mọi row body phải bỏ `trHeight` cố định và không có `cantSplit` bắt buộc.
10. Không thay đổi dữ liệu ngành đã nhập; chỉ sửa format và cách render.

## 6. Checklist kiểm tra trong lúc làm

- [ ] File 1 và file 2 đều tìm đúng bảng ngành nghề, không sửa nhầm bảng khác.
- [ ] Header có đủ `STT`, `Tên ngành`, `Mã ngành`, `Ngành, nghề kinh doanh chính`.
- [ ] STT không bị mất, trôi lên đầu trang hoặc nằm ngoài cell.
- [ ] Tên ngành không bị căn giữa/justify ngoài ý muốn.
- [ ] Mã ngành và `X` nằm giữa cột.
- [ ] Không còn paragraph numbering/indent cũ trong cell body.
- [ ] Nội dung dài tự xuống dòng như ảnh mẫu.
- [ ] Bảng nhiều hàng sang trang vẫn giữ border và header lặp lại.
- [ ] File 1 và file 2 có cùng thứ tự, tên, mã và trạng thái ngành chính.
- [ ] `validate_templates()` không báo placeholder.
- [ ] Sinh lại đủ 5 DOCX từ một hồ sơ thật.
- [ ] Kiểm tra XML geometry sau khi sinh.
- [ ] Render ảnh/PDF và kiểm tra từng trang nếu có `soffice`.
- [ ] Chạy `compileall` và toàn bộ unit test.

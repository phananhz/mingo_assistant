# Ranh giới hệ thống sinh DOCX

Tài liệu này ghi lại ranh giới hiện tại để việc tách `docx_generator.py` được thực hiện từng bước mà không thay đổi nội dung hay định dạng hồ sơ xuất ra.

## Thành phần dùng chung

- `generation_result.py`: kiểu dữ liệu mô tả tài liệu đã sinh và kết quả của một lần xuất.
- `docx_template_engine.py`: cơ chế DOCX trung lập theo workflow: đọc giá trị qua formatter/context, điền vùng vàng theo manifest và dựng bảng ngành nghề mà không chọn template hay quyết định nghiệp vụ hồ sơ.
- `template_repository.py`: tìm và cung cấp bộ mẫu Word theo workflow.
- `template_manifest.py`: khai báo các vùng và trường được phép điền trong mẫu.
- `context_builder.py`: tạo ngữ cảnh giá trị từ dữ liệu hồ sơ.
- `value_formatter.py`: chuẩn hóa giá trị hiển thị trong tài liệu.
- `package_editor.py`: thao tác an toàn với package/XML bên trong DOCX.

Các thành phần dùng chung không được chứa tên trường hoặc quy tắc chỉ thuộc một mẫu cụ thể.

Màu vàng không phải quy tắc toàn cục để quyết định vị trí nào được thay. Với từng
template, nguồn sự thật là mapping/manifest và quy tắc đã kiểm thử của generator
workflow. Một số biểu mẫu có vị trí hợp lệ không bôi vàng hoặc dùng shading thay
highlight; các ngoại lệ này phải được giữ tại generator đặc thù và có regression
test. Không được xóa mapping chỉ vì vị trí nguồn không có màu vàng.

## Generator theo workflow

- `business_amendment_generator.py`: generator độc lập cho thông báo thay đổi đăng ký doanh nghiệp, các vùng vàng đã rà soát và ngoại lệ fax/website không bôi vàng; không kế thừa pipeline thành lập doanh nghiệp.
- `dependent_unit_generator.py`: lập và thay đổi địa điểm kinh doanh; kế thừa trực tiếp engine dùng chung nhưng vẫn giữ riêng mapping, checkbox, người nước ngoài, thông báo thay đổi, người ký và hậu xử lý biểu mẫu.
- `location_termination_generator.py`: quy tắc hồ sơ chấm dứt địa điểm kinh doanh chuyên biệt.
- `business_registration_generator.py`: generator và các quy tắc của hồ sơ thành lập doanh nghiệp một thành viên; dùng engine chung nhưng không còn là lớp cha của workflow đơn vị phụ thuộc.
- `two_member_individual_generator.py`: quy tắc riêng của bộ hồ sơ công ty hai thành viên chỉ có thành viên cá nhân.
- `docx_generator.py`: facade tương thích cho các đường import cũ; không chứa implementation xử lý Word.

## Quy tắc phụ thuộc

1. Generator workflow có thể dùng helper lõi, repository, manifest, formatter và package editor.
2. Helper lõi không được import ngược UI hoặc generator workflow.
3. UI chỉ chọn generator và truyền dữ liệu; UI không xử lý XML/DOCX.
4. Trong giai đoạn chuyển đổi, các import công khai cũ phải tiếp tục hoạt động hoặc được đổi đồng thời cùng test hồi quy.
5. Không thay template hoặc SHA-256 chỉ để phục vụ refactor code.
6. Import cũ của `TwoMemberIndividualFile1DocxTemplateGenerator` được giữ bằng facade/lazy compatibility trong thời gian chuyển đổi.
7. `DependentUnitTemplateGenerator` không được kế thừa hoặc import `DocxTemplateGenerator`; hai workflow chỉ chia sẻ `DocxTemplateEngine` và các helper trung lập.
8. Vị trí không bôi vàng nhưng đã có mapping đặc thù không được tự động coi là
   protected. Muốn bỏ hoặc đổi mapping phải có yêu cầu nghiệp vụ cụ thể và test
   chứng minh từng tài liệu của bộ hồ sơ vẫn đúng.

## Bằng chứng bắt buộc khi di chuyển quy tắc

- Test generator của workflow bị tác động.
- Test xác nhận vùng được phép điền và vùng protected không đổi.
- Kiểm tra placeholder chưa xử lý trong file kết quả.
- Render DOCX đại diện và so sánh trực quan nếu thay đổi đường xử lý nội dung hoặc định dạng.

# YÊU CẦU PHÁT TRIỂN ỨNG DỤNG TỰ ĐỘNG TẠO HỒ SƠ TỪ GIẤY TỜ CÁ NHÂN

## 1. Tổng quan dự án

**Tên tạm thời:** Hồ Sơ Tự Động

**Loại ứng dụng:** Phần mềm desktop chạy trên Windows.

**Mục đích:** Hỗ trợ người dùng tạo nhanh các bộ hồ sơ hành chính, pháp lý và hồ sơ doanh nghiệp bằng cách:

1. Nhập ảnh hoặc file PDF chứa giấy tờ cá nhân.
2. Nhận diện và trích xuất dữ liệu từ giấy tờ.
3. Cho phép người dùng kiểm tra, chỉnh sửa dữ liệu.
4. Nhập thêm các thông tin riêng của từng hồ sơ.
5. Tự động điền dữ liệu vào mẫu Word có sẵn.
6. Xuất ra một hoặc nhiều file Word hoàn chỉnh.

Ví dụ:

```text
Ảnh CCCD
→ Nhận diện họ tên, ngày sinh, số CCCD, địa chỉ
→ Nhập tên công ty, vốn điều lệ, ngành nghề
→ Chọn mẫu hồ sơ thành lập doanh nghiệp
→ Tự động điền toàn bộ dữ liệu
→ Xuất bộ hồ sơ Word
```

Ứng dụng không chỉ là công cụ OCR mà là một hệ thống **tự động hóa việc lập hồ sơ theo mẫu**.

---

# 2. Đối tượng sử dụng

Ứng dụng hướng đến:

* Cá nhân làm dịch vụ thành lập doanh nghiệp.
* Nhân viên pháp lý.
* Văn phòng luật.
* Đơn vị tư vấn doanh nghiệp.
* Kế toán.
* Nhân viên hành chính.
* Cá nhân thường xuyên làm hồ sơ theo mẫu.

---

# 3. Phạm vi hồ sơ

Ứng dụng cần được thiết kế để có thể hỗ trợ nhiều loại hồ sơ khác nhau.

Trong giai đoạn đầu, ưu tiên:

## 3.1. Hồ sơ thành lập doanh nghiệp

Có thể bao gồm:

* Giấy đề nghị đăng ký doanh nghiệp.
* Điều lệ công ty.
* Danh sách thành viên.
* Danh sách cổ đông sáng lập.
* Danh sách người đại diện theo ủy quyền.
* Quyết định thành lập.
* Biên bản họp.
* Giấy ủy quyền.
* Tờ khai thông tin người nộp hồ sơ.
* Các văn bản nội bộ có liên quan.

## 3.2. Các hồ sơ khác có thể bổ sung

* Hồ sơ thay đổi nội dung đăng ký doanh nghiệp.
* Hồ sơ thay đổi người đại diện theo pháp luật.
* Hồ sơ thay đổi địa chỉ trụ sở.
* Hồ sơ thay đổi vốn điều lệ.
* Hồ sơ chuyển nhượng vốn.
* Hồ sơ bổ sung ngành nghề kinh doanh.
* Hồ sơ tạm ngừng kinh doanh.
* Hồ sơ giải thể doanh nghiệp.
* Hồ sơ đăng ký hộ kinh doanh.
* Hợp đồng và phụ lục hợp đồng theo mẫu.
* Giấy ủy quyền.
* Biên bản họp.
* Quyết định nội bộ.
* Hồ sơ lao động.
* Hồ sơ nhân sự.
* Các loại biểu mẫu hành chính khác.

Hệ thống phải được thiết kế theo hướng có thể thêm mẫu hồ sơ mới mà không phải viết lại toàn bộ chương trình.

---

# 4. Quy trình sử dụng chính

## Bước 1. Tạo hồ sơ mới

Người dùng chọn:

* Loại hồ sơ.
* Loại hình doanh nghiệp.
* Tên hồ sơ.
* Ngày lập hồ sơ.

Ví dụ:

```text
Loại hồ sơ: Thành lập doanh nghiệp
Loại hình: Công ty TNHH hai thành viên trở lên
Tên hồ sơ: Thành lập Công ty TNHH ABC
```

## Bước 2. Thêm cá nhân hoặc tổ chức

Người dùng có thể thêm:

* Chủ sở hữu.
* Thành viên góp vốn.
* Cổ đông.
* Người đại diện theo pháp luật.
* Người đại diện theo ủy quyền.
* Người được ủy quyền nộp hồ sơ.
* Người liên hệ.
* Tổ chức góp vốn.

## Bước 3. Tải giấy tờ lên

Người dùng tải lên:

* Ảnh mặt trước CCCD.
* Ảnh mặt sau CCCD.
* File scan CCCD.
* File PDF chứa giấy tờ.
* Ảnh hộ chiếu.
* Ảnh giấy tờ khác.

## Bước 4. Nhận diện và trích xuất dữ liệu

Ứng dụng tự động nhận diện:

* Họ và tên.
* Ngày sinh.
* Giới tính.
* Số CCCD.
* Ngày cấp.
* Ngày hết hạn.
* Quê quán.
* Nơi thường trú.
* Quốc tịch.
* Đặc điểm nhận dạng nếu cần.
* Các thông tin khác có trên giấy tờ.

## Bước 5. Kiểm tra dữ liệu

Ứng dụng hiển thị ảnh giấy tờ bên cạnh thông tin đã nhận diện.

Người dùng phải có thể:

* So sánh dữ liệu với ảnh gốc.
* Chỉnh sửa dữ liệu.
* Xác nhận dữ liệu chính xác.
* Đánh dấu trường chưa xác định được.
* Nhập tay trường bị thiếu.

## Bước 6. Nhập thông tin hồ sơ

Người dùng nhập thêm các dữ liệu không có trên CCCD, ví dụ:

* Tên doanh nghiệp.
* Tên viết tắt.
* Tên tiếng nước ngoài.
* Địa chỉ trụ sở.
* Số điện thoại.
* Email.
* Vốn điều lệ.
* Tỷ lệ góp vốn.
* Giá trị phần vốn góp.
* Ngành nghề kinh doanh.
* Chức danh người đại diện.
* Số lượng người đại diện theo pháp luật.
* Thời hạn góp vốn.
* Thông tin thuế.
* Người nộp hồ sơ.
* Nội dung ủy quyền.
* Ngày ký hồ sơ.

## Bước 7. Kiểm tra hồ sơ

Ứng dụng kiểm tra:

* Trường bắt buộc bị thiếu.
* Số CCCD không đúng độ dài.
* Ngày tháng không hợp lệ.
* Tỷ lệ góp vốn không đủ 100%.
* Tổng vốn góp không bằng vốn điều lệ.
* Thành viên chưa có địa chỉ.
* Người đại diện chưa có chức danh.
* Tên công ty bị bỏ trống.
* Địa chỉ chưa đầy đủ.
* Mẫu hồ sơ yêu cầu dữ liệu nhưng chưa được nhập.

## Bước 8. Tạo hồ sơ

Người dùng chọn bộ mẫu cần tạo.

Ứng dụng tự động:

* Điền dữ liệu vào file Word.
* Tạo nhiều văn bản từ cùng một bộ dữ liệu.
* Giữ nguyên định dạng mẫu.
* Thay thế các trường dữ liệu tương ứng.
* Tạo bảng thành viên hoặc cổ đông.
* Tính toán tỷ lệ và giá trị vốn góp.
* Chèn ngày tháng.
* Chèn thông tin người ký.
* Đặt tên file theo quy tắc.

## Bước 9. Xuất kết quả

Ứng dụng xuất:

* Từng file Word riêng lẻ.
* Toàn bộ bộ hồ sơ vào một thư mục.
* File Word tổng hợp nếu có mẫu.
* File ZIP chứa toàn bộ hồ sơ.
* File PDF nếu người dùng chọn.

---

# 5. Chức năng nhận diện giấy tờ

## 5.1. Loại giấy tờ hỗ trợ

Giai đoạn đầu cần hỗ trợ:

* Căn cước công dân gắn chip.
* Căn cước công dân mã vạch.
* Chứng minh nhân dân.
* Hộ chiếu.
* Giấy tờ được scan dưới dạng PDF.

## 5.2. Dữ liệu cần trích xuất từ CCCD

Ứng dụng cần cố gắng nhận diện:

```text
Họ và tên
Số CCCD
Ngày sinh
Giới tính
Quốc tịch
Quê quán
Nơi thường trú
Ngày cấp
Ngày hết hạn
```

Tùy loại giấy tờ, một số trường có thể không tồn tại.

## 5.3. Nguyên tắc xử lý

* Không chỉ OCR toàn bộ chữ trên ảnh.
* Phải xác định đúng trường dữ liệu.
* Phân biệt họ tên, số CCCD, ngày sinh và địa chỉ.
* Lưu kết quả dưới dạng dữ liệu có cấu trúc.
* Hiển thị mức độ tin cậy nếu có.
* Yêu cầu người dùng xác nhận trước khi dùng để tạo hồ sơ.

Ví dụ dữ liệu:

```json
{
  "full_name": "NGUYỄN VĂN A",
  "id_number": "001200012345",
  "date_of_birth": "01/01/1990",
  "gender": "Nam",
  "nationality": "Việt Nam",
  "place_of_origin": "Hà Nội",
  "permanent_address": "Phường A, Quận B, Thành phố Hà Nội",
  "issue_date": "01/01/2022",
  "expiry_date": "01/01/2040"
}
```

---

# 6. Quản lý dữ liệu cá nhân

Mỗi người cần được lưu thành một hồ sơ dữ liệu riêng.

## 6.1. Thông tin cá nhân

Bao gồm:

* Mã cá nhân.
* Họ và tên.
* Ngày sinh.
* Giới tính.
* Quốc tịch.
* Số CCCD.
* Ngày cấp.
* Ngày hết hạn.
* Cơ quan cấp.
* Quê quán.
* Địa chỉ thường trú.
* Địa chỉ liên lạc.
* Số điện thoại.
* Email.
* Chức danh.
* Chữ ký mẫu nếu có.
* Ảnh giấy tờ.

## 6.2. Chức năng quản lý

Người dùng có thể:

* Thêm cá nhân mới.
* Sửa thông tin.
* Tìm kiếm theo tên.
* Tìm kiếm theo số CCCD.
* Dùng lại thông tin trong hồ sơ khác.
* Sao chép thông tin.
* Xóa thông tin.
* Đính kèm lại ảnh giấy tờ.
* Xem các hồ sơ đã dùng người này.

Không cần OCR lại CCCD nếu người đó đã có trong hệ thống và thông tin vẫn còn hiệu lực.

---

# 7. Quản lý thông tin doanh nghiệp

Ứng dụng cần có khu vực nhập và lưu thông tin doanh nghiệp.

## 7.1. Thông tin cơ bản

* Tên tiếng Việt.
* Tên tiếng nước ngoài.
* Tên viết tắt.
* Loại hình doanh nghiệp.
* Địa chỉ trụ sở.
* Số điện thoại.
* Email.
* Website.
* Vốn điều lệ.
* Mệnh giá cổ phần.
* Tổng số cổ phần.
* Ngành nghề kinh doanh.
* Người đại diện theo pháp luật.
* Chức danh người đại diện.
* Thông tin người liên hệ.
* Phương pháp tính thuế nếu cần.

## 7.2. Thành viên hoặc cổ đông

Mỗi thành viên gồm:

* Cá nhân hoặc tổ chức.
* Họ tên hoặc tên tổ chức.
* Số giấy tờ.
* Địa chỉ.
* Giá trị vốn góp.
* Tỷ lệ góp vốn.
* Loại tài sản góp vốn.
* Thời điểm góp vốn.
* Chức danh nếu có.

## 7.3. Tính toán tự động

Ứng dụng cần tự động tính:

```text
Tỷ lệ góp vốn = Giá trị vốn góp / Vốn điều lệ × 100%
```

Đồng thời kiểm tra:

* Tổng tỷ lệ bằng 100%.
* Tổng giá trị vốn góp bằng vốn điều lệ.
* Số cổ phần nhân với mệnh giá bằng vốn điều lệ.
* Dữ liệu giữa các thành viên không mâu thuẫn.

---

# 8. Hệ thống mẫu Word

Đây là thành phần quan trọng nhất của ứng dụng.

## 8.1. Mẫu Word

Mỗi mẫu là một file `.docx` được thiết kế sẵn.

Trong mẫu sẽ có các biến, ví dụ:

```text
{{company_name}}
{{company_address}}
{{charter_capital}}
{{legal_representative_name}}
{{legal_representative_id}}
{{legal_representative_address}}
{{document_date}}
```

Ứng dụng thay các biến này bằng dữ liệu thực tế.

## 8.2. Trường lặp

Mẫu phải hỗ trợ danh sách nhiều người, ví dụ:

```text
Danh sách thành viên
Danh sách cổ đông
Danh sách người đại diện theo ủy quyền
```

Hệ thống phải có khả năng tạo bảng nhiều dòng trong Word.

Ví dụ:

| STT | Họ tên       | Số CCCD |     Vốn góp | Tỷ lệ |
| --: | ------------ | ------- | ----------: | ----: |
|   1 | Nguyễn Văn A | 001…    | 600.000.000 |   60% |
|   2 | Trần Văn B   | 002…    | 400.000.000 |   40% |

## 8.3. Điều kiện hiển thị

Mẫu cần hỗ trợ điều kiện, ví dụ:

* Chỉ hiển thị nội dung nếu có người đại diện thứ hai.
* Chỉ hiển thị phần cổ đông nếu là công ty cổ phần.
* Chỉ hiển thị thành viên tổ chức nếu có tổ chức góp vốn.
* Hiển thị “Ông” hoặc “Bà” theo giới tính.
* Hiển thị “Chủ tịch Hội đồng thành viên” theo chức danh đã chọn.

## 8.4. Định dạng phải được giữ nguyên

Ứng dụng phải giữ:

* Font chữ.
* Cỡ chữ.
* Căn lề.
* Khoảng cách dòng.
* Header và footer.
* Số trang.
* Bảng.
* Viền bảng.
* In đậm và in nghiêng.
* Ký hiệu.
* Ngắt trang.
* Định dạng ngày tháng.
* Định dạng tiền bằng số và bằng chữ nếu có.

## 8.5. Thêm mẫu mới

Quản trị viên hoặc người dùng có quyền cần có thể:

* Thêm mẫu Word.
* Đặt tên mẫu.
* Chọn loại hồ sơ.
* Khai báo các biến có trong mẫu.
* Chọn dữ liệu tương ứng với từng biến.
* Cập nhật mẫu.
* Sao chép mẫu.
* Ngừng sử dụng mẫu.
* Xóa mẫu.

Việc thêm mẫu mới nên hạn chế tối đa yêu cầu sửa code.

---

# 9. Bộ dữ liệu dùng chung

Một bộ dữ liệu có thể dùng để tạo nhiều văn bản.

Ví dụ, khi lập hồ sơ thành lập công ty TNHH, các thông tin sau chỉ cần nhập một lần:

```text
Tên công ty
Địa chỉ
Vốn điều lệ
Ngành nghề
Thông tin thành viên
Thông tin người đại diện
Ngày ký
Người nộp hồ sơ
```

Sau đó ứng dụng tự động dùng để tạo:

```text
Giấy đề nghị đăng ký doanh nghiệp
Điều lệ công ty
Danh sách thành viên
Quyết định thành lập
Biên bản họp
Giấy ủy quyền
```

Người dùng không phải nhập lại dữ liệu cho từng file.

---

# 10. Các loại trường dữ liệu

Hệ thống cần hỗ trợ:

* Văn bản ngắn.
* Văn bản dài.
* Số.
* Số tiền.
* Phần trăm.
* Ngày tháng.
* Địa chỉ.
* Danh sách lựa chọn.
* Có hoặc không.
* Một cá nhân.
* Nhiều cá nhân.
* Một tổ chức.
* Nhiều tổ chức.
* Danh sách ngành nghề.
* Danh sách thành viên.
* Danh sách cổ đông.
* Tệp đính kèm.
* Hình ảnh.
* Chữ ký.

---

# 11. Chuẩn hóa dữ liệu

Ứng dụng cần chuẩn hóa dữ liệu trước khi điền vào hồ sơ.

## 11.1. Họ tên

Có thể lựa chọn:

```text
NGUYỄN VĂN A
Nguyễn Văn A
```

## 11.2. Ngày tháng

Hỗ trợ các dạng:

```text
01/01/1990
Ngày 01 tháng 01 năm 1990
01-01-1990
```

## 11.3. Số tiền

Ví dụ:

```text
1.000.000.000 đồng
Một tỷ đồng
```

## 11.4. Địa chỉ

Ứng dụng cần tránh:

* Khoảng trắng thừa.
* Lặp dấu phẩy.
* Thiếu dấu câu.
* Xuống dòng không cần thiết.

## 11.5. Giới tính và đại từ

Tự động xác định:

```text
Nam → Ông
Nữ → Bà
```

Người dùng vẫn có thể chỉnh sửa thủ công.

---

# 12. Kiểm tra và cảnh báo dữ liệu

Trước khi tạo hồ sơ, ứng dụng phải hiển thị danh sách lỗi và cảnh báo.

## 12.1. Lỗi bắt buộc sửa

Ví dụ:

* Chưa nhập tên công ty.
* Chưa có người đại diện.
* Số CCCD bị thiếu.
* Vốn điều lệ bằng 0.
* Tổng tỷ lệ góp vốn không bằng 100%.
* Ngày sinh không hợp lệ.
* Chưa chọn loại hình doanh nghiệp.
* Mẫu yêu cầu trường dữ liệu chưa được nhập.

## 12.2. Cảnh báo

Ví dụ:

* CCCD sắp hết hạn.
* Địa chỉ quá ngắn.
* OCR có độ tin cậy thấp.
* Tên công ty có ký tự đặc biệt.
* Một cá nhân được nhập hai lần.
* Tỷ lệ vốn góp có số lẻ.
* Chưa có email hoặc số điện thoại.

Người dùng có thể tiếp tục xuất hồ sơ khi chỉ còn cảnh báo, nhưng không được xuất khi còn lỗi nghiêm trọng.

---

# 13. Giao diện ứng dụng

Giao diện nên chia thành các khu vực:

## 13.1. Trang quản lý hồ sơ

Hiển thị:

* Danh sách hồ sơ.
* Loại hồ sơ.
* Tên doanh nghiệp.
* Người phụ trách.
* Ngày tạo.
* Trạng thái.
* Ngày cập nhật.
* Thư mục kết quả.

Trạng thái gồm:

```text
Bản nháp
Thiếu thông tin
Sẵn sàng tạo
Đã tạo hồ sơ
Đã hoàn thành
```

## 13.2. Trang nhập thông tin

Chia theo nhóm:

```text
Thông tin doanh nghiệp
Người đại diện
Thành viên/cổ đông
Ngành nghề
Vốn
Địa chỉ
Người nộp hồ sơ
Thông tin khác
```

## 13.3. Trang giấy tờ cá nhân

Bố cục:

```text
Bên trái: Ảnh CCCD
Bên phải: Các trường dữ liệu đã nhận diện
```

Các trường nhận diện chưa chắc chắn cần được đánh dấu.

## 13.4. Trang chọn mẫu

Hiển thị:

* Tên văn bản.
* Mô tả.
* Phiên bản mẫu.
* Loại hình doanh nghiệp.
* Ngày cập nhật.
* Nút xem trước.
* Ô chọn tạo hoặc không tạo.

## 13.5. Trang xem trước

Người dùng có thể:

* Xem nội dung trước khi xuất.
* Kiểm tra dữ liệu đã điền.
* Quay lại chỉnh sửa.
* Chọn thư mục xuất.
* Tạo lại hồ sơ.

---

# 14. Quản lý hồ sơ

Người dùng cần có thể:

* Tạo hồ sơ mới.
* Sao chép hồ sơ.
* Sửa hồ sơ.
* Đổi tên hồ sơ.
* Xóa hồ sơ.
* Lưu bản nháp.
* Tìm kiếm hồ sơ.
* Lọc theo loại hồ sơ.
* Lọc theo ngày.
* Lọc theo trạng thái.
* Mở thư mục kết quả.
* Xuất lại hồ sơ.
* Tạo phiên bản mới từ hồ sơ cũ.

Ví dụ:

```text
Thay đổi tên công ty hoặc địa chỉ
→ Cập nhật dữ liệu
→ Xuất lại toàn bộ bộ hồ sơ
```

---

# 15. Quản lý mẫu hồ sơ

Hệ thống cần quản lý:

* Tên mẫu.
* Loại hồ sơ.
* Loại hình doanh nghiệp áp dụng.
* Phiên bản mẫu.
* Ngày áp dụng.
* Ngày ngừng áp dụng.
* File Word gốc.
* Danh sách trường dữ liệu.
* Trạng thái sử dụng.

Không được ghi đè mất mẫu cũ khi cập nhật mẫu mới.

Nên lưu phiên bản:

```text
Mẫu Điều lệ – Phiên bản 1
Mẫu Điều lệ – Phiên bản 2
```

Các hồ sơ cũ vẫn phải biết đã sử dụng phiên bản nào.

---

# 16. Xuất bộ hồ sơ

## 16.1. Cấu trúc thư mục

Ví dụ:

```text
Ho_so_Cong_ty_TNHH_ABC/
│
├── 01_Giay_de_nghi_dang_ky_doanh_nghiep.docx
├── 02_Dieu_le_cong_ty.docx
├── 03_Danh_sach_thanh_vien.docx
├── 04_Bien_ban_hop.docx
├── 05_Quyet_dinh.docx
├── 06_Giay_uy_quyen.docx
└── Giay_to_ca_nhan/
    ├── CCCD_Nguyen_Van_A.jpg
    └── CCCD_Tran_Van_B.jpg
```

## 16.2. Quy tắc đặt tên

Tên file cần:

* Không có ký tự lỗi trên Windows.
* Có số thứ tự.
* Có tên loại văn bản.
* Có thể chứa tên doanh nghiệp.
* Không bị trùng tên.

## 16.3. Định dạng đầu ra

Bắt buộc:

* DOCX.
* Thư mục chứa bộ hồ sơ.

Có thể bổ sung:

* PDF.
* ZIP.
* JSON dữ liệu hồ sơ.
* Excel danh sách thành viên hoặc cổ đông.

---

# 17. Bảo mật dữ liệu

Do ứng dụng xử lý CCCD và thông tin cá nhân, yêu cầu bảo mật là bắt buộc.

## 17.1. Xử lý offline

Phiên bản đầu tiên ưu tiên:

* Chạy hoàn toàn trên máy tính.
* Không tự động tải ảnh lên server.
* Không gửi dữ liệu cho dịch vụ bên thứ ba.
* Không bắt buộc đăng nhập Internet.

## 17.2. Lưu trữ

Cần có tùy chọn:

* Lưu ảnh CCCD.
* Không lưu ảnh CCCD sau khi nhận diện.
* Xóa ảnh gốc sau khi hoàn thành.
* Xóa toàn bộ dữ liệu hồ sơ.
* Chọn thư mục lưu dữ liệu.
* Sao lưu dữ liệu.
* Khôi phục dữ liệu.

## 17.3. Bảo vệ dữ liệu

Nên có:

* Mật khẩu mở ứng dụng.
* Khóa ứng dụng khi không sử dụng.
* Mã hóa cơ sở dữ liệu hoặc dữ liệu nhạy cảm.
* Phân quyền người dùng nếu sử dụng trong tổ chức.
* Ghi nhận lịch sử thay đổi dữ liệu.
* Không hiển thị đầy đủ số CCCD ở màn hình danh sách.

Ví dụ:

```text
001200****** 
```

## 17.4. Nhật ký sử dụng

Nếu có nhiều người dùng, cần ghi nhận:

* Người tạo hồ sơ.
* Người sửa hồ sơ.
* Thời gian sửa.
* Nội dung đã thay đổi.
* Người xuất hồ sơ.
* Mẫu đã sử dụng.

---

# 18. Hiệu năng

Ứng dụng cần:

* Không bị treo khi OCR.
* Không bị treo khi tạo nhiều file Word.
* Xử lý OCR bằng tác vụ riêng.
* Có thanh tiến trình.
* Có thông báo lỗi rõ ràng.
* Cho phép hủy nhận diện.
* Không mất dữ liệu khi ứng dụng đóng đột ngột.
* Tự động lưu bản nháp.
* Tạo bộ hồ sơ trong thời gian hợp lý.

---

# 19. Công nghệ đề xuất

Có thể sử dụng:

```text
Ngôn ngữ: Python
Giao diện: PySide6
OCR: PaddleOCR
Xử lý ảnh: OpenCV
Đọc PDF: PyMuPDF
Tạo Word: python-docx hoặc docxtpl
Template Engine: Jinja2/docxtpl
Lưu dữ liệu: SQLite
Đóng gói Windows: PyInstaller
Tạo bộ cài: Inno Setup
```

Đối với chức năng điền dữ liệu vào Word, nên ưu tiên `docxtpl` vì hỗ trợ:

* Biến trong Word.
* Danh sách lặp.
* Điều kiện.
* Bảng nhiều dòng.
* Giữ định dạng mẫu.

Lập trình viên có thể đề xuất công nghệ khác nếu vẫn bảo đảm:

* Chạy ổn định trên Windows.
* Xử lý offline.
* Giữ đúng định dạng Word.
* Có thể thêm mẫu mới.
* Source code dễ bảo trì.

---

# 20. Cấu trúc hệ thống đề xuất

```text
Giao diện Windows
        ↓
Quản lý hồ sơ
        ↓
Quản lý cá nhân và doanh nghiệp
        ↓
OCR giấy tờ
        ↓
Chuẩn hóa và xác thực dữ liệu
        ↓
Template Mapping
        ↓
Word Template Engine
        ↓
Xuất bộ hồ sơ
```

Các module chính:

```text
OCR Service
Person Management
Company Management
Case Management
Template Management
Data Validation
Document Generator
File Export
Security
Backup and Restore
```

---

# 21. Phạm vi bản MVP

Phiên bản đầu tiên nên tập trung vào một loại hồ sơ cụ thể.

## Đề xuất MVP

**Hồ sơ thành lập công ty TNHH hai thành viên trở lên.**

Chức năng gồm:

1. Tạo hồ sơ mới.
2. Tải ảnh CCCD của các thành viên.
3. OCR và trích xuất thông tin.
4. Cho phép chỉnh sửa dữ liệu.
5. Nhập thông tin doanh nghiệp.
6. Nhập vốn góp và tỷ lệ.
7. Kiểm tra tổng vốn và tỷ lệ.
8. Chọn bộ mẫu Word.
9. Tạo các file Word.
10. Xuất toàn bộ vào một thư mục.
11. Lưu lại hồ sơ để sử dụng hoặc chỉnh sửa sau.

Bộ văn bản MVP có thể gồm:

```text
Giấy đề nghị đăng ký doanh nghiệp
Điều lệ công ty
Danh sách thành viên
Biên bản họp
Quyết định
Giấy ủy quyền
```

---

# 22. Chức năng chưa bắt buộc trong MVP

* Chữ ký số.
* Nộp hồ sơ trực tuyến.
* Tích hợp Cổng thông tin quốc gia.
* Tích hợp dịch vụ công.
* Tự động kiểm tra tên doanh nghiệp.
* Tra cứu ngành nghề trực tuyến.
* OCR chữ viết tay.
* Ứng dụng mobile.
* Đồng bộ cloud.
* Thanh toán.
* Quản lý khách hàng nâng cao.
* Quản lý công việc.
* AI tư vấn pháp lý.
* Tự động cập nhật biểu mẫu pháp luật.
* Nhiều người dùng cùng làm trên một hồ sơ.

---

# 23. Tiêu chí nghiệm thu MVP

Ứng dụng được xem là đạt yêu cầu khi:

1. Cài đặt được trên Windows 10 và Windows 11.
2. Người dùng không cần tự cài Python.
3. Tải được ảnh CCCD.
4. Nhận diện được các trường chính trên CCCD.
5. Cho phép sửa dữ liệu OCR.
6. Lưu được thông tin nhiều thành viên.
7. Nhập được thông tin doanh nghiệp.
8. Tự tính được tỷ lệ vốn góp.
9. Cảnh báo khi tổng tỷ lệ không bằng 100%.
10. Điền đúng dữ liệu vào mẫu Word.
11. Giữ được định dạng của file Word mẫu.
12. Tạo được nhiều file Word từ một bộ dữ liệu.
13. Xuất được bộ hồ sơ vào một thư mục.
14. Có thể mở lại và chỉnh sửa hồ sơ.
15. Dữ liệu được lưu trên máy.
16. Không tự động gửi CCCD lên Internet.
17. Không bị treo khi OCR hoặc tạo hồ sơ.
18. Source code được bàn giao đầy đủ.
19. Có hướng dẫn thêm và cập nhật mẫu Word.
20. Có tài liệu hướng dẫn build lại ứng dụng.

---

# 24. Sản phẩm cần bàn giao

Đơn vị phát triển cần bàn giao:

1. Source code đầy đủ.
2. Repository Git.
3. File cài đặt Windows.
4. File chương trình đã build.
5. Database và mô tả cấu trúc dữ liệu.
6. Bộ mẫu Word ban đầu.
7. Hướng dẫn sử dụng.
8. Hướng dẫn thêm mẫu Word.
9. Hướng dẫn khai báo biến trong mẫu.
10. Hướng dẫn sửa mẫu.
11. Hướng dẫn build lại ứng dụng.
12. Danh sách thư viện và phiên bản.
13. Tài liệu mô tả các chức năng.
14. Danh sách lỗi và giới hạn hiện tại.
15. Chính sách bảo hành và sửa lỗi.
16. Cam kết bàn giao quyền sở hữu source code.
17. Cam kết không giữ lại dữ liệu hồ sơ và giấy tờ của khách hàng.

---

# 25. Dữ liệu mẫu cần cung cấp cho bên phát triển

Để lập trình viên triển khai và kiểm thử, cần chuẩn bị:

* Từ 10 đến 20 ảnh CCCD mẫu.
* Ảnh rõ và ảnh hơi nghiêng.
* CCCD cũ và CCCD mới nếu cần hỗ trợ.
* Các mẫu Word đang sử dụng.
* Một bộ hồ sơ hoàn chỉnh đã làm thủ công.
* Danh sách trường dữ liệu trong từng biểu mẫu.
* Quy tắc viết hoa họ tên.
* Quy tắc viết ngày tháng.
* Quy tắc viết số tiền bằng chữ.
* Quy tắc đặt tên file.
* Quy tắc tạo thư mục hồ sơ.
* Các trường bắt buộc.
* Các trường có thể để trống.
* Các điều kiện riêng theo từng loại hình doanh nghiệp.

---

# 26. Mô tả ngắn gọn cho đơn vị phát triển

Cần xây dựng một ứng dụng Windows giúp tự động tạo hồ sơ doanh nghiệp. Người dùng tải ảnh CCCD của khách hàng lên, hệ thống dùng OCR để lấy thông tin cá nhân và lưu thành dữ liệu có cấu trúc. Người dùng kiểm tra, chỉnh sửa, sau đó nhập thêm tên công ty, địa chỉ, vốn, ngành nghề và các thông tin liên quan.

Từ một bộ dữ liệu duy nhất, ứng dụng tự động điền vào nhiều mẫu Word như giấy đề nghị đăng ký doanh nghiệp, điều lệ, danh sách thành viên, biên bản họp, quyết định và giấy ủy quyền. Ứng dụng phải giữ nguyên định dạng Word, cho phép cập nhật mẫu, xuất toàn bộ bộ hồ sơ và lưu lại hồ sơ để chỉnh sửa hoặc sử dụng lại.

Phiên bản đầu ưu tiên chạy offline, bảo mật thông tin CCCD và không tự động gửi dữ liệu lên Internet.

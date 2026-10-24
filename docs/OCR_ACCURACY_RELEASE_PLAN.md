# Kế hoạch tăng độ chính xác scan trước release

- Ngày lập: 20/10/2026.
- Mã nguồn nền: `aa06e81` — `feat: improve certificate OCR accuracy and scan performance`.
- Trạng thái: đã lập kế hoạch; các công việc triển khai bên dưới chưa thực hiện.
- Phạm vi chính: nhận diện ERC/BRC; kiểm thử hồi quy CCCD và luồng lưu/chọn profile.

## 1. Mục tiêu và giới hạn

Tăng khả năng phát hiện chữ thiếu, mất dấu và địa chỉ sai; đọc lại đúng vùng cần thiết,
đồng thời giữ đường đọc nhanh cho tài liệu rõ. Mục tiêu quan trọng là giảm cả kết quả
sai lẫn trường hợp kết quả sai được đánh giá đủ tin cậy để dừng quét.

Các ràng buộc cho release:

- Giữ nguyên trường thông tin trên các form và quy tắc từng thủ tục.
- Giữ ưu tiên QR đối với CCCD và text có sẵn đối với PDF.
- Không OCR ảnh lại chỉ vì một địa chỉ hợp lệ ngắn hoặc chưa khớp danh mục hành chính.
- Không tự suy đoán tên riêng, tên nước ngoài, số nhà hoặc mã số từ từ điển.
- Dữ liệu OCR cần được kiểm tra và lưu trước khi dùng qua dropdown; sửa và lưu profile
  phải tiếp tục cập nhật các nhóm trường đang liên kết với profile đó.
- Xử lý offline bằng các model đã đóng gói; chưa bổ sung model lớn hoặc dịch vụ cloud
  trong đợt release này.
- Fixture thực tế, ảnh cắt, báo cáo có nội dung tài liệu, model và EXE nằm ngoài commit.
  Không thay đổi tài liệu gốc hoặc `TemplatesBefore/`.

## 2. Hiện trạng đã xác minh

| Hạng mục | Hiện trạng ở mã nguồn nền |
| --- | --- |
| PDF có text | Trích xuất text trước; có phục hồi font nhúng nếu bảng mã lỗi |
| ERC scan | Tái sử dụng kết quả kiểm tra nhanh; tăng độ nét vùng đầu trang; giảm nền vàng |
| Điều kiện dừng ERC | Theo các trường từng luồng sử dụng; luồng tên/mã số không chờ địa chỉ |
| BRC | Parser và điều kiện đủ dữ liệu riêng; có đối chiếu nhiều nguồn |
| OCR tăng cường | PP-OCRv6, VietOCR hỗ trợ dòng chữ, RapidOCR dự phòng, nhiều biến thể ảnh |
| Chọn kết quả | Chọn theo từng trường, bảo vệ chữ số và cảnh báo khi các nguồn khác nhau |

Số đo tham khảo trên máy phát triển, không phải cam kết tốc độ cho mọi máy:

- 22 ERC có text: khoảng 0,02–0,053 giây/file qua hàm trích xuất; chưa tính tương tác UI.
- Một ERC hai trang ảnh có hoa văn: khoảng 5–6 giây sau tối ưu, so với khoảng 58 giây
  ở luồng cũ đã đo. Tên, mã số và địa chỉ ở trang đầu.
- Nhóm kiểm thử liên quan gần nhất: 97 test đạt. Kết quả này bảo vệ logic, chưa thay thế
  việc đánh giá độ chính xác trên tập tài liệu có đáp án độc lập.

## 3. Các khoảng trống cần xử lý

1. Điểm chất lượng còn phụ thuộc độ dài, định dạng và một số dấu hiệu lỗi chung. Một tên
   có phần loại hình doanh nghiệp đúng nhưng phần tên riêng thiếu dấu vẫn có thể đạt điểm cao.
2. Việc chuẩn hóa cụm từ có thể làm kết quả trông tốt hơn trước khi chất lượng được đánh giá.
   Cần phân biệt chữ đọc từ nguồn với chữ được sửa bởi quy tắc.
3. Chưa có đường đọc lại vùng nghi ngờ được nối đầy đủ vào kết quả ERC/BRC. Hiện có
   `address_candidates` trong line refiner và `address_evidence.py`, nhưng chưa được sử dụng
   để quyết định kết quả cuối trong hai service giấy chứng nhận.
4. Vùng nhanh ERC dùng tỷ lệ cố định 70% trang đầu, chưa xác định vùng theo nhãn/bố cục.
5. BRC chưa tái sử dụng kết quả quét kiểm tra loại tài liệu như ERC; không áp dụng nguyên
   điều kiện dừng của ERC vì thông tin đơn vị chủ quản thường nằm phía dưới.
6. Chưa có báo cáo chuẩn so sánh độ chính xác và tốc độ trước/sau trên cùng tập fixture,
   với đáp án đã được người kiểm tra xác nhận.

## 4. Thứ tự thực hiện

### P0 — Đóng băng bộ đo và kết quả nền

- [ ] Lập manifest cục bộ phân loại: ERC/BRC có text, text hỏng, scan rõ, scan hoa văn,
  ảnh lệch, thiếu dấu, địa chỉ dài/ngắn và giấy nhiều trang.
- [ ] Ghi đáp án đúng theo từng trường cần dùng, đối chiếu trực tiếp tài liệu gốc.
- [ ] Tách tập dùng sửa thuật toán và tập kiểm tra độc lập; các biến thể của cùng một
  tài liệu phải ở cùng tập, tránh đánh giá quá tốt do trùng dữ liệu.
- [ ] Ghi kết quả nền: giá trị từng trường, nguồn đọc, lỗi, cảnh báo, thời gian và đường quét.
- [ ] Đo lần chạy mới tiến trình và lần chạy đã nạp model riêng biệt, trên cùng máy/cấu hình.

File chính: `scripts/benchmark_certificate_ocr.py` và manifest/báo cáo trong `tmp/`.

Điều kiện hoàn tất: có báo cáo nền tái chạy được; không dùng kết quả OCR hiện tại làm đáp án.

### P1 — Kiểm tra chất lượng từng trường và quyết định đọc lại

- [ ] Bổ sung thông tin nguồn cho candidate: chữ gốc, chữ sau chuẩn hóa, độ tin cậy của
  dòng OCR nếu có, trang, tọa độ và các phép sửa đã áp dụng.
- [ ] Giữ tương thích `OrganizationDocumentResult`; mọi metadata mới có mặc định và
  không làm thay đổi các khóa dữ liệu form đang sử dụng.
- [ ] Tách đánh giá phần loại hình doanh nghiệp khỏi phần tên riêng. Không cộng độ tin cậy
  cho tên riêng chỉ vì đã phục hồi được cụm `CÔNG TY TNHH`.
- [ ] Kiểm tra chữ mất nét, ký tự thay thế, từ dính, nhãn lẫn vào giá trị, dòng bị cắt và
  dấu tiếng Việt đáng nghi. Tên nước ngoài/viết tắt không bị mặc định coi là lỗi thiếu dấu.
- [ ] Tách ba trạng thái nội bộ: đủ căn cứ chấp nhận, cần đọc lại, cần người dùng đối chiếu.
  Điểm nội bộ không được hiển thị như xác suất đúng tuyệt đối.
- [ ] Giữ nguyên dữ liệu text tốt; chỉ chọn trường đọc lại khi có dấu hiệu lỗi cụ thể.
- [ ] Thêm test cho tên mất dấu nhưng phần loại hình đúng, tên nước ngoài, địa chỉ ngắn,
  số nhà có ký tự và số đăng ký có số 0 đầu.

File chính:

- `src/mingo_assistant/services/organization_documents/organization_document_service.py`
- `src/mingo_assistant/services/organization_documents/location_certificate_service.py`
- `src/mingo_assistant/services/organization_documents/business_amendment_document_service.py`

Điều kiện hoàn tất: các ca sai đã biết không còn được chấp nhận chỉ vì định dạng hợp lệ;
tập text tốt vẫn giữ đường đọc trực tiếp và các quy tắc riêng của thủ tục.

### P2 — Đọc lại riêng vùng tên/địa chỉ còn nghi ngờ

- [ ] Giữ tọa độ các dòng OCR và liên kết với trường được parser trích xuất.
- [ ] Cắt vùng theo nhãn và các dòng tiếp nối, thêm khoảng đệm để giữ đủ dấu, số nhà
  và phần địa chỉ xuống dòng; không cắt theo một tọa độ cố định cho mọi mẫu giấy.
- [ ] Đọc lại ở độ phân giải phù hợp; chỉ thử biến thể ảnh khi có lý do như nền vàng,
  độ tương phản thấp hoặc ảnh nghiêng. Luôn giữ candidate từ ảnh màu gốc.
- [ ] Nối `address_candidates` và cơ chế đối chiếu bằng chứng vào kết quả cuối;
  một module có unit test riêng chưa được coi là tính năng đã tích hợp.
- [ ] So sánh candidate theo từng trường. Việc chỉ đổi dấu vẫn phải có bằng chứng,
  vì `Trung`, `Trúng`, `Trường` có thể là các tên khác nhau.
- [ ] Bảo vệ nguyên token chứa số và dấu phân cách, ví dụ `P5.09`, `10/3/242`, `50-52`.
- [ ] Đặt giới hạn số lượt đọc lại và lưu lý do kích hoạt. Giá trị khởi điểm để đo:
  tối đa hai biến thể/vùng; điều chỉnh ngân sách toàn tài liệu từ benchmark P0.
- [ ] Nếu không tìm được vùng đáng tin hoặc kết quả chưa rõ, dùng fallback hiện có
  hoặc cảnh báo đối chiếu; không ép chọn một candidate chỉ vì có nhiều dấu hơn.

File chính: hai service ERC/BRC, `vietnamese_line_refiner.py`, `address_evidence.py`
và `certificate_layout.py` trong `src/mingo_assistant/services/`.

Điều kiện hoàn tất: có test đi qua service thật tới quyết định kết quả cuối; mã số/số nhà
không bị thay đổi; chỉ vùng nghi ngờ được đọc lại trên các ca đã đủ trường khác.

### P3 — Hoàn thiện vùng đọc và luồng BRC

- [ ] Giữ vùng nhanh ERC hiện tại làm phương án mặc định; dùng nhãn/tọa độ để mở rộng
  vùng hoặc chuyển trang khi thông tin chưa đủ, thay vì tin rằng dữ liệu luôn ở 70% đầu.
- [ ] Tái sử dụng kết quả quét kiểm tra loại BRC làm candidate, chỉ dừng khi đủ cả thông tin
  địa điểm và đơn vị chủ quản theo quy tắc BRC.
- [ ] Đọc các trang tiếp theo nếu thiếu trường; có test trường nằm ngoài vùng nhanh,
  ở trang sau, tên dài nhiều dòng và tài liệu nhiều cột.
- [ ] Giữ kiểm tra sai ERC/BRC từ đầu. Không dùng một mã doanh nghiệp xuất hiện trong
  phần chủ sở hữu/đơn vị chủ quản để thay cho mã của đối tượng cần lấy.

Điều kiện hoàn tất: ERC/BRC có điều kiện dừng riêng; không bỏ sót trường ở trang sau;
quét nhanh không chấp nhận nhầm đối tượng trong cùng tài liệu.

### P4 — Kiểm thử và chốt bản release

- [ ] So sánh báo cáo trước/sau trên cả tập sửa thuật toán và tập độc lập.
- [ ] Kiểm thử UI: chọn đúng form, sửa/lưu dữ liệu, dropdown điền lại, lưu profile đang dùng
  cập nhật đúng nhóm trường và không ghi đè sang profile khác.
- [ ] Kiểm thử hồi quy CCCD: QR rõ/mờ, không có QR, hai mặt, địa chỉ, nơi cấp; không thay
  chính sách suy luận nơi cấp trong đợt tối ưu ERC/BRC này.
- [ ] Kiểm tra lint, diff và nhóm unit test liên quan; sau khi ổn định mới chạy kiểm thử
  toàn dự án. Test Qt dùng chế độ offscreen và APPDATA tạm riêng.
- [ ] Đóng gói EXE sau khi mã nguồn đạt các cổng kiểm tra bên dưới; chạy portable self-test.
- [ ] Thử EXE trên môi trường Windows sạch, không Python và không mạng; xác minh đọc text,
  QR, PP-OCRv6/VietOCR, template và xuất Word thực tế.
- [ ] Ghi commit nguồn, phiên bản, đường dẫn artifact và SHA256 của EXE được kiểm tra.
  Chỉ công bố hoàn tất khi có bằng chứng cho chính artifact đó.

Lệnh build hiện có:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_exe.ps1
```

Artifact dự kiến: `EXE/MinAssistant.exe`. Script hiện có bước chạy self-test trong EXE;
self-test đạt chưa thay thế kiểm tra trên Windows sạch hoặc kiểm tra xuất Word.

## 5. Cổng kiểm tra trước release

Các ngưỡng thời gian sau là mục tiêu dự kiến; chốt lại sau P0 trên máy đo cố định.

| Tiêu chí | Điều kiện đạt |
| --- | --- |
| Độ chính xác | Các lỗi mục tiêu có test tái hiện được và được sửa; không tăng số trường sai trên tập độc lập |
| Sai nhưng không cảnh báo | Không xuất hiện ca mới trong bộ kiểm tra đã đối chiếu; mọi bất đồng chưa giải quyết được phải được giữ dấu vết/cảnh báo |
| Số định danh | Không đổi số 0 đầu, chữ số, token số nhà hoặc dấu phân cách trong các ca kiểm tra |
| Text PDF tốt | Không kích hoạt OCR ảnh mới; thời gian trung vị không tăng quá 10% so với nền cùng điều kiện |
| ERC hoa văn chuẩn | Mục tiêu không quá 8 giây cho ca đã đo 5–6 giây trên cùng máy; nếu vượt phải điều tra đường quét |
| Các nhóm tài liệu khác | Báo cáo trung vị và p95; mục tiêu p95 không tăng quá 20%, mọi ngoại lệ phải gắn với lỗi chính xác được sửa và được chốt trước release |
| Form/profile | Chọn form, lưu, điền và cập nhật qua dropdown đúng toàn bộ ca kiểm tra |
| Đóng gói offline | EXE tự kiểm tra đạt và chạy được trên Windows sạch với các công cụ/model cần thiết |

Không dùng một điểm chất lượng cao hoặc số test unit đạt làm bằng chứng thay cho đáp án
tài liệu đã đối chiếu. Báo riêng kết quả tự động, kết quả người kiểm tra và phần chưa xác minh.

## 6. Cách chia thay đổi để kịp release

1. Chốt P0, triển khai P1 thành một thay đổi nhỏ, đo lại ngay.
2. Triển khai P2 với số vùng/lượt đọc có giới hạn; chỉ giữ khi có cải thiện đo được.
3. Triển khai P3 theo từng parser, không gom ERC/BRC thành một bộ quy tắc chung.
4. Khi từng bước đạt mới thực hiện P4. Không đồng thời thay OCR model, sửa template
   và tái cấu trúc lớn UI trong cùng đợt này.

Nếu P3 chưa đạt trước thời điểm chốt, chỉ phát hành phần P1/P2 đã đo và đã kiểm thử;
giữ fallback đang ổn định và ghi rõ phần còn lại. Không bật đường nhận diện mới chưa
đủ kiểm tra chỉ để kịp ngày release.

## 7. Bàn giao sau mỗi bước

- Phần code thay đổi và lý do.
- Ca lỗi trước/sau, test mới có ý nghĩa và kết quả hồi quy.
- Số đo độ chính xác/thời gian, đường quét và giới hạn còn tồn tại.
- Cập nhật checkbox/trạng thái trong file này; chỉ đánh dấu xong khi có bằng chứng.
- Commit/push và xuất bản artifact theo yêu cầu của người dùng; không đưa fixture riêng,
  báo cáo chứa dữ liệu tài liệu hoặc các tài liệu local khác vào Git.

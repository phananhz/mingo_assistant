# Kế hoạch bảo trì Min Assistant

> Cập nhật gần nhất: 16/10/2026
> Trạng thái chung: Giai đoạn 0-6 hoàn thành; kế hoạch bảo trì nền tảng đã hoàn tất

## Mục tiêu

- Giữ nguyên hành vi hiện tại của ứng dụng trong quá trình bảo trì.
- Giảm độ phức tạp của các file lớn và tách rõ trách nhiệm giữa UI, nghiệp vụ, lưu trữ và sinh tài liệu.
- Bảo vệ dữ liệu hồ sơ cục bộ và định dạng của các mẫu Word.
- Tạo nền kiểm thử đủ tin cậy trước khi tiếp tục phát triển tính năng mới.
- Cập nhật tài liệu để phản ánh đúng kiến trúc đang chạy.

## Quy ước trạng thái

- `[ ]` Chưa làm.
- `[~]` Đang thực hiện hoặc đã làm một phần nhưng chưa đủ bằng chứng hoàn thành.
- `[x]` Hoàn thành và đã kiểm tra.
- `[!]` Đang bị chặn hoặc cần quyết định.

Chỉ chuyển công việc sang `[x]` khi tiêu chí hoàn thành của công việc đó đã được đáp ứng và kết quả kiểm tra đã được ghi vào nhật ký tiến độ.

## Nguyên tắc bảo trì

- Không thay đổi giao diện, nghiệp vụ hoặc nội dung DOCX trong một refactor thuần cấu trúc.
- Không chỉnh trực tiếp hoặc di chuyển mẫu nguồn trong `TemplatesBefore/`.
- Chỉ cập nhật mẫu runtime trong `assets/templates/word/` khi có yêu cầu cụ thể.
- Khi thay đổi template, mapping hoặc xử lý DOCX, phải kiểm tra cả nội dung và bản render trực quan.
- Không commit CCCD, hồ sơ khách hàng, ảnh giấy tờ, dữ liệu runtime hoặc file xuất thực tế.
- Không xóa các thư mục QA, model, release hoặc file chưa được Git theo dõi trước khi phân loại và được xác nhận.
- Mỗi đợt bảo trì nên nhỏ, có regression test và có thể review độc lập.

## Giai đoạn 0 - Thiết lập đường chuẩn

Mục tiêu: ghi nhận trạng thái hiện tại trước khi refactor.

- [x] Ghi lại commit và trạng thái working tree trước khi bảo trì.
- [x] Phân loại các file/thư mục chưa được Git theo dõi: tài sản cần giữ, dữ liệu QA, artifact có thể tạo lại và dữ liệu nhạy cảm.
- [x] Chạy `py_compile` cho mã nguồn chính.
- [x] Chạy toàn bộ unit test với Qt ở chế độ offscreen.
- [x] Chạy integration test hiện có.
- [x] Chạy Ruff theo cấu hình hiện tại.
- [x] Chạy `git diff --check`.
- [x] Chọn bộ hồ sơ DOCX đại diện cho từng workflow đang hoạt động.
- [x] Lưu bằng chứng baseline: số test, lỗi hiện có, tài liệu đầu ra và các giới hạn chưa kiểm tra.

Tiêu chí hoàn thành:

- Có kết quả kiểm tra tái lập được bằng lệnh cụ thể.
- Các lỗi tồn tại trước khi bảo trì được ghi riêng, không bị nhầm là regression mới.
- Có danh sách artifact được bảo vệ trong suốt quá trình làm việc.

## Giai đoạn 1 - Đồng bộ tài liệu kiến trúc

Mục tiêu: tài liệu phản ánh đúng code và luồng runtime hiện tại.

- [x] Cập nhật `docs/ARCHITECTURE.md` theo kiến trúc JSON atomic đang sử dụng.
- [x] Đối chiếu và cập nhật sơ đồ `UI -> application -> services/repositories -> infrastructure`.
- [x] Mô tả rõ vai trò của `AppContainer`, `MainWindow` và các workspace.
- [x] Mô tả đúng vị trí dữ liệu tại `%APPDATA%\Min Assistant` và thư mục xuất trong Documents.
- [x] Phân biệt `TemplatesBefore/` với `assets/templates/word/`.
- [x] Đồng bộ lệnh chạy source, test và build giữa README với tài liệu packaging.
- [x] Ghi rõ phần nào là hiện trạng, phần nào mới là định hướng tương lai.

Tiêu chí hoàn thành:

- Không còn mô tả SQLite hoặc module dự kiến như thể chúng đang được sử dụng trong runtime.
- Một người mới có thể lần theo entrypoint, luồng lưu hồ sơ và luồng xuất Word chỉ từ tài liệu.

## Giai đoạn 2 - Tách nghiệp vụ thay đổi ĐKDN

Mục tiêu: giảm trách nhiệm của `BusinessAmendmentWorkspace` mà không thay đổi hành vi.

- [x] Lập bản đồ các nhóm trách nhiệm hiện tại của workspace.
- [x] Tách phần ngành nghề thành component/controller độc lập nếu chưa hoàn chỉnh.
- [x] Tách phần thông tin thuế.
- [x] Tách phần vốn và cổ phần.
- [x] Tách phần người đại diện và chọn hồ sơ cá nhân/tổ chức.
- [x] Tách luồng nhận diện PDF doanh nghiệp khỏi code dựng widget.
- [x] Tách logic lưu/khôi phục form khỏi xử lý trình bày.
- [x] Bổ sung regression test cho từng phần được tách.
- [x] So sánh dữ liệu `form_values` trước và sau refactor.

Tiêu chí hoàn thành:

- Workspace chủ yếu điều phối các section thay vì chứa toàn bộ logic chi tiết.
- Hồ sơ cũ mở lại không mất dữ liệu, kể cả các trường ẩn hoặc danh sách ngành nghề nhiều trang.
- DOCX đầu ra không thay đổi ngoài các khác biệt đã được phê duyệt.

## Giai đoạn 3 - Tách hệ thống sinh DOCX

Mục tiêu: cô lập quy tắc của từng loại hồ sơ và từng mẫu Word.

- [x] Thống kê trách nhiệm đang nằm trong `docx_generator.py`.
- [x] Xác định helper dùng chung thực sự: thay placeholder, xử lý run, bảng lặp, checkbox và đóng gói DOCX.
- [x] Di chuyển quy tắc đặc thù sang generator của từng workflow/template.
- [x] Giữ tương thích API trong thời gian chuyển đổi.
- [x] Bổ sung test cho ranh giới template và vùng được phép điền.
- [x] Kiểm tra placeholder chưa được xử lý sau khi xuất.
- [x] Render và so sánh trực quan các tài liệu bị ảnh hưởng.
- [x] Không sửa template khóa theo SHA-256 trong refactor; giữ nguyên hash sau khi rà lại mapping và bản render.

Tiêu chí hoàn thành:

- `docx_generator.py` chỉ còn facade tương thích; implementation được đặt trong generator đúng workflow.
- Quy tắc của một mẫu không làm thay đổi tài liệu thuộc workflow khác.
- Các vùng protected và định dạng nguồn được giữ nguyên.

## Giai đoạn 4 - Chuẩn hóa model và migration dữ liệu

Mục tiêu: giảm phụ thuộc trực tiếp vào `dict[str, str]` khi nghiệp vụ ngày càng phức tạp.

- [x] Thống kê schema `form_values` của từng loại hồ sơ.
- [x] Xác định các nhóm cần kiểu dữ liệu riêng: người, doanh nghiệp, địa chỉ, vốn, ngành nghề và thông tin ký.
- [x] Thiết kế model cho tính năng mới trước khi áp dụng ngược vào tính năng cũ.
- [x] Định nghĩa schema version theo workflow.
- [x] Viết migration có khả năng đọc hồ sơ cũ.
- [x] Bảo toàn trường chưa nhận diện khi lưu lại hồ sơ phiên bản cũ.
- [x] Thêm test round-trip: JSON -> model -> JSON.
- [x] Thêm test migration với dữ liệu đại diện từ các phiên bản trước.

Tiêu chí hoàn thành:

- Dữ liệu nghiệp vụ quan trọng có validation và kiểu rõ ràng.
- Hồ sơ cũ tiếp tục mở, sửa, lưu và xuất được.
- Không làm mất các khóa chưa được UI hiện tại sử dụng.

## Giai đoạn 5 - Thu gọn điều hướng và MainWindow

Mục tiêu: để `MainWindow` tập trung vào shell ứng dụng thay vì biết chi tiết mọi workflow.

- [x] Thống kê các route và cách tạo workspace hiện tại.
- [x] Tạo registry/factory cho workspace theo `case_type`.
- [x] Tách điều hướng danh sách, chi tiết và màn hình tài liệu.
- [x] Chuẩn hóa lifecycle khi mở, đóng và thay workspace.
- [x] Kiểm tra không rò rỉ widget hoặc signal khi chuyển màn hình nhiều lần.
- [x] Giữ nguyên hành vi Back, Save, Export và mở lại hồ sơ.

Tiêu chí hoàn thành:

- Thêm một loại hồ sơ mới không cần bổ sung nhiều nhánh điều kiện vào `MainWindow`.
- Điều hướng hiện có vượt qua regression test và kiểm tra UI offscreen.

## Giai đoạn 6 - Tăng chất lượng tự động

Mục tiêu: phát hiện lỗi sớm nhưng không tạo một đợt sửa style diện rộng.

- [x] Mở rộng Ruff theo từng nhóm quy tắc nhỏ.
- [x] Xử lý import và biến không sử dụng trong phạm vi file đang bảo trì.
- [x] Thêm type checking trước cho `application/`, `models/` và services thuần Python.
- [x] Không ép type checking toàn bộ PySide6 UI trong cùng một đợt.
- [x] Xây dựng một lệnh hoặc script kiểm tra thống nhất cho local/CI.
- [x] Ghi rõ kiểm tra nào là bắt buộc trước commit và trước release.

Tiêu chí hoàn thành:

- Nhà phát triển có một quy trình kiểm tra ngắn, tái lập được.
- Quy tắc mới không kéo theo thay đổi hàng loạt ngoài phạm vi bảo trì.

## Checklist bắt buộc cho mỗi thay đổi

- [ ] Đã kiểm tra `git status --short` trước khi sửa.
- [ ] Đã xác định file người dùng đang thay đổi và tránh ghi đè.
- [ ] Thay đổi nằm đúng lớp kiến trúc.
- [ ] Có test cho logic hoặc regression liên quan.
- [ ] Test mục tiêu đã chạy và đạt.
- [ ] Toàn bộ test cần thiết đã chạy và đạt, hoặc giới hạn đã được ghi rõ.
- [ ] `git diff --check` đạt.
- [ ] Không có dữ liệu CCCD/hồ sơ thật trong diff.
- [ ] Nếu ảnh hưởng DOCX: đã kiểm tra placeholder và vùng protected.
- [ ] Nếu ảnh hưởng layout DOCX: đã render và kiểm tra trực quan.
- [ ] Nếu ảnh hưởng dữ liệu: đã kiểm tra mở/lưu lại hồ sơ cũ.
- [ ] README/tài liệu đã cập nhật nếu hành vi hoặc kiến trúc thay đổi.

## Tiến độ tổng hợp

| Giai đoạn | Trạng thái | Tiến độ | Ghi chú |
| --- | --- | ---: | --- |
| 0. Thiết lập đường chuẩn | Hoàn thành | 100% | Baseline 251 unit và 2 integration test đạt |
| 1. Đồng bộ tài liệu | Hoàn thành | 100% | Kiến trúc, test và packaging đã đồng bộ với runtime |
| 2. Tách thay đổi ĐKDN | Hoàn thành | 100% | Workspace còn 742 dòng; section/controller/state đã tách |
| 3. Tách hệ thống DOCX | Hoàn thành | 100% | Facade tương thích, engine dùng chung và generator đặc thù đã tách; regression, full test và render đại diện đều đạt |
| 4. Model và migration | Hoàn thành | 100% | Adapter typed cho ba nhóm workflow, registry migration theo version và round-trip dữ liệu cũ đều đã kiểm tra |
| 5. Điều hướng/MainWindow | Hoàn thành | 100% | Registry/factory, lifecycle view tạm và hồi quy điều hướng offscreen đều đạt |
| 6. Chất lượng tự động | Hoàn thành | 100% | Ruff F401, mypy phạm vi thuần Python và full gate local/CI đã đạt |

## Nhật ký tiến độ

### 15/10/2026

- [x] Bắt đầu Giai đoạn 4: lập `docs/FORM_VALUES_SCHEMA.md`, kiểm kê nhóm khóa dùng chung và khóa đặc thù của đăng ký doanh nghiệp, đơn vị phụ thuộc và thay đổi ĐKDN.
- [x] Thêm `form_schema_version` tương thích ngược vào `CaseSummary`; hồ sơ cũ không có metadata được đọc là version 0 và không bị tự động ghi lại chỉ vì mở danh sách.
- [x] Thêm lớp merge lossless cho workflow đăng ký doanh nghiệp: giữ khóa chưa nhận diện, nhưng thay toàn bộ các namespace danh sách động do UI quản lý để hàng đã xóa không quay lại.
- [x] Hồ sơ đăng ký doanh nghiệp/đơn vị phụ thuộc mới lưu ở schema version 1; hồ sơ thay đổi ĐKDN lưu version 4 đồng bộ với `amendment_schema_version` hiện có.
- [x] Thêm test cho metadata round-trip, chuẩn hóa giá trị cũ, giữ khóa lạ và thay namespace động; 84 test schema/repository/workspace liên quan đạt.
- [x] Checkpoint Giai đoạn 4 lát cắt đầu: Ruff và compile đạt; 256/257 unit test đạt trong sandbox, ca DPAPI còn lại đạt ngoài sandbox; 2/2 integration test và `git diff --check` đạt. Không có template Word nào bị sửa.
- [x] Bổ sung `SigningContext` và adapter hai chiều `RegistrationCase.from_form_values()` / `to_form_values(base=...)` cho doanh nghiệp, người, địa chỉ, vốn, ngành nghề và thông tin ký.
- [x] Adapter giữ khóa chưa nhận diện, định dạng vốn không đổi, chỉ số ngành nghề không liên tục và không khôi phục dòng động đã xóa; 19 test domain/application/formatter liên quan đạt.
- [x] Checkpoint adapter typed: Ruff và compile đạt; 258/259 unit test đạt trong sandbox, ca DPAPI còn lại đạt ngoài sandbox; 2/2 integration test và `git diff --check` đạt. Template Word và SHA-256 không thay đổi.
- [x] Tạo `DependentUnitCase` cùng các model `ParentEntity`, `IdentityDocument`, `LegalRepresentative` và `DependentUnitManager` cho ba workflow địa điểm kinh doanh.
- [x] Adapter đơn vị phụ thuộc giữ đồng thời CCCD/hộ chiếu và để validation workflow quyết định trường bắt buộc; các khóa thuế, OCR, checkbox, giấy chứng nhận chưa typed vẫn được bảo toàn qua map nền.
- [x] Thêm test round-trip cho người nước ngoài, nội dung thay đổi, ngành nghề động và chấm dứt địa điểm kinh doanh; 14 test domain/formatter/location liên quan đạt.

### 16/10/2026

- [x] Checkpoint adapter đơn vị phụ thuộc: Ruff và compile đạt; 261/262 unit test đạt trong sandbox, ca DPAPI còn lại đạt ngoài sandbox; 2/2 integration test và `git diff --check` đạt. Template Word không thay đổi.
- [x] Tạo `BusinessAmendmentCase`, `AmendmentRepresentative` và `AmendmentLineChange`; migration v0-3 -> v4 chuyển lựa chọn cổ phần cũ, thu gọn dòng ngành nghề rỗng và giữ khóa chưa nhận diện.
- [x] Thêm registry migration theo `case_type`; workflow đăng ký/đơn vị phụ thuộc nâng v0 -> v1 không đổi map, workflow thay đổi ĐKDN nâng lên v4, workflow chưa biết không bị tự nâng version.
- [x] Ghi rõ màu vàng không phải quy tắc toàn cục: mapping/manifest của từng generator mới là nguồn sự thật; vị trí không bôi vàng đã có quy tắc đặc thù không được tự ý xóa.
- [x] Checkpoint hoàn tất Giai đoạn 4: 265/266 unit test đạt trong sandbox; ca DPAPI duy nhất đạt ngoài sandbox; 2/2 integration test, Ruff, compile và `git diff --check` đều đạt. Không có diff trong `assets/templates`; không commit hoặc push Git.
- [x] Bắt đầu Giai đoạn 5: tạo `ui/routing/workspace_registry.py` ánh xạ `case_type` sang class workspace, nhóm điều hướng và điểm Back; `MainWindow` không còn chuỗi nhánh mở từng workflow.
- [x] Gom lifecycle workspace/màn hình tài liệu vào `_show_transient_view()`; thêm test chuyển liên tiếp xác nhận stack chỉ có một view tạm và widget cũ được hủy sau deferred delete.
- [x] Điều hướng trang hub dùng registry trang; 93 test mục tiêu về route, modal, sidebar, thay đổi ĐKDN và ba workflow địa điểm kinh doanh đạt.
- [x] Checkpoint hoàn tất Giai đoạn 5: 269/270 unit test đạt trong sandbox; ca DPAPI duy nhất đạt ngoài sandbox; 2/2 integration test, Ruff, compile và `git diff --check` đều đạt. `assets/templates` không có diff.
- [x] Bắt đầu Giai đoạn 6: bật thêm Ruff `F401` và dọn 16 import không dùng; không mở rộng style rule diện rộng.
- [x] Thêm mypy cho 19 module trong `application/`, `models/` và `domains/`; sửa ranh giới map JSON để type-check đạt mà không đổi format lưu trữ.
- [x] Thêm `scripts/verify.py` làm entrypoint chung cho compile, Ruff, mypy, unit, integration và `git diff --check`; CI chuyển sang dùng cùng lệnh này.
- [x] Checkpoint hoàn tất Giai đoạn 6 và toàn bộ kế hoạch: `scripts/verify.py` đạt với 270/270 unit test, 2/2 integration test, Ruff, compile, mypy 19 module và `git diff --check`. Không có diff trong `assets/templates`; không commit hoặc push Git.
- [x] Tạo `DocxTemplateEngine` cho cơ chế trung lập: formatter/context, điền vùng vàng theo manifest và bảng ngành nghề; không đưa quy tắc chọn hồ sơ hay mapping đặc thù vào engine.
- [x] `DependentUnitTemplateGenerator` không còn import/kế thừa `DocxTemplateGenerator`; các quy tắc riêng về người nước ngoài, checkbox, thông báo thay đổi, người ký và vùng protected vẫn nằm tại workflow đơn vị phụ thuộc.
- [x] Thêm regression test khóa ranh giới kế thừa; 40 test mục tiêu của đăng ký doanh nghiệp và đơn vị phụ thuộc đạt.
- [x] Sinh mới bộ 3 tài liệu lập địa điểm kinh doanh, không còn placeholder; render và kiểm tra đủ 8 trang đầu ra. Bảng ngành nghề đúng 4 cột/2 dòng, không cắt hoặc chồng chữ.
- [x] Đối chiếu trang ký thưa với template nguồn: đây là bố cục có sẵn; đầu ra giảm từ 6 xuống 5 trang do bỏ các dòng ngành nghề mẫu thừa, không mất nội dung.
- [x] Checkpoint mới: 253/254 unit test đạt trong sandbox; test DPAPI duy nhất đạt khi chạy riêng ngoài sandbox; 2 integration test, Ruff và compile đều đạt.
- [x] Sinh mới bộ 6 tài liệu của workflow công ty TNHH hai thành viên chỉ có thành viên cá nhân; không còn placeholder chưa xử lý.
- [x] Render và kiểm tra trực quan 36 trang đầu ra hiện tại. Các trang có nội dung đều đọc được, không bị cắt hoặc chồng chữ.
- [x] Phát hiện luồng điền chung ghi vốn điều lệ vào hàng đánh số cột của File 3, làm phát sinh một trang trắng; đã khôi phục hàng số 1-14 từ đúng template của File 3 và thêm regression test.
- [x] Render lại File 3 sau sửa: còn đúng 2 trang, trang ký trở về trang 2 và không còn trang trắng phát sinh.
- [x] Đối chiếu template gốc: File 1 và File 4 đã có trang trắng do bố cục nguồn; chưa tự ý xóa trong đợt refactor cấu trúc này.
- [x] Sau sửa lỗi File 3: 252 unit test còn lại đạt trong lần chạy sandbox; test DPAPI duy nhất đạt khi chạy riêng ngoài sandbox; 2 integration test, Ruff, compile với cache tạm và `git diff --check` đều đạt.
- [x] Gỡ phụ thuộc kế thừa không cần thiết của `BusinessAmendmentTemplateGenerator` khỏi pipeline thành lập doanh nghiệp; 41 test thay đổi ĐKDN đạt, Ruff, compile và `git diff --check` đạt.
- [x] Xóa phần implementation dùng chung bị lặp và các helper bảng ngành nghề cũ không còn được gọi khỏi `business_registration_generator.py`; generator đăng ký doanh nghiệp kế thừa cơ chế trung lập từ `DocxTemplateEngine` nhưng vẫn giữ các hook và mapping riêng của workflow.
- [x] Sau lần dọn cuối, 44 test mục tiêu về kết quả sinh file, đăng ký doanh nghiệp, hai thành viên, đơn vị phụ thuộc, thay đổi ĐKDN và integration workflow đều đạt.
- [x] Sinh mới bộ 5 tài liệu công ty TNHH một thành viên, không còn placeholder chưa xử lý; render và kiểm tra trực quan đủ 33 trang, không có bảng/chữ bị cắt hoặc chồng lấn.
- [x] Đối chiếu với template nguồn xác nhận các trang trắng của `Giấy đề nghị thành lập DN` và `Danh sách chủ sở hữu hưởng lợi` là bố cục có sẵn; không tự ý thay đổi template trong refactor.
- [x] Checkpoint hoàn tất Giai đoạn 3: Ruff và compile đạt; 253/254 unit test đạt trong sandbox, ca DPAPI còn lại đạt ngoài sandbox; 2/2 integration test và `git diff --check` đạt.
- [x] Không sửa template nguồn, không cập nhật SHA-256, không commit và không push Git.

### 14/10/2026

- [x] Đã tạo kế hoạch bảo trì và checklist theo dõi.
- [x] Đã fetch `origin` và xác nhận `HEAD == origin/main == d30b9d3`, ahead/behind là `0/0` trước khi sửa.
- [x] Đã xác nhận không có thay đổi ở source code được Git theo dõi trước khi bắt đầu bảo trì.
- [x] Python 3.12.10; `compileall`, Ruff và `git diff --check` đều đạt.
- [x] Toàn bộ 251 unit test đạt trong 153,441 giây với Qt offscreen và `APPDATA` tạm cô lập.
- [x] Cả 2 integration test đạt trong 1,766 giây.
- [x] Test DPAPI chạy riêng ngoài sandbox đạt; lỗi WinError 2 trong lần chạy sandbox được xác nhận là giới hạn môi trường.
- [x] Sửa hai test baseline: ngày ký không còn hard-code 27/09/2026 và autosave chờ theo điều kiện thay vì một khoảng cố định duy nhất.
- [x] Cảnh báo còn lại: API `fitz` đã deprecated và nên chuyển sang `pymupdf` trong một thay đổi riêng.
- [x] Hoàn thành Giai đoạn 1: cập nhật kiến trúc hiện hành, đường dẫn dữ liệu, template, lệnh test cô lập và lệnh build chuẩn.
- [x] Giai đoạn 2: `BusinessAmendmentWorkspace` giảm từ 1.259 xuống 742 dòng sau khi tách thuế, vốn/cổ phần, nhận diện tổ chức và form state bằng composition.
- [x] 41 test generator/workflow thay đổi ĐKDN đạt sau refactor; compile với cache tạm, Ruff và `git diff --check` đều đạt.
- [x] Sau checkpoint Giai đoạn 2, chạy lại toàn bộ 251 unit test và 2 integration test: tất cả đều đạt; Ruff, compile và `git diff --check` tiếp tục đạt.
- [x] Sau khi hoàn tất controller PDF/người đại diện và form state, chạy lại 41 test thay đổi ĐKDN: tất cả đều đạt.
- [x] Refactor hiện tại không thay đổi hành vi production hoặc template Word.
- [x] Bắt đầu Giai đoạn 3: lập `docs/DOCX_GENERATION_BOUNDARIES.md`, tách `GeneratedDocument` và `GenerationResult` sang module dùng chung, đồng thời giữ tương thích đường import cũ.
- [x] Ruff, compile và 76 test DOCX/workflow trọng yếu đều đạt sau bước tách đầu tiên của Giai đoạn 3.
- [x] Chuyển implementation sinh hồ sơ đăng ký doanh nghiệp sang `business_registration_generator.py`; `docx_generator.py` còn là facade tương thích và production code đã dùng đường import mới.
- [x] Sau khi đổi ranh giới module, Ruff, compile và 78 test DOCX/workflow trọng yếu đều đạt.
- [x] Checkpoint hiện tại: toàn bộ 253 unit test và 2 integration test đạt; `git diff --check` đạt. Số unit test tăng thêm 2 do bổ sung kiểm tra kiểu kết quả và đường import tương thích.
- [x] Tách 556 dòng quy tắc DOCX của bộ hồ sơ công ty hai thành viên cá nhân sang `two_member_individual_generator.py`; đường import cũ từ cả hai module vẫn trả về đúng cùng một class.

## Phân loại artifact cục bộ

| Đường dẫn | Phân loại | Cách xử lý |
| --- | --- | --- |
| `TemplatesBefore/` | Mẫu nguồn do người dùng cung cấp | Giữ nguyên, không move hoặc ghi đè |
| `assets/models/` | Model OCR runtime, dung lượng lớn | Giữ nguyên; quyết định cách phân phối riêng, không tự động commit |
| `release/` | EXE, log và output PyInstaller có thể tạo lại | Không xóa trong đợt bảo trì; không dùng làm bằng chứng build mới |
| `tmp_*_qa*` và `tmp_*_review*` | DOCX/PDF/PNG và profile LibreOffice phục vụ QA | Giữ ngoài Git; chỉ xóa sau khi có xác nhận |
| `mingo-signature-format-*`, `mingo-signature-highlight-*` | Thư mục tạm hiện không có quyền đọc | Không đổi owner/ACL; coi là dữ liệu được bảo vệ và bỏ qua |
| `docs/MAINTENANCE_ROADMAP.md` | Tài liệu của đợt bảo trì hiện tại | Theo dõi cùng thay đổi bảo trì khi được commit |

## Bộ DOCX đại diện cho regression QA

- Thành lập công ty TNHH một thành viên: toàn bộ bộ mẫu trong `business_registration/`.
- Thành lập công ty TNHH hai thành viên chỉ có thành viên cá nhân: bộ 6 tài liệu.
- Thành lập công ty TNHH hai thành viên có thành viên tổ chức: bộ 7 tài liệu.
- Thay đổi đăng ký doanh nghiệp: `business_amendment/Thong bao thay doi.docx`.
- Lập địa điểm kinh doanh: bộ mẫu trong `dependent_units/ddkd_create/`.
- Thay đổi địa điểm kinh doanh: bộ mẫu trong `dependent_units/ddkd_update/`.
- Chấm dứt địa điểm kinh doanh: bộ mẫu trong `dependent_units/ddkd_terminate/`.

## Quyết định cần ghi lại trong quá trình làm

Mỗi quyết định đáng kể nên được bổ sung theo mẫu:

```text
Ngày:
Phạm vi:
Quyết định:
Lý do:
Ảnh hưởng tương thích:
Bằng chứng kiểm tra:
Việc còn lại:
```

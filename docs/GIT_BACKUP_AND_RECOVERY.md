# Backup Git và khôi phục an toàn trước khi refactor

> Cập nhật: 16/10/2026
> Mục tiêu: giữ một mốc có thể quay lại khi refactor thất bại, đồng thời không
> làm mất phần việc chưa commit hiện có.

## 1. Mốc baseline hiện tại

Commit gần nhất của dự án tại thời điểm viết tài liệu:

```text
Mã đầy đủ : d30b9d353198fbeed8fb9a749c336b03b6e7c055
Mã ngắn   : d30b9d3
Nhánh     : main
Tác giả   : phananhz <duyle2004k@gmail.com>
Thời gian : 2026-10-12 22:42:27 +07:00
Nội dung  : fix: remove extra zero from asset total label
```

Tại lần kiểm tra này, cả `HEAD -> main` và bản ghi theo dõi cục bộ
`origin/main` đều trỏ tới `d30b9d3`.

Đây là **baseline đã commit**. Nó phù hợp để làm điểm quay lại của mã nguồn đã
được ghi nhận. Nó không tự động bao gồm các file đang sửa hoặc file mới chưa
commit.

## 2. Điều quan trọng trước khi refactor

Working tree hiện đang có nhiều file sửa đổi và file chưa được theo dõi, bao
gồm code, test, template, tài liệu và thư mục QA tạm. Vì vậy cần phân biệt hai
loại backup:

| Cần bảo vệ | Cách phù hợp |
|---|---|
| Bản code đã commit `d30b9d3` | Tạo local branch hoặc annotated tag trỏ cố định vào commit này. |
| Toàn bộ trạng thái đang làm, kể cả untracked files | Tạo một commit WIP trên nhánh backup riêng, hoặc sao chép workspace thành snapshot. |

Chỉ tạo branch/tag cho `d30b9d3` sẽ **không** sao lưu các thay đổi chưa commit
hiện có. Ngược lại, `git stash` mặc định cũng không giữ untracked files; không
dùng nó làm backup duy nhất cho workspace này.

## 3. Cách khuyến nghị: tạo mốc baseline cục bộ

Lệnh sau chỉ tạo một tên tham chiếu mới đến commit cũ; không sửa file, không
chuyển nhánh, không commit mới và không upload lên GitHub:

```powershell
git branch backup/pre-refactor-d30b9d3 d30b9d353198fbeed8fb9a749c336b03b6e7c055
```

Kiểm tra mốc vừa tạo:

```powershell
git show --no-patch --decorate backup/pre-refactor-d30b9d3
```

Sau đó có thể kiểm tra lại bằng:

```powershell
git branch --contains d30b9d353198fbeed8fb9a749c336b03b6e7c055
```

Tên branch `backup/pre-refactor-d30b9d3` là tên gợi ý. Có thể thay phần
`pre-refactor` bằng tên đợt thay đổi, ví dụ `backup/before-document-engine`.

### Vì sao dùng branch thay vì chỉ nhớ mã commit?

Mã commit đã đủ để Git tìm lại khi còn trong lịch sử, nhưng branch là một mốc
rõ ràng, dễ nhận biết và bảo vệ commit khỏi khả năng bị dọn bởi cơ chế garbage
collection khi lịch sử sau này bị viết lại. Branch này chỉ là backup **cục bộ**
cho đến khi chủ động push nó.

Không push branch backup khi chưa có yêu cầu. Nếu sau này muốn có thêm bản sao
trên remote, dùng lệnh sau một cách chủ động:

```powershell
git push origin backup/pre-refactor-d30b9d3
```

## 4. Bảo vệ cả phần việc chưa commit

Mốc baseline ở phần 3 không bao gồm phần việc hiện tại. Trước một refactor lớn,
chọn **một** trong hai cách dưới đây.

### Cách A — commit WIP vào nhánh backup riêng (khuyến nghị khi code đã nhất quán)

```powershell
git switch -c backup/wip-before-refactor-YYYYMMDD
git add -A
git commit -m "backup: WIP before <ten-refactor>"
```

Commit này chỉ nằm trên máy cho đến khi có lệnh `git push`. Nó tạo một mốc đầy
đủ cho cả tracked và untracked files. Chỉ dùng `git add -A` sau khi đã xem kỹ:

```powershell
git status --short
git diff --stat
```

Không đưa secrets, file dung lượng lớn không cần thiết, output build hoặc dữ
liệu khách hàng vào commit WIP.

### Cách B — tạo snapshot ngoài Git (khi chưa muốn commit)

1. Đóng ứng dụng để tránh file dữ liệu thay đổi trong lúc sao chép.
2. Sao chép toàn bộ thư mục `mingo_assistant` sang thư mục cùng cấp có gắn ngày,
   ví dụ `mingo_assistant_snapshot_20261016`.
3. Xác nhận thư mục snapshot có `.git`, `src`, `tests`, `TemplatesBefore` và
   các file untracked cần giữ.
4. Không ghi đè workspace gốc; snapshot chỉ để khôi phục khi cần.

Snapshot ngoài Git tốn dung lượng hơn nhưng không phụ thuộc vào staging và giữ
được cả mọi file chưa theo dõi.

## 5. Cách xem lại baseline mà không phá workspace hiện tại

Do workspace có thay đổi chưa commit, không nên chạy `git switch d30b9d3` trực
tiếp. Cách an toàn nhất là tạo worktree riêng:

```powershell
git worktree add ..\mingo_assistant_baseline_d30b9d3 d30b9d353198fbeed8fb9a749c336b03b6e7c055
```

Lệnh này tạo một thư mục khác chứa đúng code ở baseline để so sánh, build hoặc
chạy test. Workspace đang làm không bị thay đổi.

Khi không cần bản xem riêng nữa và đã chắc chắn không có thay đổi trong nó:

```powershell
git worktree remove ..\mingo_assistant_baseline_d30b9d3
```

Lệnh `remove` ở trên xóa thư mục worktree được tạo bởi chính lệnh `add`; kiểm
tra đúng đường dẫn trước khi chạy.

## 6. Khôi phục sau khi refactor thất bại

### Tình huống 1 — chỉ cần lấy lại một hoặc vài file

Đây là cách ưu tiên vì phạm vi hẹp:

```powershell
git restore --source backup/pre-refactor-d30b9d3 -- src/mingo_assistant/services/documents/docx_generator.py
```

Sau đó xem diff, chạy test liên quan rồi commit phần khôi phục nếu quyết định
giữ lại.

### Tình huống 2 — muốn thử lại toàn bộ baseline trên nhánh mới

```powershell
git switch -c recovery/from-d30b9d3 backup/pre-refactor-d30b9d3
```

Cách này không xóa nhánh đang refactor. Nó mở một nhánh recovery mới, đúng tại
baseline, để kiểm tra hoặc tiếp tục phát triển theo hướng khác.

### Tình huống 3 — thật sự muốn bỏ toàn bộ refactor và đưa nhánh về baseline

Đây là thao tác phá hủy thay đổi tracked chưa commit trên nhánh hiện tại. Chỉ
thực hiện sau khi đã tạo backup WIP/snapshot và xác nhận lại branch mục tiêu:

```powershell
git status --short
git branch --show-current
git reset --hard backup/pre-refactor-d30b9d3
```

`git reset --hard` không xóa untracked files, nhưng xóa thay đổi chưa commit ở
những file Git đang theo dõi. Không chạy `git clean -fd` như một phần của quy
trình khôi phục trừ khi đã lập danh sách chính xác các file được phép xóa.

Nếu nhánh đã bị push với commit refactor, không force-push ngay. Tạo branch
recovery trước, kiểm tra test, rồi quyết định dùng pull request/revert hay
phương án phát hành phù hợp.

## 7. Quy trình ngắn dùng trước mỗi refactor lớn

```text
1. git status --short
2. Tạo backup/pre-refactor-<short-sha> trỏ về baseline commit.
3. Bảo vệ working tree hiện có bằng WIP commit hoặc snapshot thư mục.
4. Tạo nhánh làm việc cho refactor.
5. Refactor theo từng phần nhỏ, test sau mỗi phần.
6. Nếu lỗi: restore file hẹp trước; chỉ reset hard khi đã có bản backup.
```

## 8. Các lệnh kiểm tra chỉ đọc

```powershell
git log -1 --format="%H%n%h%n%an%n%ad%n%s" --date=iso-strict
git status --short
git branch -vv
git show --no-patch --decorate d30b9d353198fbeed8fb9a749c336b03b6e7c055
```

## 9. Nguyên tắc cho repository này

- Không commit hoặc push tự động; chỉ thực hiện khi người dùng yêu cầu rõ.
- Không dùng `reset --hard`, `clean`, hoặc force-push để "dọn" workspace.
- Không coi template, dữ liệu hồ sơ, thư mục tài nguyên hoặc kết quả QA là rác
  chỉ vì chúng chưa được Git theo dõi; xác định vai trò trước khi xoá/commit.
- Khi backup nhằm bảo vệ template Word và workflow riêng, ưu tiên snapshot hoặc
  WIP commit đầy đủ, vì các tài nguyên đó có thể nằm ngoài danh sách file
  tracked ở baseline.

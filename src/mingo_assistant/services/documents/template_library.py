"""Original form copies, independent of dossier generation."""
from pathlib import Path
import shutil
import tempfile

class TemplateLibraryFiles:
    def __init__(self, bundle_root: Path, filenames: dict[str, str], group: str = "dkdn"):
        if group not in {"dkdn", "tax"}:
            raise ValueError("Nhóm biểu mẫu không hợp lệ.")
        self.root = bundle_root / "assets/templates/library" / group
        self.filenames = dict(filenames)

    def source(self, template_id: str) -> Path:
        if template_id not in self.filenames:
            raise ValueError("Biểu mẫu này chưa hỗ trợ xem trước hoặc tải xuống.")
        path = self.root / self.filenames[template_id]
        if not path.is_file():
            raise FileNotFoundError("Không tìm thấy file biểu mẫu trong tài nguyên ứng dụng.")
        return path

    def preview_copy(self, template_id: str) -> Path:
        source = self.source(template_id)
        # The viewer may keep the document open after this page/app closes.
        # Leave its isolated copy in the OS temp folder, never open the source.
        target = Path(tempfile.mkdtemp(prefix="min-template-preview-")) / source.name
        shutil.copyfile(source, target)
        target.chmod(0o444)
        return target

    def download(self, template_id: str, destination: Path) -> None:
        source = self.source(template_id)
        if destination.resolve() == source.resolve():
            raise ValueError("Vui lòng chọn nơi lưu khác với file mẫu của ứng dụng.")
        shutil.copyfile(source, destination)

"""Move displayed exported files and commit their new paths, without settings changes."""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from collections.abc import Callable, Sequence

from mingo_assistant.services.documents.open_document_closer import close_open_documents


def move_exported_dossier(
    files: Sequence[Path], destination: Path, folder_name: str, commit: Callable[[Path], None],
) -> Path:
    """Relocate exactly these files; roll back if moving or path persistence fails."""
    sources = [Path(path) for path in files]
    if not sources:
        raise ValueError("Phiên bản đang chọn chưa có file để chuyển.")
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(f"File hồ sơ không còn tồn tại:\n{source}")
    if len({source.name.casefold() for source in sources}) != len(sources):
        raise ValueError("Có file trùng tên trong phiên bản này. Chưa chuyển để tránh mất file.")
    if not destination.is_dir():
        raise NotADirectoryError(f"Thư mục đích không tồn tại:\n{destination}")
    close_open_documents(sources)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", folder_name).strip(" .")[:100].rstrip(" .") or "Ho so"
    index = 1
    while True:
        target = destination / (name if index == 1 else f"{name} ({index})")
        try:
            target.mkdir()
            break
        except FileExistsError:
            index += 1
    attempted: list[tuple[Path, Path, bool]] = []
    try:
        for source in sources:
            moved = target / source.name
            attempted.append((source, moved, False))
            shutil.move(str(source), str(moved))
            attempted[-1] = (source, moved, True)
        commit(target)
    except Exception as error:
        failures = []
        for source, moved, complete in reversed(attempted):
            if not moved.exists():
                continue
            try:
                if source.exists():
                    if complete:
                        raise OSError(f"Đường dẫn gốc đã có file khác: {source}")
                    # A cross-volume copy failed before deleting its source.
                    moved.unlink()
                else:
                    shutil.move(str(moved), str(source))
            except OSError as rollback_error:
                failures.append(str(rollback_error))
        try:
            target.rmdir()  # Only our newly created, empty folder is removable.
        except OSError:
            pass
        if failures:
            raise OSError(
                f"Chuyển hồ sơ thất bại: {error}\nMột số file chưa đưa lại được về chỗ cũ. "
                f"Không xóa file còn tại:\n{target}\n" + "\n".join(failures)
            ) from error
        raise
    return target

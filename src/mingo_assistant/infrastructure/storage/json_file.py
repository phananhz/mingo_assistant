"""Small, reusable JSON persistence primitives.

All writes use a sibling temporary file followed by ``os.replace`` so a normal
application interruption cannot leave a partially-written JSON file in place.
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from mingo_assistant.core.errors import CorruptDataError, FileSystemError


def read_json(path: Path) -> Any:
    """Read a UTF-8 JSON document, preserving the standard JSON exceptions."""
    return json.loads(path.read_text(encoding="utf-8"))


def preserve_corrupt_file(path: Path) -> Path:
    """Copy a malformed file beside itself without deleting or replacing it."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = path.with_name(f"{path.name}.corrupt-{stamp}.bak")
    try:
        shutil.copy2(path, backup_path)
    except OSError as exc:
        raise FileSystemError(path, "Không thể tạo bản sao phục hồi dữ liệu lỗi") from exc
    return backup_path


def read_json_with_recovery(path: Path) -> Any:
    """Read JSON and preserve malformed content before raising a typed error."""
    try:
        return read_json(path)
    except json.JSONDecodeError as exc:
        backup_path = preserve_corrupt_file(path)
        raise CorruptDataError(path, "Tệp JSON bị hỏng", backup_path) from exc
    except OSError as exc:
        raise FileSystemError(path, "Không thể đọc tệp dữ liệu") from exc


def write_json_atomic(path: Path, payload: Any) -> None:
    """Write a UTF-8 JSON document without exposing a partially-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(payload, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    except OSError as exc:
        raise FileSystemError(path, "Không thể ghi tệp dữ liệu") from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass

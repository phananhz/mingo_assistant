from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QLockFile


class SingleInstanceGuard:
    """Local per-user process lock backed by Qt's stale-lock handling."""

    def __init__(self, lock_path: Path) -> None:
        self.lock_path = lock_path
        self._lock = QLockFile(str(lock_path))
        self._acquired = False

    def acquire(self) -> bool:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._acquired = self._lock.tryLock(0)
        return self._acquired

    def release(self) -> None:
        if self._acquired:
            self._lock.unlock()
            self._acquired = False


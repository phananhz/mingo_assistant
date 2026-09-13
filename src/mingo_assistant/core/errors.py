from __future__ import annotations

from pathlib import Path


class MinAssistantError(Exception):
    """Base class for expected application errors."""


class DataError(MinAssistantError):
    """Base class for persistence and migration failures."""


class RecoverableError(MinAssistantError):
    """An expected failure where user data remains available for recovery."""


class FileSystemError(DataError):
    def __init__(self, path: Path, message: str) -> None:
        self.path = path
        super().__init__(f"{message}: {path}")


class ConfigurationError(MinAssistantError):
    """Invalid application or bundled-resource configuration."""


class CorruptDataError(DataError):
    def __init__(self, path: Path, message: str, backup_path: Path | None = None) -> None:
        self.path = path
        self.backup_path = backup_path
        super().__init__(f"{message}: {path}")

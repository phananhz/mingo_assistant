"""Local persistence adapters."""

from .json_file import preserve_corrupt_file, read_json, read_json_with_recovery, write_json_atomic

__all__ = ("preserve_corrupt_file", "read_json", "read_json_with_recovery", "write_json_atomic")

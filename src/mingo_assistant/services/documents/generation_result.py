from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GeneratedDocument:
    """A generated document and the source template used to create it."""

    source_name: str
    output_path: Path


@dataclass(frozen=True)
class GenerationResult:
    """Summary of a document-generation run."""

    output_dir: Path
    generated: list[GeneratedDocument]
    skipped: list[str]
    unresolved: dict[str, list[str]]

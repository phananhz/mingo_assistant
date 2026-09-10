"""Data models used by business-registration workflows."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OcrPerson:
    name: str
    role: str = "member"
    front_path: str = ""
    back_path: str = ""
    data: dict[str, str] = field(default_factory=dict)
    recognition_type: str = ""
    raw_text: str = ""
    organization_data: dict[str, str] = field(default_factory=dict)
    organization_extraction_method: str = ""

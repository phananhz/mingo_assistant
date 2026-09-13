from __future__ import annotations

from pathlib import Path
import unicodedata
from typing import Mapping


class BusinessRegistrationTemplateRepository:
    """Selects the existing dossier templates without rendering them."""

    PERSONAL_CHARTER_TEMPLATE = "2. Điều lệ.docx"
    ORGANIZATION_CHARTER_TEMPLATE = "2. Dieu le_CSH la to chuc.docx"

    def __init__(self, template_dir: Path) -> None:
        self.template_dir = template_dir

    def selected(self, values: Mapping[str, str]) -> list[Path]:
        owner_is_organization = self._fold(str(values.get("owner_type", "") or "")) == "to chuc"
        selected: list[Path] = []
        for template in sorted(self.template_dir.iterdir()):
            if template.name.startswith("~$"):
                continue
            if template.name == self.PERSONAL_CHARTER_TEMPLATE and owner_is_organization:
                continue
            if template.name == self.ORGANIZATION_CHARTER_TEMPLATE and not owner_is_organization:
                continue
            selected.append(template)
        return selected

    @staticmethod
    def _fold(value: str) -> str:
        normalized = unicodedata.normalize("NFD", value.lower().replace("đ", "d"))
        return "".join(character for character in normalized if unicodedata.category(character) != "Mn")


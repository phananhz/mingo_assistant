from __future__ import annotations

import json
from pathlib import Path


class TemplateManifest:
    """Loads a template manifest once and exposes type-safe dictionary views."""

    def __init__(self, manifest_path: Path) -> None:
        self.manifest_path = manifest_path
        self._cache: dict[str, object] | None = None

    def load(self) -> dict[str, object]:
        if self._cache is not None:
            return self._cache
        if not self.manifest_path.exists():
            self._cache = {}
            return self._cache
        with self.manifest_path.open("r", encoding="utf-8-sig") as file:
            loaded = json.load(file)
        self._cache = loaded if isinstance(loaded, dict) else {}
        return self._cache

    def template(self, template_name: str) -> dict[str, object]:
        templates = self.load().get("templates", {})
        if not isinstance(templates, dict):
            return {}
        config = templates.get(template_name, {})
        return config if isinstance(config, dict) else {}

    def part(self, template_name: str, part_name: str) -> dict[str, object]:
        part = self.template(template_name).get(part_name, {})
        return part if isinstance(part, dict) else {}


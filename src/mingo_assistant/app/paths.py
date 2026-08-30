from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path


APP_NAME = "Mingo Assistant"


@dataclass
class AppPaths:
    """Paths that work both from source and from a frozen PyInstaller app."""

    bundle_root: Path
    user_data_root: Path
    documents_root: Path

    @property
    def settings_file(self) -> Path:
        return self.user_data_root / "settings.json"

    @property
    def cases_file(self) -> Path:
        return self.user_data_root / "cases.json"

    @property
    def authorized_person_file(self) -> Path:
        return self.user_data_root / "authorized_person.json"

    @property
    def template_dir(self) -> Path:
        return self.bundle_root / "assets" / "templates" / "word" / "business_registration"

    def ensure_user_dirs(self) -> None:
        self.user_data_root.mkdir(parents=True, exist_ok=True)
        self.documents_root.mkdir(parents=True, exist_ok=True)


def get_app_paths() -> AppPaths:
    project_root = Path(__file__).resolve().parents[3]
    if getattr(sys, "frozen", False):
        bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        bundle_root = project_root

    app_data = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    user_data_root = app_data / APP_NAME
    documents_root = Path.home() / "Documents" / APP_NAME
    return AppPaths(bundle_root=bundle_root, user_data_root=user_data_root, documents_root=documents_root)


def load_settings(paths: AppPaths) -> dict[str, str]:
    if not paths.settings_file.exists():
        return {}
    try:
        raw = json.loads(paths.settings_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {str(key): str(value) for key, value in raw.items()} if isinstance(raw, dict) else {}


def save_settings(paths: AppPaths, values: dict[str, str]) -> None:
    paths.ensure_user_dirs()
    current = load_settings(paths)
    current.update({str(key): str(value) for key, value in values.items()})
    paths.settings_file.write_text(
        json.dumps(current, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

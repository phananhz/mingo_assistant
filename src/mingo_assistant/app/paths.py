from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from mingo_assistant.infrastructure.storage import read_json, write_json_atomic


APP_NAME = "Min Assistant"
LEGACY_APP_NAME = "Mingo Assistant"


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
    def authorized_person_defaults_file(self) -> Path:
        return self.bundle_root / 'assets' / 'defaults' / 'authorized_person_profiles.json'

    @property
    def personal_profiles_file(self) -> Path:
        return self.user_data_root / "personal_profiles.json"

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
    legacy_user_data_root = app_data / LEGACY_APP_NAME
    # Preserve existing local cases and settings when upgrading from the former
    # Mingo Assistant brand. The copy runs once, only when the new folder has
    # not been created yet.
    if not user_data_root.exists() and legacy_user_data_root.exists():
        try:
            shutil.copytree(legacy_user_data_root, user_data_root)
        except OSError:
            pass
    documents_root = Path.home() / "Documents" / APP_NAME
    return AppPaths(bundle_root=bundle_root, user_data_root=user_data_root, documents_root=documents_root)


def load_settings(paths: AppPaths) -> dict[str, str]:
    if not paths.settings_file.exists():
        return {}
    try:
        raw = read_json(paths.settings_file)
    except (OSError, json.JSONDecodeError):
        return {}
    return {str(key): str(value) for key, value in raw.items()} if isinstance(raw, dict) else {}


def save_settings(paths: AppPaths, values: dict[str, str]) -> None:
    paths.ensure_user_dirs()
    current = load_settings(paths)
    current.update({str(key): str(value) for key, value in values.items()})
    write_json_atomic(paths.settings_file, current)

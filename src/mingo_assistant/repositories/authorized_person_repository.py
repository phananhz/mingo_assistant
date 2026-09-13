from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from mingo_assistant.core.errors import CorruptDataError
from mingo_assistant.infrastructure.storage import read_json, read_json_with_recovery, write_json_atomic


class AuthorizedPersonProfileRepository:
    """Merge bundled fixed profiles with editable profiles stored on this machine."""

    SCHEMA_VERSION = 1

    def __init__(self, data_file: Path, defaults_file: Path) -> None:
        self.data_file = data_file
        self.defaults_file = defaults_file
        self.last_recovery_error: CorruptDataError | None = None

    def load(self) -> dict[str, object]:
        selected_profile_id = ""
        saved_profiles: list[dict[str, str]] = []

        if self.last_recovery_error is not None:
            return self.merge("", [])
        if self.data_file.exists():
            try:
                raw = read_json_with_recovery(self.data_file)
            except CorruptDataError as exc:
                self.last_recovery_error = exc
                raw = {}
            if isinstance(raw, dict) and isinstance(raw.get("profiles"), list):
                selected_profile_id = str(raw.get("selected_profile_id", ""))
                saved_profiles = self._profile_list(raw["profiles"])
            elif isinstance(raw, dict) and any(str(key).startswith("authorized_person_") for key in raw):
                profile = {str(key): str(value) for key, value in raw.items()}
                profile.setdefault("id", str(uuid4()))
                selected_profile_id = profile["id"]
                saved_profiles = [profile]

        return self.merge(selected_profile_id, saved_profiles)

    def save(self, payload: dict[str, object]) -> None:
        write_json_atomic(
            self.data_file,
            {
                "schema_version": self.SCHEMA_VERSION,
                "selected_profile_id": str(payload.get("selected_profile_id", "")),
                "profiles": self._profile_list(payload.get("profiles", [])),
            },
        )

    def default_profiles(self) -> list[dict[str, str]]:
        try:
            raw = read_json(self.defaults_file)
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(raw, dict):
            return []
        return self._profile_list(raw.get("profiles", []))

    def is_default(self, profile_id: str) -> bool:
        return any(profile_id == profile.get("id", "") for profile in self.default_profiles())

    def merge(self, selected_profile_id: str, profiles: list[dict[str, str]]) -> dict[str, object]:
        default_profiles = self.default_profiles()
        saved_profiles = {str(profile.get("id", "")): dict(profile) for profile in profiles}
        for profile in default_profiles:
            saved_profiles.pop(profile["id"], None)
        merged_profiles = default_profiles + list(saved_profiles.values())
        if not self._find(merged_profiles, selected_profile_id):
            selected_profile_id = str(merged_profiles[0].get("id", "")) if merged_profiles else ""
        return {"selected_profile_id": selected_profile_id, "profiles": merged_profiles}

    @staticmethod
    def _find(profiles: list[dict[str, str]], profile_id: str) -> dict[str, str] | None:
        return next((profile for profile in profiles if str(profile.get("id", "")) == profile_id), None)

    @staticmethod
    def _profile_list(values: object) -> list[dict[str, str]]:
        if not isinstance(values, list):
            return []
        return [
            {str(key): str(value) for key, value in profile.items()}
            for profile in values
            if isinstance(profile, dict)
        ]

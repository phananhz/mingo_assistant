from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from mingo_assistant.core.errors import CorruptDataError
from mingo_assistant.core.text_normalization import normalize_authorized_person_values
from mingo_assistant.infrastructure.storage import read_json, read_json_with_recovery, write_json_atomic


class AuthorizedPersonProfileRepository:
    """Merge bundled fixed profiles with editable profiles stored on this machine."""

    SCHEMA_VERSION = 1

    def __init__(self, data_file: Path, defaults_file: Path, seed_file: Path | None = None) -> None:
        self.data_file = data_file
        self.defaults_file = defaults_file
        self.seed_file = seed_file or defaults_file.with_name("authorized_person_seed.json")
        self.last_recovery_error: CorruptDataError | None = None

    def load(self) -> dict[str, object]:
        selected_profile_id = ""
        saved_profiles: list[dict[str, str]] = []

        if self.last_recovery_error is not None:
            return self.merge("", [])
        if not self.data_file.exists() and self.seed_file.is_file():
            # Personal release resources initialize a new machine once. They
            # are editable local profiles, not immutable built-in defaults.
            seed = read_json(self.seed_file)
            if not isinstance(seed, dict) or not isinstance(seed.get("profiles"), list):
                raise ValueError("Tài nguyên profile người được ủy quyền không hợp lệ.")
            self.save(seed)
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
        saved_profiles = {
            str(profile.get("id", "")): normalize_authorized_person_values(profile)
            for profile in self._profile_list(profiles)
        }
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
    def _is_legacy_sample(profile: dict) -> bool:
        # Match the shipped placeholders narrowly. A real profile may still
        # have an old builtin ID; that alone must never hide the user's data.
        return any(
            profile.get("id") == f"builtin-authorized-person-{index}"
            and str(profile.get("authorized_person_full_name", "")).strip().upper()
            == f"NGƯỜI ỦY QUYỀN MẪU {index}"
            and profile.get("authorized_person_id_number") == "000000000000"
            for index in range(1, 4)
        )

    @staticmethod
    def _profile_list(values: object) -> list[dict[str, str]]:
        if not isinstance(values, list):
            return []
        return [
            normalize_authorized_person_values(profile)
            for profile in values
            if isinstance(profile, dict) and not AuthorizedPersonProfileRepository._is_legacy_sample(profile)
        ]

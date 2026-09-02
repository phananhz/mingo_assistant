from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from mingo_assistant.app.paths import get_app_paths


PERSONAL_PROFILE_FIELDS = (
    "legal_representative_full_name",
    "legal_representative_id_number",
    "legal_representative_date_of_birth",
    "legal_representative_gender",
    "legal_representative_nationality",
    "legal_representative_permanent_address",
    "legal_representative_issue_date",
    "legal_representative_expiry_date",
    "legal_representative_issue_place",
    "personal_phone",
    "personal_email",
)


class PersonalProfileRepository:
    """Persistent, QR-derived personal records for quick form completion."""

    def __init__(self, data_file: Path | None = None) -> None:
        self.data_file = data_file or get_app_paths().personal_profiles_file

    def list_profiles(self) -> list[dict[str, str]]:
        payload = self._read_payload()
        return [dict(profile) for profile in payload.get("profiles", []) if isinstance(profile, dict)]

    def upsert(self, values: dict[str, str]) -> dict[str, str]:
        profile = {key: str(values.get(key, "") or "").strip() for key in PERSONAL_PROFILE_FIELDS}
        if not profile["legal_representative_full_name"] or not profile["legal_representative_id_number"]:
            raise ValueError("Cần có họ tên và số CCCD để lưu dữ liệu cá nhân.")

        payload = self._read_payload()
        profiles = [dict(item) for item in payload.get("profiles", []) if isinstance(item, dict)]
        profile_id = ""
        for existing in profiles:
            if existing.get("legal_representative_id_number") == profile["legal_representative_id_number"]:
                profile_id = str(existing.get("id", ""))
                existing.update(profile)
                profile = existing
                break
        else:
            profile_id = str(uuid4())
            profile["id"] = profile_id
            profiles.append(profile)

        profile["id"] = profile_id
        self._write_payload({"profiles": profiles})
        return profile

    def _read_payload(self) -> dict[str, object]:
        if not self.data_file.exists():
            return {"profiles": []}
        try:
            loaded = json.loads(self.data_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"profiles": []}
        return loaded if isinstance(loaded, dict) else {"profiles": []}

    def _write_payload(self, payload: dict[str, object]) -> None:
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self.data_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
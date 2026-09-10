from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from mingo_assistant.app.paths import get_app_paths
from mingo_assistant.infrastructure.storage import read_json, write_json_atomic


PERSONAL_PROFILE_FIELDS = (
    "legal_representative_full_name",
    "legal_representative_id_number",
    "legal_representative_date_of_birth",
    "legal_representative_gender",
    "legal_representative_nationality",
    "legal_representative_ethnicity",
    "legal_representative_permanent_address",
    "legal_representative_issue_date",
    "legal_representative_expiry_date",
    "legal_representative_issue_place",
    "personal_phone",
    "personal_email",
)


ORGANIZATION_PROFILE_FIELDS = (
    "organization_owner_name",
    "organization_owner_registration_number",
    "organization_owner_issue_date",
    "organization_owner_issue_place",
    "organization_owner_address_detail",
    "organization_owner_ward",
    "organization_owner_province",
    "organization_owner_country",
    "organization_owner_phone",
    "organization_owner_fax",
    "organization_owner_email",
    "organization_owner_website",
)


class PersonalProfileRepository:
    """Persistent, QR-derived personal records for quick form completion."""

    def __init__(self, data_file: Path | None = None) -> None:
        self.data_file = data_file or get_app_paths().personal_profiles_file

    def list_profiles(self) -> list[dict[str, str]]:
        payload = self._read_payload()
        return [dict(profile) for profile in payload.get("profiles", []) if isinstance(profile, dict)]

    def list_organization_profiles(self) -> list[dict[str, str]]:
        payload = self._read_payload()
        return [
            dict(profile)
            for profile in payload.get("organization_profiles", [])
            if isinstance(profile, dict)
        ]

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
        payload["profiles"] = profiles
        self._write_payload(payload)
        return profile

    def upsert_organization(self, values: dict[str, str]) -> dict[str, str]:
        profile = {key: str(values.get(key, "") or "").strip() for key in ORGANIZATION_PROFILE_FIELDS}
        if not profile["organization_owner_name"] or not profile["organization_owner_registration_number"]:
            raise ValueError("Cần có tên tổ chức và mã số doanh nghiệp để lưu dữ liệu tổ chức.")

        payload = self._read_payload()
        profiles = [
            dict(item)
            for item in payload.get("organization_profiles", [])
            if isinstance(item, dict)
        ]
        profile_id = ""
        for existing in profiles:
            if existing.get("organization_owner_registration_number") == profile["organization_owner_registration_number"]:
                profile_id = str(existing.get("id", ""))
                existing.update(profile)
                profile = existing
                break
        else:
            profile_id = str(uuid4())
            profile["id"] = profile_id
            profiles.append(profile)

        profile["id"] = profile_id
        payload["organization_profiles"] = profiles
        self._write_payload(payload)
        return profile

    def _read_payload(self) -> dict[str, object]:
        if not self.data_file.exists():
            return {"profiles": []}
        try:
            loaded = read_json(self.data_file)
        except (OSError, json.JSONDecodeError):
            return {"profiles": []}
        return loaded if isinstance(loaded, dict) else {"profiles": []}

    def _write_payload(self, payload: dict[str, object]) -> None:
        write_json_atomic(self.data_file, payload)

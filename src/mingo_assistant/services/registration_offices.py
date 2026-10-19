from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


PROVINCE_NAME_UPDATES = {
    "Tỉnh Đồng Nai": "Thành phố Đồng Nai",
    "Tỉnh Quảng Ninh": "Thành phố Quảng Ninh",
    "Tỉnh Bắc Ninh": "Thành phố Bắc Ninh",
}

REGISTRATION_OFFICE_NAME_UPDATES = {
    "Phòng Đăng ký kinh doanh Tỉnh Đồng Nai": "Phòng Đăng ký kinh doanh thành phố Đồng Nai",
    "Phòng Quản lý doanh nghiệp Tỉnh Quảng Ninh": "Phòng Quản lý doanh nghiệp thành phố Quảng Ninh",
    "Phòng Đăng ký kinh doanh và Quản lý doanh nghiệp Tỉnh Bắc Ninh": "Phòng Quản lý doanh nghiệp thành phố Bắc Ninh",
}


def update_current_administrative_names(value: object) -> str:
    """Replace only the province names changed by the 2026 resolutions."""

    current = str(value or "")
    for old_name, new_name in PROVINCE_NAME_UPDATES.items():
        current = current.replace(old_name, new_name)
    return current


def update_registration_office_name(value: object) -> str:
    """Return the current office name while preserving unrelated/manual values."""

    current = " ".join(str(value or "").split())
    folded_current = current.casefold()
    for old_name, new_name in REGISTRATION_OFFICE_NAME_UPDATES.items():
        if folded_current == old_name.casefold():
            return new_name
    return current


def signing_place_for_province(value: object) -> str:
    """Format the signing place while retaining the two special city prefixes."""

    place = update_current_administrative_names(value).strip()
    if place.casefold() in {"thành phố hồ chí minh", "thành phố hà nội"}:
        return place
    return re.sub(r"^(?:Thành phố|Tỉnh)\s+", "", place, flags=re.IGNORECASE).strip()


def update_saved_signing_line(value: object) -> str:
    """Update only the leading place in an existing place/date display line."""

    current = update_current_administrative_names(value).strip()
    match = re.match(r"^([^,]+)(,.*)?$", current)
    if not match:
        return current
    place = signing_place_for_province(match.group(1))
    return f"{place}{match.group(2) or ''}"


def update_saved_registration_values(
    values: dict[str, str],
    *,
    update_office: bool = True,
) -> dict[str, str]:
    """Upgrade saved display values in memory when an existing case is opened."""

    updated: dict[str, str] = {}
    for key, value in values.items():
        normalized_key = str(key)
        if normalized_key == "business_registration_office":
            updated[normalized_key] = (
                update_registration_office_name(value)
                if update_office
                else str(value or "")
            )
            continue
        if normalized_key == "document_place":
            updated[normalized_key] = signing_place_for_province(value)
            continue
        if normalized_key == "document_place_date":
            updated[normalized_key] = update_saved_signing_line(value)
            continue
        updated[normalized_key] = update_current_administrative_names(value)
    return updated


@dataclass(frozen=True)
class RegistrationOffice:
    province: str
    office_name: str
    display_name: str
    address: str = ""
    reception_address: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""

    @classmethod
    def from_dict(cls, item: dict[str, object]) -> "RegistrationOffice":
        return cls(
            province=update_current_administrative_names(item.get("province", "")).strip(),
            office_name=str(item.get("office_name", "")).strip(),
            display_name=update_registration_office_name(item.get("display_name", "")),
            address=str(item.get("address", "")).strip(),
            reception_address=str(item.get("reception_address", "")).strip(),
            phone=str(item.get("phone", "")).strip(),
            email=str(item.get("email", "")).strip(),
            website=str(item.get("website", "")).strip(),
        )


@dataclass(frozen=True)
class RegistrationOfficeCatalog:
    source_path: Path | None
    offices: list[RegistrationOffice]
    source_title: str = "Danh sách Phòng đăng ký kinh doanh"
    source_url: str = ""

    @property
    def is_available(self) -> bool:
        return bool(self.offices)

    @classmethod
    def load_from_project(cls, project_root: Path) -> "RegistrationOfficeCatalog":
        candidates = [
            project_root / "assets" / "registration_offices" / "registration_offices_2025.json",
            project_root / "data" / "reference" / "registration_offices_2025.json",
        ]
        for candidate in candidates:
            if not candidate.exists():
                continue
            with candidate.open("r", encoding="utf-8-sig") as file:
                payload = json.load(file)
            return cls(
                source_path=candidate,
                offices=[
                    RegistrationOffice.from_dict(item)
                    for item in payload.get("items", []) or []
                    if isinstance(item, dict)
                ],
                source_title=str(payload.get("source_title") or cls.source_title),
                source_url=str(payload.get("source_url") or ""),
            )
        return cls(source_path=None, offices=[])

    def suggestions(self, query: str, limit: int = 8) -> list[str]:
        folded_query = self._fold(query)
        if not folded_query:
            return []
        matches = [office for office in self.offices if self._matches(office, folded_query)]
        matches.sort(key=lambda office: self._rank(office, folded_query))
        return [office.display_name for office in matches[:limit]]

    def province_for_office(self, office_name: str) -> str:
        folded_office = self._fold(update_registration_office_name(office_name))
        if not folded_office:
            return ""
        for office in self.offices:
            if folded_office in {self._fold(office.display_name), self._fold(office.office_name)}:
                return office.province
        return ""
    def display_name_for_province(self, province: str) -> str:
        folded_province = self._fold(province)
        if not folded_province:
            return ""
        for office in self.offices:
            if self._matches(office, folded_province):
                return office.display_name
        return ""

    def _matches(self, office: RegistrationOffice, folded_query: str) -> bool:
        return any(folded_query in value for value in self._search_values(office))

    def _rank(self, office: RegistrationOffice, folded_query: str) -> tuple[int, str]:
        values = self._search_values(office)
        if any(value == folded_query for value in values):
            return (0, office.province)
        if any(value.startswith(folded_query) for value in values):
            return (1, office.province)
        return (2, office.province)

    def _search_values(self, office: RegistrationOffice) -> list[str]:
        province_without_prefix = re.sub(
            r"^(tinh|thanh pho)\s+",
            "",
            self._fold(office.province),
        ).strip()
        values = {
            self._fold(office.province),
            province_without_prefix,
            self._fold(office.display_name),
            self._fold(office.office_name),
        }
        for old_name, current_name in PROVINCE_NAME_UPDATES.items():
            if self._fold(office.province) == self._fold(current_name):
                values.add(self._fold(old_name))
                values.add(self._fold(re.sub(r"^(?:Tỉnh|Thành phố)\s+", "", old_name)))
        if province_without_prefix == "ho chi minh":
            values.update({"tp hcm", "tphcm", "hcm", "sai gon", "sg"})
        if province_without_prefix == "da nang":
            values.add("danang")
        if province_without_prefix == "can tho":
            values.add("cantho")
        if province_without_prefix == "ha noi":
            values.add("hanoi")
        if province_without_prefix == "hai phong":
            values.add("haiphong")
        return [value for value in values if value]

    def _fold(self, value: str) -> str:
        text = value.strip().lower().replace("đ", "d")
        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return " ".join(text.split())

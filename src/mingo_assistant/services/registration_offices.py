from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


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
            province=str(item.get("province", "")).strip(),
            office_name=str(item.get("office_name", "")).strip(),
            display_name=str(item.get("display_name", "")).strip(),
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

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class PlaceCandidate:
    name: str
    normalized: str
    kind: str
    province_code: str = ""
    province_name: str = ""
    district_name: str = ""
    new_ward_name: str = ""
    new_province_name: str = ""


class AdministrativePlaceMatcher:
    """Normalize Vietnamese administrative place names from noisy OCR text."""

    def __init__(self, data_path: Path | None = None) -> None:
        self.data_path = data_path or self._default_data_path()
        data = self._load_data(str(self.data_path))
        self.province_candidates = self._province_candidates(data)
        self.ward_candidates = self._ward_candidates(data)
        self.district_candidates = self._district_candidates(data)
        self.old_mapping_candidates = self._old_mapping_candidates(data)

    def normalize_address(self, address: str) -> str:
        parts = [part.strip(" ,.;") for part in re.split(r"[,;]", address or "") if part.strip(" ,.;")]
        if not parts:
            return address
        merged = self._normalize_old_split_sequence(parts)
        if merged != parts:
            return ", ".join(self._dedupe_keep_order(merged))

        province = self._best_province(parts)
        district = self._best_district(parts)
        normalized_parts: list[str] = []
        for part in parts:
            normalized_parts.append(self._normalize_part(part, province=province, district=district))
        return ", ".join(self._dedupe_keep_order(normalized_parts))

    def _normalize_old_split_sequence(self, parts: list[str]) -> list[str]:
        province = self._best_province(parts)
        result: list[str] = []
        index = 0
        changed = False
        while index < len(parts):
            match, window = self._best_old_mapping_window(parts, index, province=province)
            if not match:
                result.append(parts[index])
                index += 1
                continue

            if match.new_ward_name:
                result.append(match.new_ward_name)
            if match.new_province_name:
                result.append(match.new_province_name)
            changed = True
            index += window
            while index < len(parts) and self._is_old_context_part(parts[index], match):
                index += 1
        return self._dedupe_keep_order(result) if changed else parts

    def _best_old_mapping_window(
        self,
        parts: list[str],
        index: int,
        *,
        province: PlaceCandidate | None,
    ) -> tuple[PlaceCandidate | None, int]:
        best: PlaceCandidate | None = None
        best_window = 0
        best_score = 0.0
        for window in (3, 2):
            if index + window > len(parts):
                continue
            value = " ".join(parts[index : index + window])
            candidates = self.old_mapping_candidates
            if province:
                scoped = [candidate for candidate in candidates if self._same_place(candidate.province_name, province.name)]
                if scoped:
                    candidates = scoped
            for candidate in candidates:
                score = self._candidate_score(self._fold(value), candidate.normalized)
                if score > best_score:
                    best = candidate
                    best_window = window
                    best_score = score
        if best and best_score >= 0.96:
            return best, best_window
        return None, 0

    def _is_old_context_part(self, part: str, match: PlaceCandidate) -> bool:
        folded = self._fold(part)
        if not folded:
            return True
        if folded.startswith(("tinh ", "thi xa ", "huyen ", "quan ", "tp ", "thanh pho ")):
            return True
        if self._best_match(part, self.province_candidates, threshold=0.82):
            return True
        if self._best_district_match(part, province=None, threshold=0.90):
            return True
        if match.district_name and self._candidate_score(folded, self._fold(match.district_name)) >= 0.88:
            return True
        if match.province_name and self._candidate_score(folded, self._fold(match.province_name)) >= 0.88:
            return True
        if match.new_province_name and self._candidate_score(folded, self._fold(match.new_province_name)) >= 0.88:
            return True
        return False

    def best_province_name(self, value: str) -> str:
        match = self._best_match(value, self.province_candidates, threshold=0.93)
        return match.name if match else ""

    def _normalize_part(self, part: str, *, province: PlaceCandidate | None, district: PlaceCandidate | None) -> str:
        folded = self._fold(part)
        if self._looks_like_province(folded):
            match = self._best_match(part, self.province_candidates, threshold=0.82)
            if match:
                return match.name
        if self._looks_like_ward(folded):
            match = self._best_ward_match(part, province=province, district=district)
            if match:
                return match.name
        if self._looks_like_district(folded):
            match = self._best_match(part, self.district_candidates, threshold=0.84)
            if match:
                return match.name
        match = self._best_match(part, self.province_candidates, threshold=0.93)
        if match:
            return match.name
        match = self._best_district_match(part, province=province, threshold=0.94)
        if match:
            return match.name
        if province or district:
            match = self._best_ward_match(part, province=province, district=district, threshold=0.96)
            if match:
                return match.name
        return self._clean_common_prefix_errors(part)

    def _best_province(self, parts: list[str]) -> PlaceCandidate | None:
        best: PlaceCandidate | None = None
        best_score = 0.0
        for part in parts:
            match = self._best_match(part, self.province_candidates, threshold=0.82)
            if not match:
                continue
            score = self._similarity(self._fold(part), match.normalized)
            if score > best_score:
                best = match
                best_score = score
        return best

    def _best_district(self, parts: list[str]) -> PlaceCandidate | None:
        best: PlaceCandidate | None = None
        best_score = 0.0
        for part in parts:
            threshold = 0.84 if self._looks_like_district(self._fold(part)) else 0.94
            match = self._best_district_match(part, province=self._best_province(parts), threshold=threshold)
            if not match:
                continue
            score = self._similarity(self._fold(part), match.normalized)
            if score > best_score:
                best = match
                best_score = score
        return best

    def _best_district_match(
        self,
        part: str,
        *,
        province: PlaceCandidate | None,
        threshold: float,
    ) -> PlaceCandidate | None:
        candidates = self.district_candidates
        if province:
            scoped = [
                candidate
                for candidate in candidates
                if self._same_place(candidate.province_name, province.name)
            ]
            if scoped:
                candidates = scoped
        return self._best_match(part, candidates, threshold=threshold)

    def _best_ward_match(
        self,
        part: str,
        *,
        province: PlaceCandidate | None,
        district: PlaceCandidate | None,
        threshold: float = 0.84,
    ) -> PlaceCandidate | None:
        candidates = self.ward_candidates
        if province:
            scoped = [
                candidate
                for candidate in candidates
                if candidate.province_code == province.province_code
                or self._same_place(candidate.province_name, province.name)
            ]
            if scoped:
                candidates = scoped
        if district:
            district_scoped = [
                candidate
                for candidate in candidates
                if candidate.district_name and self._same_place(candidate.district_name, district.name)
            ]
            if district_scoped:
                candidates = district_scoped
        return self._best_match(part, candidates, threshold=threshold)

    def _best_match(
        self,
        value: str,
        candidates: list[PlaceCandidate],
        *,
        threshold: float,
    ) -> PlaceCandidate | None:
        normalized = self._fold(value)
        if not normalized:
            return None
        best: PlaceCandidate | None = None
        best_score = 0.0
        for candidate in candidates:
            score = self._candidate_score(normalized, candidate.normalized)
            if score > best_score:
                best = candidate
                best_score = score
        return best if best and best_score >= threshold else None

    def _candidate_score(self, value: str, candidate: str) -> float:
        if value == candidate:
            return 1.0
        if value == self._strip_admin_prefix(candidate):
            return 0.98
        if self._strip_admin_prefix(value) == self._strip_admin_prefix(candidate):
            return 0.98
        return self._similarity(value, candidate)

    def _province_candidates(self, data: dict[str, object]) -> list[PlaceCandidate]:
        candidates: list[PlaceCandidate] = []
        for item in data.get("provinces", []):
            if not isinstance(item, dict):
                continue
            code = str(item.get("code", ""))
            name = str(item.get("name", ""))
            short_name = str(item.get("short_name", name))
            for alias in self._province_aliases(name, short_name):
                candidates.append(PlaceCandidate(name=name, normalized=self._fold(alias), kind="province", province_code=code))
        return self._unique_candidates(candidates)

    def _province_aliases(self, name: str, short_name: str) -> list[str]:
        aliases = {name, short_name, self._strip_display_prefix(name), self._strip_display_prefix(short_name)}
        folded = self._fold(name)
        if "ho chi minh" in folded:
            aliases.update({"TP Hồ Chí Minh", "TP. Hồ Chí Minh", "TP HCM", "TPHCM", "Hồ Chí Minh"})
        if "ha noi" in folded:
            aliases.update({"TP Hà Nội", "TP. Hà Nội", "Hà Nội"})
        return [alias for alias in aliases if alias]

    def _ward_candidates(self, data: dict[str, object]) -> list[PlaceCandidate]:
        province_by_code = {
            str(item.get("code", "")): str(item.get("name", ""))
            for item in data.get("provinces", [])
            if isinstance(item, dict)
        }
        candidates: list[PlaceCandidate] = []
        for item in data.get("wards", []):
            if not isinstance(item, dict):
                continue
            province_code = str(item.get("province_code", ""))
            name = str(item.get("name", ""))
            candidates.append(
                PlaceCandidate(
                    name=name,
                    normalized=self._fold(name),
                    kind="ward",
                    province_code=province_code,
                    province_name=province_by_code.get(province_code, ""),
                )
            )
        for item in data.get("ward_mappings", []):
            if not isinstance(item, dict):
                continue
            old_name = str(item.get("old_ward_name", ""))
            old_district = str(item.get("old_district_name", ""))
            old_province = str(item.get("old_province_name", ""))
            if old_name:
                candidates.append(
                    PlaceCandidate(
                        name=old_name,
                        normalized=self._fold(old_name),
                        kind="old_ward",
                        province_name=old_province,
                        district_name=old_district,
                    )
                )
        return self._unique_candidates(candidates)

    def _district_candidates(self, data: dict[str, object]) -> list[PlaceCandidate]:
        candidates: list[PlaceCandidate] = []
        for item in data.get("ward_mappings", []):
            if not isinstance(item, dict):
                continue
            name = str(item.get("old_district_name", ""))
            province_name = str(item.get("old_province_name", ""))
            if name:
                candidates.append(
                    PlaceCandidate(
                        name=name,
                        normalized=self._fold(name),
                        kind="old_district",
                        province_name=province_name,
                    )
                )
        return self._unique_candidates(candidates)

    def _old_mapping_candidates(self, data: dict[str, object]) -> list[PlaceCandidate]:
        candidates: list[PlaceCandidate] = []
        for item in data.get("ward_mappings", []):
            if not isinstance(item, dict):
                continue
            old_name = str(item.get("old_ward_name", ""))
            old_district = str(item.get("old_district_name", ""))
            old_province = str(item.get("old_province_name", ""))
            new_name = str(item.get("new_ward_name", ""))
            new_province = str(item.get("new_province_name", ""))
            if not old_name or not new_name:
                continue
            candidates.append(
                PlaceCandidate(
                    name=old_name,
                    normalized=self._fold(old_name),
                    kind="old_mapping",
                    province_name=old_province,
                    district_name=old_district,
                    new_ward_name=new_name,
                    new_province_name=new_province,
                )
            )
        return self._unique_candidates(candidates)

    def _unique_candidates(self, candidates: list[PlaceCandidate]) -> list[PlaceCandidate]:
        seen: set[tuple[str, str, str, str]] = set()
        result: list[PlaceCandidate] = []
        for candidate in candidates:
            key = (candidate.normalized, candidate.kind, candidate.province_name, candidate.district_name)
            if key in seen:
                continue
            seen.add(key)
            result.append(candidate)
        return result

    def _looks_like_province(self, folded: str) -> bool:
        return any(marker in folded for marker in ["tinh", "tp", "thanh pho", "tphcm", "ha noi", "ho chi minh"])

    def _looks_like_ward(self, folded: str) -> bool:
        return any(marker in folded for marker in ["phuong", "xa", "thi tran"])

    def _looks_like_district(self, folded: str) -> bool:
        return any(marker in folded for marker in ["quan", "huyen", "thi xa"]) or folded.startswith("tp ")

    def _clean_common_prefix_errors(self, value: str) -> str:
        replacements = {
            r"\bQuan\b": "Quận",
            r"\bQuân\b": "Quận",
            r"\bPhuong\b": "Phường",
            r"\bThanh pho\b": "Thành phố",
        }
        result = value
        for pattern, replacement in replacements.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

    def _same_place(self, left: str, right: str) -> bool:
        return self._strip_admin_prefix(self._fold(left)) == self._strip_admin_prefix(self._fold(right))

    def _strip_admin_prefix(self, value: str) -> str:
        prefixes = [
            "thanh pho ",
            "tinh ",
            "phuong ",
            "xa ",
            "thi tran ",
            "quan ",
            "huyen ",
            "thi xa ",
            "tp ",
        ]
        result = value
        for prefix in prefixes:
            if result.startswith(prefix):
                result = result[len(prefix) :]
                break
        return result

    def _strip_display_prefix(self, value: str) -> str:
        return re.sub(r"^(Thành phố|Tỉnh)\s+", "", value).strip()

    def _similarity(self, left: str, right: str) -> float:
        return SequenceMatcher(None, left, right).ratio()

    def _dedupe_keep_order(self, parts: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for part in parts:
            key = self._fold(part)
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(part)
        return result

    def _fold(self, value: str) -> str:
        value = value.replace(chr(273), "d").replace(chr(272), "D")
        text = unicodedata.normalize("NFD", value.strip().lower())
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return " ".join(text.split())

    def _default_data_path(self) -> Path:
        return Path(__file__).resolve().parents[4] / "assets" / "administrative_places" / "vietnam_admin_2025.json"

    @staticmethod
    @lru_cache(maxsize=4)
    def _load_data(path: str) -> dict[str, object]:
        with Path(path).open("r", encoding="utf-8") as file:
            return json.load(file)

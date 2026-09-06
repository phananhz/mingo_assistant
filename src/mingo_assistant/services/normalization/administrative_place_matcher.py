from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

from mingo_assistant.app.paths import get_app_paths


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


@dataclass(frozen=True)
class AddressNormalization:
    raw_address: str
    normalized_address: str
    status: str
    message: str = ""

    @property
    def needs_confirmation(self) -> bool:
        return self.status == "needs_confirmation"


class AdministrativePlaceMatcher:
    """Normalize Vietnamese administrative place names from noisy OCR text."""

    def __init__(self, data_path: Path | None = None) -> None:
        self.data_path = data_path or self._default_data_path()
        data = self._load_data(str(self.data_path))
        self.province_candidates = self._province_candidates(data)
        self.province_by_normalized = self._index_candidates(self.province_candidates)
        self.ward_candidates = self._ward_candidates(data)
        self.current_ward_candidates = [
            candidate
            for candidate in self.ward_candidates
            if candidate.kind == "ward" and self._looks_like_ward(candidate.normalized)
        ]
        self.district_candidates = self._district_candidates(data)
        self.old_mapping_candidates = self._old_mapping_candidates(data)
        self.current_ward_by_normalized = self._index_candidates(self.current_ward_candidates)
        self.current_ward_by_short_name = self._index_candidates_by_short_name(self.current_ward_candidates)
        self.district_by_normalized = self._index_candidates(self.district_candidates)
        self.district_by_short_name = self._index_candidates_by_short_name(self.district_candidates)
        self.old_mapping_by_normalized = self._index_candidates(self.old_mapping_candidates)
        self.old_mapping_by_short_name = self._index_candidates_by_short_name(self.old_mapping_candidates)

    def normalize_address(self, address: str) -> str:
        return self.analyze_address(address).normalized_address

    def analyze_address(self, address: str) -> AddressNormalization:
        """Resolve an address from province inward without discarding raw CCCD data."""
        raw_address = re.sub(r"\s+", " ", address or "").strip(" ,;")
        repaired_address = self._repair_ocr_administrative_boundaries(raw_address)
        parts = self._split_address_parts(repaired_address)
        if not parts:
            return AddressNormalization("", "", "needs_confirmation", "Ch\u01b0a c\u00f3 \u0111\u1ecba ch\u1ec9 \u0111\u1ec3 \u0111\u1ed1i chi\u1ebfu.")

        province = self._terminal_province(parts[-1])
        if not province:
            return AddressNormalization(
                raw_address,
                raw_address,
                "needs_confirmation",
                "Kh\u00f4ng x\u00e1c \u0111\u1ecbnh \u0111\u01b0\u1ee3c t\u1ec9nh/th\u00e0nh ph\u1ed1 \u1edf cu\u1ed1i \u0111\u1ecba ch\u1ec9 CCCD.",
            )

        mappings = self._exact_legacy_mapping_matches(parts, province)
        resolved_outputs = {
            (candidate.new_ward_name, candidate.new_province_name or province.name)
            for candidate, _ward_index, _district_index in mappings
        }
        if len(resolved_outputs) == 1:
            candidate, ward_index, district_index = mappings[0]
            administrative_indexes = {ward_index, district_index, len(parts) - 1}
            detail_parts = [
                part for index, part in enumerate(parts) if index not in administrative_indexes
            ]
            normalized_parts = self._dedupe_keep_order(
                [*detail_parts, candidate.new_ward_name, candidate.new_province_name or province.name]
            )
            return AddressNormalization(
                raw_address,
                ", ".join(normalized_parts),
                "converted",
                "\u0110\u00e3 chuy\u1ec3n \u0111\u1ed5i t\u1eeb \u0111\u01a1n v\u1ecb h\u00e0nh ch\u00ednh c\u0169.",
            )
        if len(resolved_outputs) > 1:
            return AddressNormalization(
                raw_address,
                raw_address,
                "needs_confirmation",
                "\u0110\u1ecba ch\u1ec9 c\u0169 c\u00f3 nhi\u1ec1u k\u1ebft qu\u1ea3 chuy\u1ec3n \u0111\u1ed5i trong c\u00f9ng t\u1ec9nh/th\u00e0nh ph\u1ed1.",
            )

        current_ward = self._exact_current_ward(parts[-2], province) if len(parts) >= 2 else None
        if current_ward:
            normalized_parts = self._dedupe_keep_order(
                [*parts[:-2], current_ward.name, province.name]
            )
            return AddressNormalization(
                raw_address,
                ", ".join(normalized_parts),
                "current",
                "\u0110\u1ecba ch\u1ec9 CCCD \u0111\u00e3 theo ch\u00ednh quy\u1ec1n hai c\u1ea5p.",
            )

        return AddressNormalization(
            raw_address,
            raw_address,
            "needs_confirmation",
            "Ch\u01b0a \u0111\u1ee7 ng\u1eef c\u1ea3nh \u0111\u1ec3 chuy\u1ec3n \u0111\u1ed5i \u0111\u1ecba ch\u1ec9 h\u00e0nh ch\u00ednh an to\u00e0n.",
        )

    @staticmethod
    def _split_address_parts(address: str) -> list[str]:
        return [part.strip(" ,.;") for part in re.split(r"[,;\r\n]+", address) if part.strip(" ,.;")]

    @staticmethod
    def _index_candidates(candidates: list[PlaceCandidate]) -> dict[str, list[PlaceCandidate]]:
        indexed: dict[str, list[PlaceCandidate]] = {}
        for candidate in candidates:
            indexed.setdefault(candidate.normalized, []).append(candidate)
        return indexed

    def _index_candidates_by_short_name(
        self, candidates: list[PlaceCandidate]
    ) -> dict[str, list[PlaceCandidate]]:
        indexed: dict[str, list[PlaceCandidate]] = {}
        for candidate in candidates:
            indexed.setdefault(self._strip_admin_prefix(candidate.normalized), []).append(candidate)
        return indexed

    def _exact_province(self, value: str) -> PlaceCandidate | None:
        folded = self._fold(value)
        candidates = self.province_by_normalized.get(folded)
        if candidates is None:
            candidates = self.province_by_normalized.get(self._strip_admin_prefix(folded))
        if not candidates:
            return None
        unique_codes = {candidate.province_code for candidate in candidates}
        return candidates[0] if len(unique_codes) == 1 else None

    def _terminal_province(self, value: str) -> PlaceCandidate | None:
        exact = self._exact_province(value)
        if exact:
            return exact
        # This is deliberately limited to the terminal province token.  A high
        # threshold repairs minor OCR errors without using an unscoped district.
        return self._best_match(value, self.province_candidates, threshold=0.92)

    def _exact_legacy_mapping_matches(
        self, parts: list[str], province: PlaceCandidate
    ) -> list[tuple[PlaceCandidate, int, int]]:
        matches: list[tuple[PlaceCandidate, int, int]] = []
        seen: set[tuple[str, str, str, int, int]] = set()
        for ward_index, part in enumerate(parts[:-1]):
            folded = self._fold(part)
            candidates = self.old_mapping_by_normalized.get(folded)
            if candidates is None:
                candidates = self.old_mapping_by_short_name.get(self._strip_admin_prefix(folded))
            if not candidates:
                continue
            for candidate in candidates:
                if not candidate.district_name or not self._same_place(candidate.province_name, province.name):
                    continue
                for district_index in (ward_index - 1, ward_index + 1):
                    if not 0 <= district_index < len(parts) - 1:
                        continue
                    if not self._same_place(parts[district_index], candidate.district_name):
                        continue
                    key = (
                        candidate.new_ward_name,
                        candidate.new_province_name,
                        candidate.district_name,
                        ward_index,
                        district_index,
                    )
                    if key not in seen:
                        seen.add(key)
                        matches.append((candidate, ward_index, district_index))
        return matches

    def _canonicalize_current_two_tier_tail(self, parts: list[str]) -> list[str]:
        """Keep an already-current ward/province pair out of legacy conversion."""
        if len(parts) < 2:
            return parts

        province_candidates = self.province_by_normalized.get(self._fold(parts[-1]))
        if not province_candidates:
            return parts
        province = province_candidates[0]
        if (
            self._has_explicit_legacy_district_label(parts[:-1])
            or self._has_mapped_legacy_district_context(parts, province)
        ):
            return parts

        ward = self._exact_current_ward(parts[-2], province)
        if not ward:
            return parts
        return self._dedupe_keep_order([*parts[:-2], ward.name, province.name])

    def _has_explicit_legacy_district_label(self, parts: list[str]) -> bool:
        return any(self._looks_like_district(self._fold(part)) for part in parts)

    def _has_mapped_legacy_district_context(
        self, parts: list[str], province: PlaceCandidate
    ) -> bool:
        """Detect an old ward only when its following district corroborates it."""
        for index in range(len(parts) - 2):
            folded = self._fold(parts[index])
            candidates = self.old_mapping_by_normalized.get(folded)
            if candidates is None:
                candidates = self.old_mapping_by_short_name.get(
                    self._strip_admin_prefix(folded)
                )
            if not candidates:
                continue
            for candidate in candidates:
                if not candidate.district_name:
                    continue
                if not self._same_place(candidate.province_name, province.name):
                    continue
                if self._same_place(parts[index + 1], candidate.district_name):
                    return True
        return False

    def _exact_current_ward(
        self, part: str, province: PlaceCandidate
    ) -> PlaceCandidate | None:
        folded = self._fold(part)
        candidates = self.current_ward_by_normalized.get(folded)
        if candidates is None:
            candidates = self.current_ward_by_short_name.get(self._strip_admin_prefix(folded))
        if not candidates:
            return None
        short_name = self._strip_admin_prefix(folded)
        matches = [
            candidate
            for candidate in candidates
            if (
                candidate.province_code == province.province_code
                or self._same_place(candidate.province_name, province.name)
            )
            and (
                folded == candidate.normalized
                or short_name == self._strip_admin_prefix(candidate.normalized)
            )
        ]
        return matches[0] if len(matches) == 1 else None

    def _repair_ocr_administrative_boundaries(self, address: str) -> str:
        """Split common Vietnamese administrative labels that OCR joins together."""
        repaired = address or ""
        repaired = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", repaired)
        repaired = re.sub(r"(?i)\bp\.?\s*(\d+)\b", r"Phường \1", repaired)
        repaired = re.sub(r"(?i)\bph(?:uong|ng)\s*(\d+)\b", r"Phường \1", repaired)
        repaired = re.sub(r"(?i)\bq\.?\s*(\d+)\b", r"Quận \1", repaired)
        repaired = re.sub(r"(?i)\bq(?:uan|un)\b\s*", "Quận ", repaired)
        repaired = re.sub(r"(?i)\bthanh\s*ph(?:o|h)?\b\s*", "Thành phố ", repaired)
        repaired = re.sub(
            r"(?i)(Phường\s+\d+)\s*[.\-]?\s*(Quận\b)",
            r"\1, \2",
            repaired,
        )
        repaired = re.sub(
            r"(?i)(Quận\s+[^,;]+?)\s*(?=(?:Thành phố|Tỉnh)\b)",
            r"\1, ",
            repaired,
        )
        return repaired
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

            while result and self._is_old_context_part(result[-1], match):
                result.pop()
            if match.new_ward_name:
                result.append(unicodedata.normalize("NFC", match.new_ward_name))
            if match.new_province_name:
                result.append(unicodedata.normalize("NFC", match.new_province_name))
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
        for window in (3, 2, 1):
            if index + window > len(parts):
                continue
            value = " ".join(parts[index : index + window])
            folded_value = self._fold(value)
            if self.province_by_normalized.get(folded_value):
                continue
            short_value = self._strip_admin_prefix(folded_value)
            has_ward_marker = self._looks_like_ward(folded_value)
            candidates = self.old_mapping_by_normalized.get(folded_value)
            matched_by_short_name = candidates is None
            if candidates is None:
                candidates = self.old_mapping_by_short_name.get(short_value)
            current = None
            if has_ward_marker:
                current_candidates = self.current_ward_by_normalized.get(folded_value)
                if current_candidates is None:
                    current_candidates = self.current_ward_by_short_name.get(short_value)
                if current_candidates:
                    current = self._best_current_ward_match(
                        value, province=province, district=None, threshold=0.98
                    )
            if candidates is None and current:
                continue
            if candidates is None and not has_ward_marker:
                continue
            candidates = candidates or self.old_mapping_candidates
            if province:
                candidates = [
                    candidate
                    for candidate in candidates
                    if self._same_place(candidate.province_name, province.name)
                ]
                if not candidates:
                    continue
            for candidate in candidates:
                score = self._candidate_score(folded_value, candidate.normalized)
                if score < 0.96:
                    continue
                context_matches = self._mapping_context_matches(parts, index, window, candidate)
                if current and not context_matches:
                    continue
                has_same_short_name = matched_by_short_name and sum(
                    1
                    for possible in candidates
                    if self._strip_admin_prefix(possible.normalized) == short_value
                ) > 1
                if has_same_short_name and not context_matches:
                    continue
                has_same_name = sum(
                    1 for possible in candidates if possible.normalized == candidate.normalized
                ) > 1
                if has_same_name and not context_matches:
                    continue
                if context_matches:
                    score += 0.05
                if score > best_score:
                    best = candidate
                    best_window = window
                    best_score = score
        if best and best_score >= 0.96:
            return best, best_window
        return None, 0

    def _mapping_context_matches(
        self,
        parts: list[str],
        index: int,
        window: int,
        candidate: PlaceCandidate,
    ) -> bool:
        if not candidate.district_name:
            return True
        context = " ".join(parts[:index] + parts[index + window :])
        district = self._strip_admin_prefix(self._fold(candidate.district_name))
        context_normalized = self._strip_admin_prefix(self._fold(context))
        if not district or not context_normalized:
            return False
        return district in context_normalized or self._similarity(district, context_normalized) >= 0.88
    def _is_old_context_part(self, part: str, match: PlaceCandidate) -> bool:
        folded = self._fold(part)
        if not folded:
            return True
        if folded.startswith(("tinh ", "thi xa ", "huyen ", "quan ", "tp ", "thanh pho ")):
            return True
        if self._looks_like_province(folded) and self._best_match(part, self.province_candidates, threshold=0.82):
            return True
        if self._looks_like_district(folded) and self._best_district_match(part, province=None, threshold=0.84):
            return True
        if match.district_name and self._candidate_score(folded, self._fold(match.district_name)) >= 0.88:
            return True
        if match.province_name and self._candidate_score(folded, self._fold(match.province_name)) >= 0.88:
            return True
        if match.new_province_name and self._candidate_score(folded, self._fold(match.new_province_name)) >= 0.88:
            return True
        return False

    def best_province_name(self, value: str) -> str:
        folded = self._fold(value)
        match = self.province_by_normalized.get(folded)
        if match:
            return match[0].name
        match = self._best_match(value, self.province_candidates, threshold=0.93)
        return match.name if match else ""

    def best_ward_name(self, value: str, province_name: str = "") -> str:
        province = self._best_match(province_name, self.province_candidates, threshold=0.82) if province_name else None
        for part in reversed(self._split_address_parts(value)):
            match = self._best_current_ward_match(part, province=province, district=None, threshold=0.98)
            if match:
                return match.name
        source = ", ".join(part for part in (value, province_name) if part)
        for part in reversed(self._split_address_parts(self.normalize_address(source))):
            match = self._best_current_ward_match(part, province=province, district=None, threshold=0.98)
            if match:
                return match.name
        return ""

    def _normalize_part(self, part: str, *, province: PlaceCandidate | None, district: PlaceCandidate | None) -> str:
        folded = self._fold(part)
        if self._looks_like_province(folded):
            indexed = self.province_by_normalized.get(folded)
            match = indexed[0] if indexed else self._best_match(part, self.province_candidates, threshold=0.82)
            if match:
                return match.name
        if self._looks_like_ward(folded):
            match = self._best_current_ward_match(part, province=province, district=district)
            if match:
                return match.name
        if self._looks_like_district(folded):
            match = self._best_match(part, self.district_candidates, threshold=0.84)
            if match:
                return match.name
        indexed = self.province_by_normalized.get(folded)
        match = indexed[0] if indexed else self._best_match(part, self.province_candidates, threshold=0.93)
        if match:
            return match.name
        district_candidates = self.district_by_normalized.get(folded)
        if district_candidates is None:
            district_candidates = self.district_by_short_name.get(
                self._strip_admin_prefix(folded)
            )
        if district_candidates:
            if province:
                scoped = [
                    candidate
                    for candidate in district_candidates
                    if self._same_place(candidate.province_name, province.name)
                ]
                if scoped:
                    district_candidates = scoped
            match = self._best_match(part, district_candidates, threshold=0.94)
            if match:
                return match.name
        return self._clean_common_prefix_errors(part)

    def _best_province(self, parts: list[str]) -> PlaceCandidate | None:
        best: PlaceCandidate | None = None
        best_score = 0.0
        for part in parts:
            folded = self._fold(part)
            threshold = 0.82 if self._looks_like_province(folded) else 0.93
            indexed = self.province_by_normalized.get(folded)
            match = indexed[0] if indexed else self._best_match(part, self.province_candidates, threshold=threshold)
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
        province = self._best_province(parts)
        for part in parts:
            if not self._looks_like_district(self._fold(part)):
                continue
            match = self._best_district_match(part, province=province, threshold=0.84)
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
        candidates = self.district_by_normalized.get(self._fold(part), self.district_candidates)
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

    def _best_current_ward_match(
        self,
        part: str,
        *,
        province: PlaceCandidate | None,
        district: PlaceCandidate | None,
        threshold: float = 0.84,
    ) -> PlaceCandidate | None:
        folded = self._fold(part)
        candidates = self.current_ward_by_normalized.get(folded)
        if candidates is None:
            candidates = self.current_ward_by_short_name.get(self._strip_admin_prefix(folded))
        if candidates is None:
            if not self._looks_like_ward(folded):
                return None
            candidates = self.current_ward_candidates
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

    @staticmethod
    def _has_whole_marker(folded: str, markers: list[str]) -> bool:
        return any(
            re.search(rf"(?:^|\s){re.escape(marker)}(?:\s|$)", folded)
            for marker in markers
        )

    def _looks_like_province(self, folded: str) -> bool:
        return self._has_whole_marker(
            folded,
            ["tinh", "tp", "thanh pho", "tphcm", "ha noi", "ho chi minh"],
        )

    def _looks_like_ward(self, folded: str) -> bool:
        return self._has_whole_marker(folded, ["phuong", "xa", "thi tran"])

    def _looks_like_district(self, folded: str) -> bool:
        return self._has_whole_marker(folded, ["quan", "huyen", "thi xa"]) or folded.startswith("tp ")

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
        return get_app_paths().bundle_root / "assets" / "administrative_places" / "vietnam_admin_2025.json"

    @staticmethod
    @lru_cache(maxsize=4)
    def _load_data(path: str) -> dict[str, object]:
        with Path(path).open("r", encoding="utf-8") as file:
            return json.load(file)

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from mingo_assistant.services.normalization.administrative_place_matcher import AdministrativePlaceMatcher


@dataclass
class AddressParseResult:
    raw_address: str = ""
    normalized_address: str = ""
    normalization_status: str = ""
    normalization_message: str = ""
    company_name: str = ""
    street_line: str = ""
    village: str = ""
    ward: str = ""
    district: str = ""
    province: str = ""

    def summary(self) -> str:
        lines = []
        if self.company_name:
            lines.append(f"T\u00ean c\u00f4ng ty ph\u00e1t hi\u1ec7n: {self.company_name}")
        if self.street_line:
            lines.append(f"S\u1ed1 nh\u00e0/\u0111\u01b0\u1eddng/th\u00f4n: {self.street_line}")
        if self.village:
            lines.append(f"Th\u00f4n/Khu: {self.village}")
        if self.ward:
            lines.append(f"X\u00e3/Ph\u01b0\u1eddng: {self.ward}")
        if self.district:
            lines.append(f"Qu\u1eadn/Huy\u1ec7n: {self.district}")
        if self.province:
            lines.append(f"T\u1ec9nh/Th\u00e0nh ph\u1ed1: {self.province}")
        if self.raw_address:
            lines.append(f"\u0110\u1ecba ch\u1ec9 g\u1ed1c: {self.raw_address}")
        if self.normalized_address:
            lines.append(f"\u0110\u1ecba ch\u1ec9 d\u00f9ng \u0111i\u1ec1n h\u1ed3 s\u01a1: {self.normalized_address}")
        if self.normalization_message:
            lines.append(f"Tr\u1ea1ng th\u00e1i chuy\u1ec3n \u0111\u1ed5i: {self.normalization_message}")
        return "\\n".join(lines)


class AddressParser:
    COMPANY_PATTERN = re.compile(
        r"((?:công ty|cty)\s+(?:tnhh|cổ phần|cp|trách nhiệm hữu hạn)?\s*[^,;\n]+)",
        re.IGNORECASE,
    )


    def __init__(self, place_matcher: AdministrativePlaceMatcher | None = None) -> None:
        self.place_matcher = place_matcher or AdministrativePlaceMatcher()

    def parse(self, text: str) -> AddressParseResult:
        normalization = self.place_matcher.analyze_address(text)
        clean = self._normalize_spaces(normalization.normalized_address)
        parts = self._address_parts(clean)
        result = AddressParseResult(
            raw_address=normalization.raw_address,
            normalized_address=normalization.normalized_address,
            normalization_status=normalization.status,
            normalization_message=normalization.message,
        )
        result.company_name = self._extract_company_name(clean)
        result.village = self._extract_level(clean, ["thôn", "ấp", "khu", "tổ"])
        result.ward = self._extract_level(clean, ["xã", "phường", "thị trấn"])
        result.district = ""
        result.province = self._extract_province_from_parts(parts)
        if result.ward:
            result.ward = self.place_matcher.best_ward_name(result.ward, result.province) or result.ward
        result.street_line = self._extract_street_line(parts, result)
        if normalization.needs_confirmation:
            # Never rebuild an uncertain address from partial guesses.
            result.normalized_address = normalization.normalized_address
        else:
            result.normalized_address = self._build_normalized_address(result)
        return result

    def _normalize_spaces(self, text: str) -> str:
        return " ".join(text.replace("\n", ", ").split())

    def _extract_company_name(self, text: str) -> str:
        match = self.COMPANY_PATTERN.search(text)
        if not match:
            return ""
        company = match.group(1).strip(" ,.;")
        return company.upper() if company else ""

    def _extract_level(self, text: str, prefixes: list[str]) -> str:
        canonical_labels = {
            "thon": "Thôn",
            "ap": "Ấp",
            "khu": "Khu",
            "to": "Tổ",
            "xa": "Xã",
            "phuong": "Phường",
            "thi tran": "Thị trấn",
        }
        aliases: dict[str, str] = {}
        for prefix in prefixes:
            folded = self._fold(prefix)
            canonical = canonical_labels.get(folded, prefix.title())
            aliases[folded] = canonical
            aliases[prefix.lower()] = canonical
        prefix_pattern = "|".join(re.escape(alias) for alias in sorted(aliases, key=len, reverse=True))
        pattern = re.compile(rf"\b({prefix_pattern})\s+([^,;]+)", re.IGNORECASE)
        match = pattern.search(text)
        if not match:
            return ""
        label = aliases[self._fold(match.group(1))]
        return f"{label} {match.group(2).strip()}".strip(" ,.;")

    def _village_tail_pattern(self, village: str) -> str:
        match = re.match(r"^(Thôn|Ấp|Khu|Tổ)\s+(.+)$", village, re.IGNORECASE)
        if not match:
            return re.escape(village)
        aliases = {
            "Thôn": r"(?:Thôn|Thon)",
            "Ấp": r"(?:Ấp|Ap)",
            "Khu": r"Khu",
            "Tổ": r"(?:Tổ|To)",
        }
        label = match.group(1).title()
        return rf"{aliases[label]}\s+{re.escape(match.group(2))}"

    def _address_parts(self, text: str) -> list[str]:
        return [part.strip(" ,.;") for part in re.split(r"[,;]", text) if part.strip(" ,.;")]

    def _extract_province_from_parts(self, parts: list[str]) -> str:
        for part in reversed(parts):
            match = self.place_matcher.best_province_name(part)
            if match:
                return match
        return ""

    def _extract_street_line(self, candidates: list[str], result: AddressParseResult) -> str:
        blocked = {result.company_name.lower(), result.village.lower(), result.ward.lower(), result.district.lower(), result.province.lower()}
        details: list[str] = []
        for candidate in candidates:
            lowered = candidate.lower()
            if lowered in blocked:
                continue
            if any(keyword in lowered for keyword in ["công ty", "xã ", "phường ", "huyện ", "quận ", "tỉnh ", "thành phố "]):
                continue
            detail = candidate
            if result.village:
                detail = re.sub(rf"(?:[,\s]+){self._village_tail_pattern(result.village)}\s*$", "", detail, flags=re.IGNORECASE).strip(" ,.;")
            if detail:
                details.append(detail)
        return ", ".join(details)

    def _build_normalized_address(self, result: AddressParseResult) -> str:
        parts = [result.street_line, result.village, result.ward, result.province]
        return ", ".join(part for part in parts if part)

    def _fold(self, value: str) -> str:
        value = value.replace(chr(273), "d").replace(chr(272), "D")
        text = unicodedata.normalize("NFD", value.strip().lower())
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return " ".join(text.split())

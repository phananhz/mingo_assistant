from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class AddressParseResult:
    normalized_address: str = ""
    company_name: str = ""
    street_line: str = ""
    village: str = ""
    ward: str = ""
    district: str = ""
    province: str = ""

    def summary(self) -> str:
        lines = []
        if self.company_name:
            lines.append(f"Tên công ty phát hiện: {self.company_name}")
        if self.street_line:
            lines.append(f"Số nhà/đường/thôn: {self.street_line}")
        if self.village:
            lines.append(f"Thôn/Khu: {self.village}")
        if self.ward:
            lines.append(f"Xã/Phường: {self.ward}")
        if self.district:
            lines.append(f"Quận/Huyện: {self.district}")
        if self.province:
            lines.append(f"Tỉnh/Thành phố: {self.province}")
        if self.normalized_address:
            lines.append(f"Địa chỉ chuẩn hóa: {self.normalized_address}")
        return "\n".join(lines)


class AddressParser:
    COMPANY_PATTERN = re.compile(
        r"((?:công ty|cty)\s+(?:tnhh|cổ phần|cp|trách nhiệm hữu hạn)?\s*[^,;\n]+)",
        re.IGNORECASE,
    )

    def parse(self, text: str) -> AddressParseResult:
        clean = self._normalize_spaces(text)
        result = AddressParseResult()
        result.company_name = self._extract_company_name(clean)
        result.village = self._extract_level(clean, ["thôn", "ấp", "khu", "tổ"])
        result.ward = self._extract_level(clean, ["xã", "phường", "thị trấn"])
        result.district = self._extract_level(clean, ["huyện", "quận", "thị xã", "thành phố"])
        result.province = self._extract_level(clean, ["tỉnh", "thành phố"])
        result.street_line = self._extract_street_line(clean, result)
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
        prefix_pattern = "|".join(re.escape(prefix) for prefix in sorted(prefixes, key=len, reverse=True))
        pattern = re.compile(rf"\b({prefix_pattern})\s+([^,;]+)", re.IGNORECASE)
        match = pattern.search(text)
        if not match:
            return ""
        return f"{match.group(1).title()} {match.group(2).strip()}".strip(" ,.;")

    def _extract_street_line(self, text: str, result: AddressParseResult) -> str:
        candidates = [part.strip(" ,.;") for part in re.split(r"[,;]", text) if part.strip(" ,.;")]
        blocked = {result.company_name.lower(), result.village.lower(), result.ward.lower(), result.district.lower(), result.province.lower()}
        for candidate in candidates:
            lowered = candidate.lower()
            if lowered in blocked:
                continue
            if any(keyword in lowered for keyword in ["công ty", "xã ", "phường ", "huyện ", "quận ", "tỉnh ", "thành phố "]):
                continue
            return candidate
        return ""

    def _build_normalized_address(self, result: AddressParseResult) -> str:
        parts = [result.street_line, result.village, result.ward, result.district, result.province]
        return ", ".join(part for part in parts if part)

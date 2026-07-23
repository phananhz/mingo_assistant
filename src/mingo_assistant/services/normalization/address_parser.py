from __future__ import annotations

import re
import unicodedata
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

    PROVINCE_AFTER_MERGER = {
        "ha giang": "Tuyên Quang",
        "tuyen quang": "Tuyên Quang",
        "yen bai": "Lào Cai",
        "lao cai": "Lào Cai",
        "bac kan": "Thái Nguyên",
        "thai nguyen": "Thái Nguyên",
        "vinh phuc": "Phú Thọ",
        "hoa binh": "Phú Thọ",
        "phu tho": "Phú Thọ",
        "bac giang": "Bắc Ninh",
        "bac ninh": "Bắc Ninh",
        "thai binh": "Hưng Yên",
        "hung yen": "Hưng Yên",
        "hai duong": "Thành phố Hải Phòng",
        "hai phong": "Thành phố Hải Phòng",
        "ha nam": "Ninh Bình",
        "nam dinh": "Ninh Bình",
        "ninh binh": "Ninh Bình",
        "quang binh": "Quảng Trị",
        "quang tri": "Quảng Trị",
        "quang nam": "Thành phố Đà Nẵng",
        "da nang": "Thành phố Đà Nẵng",
        "kon tum": "Quảng Ngãi",
        "quang ngai": "Quảng Ngãi",
        "binh dinh": "Gia Lai",
        "gia lai": "Gia Lai",
        "ninh thuan": "Khánh Hòa",
        "khanh hoa": "Khánh Hòa",
        "dak nong": "Lâm Đồng",
        "binh thuan": "Lâm Đồng",
        "lam dong": "Lâm Đồng",
        "phu yen": "Đắk Lắk",
        "dak lak": "Đắk Lắk",
        "ba ria vung tau": "Thành phố Hồ Chí Minh",
        "binh duong": "Thành phố Hồ Chí Minh",
        "ho chi minh": "Thành phố Hồ Chí Minh",
        "tp ho chi minh": "Thành phố Hồ Chí Minh",
        "tphcm": "Thành phố Hồ Chí Minh",
        "binh phuoc": "Đồng Nai",
        "dong nai": "Đồng Nai",
        "long an": "Tây Ninh",
        "tay ninh": "Tây Ninh",
        "soc trang": "Thành phố Cần Thơ",
        "hau giang": "Thành phố Cần Thơ",
        "can tho": "Thành phố Cần Thơ",
        "ben tre": "Vĩnh Long",
        "tra vinh": "Vĩnh Long",
        "vinh long": "Vĩnh Long",
        "tien giang": "Đồng Tháp",
        "dong thap": "Đồng Tháp",
        "bac lieu": "Cà Mau",
        "ca mau": "Cà Mau",
        "kien giang": "An Giang",
        "an giang": "An Giang",
    }

    def parse(self, text: str) -> AddressParseResult:
        clean = self._normalize_spaces(text)
        result = AddressParseResult()
        result.company_name = self._extract_company_name(clean)
        result.village = self._extract_level(clean, ["thôn", "ấp", "khu", "tổ"])
        result.ward = self._extract_level(clean, ["xã", "phường", "thị trấn"])
        result.district = self._extract_level(clean, ["huyện", "quận", "thị xã", "thành phố"])
        result.province = self._extract_level(clean, ["tỉnh", "thành phố"])
        result.district = ""
        result.province = self._normalize_province(result.province)
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
        parts = [result.street_line, result.village, result.ward, result.province]
        return ", ".join(part for part in parts if part)

    def _normalize_province(self, value: str) -> str:
        if not value:
            return ""
        folded = self._fold(value)
        for prefix in ("tinh ", "thanh pho "):
            if folded.startswith(prefix):
                folded = folded[len(prefix) :]
                break
        return self.PROVINCE_AFTER_MERGER.get(folded, value)

    def _fold(self, value: str) -> str:
        value = value.replace(chr(273), "d").replace(chr(272), "D")
        text = unicodedata.normalize("NFD", value.strip().lower())
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return " ".join(text.split())

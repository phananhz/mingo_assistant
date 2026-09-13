from __future__ import annotations

import re
import unicodedata
from typing import Callable, Mapping


class DocumentValueFormatter:
    """Pure value formatting used by DOCX template rules."""

    def __init__(self, province_resolver: Callable[[str], str]) -> None:
        self._province_resolver = province_resolver

    @staticmethod
    def date_component(value: object, component: int) -> str:
        parts = re.findall(r"\d+", str(value or ""))
        if len(parts) != 3:
            return ""
        return parts[component].zfill(2) if component in (0, 1) else parts[component]

    def company_address_part(self, values: Mapping[str, str], part: str) -> str:
        full = str(values.get("company_address", "") or "").strip()
        detail = str(values.get("company_address_detail", "") or "").strip()
        ward = str(values.get("company_ward", "") or "").strip()
        province = str(values.get("company_province", "") or "").strip()
        has_admin_parts = bool(
            re.search(r"(?i)\b(xã|phường|thị trấn|đặc khu|tỉnh|thành phố)\b", full)
        )
        source = full if has_admin_parts else detail
        if part == "detail":
            return self.address_detail_only(source or detail)
        if part == "ward":
            parsed = self.administrative_part_only(source, {"xa", "phuong", "thi_tran", "dac_khu"})
            return parsed if parsed != source or source else ward
        parsed = self.normalize_province(
            self.administrative_part_only(source, {"tinh", "thanh_pho"})
        )
        return parsed if parsed != source or source else province

    def capital_total_ratio(self, values: Mapping[str, str]) -> str:
        ratio = str(values.get("capital_total_ratio", "") or "").strip()
        if ratio:
            return ratio.rstrip("% ").strip()
        return "100"

    def member_count(self, values: Mapping[str, str]) -> int:
        explicit = self.money_number(values.get("member_count", "")) or self.money_number(
            values.get("company_member_count", "")
        )
        if explicit:
            return explicit
        count = sum(
            bool(str(values.get(f"member_{index}_full_name", "") or "").strip())
            for index in range(1, 21)
        )
        return count or 1

    def with_vnd(self, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        folded = self.fold(text)
        if "vnd" in folded or "dong" in folded:
            return text
        return f"{text} VNĐ"

    def address_detail_only(self, value: str) -> str:
        parts = [part.strip(" ,.;") for part in re.split(r"[,;]", str(value or "")) if part.strip(" ,.;")]
        kept: list[str] = []
        blocked_prefixes = {"xa", "phuong", "thi_tran", "huyen", "quan", "thi_xa", "thanh_pho", "tinh"}
        for part in parts:
            normalized = self.normalize_key(part)
            if any(normalized.startswith(prefix + "_") or normalized == prefix for prefix in blocked_prefixes):
                continue
            kept.append(part)
        return ", ".join(kept) if kept else str(value or "").strip()

    def administrative_part_only(self, value: str, allowed_prefixes: set[str]) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        parts = [part.strip(" ,.;") for part in re.split(r"[,;]", text) if part.strip(" ,.;")]
        for part in parts:
            normalized = self.normalize_key(part)
            if any(normalized.startswith(prefix + "_") or normalized == prefix for prefix in allowed_prefixes):
                return part
        return text

    def normalize_province(self, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        return self._province_resolver(text) or text

    @staticmethod
    def money_number(value: str) -> int:
        digits = re.sub(r"\D", "", str(value or ""))
        return int(digits) if digits else 0

    @staticmethod
    def business_line_indices(values: Mapping[str, str]) -> list[int]:
        indices = {
            int(match.group(1))
            for key in values
            if (match := re.match(r"^business_line_(\d+)_(?:name|detail|code|is_main)$", key))
        }
        return sorted(index for index in indices if index > 0)

    @classmethod
    def business_lines(cls, values: Mapping[str, str]) -> list[dict[str, str | bool]]:
        lines: list[dict[str, str | bool]] = []
        for index in cls.business_line_indices(values):
            name = cls.normalize_business_line_text(values.get(f"business_line_{index}_name", ""))
            detail = cls.normalize_business_line_text(values.get(f"business_line_{index}_detail", ""))
            if detail:
                name = f"{name}\n{detail}" if name else detail
            code = re.sub(r"\D", "", values.get(f"business_line_{index}_code", ""))[:4]
            is_main = bool(values.get(f"business_line_{index}_is_main", "").strip())
            if name or code or is_main:
                lines.append({"name": name, "code": code, "is_main": is_main})
        return lines

    @staticmethod
    def normalize_business_line_text(value: str) -> str:
        text = "\n".join(part.strip() for part in value.replace("\r", "\n").split("\n") if part.strip())
        text = re.sub(r"\s+(Chi\s*tiết\s*:)", r"\n\1", text, flags=re.IGNORECASE)
        return re.sub(r"(?i)chi\s*tiết\s*:", "Chi tiết:", text)

    @staticmethod
    def normalize_key(value: str) -> str:
        text = str(value or "").strip().lower().replace("đ", "d")
        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        return re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    @classmethod
    def fold(cls, value: str) -> str:
        return cls.normalize_key(value).replace("_", " ")

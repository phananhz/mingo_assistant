from __future__ import annotations

import re
from collections.abc import Mapping, Set

from mingo_assistant.services.documents.value_formatter import DocumentValueFormatter


class DocumentContextBuilder:
    """Resolve template-specific values before Word rendering begins."""

    def __init__(
        self,
        formatter: DocumentValueFormatter,
        *,
        uppercase_fields: Set[str],
        detail_address_fields: Set[str],
        ward_fields: Set[str],
        province_fields: Set[str],
    ) -> None:
        self._formatter = formatter
        self._uppercase_fields = uppercase_fields
        self._detail_address_fields = detail_address_fields
        self._ward_fields = ward_fields
        self._province_fields = province_fields

    def value_for_target(self, target: str, values: Mapping[str, str]) -> str:
        if target == "__clear":
            return ""
        if target.endswith("_date_of_birth_day"):
            return self._formatter.date_component(values.get(target.removesuffix("_day"), ""), 0)
        if target.endswith("_date_of_birth_month"):
            return self._formatter.date_component(values.get(target.removesuffix("_month"), ""), 1)
        if target.endswith("_date_of_birth_year"):
            return self._formatter.date_component(values.get(target.removesuffix("_year"), ""), 2)
        if target == "document_year_with_prefix":
            year = str(values.get("document_year", "") or "").strip()
            return f" năm {year}" if year else ""
        if target == "company_province_with_nationality":
            province = self.value_for_target("company_province", values)
            return f"{province}, Việt Nam" if province else ""
        if target == "legal_representative_province_with_nationality":
            province = self.value_for_target("legal_representative_province", values)
            return f"{province}, Việt Nam" if province else ""
        if target == "charter_capital_article_6_text":
            number = self._formatter.with_vnd(values.get("charter_capital_number", ""))
            words = str(values.get("charter_capital_text", "") or "").strip()
            if words and not re.search(r"\sđồng$", words, re.IGNORECASE):
                words = f"{words} đồng"
            return f"{number} (Ghi bằng chữ: {words})" if number and words else number
        if target == "organization_owner_issue_place":
            return str(values.get(target, "") or "").split(" - ", 1)[0].strip(" ,;-")
        if target == "charter_capital_words_without_currency":
            return re.sub(
                r"\s*đồng\s*$",
                "",
                str(values.get("charter_capital_text", "") or ""),
                flags=re.IGNORECASE,
            ).strip()
        if target.startswith("organization_owner_representative_contact_address_"):
            address = str(values.get("organization_owner_representative_contact_address", "") or "").strip()
            suffix = target.removeprefix("organization_owner_representative_contact_address_")
            if suffix == "detail":
                return self._formatter.address_detail_only(address)
            if suffix == "ward":
                return self._formatter.administrative_part_only(address, {"xa", "phuong", "thi_tran"})
            if suffix == "province":
                part = self._formatter.administrative_part_only(address, {"tinh", "thanh_pho"})
                return self._formatter.normalize_province(part)
        if target == "organization_owner_representative_id_number":
            identity = str(values.get("organization_owner_representative_identity", "") or "")
            match = re.search(
                r"(?:CCCD\s*số|Số\s*định\s*danh\s*cá\s*nhân)\s*:?\s*([0-9A-Za-z-]+)",
                identity,
                re.IGNORECASE,
            )
            if match:
                return match.group(1)
            fallback = re.search(r"[0-9]{6,}", identity)
            return fallback.group(0) if fallback else ""
        if target == "legal_representative_full_name_title":
            return str(values.get("legal_representative_full_name", "") or "").title()
        if target in {"legal_representative_address_without_province", "beneficial_owner_address_without_province"}:
            source = "legal_representative_permanent_address" if target.startswith("legal_representative_") else "beneficial_owner_address"
            parts = [part.strip() for part in str(values.get(source, "") or "").split(",") if part.strip()]
            return ", ".join(parts[:-1]) if len(parts) > 1 else ""
        if target == "beneficial_owner_province":
            parts = [part.strip() for part in str(values.get("beneficial_owner_address", "") or "").split(",") if part.strip()]
            return parts[-1] if parts else ""
        if target == "tax_vat_method_x":
            return "X" if values.get("tax_vat_method") == "Khấu trừ" else ""
        if target == "tax_declaration_period_x":
            return "X" if values.get("tax_declaration_period") == "Hàng tháng" else ""
        if target == "document_date_only":
            day = str(values.get("document_day", "") or "").strip()
            month = str(values.get("document_month", "") or "").strip()
            year = str(values.get("document_year", "") or "").strip()
            return f"ngày {day} tháng {month} năm {year}." if day and month and year else ""
        if target == "document_day_with_trailing_space":
            day = str(values.get("document_day", "") or "").strip()
            return f"{day} " if day else ""
        if target == "charter_capital_number_vnd":
            return self._formatter.with_vnd(values.get("charter_capital_number", ""))
        if target == "capital_total_ratio_number":
            return self._formatter.capital_total_ratio(values)
        if target == "member_capital_ratio_number":
            ratio = str(values.get("member_capital_ratio", "") or "").strip()
            return ratio.rstrip("% ").strip()

        raw = str(values.get(target, "") or "").strip()
        if target in self._detail_address_fields:
            if target.startswith("company_"):
                return self._formatter.company_address_part(values, "detail")
            return self._formatter.address_detail_only(raw)
        if target in self._ward_fields:
            if target.startswith("company_"):
                return self._formatter.company_address_part(values, "ward")
            return self._formatter.administrative_part_only(raw, {"xa", "phuong", "thi_tran"})
        if target in self._province_fields:
            if target.startswith("company_"):
                return self._formatter.company_address_part(values, "province")
            part = self._formatter.administrative_part_only(raw, {"tinh", "thanh_pho"})
            return self._formatter.normalize_province(part)
        if target in self._uppercase_fields:
            return raw.upper()
        return raw

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Mapping, Protocol

from mingo_assistant.domains.business_registration import (
    RegistrationCase,
    RegistrationValidationResult,
    RegistrationValidator,
    VietnameseMoneyFormatter,
)


class ParsedAddressPort(Protocol):
    street_line: str
    village: str
    ward: str
    province: str


class AddressParserPort(Protocol):
    def parse(self, address: str) -> ParsedAddressPort: ...


class RegistrationOfficePort(Protocol):
    def province_for_office(self, office_name: str) -> str: ...


class RegistrationViewModel:
    """UI-independent registration state and validation facade."""

    def __init__(self, validator: RegistrationValidator) -> None:
        self._validator = validator
        self._values: dict[str, str] = {}

    def replace(self, values: Mapping[str, str]) -> None:
        self._values = {str(key): str(value or "") for key, value in values.items()}

    def snapshot(self) -> dict[str, str]:
        return dict(self._values)

    def domain_case(self) -> RegistrationCase:
        return RegistrationCase.from_form_values(self._values)

    def validate(self, *, address_confirmation_required: bool = False) -> RegistrationValidationResult:
        return self._validator.validate(
            self._values,
            address_confirmation_required=address_confirmation_required,
        )

    def missing_required_fields(self, *, address_confirmation_required: bool = False) -> list[str]:
        return self._validator.missing_required_fields(
            self._values,
            address_confirmation_required=address_confirmation_required,
        )


class RegistrationValueComposer:
    """Completes derived form values without depending on Qt widgets."""

    def __init__(
        self,
        address_parser: AddressParserPort,
        registration_offices: RegistrationOfficePort,
        money_formatter: VietnameseMoneyFormatter | None = None,
        *,
        capital_source_count: int = 4,
        asset_contribution_count: int = 6,
    ) -> None:
        self._address_parser = address_parser
        self._registration_offices = registration_offices
        self._money = money_formatter or VietnameseMoneyFormatter()
        self._capital_source_count = capital_source_count
        self._asset_contribution_count = asset_contribution_count

    def compose(self, source: Mapping[str, str], *, member_count: int = 1) -> dict[str, str]:
        values = {str(key): str(value or "") for key, value in source.items()}
        day = values.get("document_day", "").strip()
        month = values.get("document_month", "").strip()
        year = values.get("document_year", "").strip()

        signing_place = self.signing_place_for_office(values.get("business_registration_office", ""))
        if signing_place:
            values["document_place"] = signing_place
        if day and month and year:
            date_text = f"ngày {day} tháng {month} năm {year}"
            values["document_place_date"] = f"{values.get('document_place', '').strip()}, {date_text}".strip(", ")

        self._fill_composed_address(
            values,
            "company_address",
            ("company_address_detail", "company_ward", "company_province"),
        )
        self._fill_composed_address(
            values,
            "legal_representative_permanent_address",
            (
                "legal_representative_address_detail",
                "legal_representative_ward",
                "legal_representative_province",
            ),
        )
        self._fill_if_missing(
            values,
            "legal_representative_contact_address",
            "legal_representative_permanent_address",
        )
        self._fill_if_missing(values, "company_province", "document_place")

        owner_address = values.get("beneficial_owner_address", "").strip()
        if owner_address:
            parsed = self._address_parser.parse(owner_address)
            values.setdefault("beneficial_owner_address_detail", parsed.street_line or parsed.village)
            values.setdefault("beneficial_owner_ward", parsed.ward)
            values.setdefault("beneficial_owner_province", parsed.province)

        if self._is_organization_owner(values.get("owner_type", "")):
            for target, origin in {
                "beneficial_owner_list_number": "organization_owner_representative_number",
                "beneficial_owner_list_full_name": "organization_owner_representative_full_name",
                "beneficial_owner_list_date_of_birth": "organization_owner_representative_date_of_birth",
                "beneficial_owner_list_gender": "organization_owner_representative_gender",
                "beneficial_owner_list_identity": "organization_owner_representative_identity",
                "beneficial_owner_list_ethnicity": "organization_owner_representative_ethnicity",
                "beneficial_owner_list_address": "organization_owner_representative_contact_address",
            }.items():
                self._fill_if_missing(values, target, origin)
            values.setdefault("beneficial_owner_list_number", "1")

        aliases = {
            "director_full_name": "legal_representative_full_name",
            "director_date_of_birth": "legal_representative_date_of_birth",
            "director_gender": "legal_representative_gender",
            "director_id_number": "legal_representative_id_number",
            "director_position": "legal_representative_position",
            "director_phone": "legal_representative_phone",
            "applicant_full_name": "legal_representative_full_name",
            "applicant_date_of_birth": "legal_representative_date_of_birth",
            "applicant_gender": "legal_representative_gender",
            "applicant_id_number": "legal_representative_id_number",
            "applicant_address_detail": "legal_representative_address_detail",
            "applicant_ward": "legal_representative_ward",
            "applicant_province": "legal_representative_province",
            "applicant_phone": "legal_representative_phone",
            "applicant_email": "legal_representative_email",
        }
        for target, origin in aliases.items():
            self._fill_if_missing(values, target, origin)
        for target, origin in {key: value for key, value in aliases.items() if key.startswith("director_")}.items():
            values[target] = values.get(origin, "").strip()
        values["director_phone"] = values.get("legal_representative_phone", "").strip()

        self._fill_if_missing(values, "member_capital_amount", "charter_capital_number")
        self._fill_if_missing(values, "cash_capital_text", "charter_capital_full_text")
        capital_digits = self._money.digits(values.get("charter_capital_number", ""))
        if capital_digits:
            formatted_capital = self._money.format_digits(capital_digits)
            values["charter_capital_number"] = formatted_capital
            if not values.get("member_capital_amount") or self._money.digits(values.get("member_capital_amount", "")) == capital_digits:
                values["member_capital_amount"] = formatted_capital
            if not values.get("charter_capital_text"):
                values["charter_capital_text"] = self._money.to_words(int(capital_digits)).capitalize() + " đồng"
        if not values.get("charter_capital_full_text"):
            capital_number = values.get("charter_capital_number", "")
            capital_text = values.get("charter_capital_text", "")
            if capital_number and capital_text:
                values["charter_capital_full_text"] = f"{capital_number} đồng ({capital_text})"
            elif capital_number:
                values["charter_capital_full_text"] = capital_number
        if not values.get("cash_capital_text"):
            values["cash_capital_text"] = values.get("charter_capital_full_text", "")
        values.setdefault("capital_zero", "0")
        values.setdefault("asset_capital_text", "(không có)")
        self._normalize_capital_breakdown(values)

        member_count = max(1, member_count)
        values["company_member_count"] = str(member_count)
        values["company_type_label"] = self.case_type_for_members(member_count)
        if member_count == 1:
            values["member_capital_ratio"] = "100%"
        elif capital_digits:
            equal_amount = int(capital_digits) // member_count
            equal_ratio = round(100 / member_count, 2)
            values["member_capital_ratio"] = values.get("member_capital_ratio") or f"{equal_ratio:g}%"
            if self._money.digits(values.get("member_capital_amount", "")) == capital_digits:
                values["member_capital_amount"] = self._money.format_digits(str(equal_amount))
        for index in range(1, member_count + 1):
            default_amount = values.get("charter_capital_number", "")
            default_ratio = "100%" if member_count == 1 else values.get("member_capital_ratio", "")
            if member_count > 1 and capital_digits:
                default_amount = values.get("member_capital_amount", default_amount)
            values.setdefault(f"member_{index}_capital_amount", default_amount)
            values.setdefault(f"member_{index}_capital_ratio", default_ratio)
        values.setdefault("tax_labor_count", "1")
        values["business_lines"] = self.business_lines_summary(values)
        return values

    def signing_place_for_office(self, office_name: str) -> str:
        place = self._registration_offices.province_for_office(office_name).strip()
        if place.casefold() == "thành phố hồ chí minh":
            return place
        return re.sub(r"^(?:Thành phố|Tỉnh)\s+", "", place, flags=re.IGNORECASE).strip()

    @staticmethod
    def case_type_for_members(member_count: int) -> str:
        if member_count <= 1:
            return "TNHH một thành viên"
        return "TNHH hai thành viên trở lên"

    def _normalize_capital_breakdown(self, values: dict[str, str]) -> None:
        for prefix, count in (
            ("capital_source", self._capital_source_count),
            ("asset_contribution", self._asset_contribution_count),
        ):
            amounts = [
                int(self._money.digits(values.get(f"{prefix}_{index}_amount", "")) or "0")
                for index in range(1, count + 1)
            ]
            total = sum(amounts)
            for index, amount in enumerate(amounts, start=1):
                values[f"{prefix}_{index}_amount"] = self._money.format_digits(str(amount)) if amount else "0"
                ratio = amount * 100 / total if total else 0
                values[f"{prefix}_{index}_ratio"] = f"{ratio:.2f}".rstrip("0").rstrip(".")
            values[f"{prefix}_total_amount"] = self._money.format_digits(str(total)) if total else "0"
            values[f"{prefix}_total_ratio"] = "100" if total else "0"

    @classmethod
    def business_lines_summary(cls, values: Mapping[str, str]) -> str:
        lines: list[str] = []
        for index in cls._business_line_indices(values):
            name = cls.normalize_business_line_text(values.get(f"business_line_{index}_name", ""))
            code = values.get(f"business_line_{index}_code", "").strip()
            if not name and not code:
                continue
            main = " - ngành nghề chính" if values.get(f"business_line_{index}_is_main") else ""
            line = f"{name} [{code}]" if name and code else name or f"[{code}]"
            lines.append(f"{line}{main}")
        return "\n".join(lines)

    @staticmethod
    def normalize_business_line_text(value: str) -> str:
        text = "\n".join(part.strip() for part in value.replace("\r", "\n").split("\n") if part.strip())
        text = re.sub(r"\s+(Chi\s*tiết\s*:)", r"\n\1", text, flags=re.IGNORECASE)
        return re.sub(r"(?i)chi\s*tiết\s*:", "Chi tiết:", text)

    @staticmethod
    def _business_line_indices(values: Mapping[str, str]) -> list[int]:
        return sorted(
            {
                int(match.group(1))
                for key in values
                if (match := re.fullmatch(r"business_line_(\d+)_(?:name|detail|code|is_main)", key))
            }
        )

    @staticmethod
    def _fill_if_missing(values: dict[str, str], target: str, source: str) -> None:
        if not values.get(target) and values.get(source):
            values[target] = values[source]

    @staticmethod
    def _fill_composed_address(values: dict[str, str], target: str, parts: tuple[str, ...]) -> None:
        if values.get(target):
            return
        address = ", ".join(values.get(part, "").strip() for part in parts if values.get(part, "").strip())
        if address:
            values[target] = address

    @staticmethod
    def _is_organization_owner(value: object) -> bool:
        import unicodedata

        text = str(value or "").strip().lower().replace("đ", "d")
        text = unicodedata.normalize("NFD", text)
        text = "".join(character for character in text if unicodedata.category(character) != "Mn")
        return text == "to chuc"


@dataclass(frozen=True)
class ExportVersion:
    name: str
    case_export_dir: str
    export_dir: str
    exported_at: str
    documents: list[str]

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "case_export_dir": self.case_export_dir,
            "export_dir": self.export_dir,
            "exported_at": self.exported_at,
            "documents": list(self.documents),
        }


class RegistrationExportPlanner:
    """Names export folders and keeps only the latest registration export."""

    VERSION_FOLDER_PATTERN = re.compile("b\u1ea3n\\s+(\\d+)", flags=re.IGNORECASE)

    @staticmethod
    def safe_folder_name(value: str) -> str:
        text = re.sub(r'[<>:"/\\|?*]', " ", value)
        text = re.sub(r"\s+", " ", text).strip(" .")
        return text[:160] or "ho_so_thanh_lap"

    def case_folder_name(self, values: Mapping[str, str]) -> str:
        company_name = (values.get("company_name", "") or "HO SO THANH LAP").strip()
        return self.safe_folder_name(company_name)

    def output_dir(self, case_export_dir: Path, case_name: str, version_name: str) -> Path:
        return case_export_dir / version_name / self.safe_folder_name(case_name)

    @staticmethod
    def next_version_number(
        case_export_dir: Path,
        existing_versions: list[dict[str, object]],
        legacy_export_dir: str = "",
    ) -> int:
        numbers = [len(existing_versions)]
        if not existing_versions and legacy_export_dir:
            numbers.append(1)
        if case_export_dir.exists():
            for child in case_export_dir.iterdir():
                if not child.is_dir():
                    continue
                match = RegistrationExportPlanner.VERSION_FOLDER_PATTERN.fullmatch(child.name.strip())
                if match:
                    numbers.append(int(match.group(1)))
        return max(numbers) + 1

    @classmethod
    def previous_version_directories(
        cls,
        case_export_dir: Path,
        keep_export_dir: Path,
    ) -> list[Path]:
        """Return safe, direct ``bản N`` folders older than the kept export."""
        try:
            root = case_export_dir.resolve()
            relative_keep = keep_export_dir.resolve().relative_to(root)
        except (OSError, ValueError):
            return []
        if not relative_keep.parts:
            return []
        keep_version_dir = (root / relative_keep.parts[0]).resolve()
        if not case_export_dir.exists():
            return []

        previous: list[Path] = []
        for child in case_export_dir.iterdir():
            if not child.is_dir() or not cls.VERSION_FOLDER_PATTERN.fullmatch(child.name.strip()):
                continue
            try:
                resolved = child.resolve()
            except OSError:
                continue
            if resolved.parent == root and resolved != keep_version_dir:
                previous.append(child)
        return previous

    @staticmethod
    def append_version(
        existing_versions: list[dict[str, object]],
        *,
        legacy_export_dir: str,
        legacy_exported_at: str,
        legacy_documents: list[str],
        case_export_dir: str,
        version_export_dir: str,
        exported_at: str,
        documents: list[str],
        version_name: str,
    ) -> list[dict[str, object]]:
        return [
            ExportVersion(
                name="m\u1edbi nh\u1ea5t",
                case_export_dir=case_export_dir,
                export_dir=version_export_dir,
                exported_at=exported_at,
                documents=documents,
            ).as_dict()
        ]

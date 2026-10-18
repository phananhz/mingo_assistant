from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from mingo_assistant.domains.household_business import HOUSEHOLD_BUSINESS_SCHEMA_VERSION
from mingo_assistant.models.case import CaseSummary
from mingo_assistant.services.documents.household_business_generator import (
    HouseholdBusinessTemplateGenerator,
)
from mingo_assistant.ui.views.business_registration_workspace import BusinessRegistrationWorkspace


HOUSEHOLD_BUSINESS_CASE_TYPE = "Thành lập hộ kinh doanh"
HOUSEHOLD_OWNER_SECTION = "Thông tin chủ hộ kinh doanh"
HOUSEHOLD_DETAILS_SECTION = "Thông tin hộ kinh doanh"
HOUSEHOLD_CAPITAL_SECTION = "Vốn kinh doanh"
HOUSEHOLD_TAX_SECTION = "Thông tin đăng ký thuế"

HOUSEHOLD_FIELD_GROUPS = [
    (
        "Thông tin cơ quan tiếp nhận và thời gian ký",
        [
            ("business_registration_office", "Phòng đăng ký kinh doanh"),
            ("document_place", "Nơi ký"),
            ("document_day", "Ngày ký"),
            ("document_month", "Tháng ký"),
            ("document_year", "Năm ký"),
            ("document_place_date", "Dòng địa điểm/ngày tháng"),
        ],
    ),
    (
        HOUSEHOLD_OWNER_SECTION,
        [
            ("applicant_full_name", "Họ tên"),
            ("applicant_date_of_birth", "Ngày sinh"),
            ("applicant_gender", "Giới tính"),
            ("applicant_id_number", "Số định danh cá nhân"),
        ],
    ),
    (
        HOUSEHOLD_DETAILS_SECTION,
        [
            ("company_name", "Tên hộ kinh doanh"),
            ("company_english_name", "Tên bằng tiếng nước ngoài (nếu có)"),
            ("company_short_name", "Tên viết tắt (nếu có)"),
            ("company_address_detail", "Số nhà/phòng, đường/phố, tổ/xóm/ấp/thôn"),
            ("company_ward", "Xã/Phường/Đặc khu"),
            ("company_province", "Tỉnh/Thành phố trực thuộc trung ương"),
            ("company_phone", "Điện thoại"),
            ("company_email", "Thư điện tử (nếu có)"),
        ],
    ),
    ("Ngành nghề kinh doanh", []),
    (
        HOUSEHOLD_CAPITAL_SECTION,
        [
            ("charter_capital_number", "Vốn kinh doanh (VNĐ)"),
            ("charter_capital_full_text", "Bằng số, bằng chữ, VNĐ"),
        ],
    ),
    (HOUSEHOLD_TAX_SECTION, [("tax_labor_count", "Tổng số lao động dự kiến")]),
    (
        "Thông tin người được ủy quyền",
        [
            ("authorized_person_full_name", "Họ tên"),
            ("authorized_person_date_of_birth", "Ngày sinh"),
            ("authorized_person_gender", "Giới tính"),
            ("authorized_person_id_number", "Số CCCD"),
            ("authorized_person_issue_date", "Ngày cấp CCCD"),
            ("authorized_person_issue_place", "Nơi cấp CCCD"),
            ("authorized_person_contact_address", "Địa chỉ liên lạc"),
            ("authorized_person_phone", "Điện thoại"),
            ("authorized_person_email", "Email (nếu có)"),
        ],
    ),
]


class HouseholdBusinessWorkspace(BusinessRegistrationWorkspace):
    """Household-business shell reusing the established registration form and CCCD flow."""

    FORM_SCHEMA_VERSION = HOUSEHOLD_BUSINESS_SCHEMA_VERSION

    def __init__(self, *args, **kwargs) -> None:
        case = kwargs.get("case") or (args[2] if len(args) > 2 else None)
        owner_authorization_values: dict[str, str] = {}
        if case is not None:
            migrated = self._registration_compatible_values(case.form_values)
            owner_authorization_values = {
                "household_owner_issue_date": str(migrated.get("household_owner_issue_date", "") or migrated.get("legal_representative_issue_date", "")),
                "household_owner_issue_place": str(migrated.get("household_owner_issue_place", "") or migrated.get("legal_representative_issue_place", "")),
                "household_owner_contact_address": str(migrated.get("household_owner_contact_address", "") or migrated.get("legal_representative_contact_address", "") or migrated.get("legal_representative_permanent_address", "")),
            }
            case = replace(case, form_values=migrated)
            if "case" in kwargs:
                kwargs["case"] = case
            elif len(args) > 2:
                args = (*args[:2], case, *args[3:])
        self._household_owner_authorization_values = owner_authorization_values
        super().__init__(*args, **kwargs)

    def _create_field(self, key: str):
        field = super()._create_field(key)
        if key == "company_address_detail" and isinstance(field, QLineEdit):
            field.setPlaceholderText(
                "Có thể nhập toàn bộ địa chỉ; ứng dụng sẽ tự tách xã/phường và tỉnh/thành phố"
            )
            field.textChanged.connect(
                lambda _text: self._schedule_address_sync("company_address_detail")
            )
        if key == "document_place" and isinstance(field, QLineEdit):
            field.setReadOnly(False)
            field.setPlaceholderText("Nhập thủ công nơi ký")
            field.textChanged.connect(self._sync_document_place_date)
        if key == "charter_capital_full_text" and isinstance(field, QLineEdit):
            field.setReadOnly(True)
        return field

    @staticmethod
    def _split_household_business_address(address: str) -> tuple[str, str, str] | None:
        """Split a complete typed address using only explicit administrative prefixes."""
        parts = [
            " ".join(part.split()).strip(" ,.;")
            for part in re.split(r"[,;\r\n]+", address or "")
            if part.strip(" ,.;")
        ]
        if not parts:
            return None

        ward = ""
        province = ""
        details: list[str] = []
        ward_prefixes = ("xã ", "phường ", "đặc khu ")
        province_prefixes = ("tỉnh ", "thành phố ")

        for part in parts:
            folded = part.casefold()
            if not ward and folded.startswith(ward_prefixes):
                ward = part
            elif not province and folded.startswith(province_prefixes):
                province = part
            else:
                details.append(part)

        # An incomplete address stays untouched so the user can finish typing
        # or enter the administrative fields manually without losing data.
        if not ward or not province or not details:
            return None
        return ", ".join(details), ward, province

    def _sync_address_parts(self, source_key: str) -> None:
        if source_key != "company_address_detail":
            super()._sync_address_parts(source_key)
            return
        if self.syncing_address_fields:
            return

        split = self._split_household_business_address(self._field_value(source_key))
        if split is None:
            return
        detail, ward, province = split

        self.syncing_address_fields = True
        try:
            self._set_field("company_address_detail", detail)
            self._set_field("company_ward", ward)
            self._set_field("company_province", province)
        finally:
            self.syncing_address_fields = False

    def _form_field_groups(self) -> list[tuple[str, list[tuple[str, str]]]]:
        return HOUSEHOLD_FIELD_GROUPS

    def _person_fill_target_for_section(self, title: str) -> str:
        if title == HOUSEHOLD_OWNER_SECTION:
            return "applicant"
        return super()._person_fill_target_for_section(title)

    def _capture_household_owner_authorization_values(self, data: dict[str, str]) -> None:
        normalized = self._normalize_person_fill_data(data)
        self._household_owner_authorization_values = {
            "household_owner_issue_date": normalized.get("legal_representative_issue_date", "").strip(),
            "household_owner_issue_place": normalized.get("legal_representative_issue_place", "").strip(),
            "household_owner_contact_address": self._authorization_contact_address(normalized).strip(),
        }

    def _fill_section_from_person(self, target: str, person) -> None:
        super()._fill_section_from_person(target, person)
        if target == "applicant":
            self._capture_household_owner_authorization_values(self._person_data_for_fill(person))
            self._refresh_preview()

    def _apply_person_data_to_role(
        self,
        card_values: dict[str, str],
        role: str,
        person_number: int,
        overwrite: bool = False,
    ) -> None:
        super()._apply_person_data_to_role(card_values, role, person_number, overwrite=overwrite)
        if role == "applicant":
            self._capture_household_owner_authorization_values(card_values)

    def _clear_person_fill_target(self, target: str) -> None:
        super()._clear_person_fill_target(target)
        if target == "applicant":
            self._household_owner_authorization_values = {
                "household_owner_issue_date": "",
                "household_owner_issue_place": "",
                "household_owner_contact_address": "",
            }

    def _setup_registration_office_field(self, field: QLineEdit) -> None:
        """Household dossiers require the receiving office to be typed manually."""
        field.setPlaceholderText("Nhập thủ công phòng đăng ký kinh doanh")

    def _sync_document_place_from_registration_office(self) -> None:
        """Do not infer the signing place from the receiving office."""
        self._sync_document_place_date()

    def _fill_registration_office_from_province(self) -> None:
        """Do not infer the receiving office from an address or province."""

    def _parse_registration_office_from_text(self, text: str) -> None:
        """CCCD/QR text must not populate either manual signing field."""

    def _fill_address_parts_from_result(self, target: str, result) -> None:
        """Keep address parsing, without deriving the receiving office."""
        detail = self._address_detail_from_result(result)
        if target == "company_address":
            mapping = {
                "company_address_detail": detail,
                "company_ward": result.ward,
                "company_province": result.province,
            }
        else:
            mapping = {
                "legal_representative_address_detail": detail,
                "legal_representative_ward": result.ward,
                "legal_representative_province": result.province,
            }
        for key, value in mapping.items():
            if value:
                self._set_field(key, value)

    def _apply_value_defaults(self, values: dict[str, str]) -> None:
        manual_place = str(values.get("document_place", "") or "").strip()
        super()._apply_value_defaults(values)
        values["document_place"] = manual_place
        day = str(values.get("document_day", "") or "").strip()
        month = str(values.get("document_month", "") or "").strip()
        year = str(values.get("document_year", "") or "").strip()
        if day and month and year:
            date_text = f"ngày {day} tháng {month} năm {year}"
            values["document_place_date"] = f"{manual_place}, {date_text}" if manual_place else date_text

        capital_text = self._household_capital_text(values.get("charter_capital_number", ""))
        values["charter_capital_full_text"] = capital_text
        digits = self.money_formatter.digits(values.get("charter_capital_number", ""))
        if digits:
            values["charter_capital_number"] = self.money_formatter.format_digits(digits)

    def _handle_capital_number_changed(self, text: str) -> None:
        if self.updating_capital:
            return
        digits = self.money_formatter.digits(text)
        self.updating_capital = True
        try:
            if not digits:
                self._set_field("charter_capital_full_text", "")
                return
            formatted = self.money_formatter.format_digits(digits)
            field = self.fields.get("charter_capital_number")
            if isinstance(field, QLineEdit) and field.text() != formatted:
                field.setText(formatted)
                field.setCursorPosition(len(formatted))
            self._set_field("charter_capital_full_text", self._household_capital_text(digits))
        finally:
            self.updating_capital = False
        self._refresh_preview()

    def _household_capital_text(self, value: str) -> str:
        digits = self.money_formatter.digits(value)
        if not digits:
            return ""
        formatted = self.money_formatter.format_digits(digits)
        words = self.money_formatter.to_words(int(digits)).capitalize()
        return f"{formatted} VNĐ ({words} đồng)"

    def _missing_required_fields(self, values: dict[str, str]) -> list[str]:
        issues = HouseholdBusinessTemplateGenerator.validation_issues(
            self._household_document_values(values)
        )
        return [issue.removeprefix("Chưa có: ") for issue in issues if issue.startswith("Chưa có: ")]

    def _validation_issues(self, values: dict[str, str]) -> list[str]:
        return HouseholdBusinessTemplateGenerator.validation_issues(
            self._household_document_values(values)
        )

    @staticmethod
    def _missing_manual_signing_fields(values: dict[str, str]) -> list[str]:
        required = (
            ("business_registration_office", "Phòng đăng ký kinh doanh"),
            ("document_place", "Nơi ký"),
        )
        return [label for key, label in required if not str(values.get(key, "") or "").strip()]

    def _refresh_form_completion(self, values: dict[str, str]) -> None:
        requirements = {
            "Thông tin cơ quan tiếp nhận và thời gian ký": (
                "business_registration_office", "document_place", "document_day", "document_month", "document_year",
            ),
            HOUSEHOLD_OWNER_SECTION: (
                "applicant_full_name", "applicant_date_of_birth", "applicant_gender", "applicant_id_number",
            ),
            HOUSEHOLD_DETAILS_SECTION: (
                "company_name", "company_address_detail", "company_ward", "company_province", "company_phone",
            ),
            HOUSEHOLD_CAPITAL_SECTION: ("charter_capital_number",),
            HOUSEHOLD_TAX_SECTION: ("tax_labor_count",),
            "Thông tin người được ủy quyền": ("authorized_person_full_name", "authorized_person_id_number"),
        }
        completed_prefix = chr(0x2713) + " "
        for title, button in self.form_nav_buttons.items():
            if title == "Ngành nghề kinh doanh":
                complete = any(
                    values.get(f"business_line_{index}_name", "").strip()
                    and values.get(f"business_line_{index}_code", "").strip()
                    for index in self._business_line_indices(values)
                )
            else:
                fields = requirements.get(title, ())
                complete = bool(fields) and all(values.get(field, "").strip() for field in fields)
            button.setText(completed_prefix + title if complete else title)
            button.setToolTip("Đã nhập đủ thông tin chính" if complete else "Chưa nhập đủ thông tin chính")

    @staticmethod
    def _registration_compatible_values(values: dict[str, str]) -> dict[str, str]:
        """Keep early household drafts readable in the reused registration form."""
        migrated = dict(values)
        aliases = {
            "household_registration_office": "business_registration_office",
            "household_owner_full_name": "applicant_full_name",
            "household_owner_date_of_birth": "applicant_date_of_birth",
            "household_owner_gender": "applicant_gender",
            "household_owner_id_number": "applicant_id_number",
            "household_owner_issue_date": "legal_representative_issue_date",
            "household_owner_issue_place": "legal_representative_issue_place",
            "household_owner_contact_address": "legal_representative_contact_address",
            "household_business_name": "company_name",
            "household_foreign_name": "company_english_name",
            "household_short_name": "company_short_name",
            "household_address_detail": "company_address_detail",
            "household_ward": "company_ward",
            "household_province": "company_province",
            "household_phone": "company_phone",
            "household_email": "company_email",
            "household_capital": "charter_capital_number",
        }
        for source, target in aliases.items():
            if migrated.get(source) and not migrated.get(target):
                migrated[target] = migrated[source]
        legacy_owner_aliases = {
            "legal_representative_full_name": "applicant_full_name",
            "legal_representative_date_of_birth": "applicant_date_of_birth",
            "legal_representative_gender": "applicant_gender",
            "legal_representative_id_number": "applicant_id_number",
            "company_foreign_name": "company_english_name",
        }
        for source, target in legacy_owner_aliases.items():
            if migrated.get(source) and not migrated.get(target):
                migrated[target] = migrated[source]
        for key, value in tuple(migrated.items()):
            if key.startswith("household_line_"):
                migrated.setdefault(key.replace("household_line_", "business_line_", 1), value)
        return migrated

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        back_button = QPushButton("← Quay lại")
        back_button.setObjectName("GhostButton")
        back_button.clicked.connect(self.on_back)

        text = QVBoxLayout()
        title = QLabel("Tạo hồ sơ thành lập hộ kinh doanh")
        title.setObjectName("PageTitle")
        description = QLabel(
            "Quét QR CCCD, chuẩn hóa địa chỉ, kiểm tra dữ liệu và xuất bộ hồ sơ thành lập hộ kinh doanh."
        )
        description.setObjectName("PageDescription")
        description.setWordWrap(True)
        text.addWidget(title)
        text.addWidget(description)

        save_button = QPushButton("Lưu nháp")
        save_button.setObjectName("GhostButton")
        save_button.clicked.connect(self._save_draft)

        export_button = QPushButton("Xuất hồ sơ")
        export_button.setObjectName("PrimaryButton")
        export_button.clicked.connect(self._export_documents)

        header.addWidget(back_button)
        header.addLayout(text, 1)
        header.addWidget(save_button)
        header.addWidget(export_button)
        return header

    def form_values(self, apply_defaults: bool = True) -> dict[str, str]:
        values = super().form_values(apply_defaults=apply_defaults)
        values["household_schema_version"] = str(self.FORM_SCHEMA_VERSION)
        return self._household_document_values(values)

    def _household_document_values(self, values: dict[str, str]) -> dict[str, str]:
        mapped = dict(values)
        mapped.update(self._household_owner_authorization_values)
        aliases = {
            "business_registration_office": "household_registration_office",
            "applicant_full_name": "household_owner_full_name",
            "applicant_date_of_birth": "household_owner_date_of_birth",
            "applicant_gender": "household_owner_gender",
            "applicant_id_number": "household_owner_id_number",
            "company_name": "household_business_name",
            "company_english_name": "household_foreign_name",
            "company_short_name": "household_short_name",
            "company_address_detail": "household_address_detail",
            "company_ward": "household_ward",
            "company_province": "household_province",
            "company_phone": "household_phone",
            "company_email": "household_email",
            "charter_capital_number": "household_capital",
            "tax_labor_count": "household_labor_count",
        }
        for source, target in aliases.items():
            mapped[target] = str(mapped.get(source, "") or "").strip()
        mapped.setdefault("household_subject_type", "individual")
        for key, value in tuple(mapped.items()):
            if key.startswith("business_line_"):
                mapped[key.replace("business_line_", "household_line_", 1)] = value
        return mapped

    def build_case_summary(self, *args, **changes) -> CaseSummary:
        summary = super().build_case_summary(*args, **changes)
        return replace(
            summary,
            case_type=HOUSEHOLD_BUSINESS_CASE_TYPE,
            company_name=summary.form_values.get("company_name") or "Hồ sơ thành lập hộ kinh doanh mới",
            form_schema_version=self.FORM_SCHEMA_VERSION,
        )

    def _document_generator_class(self) -> type:
        return HouseholdBusinessTemplateGenerator

    def _template_and_export_dirs(self) -> tuple[Path, Path]:
        return (
            self.bundle_root / "assets" / "templates" / "word" / "household_business",
            self.selected_export_root or self.default_export_root,
        )

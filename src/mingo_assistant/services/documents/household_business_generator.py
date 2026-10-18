"""Generate household-business documents from explicitly mapped yellow slots."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
from pathlib import Path
import re
import shutil

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

from mingo_assistant.core.text_normalization import uppercase_authorized_person_name
from mingo_assistant.domains.business_registration.money import VietnameseMoneyFormatter
from mingo_assistant.services.documents.generation_result import GeneratedDocument, GenerationResult

REQUEST_TEMPLATE = "1. Giay de nghi thanh lap.docx"
REQUEST_SOURCE_TEMPLATE = "1. Giay de nghi thanh lap.code.docx"
AUTHORIZATION_TEMPLATE = "2. Giay uy quyen.docx"
AUTHORIZATION_SOURCE_TEMPLATE = "2. Giay uy quyen.code.docx"
TEMPLATE_SOURCES = {
    REQUEST_TEMPLATE: REQUEST_SOURCE_TEMPLATE,
    AUTHORIZATION_TEMPLATE: AUTHORIZATION_SOURCE_TEMPLATE,
}
TEMPLATE_HASHES = {
    REQUEST_TEMPLATE: "2d4f7291dc4682ce499cff799e6946a2d510306f02a90683ce6a94c29c4a54a7",
    AUTHORIZATION_TEMPLATE: "bf34644fc6c6d58c944c88bab2064af7461650a4e838961af6525a5769568b98",
}


def _selected(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "x", "true", "yes", "có"}


def _highlighted_runs(paragraph):
    return [run for run in paragraph.runs if run.font.highlight_color is not None]


def _write_yellow(paragraph, replacements: list[str | None]) -> None:
    runs = _highlighted_runs(paragraph)
    if len(runs) != len(replacements):
        raise ValueError("Vị trí vùng vàng của mẫu đã thay đổi")
    for run, replacement in zip(runs, replacements):
        if replacement is not None:
            run.text = str(replacement)


def _money_text(value: str) -> str:
    digits = re.sub(r"[^0-9]", "", value or "")
    if not digits:
        return ""
    amount = int(digits)
    formatter = VietnameseMoneyFormatter()
    return f"{formatter.format_digits(str(amount))} VNĐ ({formatter.to_words(amount).capitalize()} đồng)"


class HouseholdBusinessTemplateGenerator:
    """Fill only reviewed yellow runs; all other template XML stays untouched."""

    def __init__(self, template_dir: Path, export_root: Path) -> None:
        self.template_dir = template_dir
        self.export_root = export_root

    def validate_templates(self, _values: dict[str, str] | None = None) -> dict[str, list[str]]:
        issues: dict[str, list[str]] = {}
        for name, expected in TEMPLATE_HASHES.items():
            path = self.template_dir / TEMPLATE_SOURCES[name]
            try:
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                issues[name] = ["Không tìm thấy mẫu Word"]
                continue
            if actual != expected:
                issues[name] = ["Mẫu đã thay đổi; cần rà soát lại mapping vùng vàng"]
        return issues

    @staticmethod
    def validation_issues(values: dict[str, str]) -> list[str]:
        required = {
            "household_registration_office": "Cơ quan tiếp nhận",
            "document_place": "Nơi ký",
            "document_day": "Ngày ký",
            "document_month": "Tháng ký",
            "document_year": "Năm ký",
            "household_owner_full_name": "Họ tên chủ hộ",
            "household_owner_date_of_birth": "Ngày sinh chủ hộ",
            "household_owner_gender": "Giới tính chủ hộ",
            "household_owner_id_number": "Số định danh cá nhân",
            "household_owner_issue_date": "Ngày cấp CCCD của chủ hộ",
            "household_owner_issue_place": "Nơi cấp CCCD của chủ hộ",
            "household_owner_contact_address": "Địa chỉ liên lạc của chủ hộ",
            "household_business_name": "Tên hộ kinh doanh",
            "household_address_detail": "Địa chỉ trụ sở",
            "household_ward": "Xã/Phường/Đặc khu",
            "household_province": "Tỉnh/Thành phố",
            "household_phone": "Điện thoại hộ kinh doanh",
            "household_capital": "Vốn kinh doanh",
            "household_labor_count": "Số lao động dự kiến",
            "authorized_person_full_name": "Người nhận ủy quyền",
            "authorized_person_id_number": "CCCD người nhận ủy quyền",
            "authorized_person_issue_date": "Ngày cấp CCCD người nhận ủy quyền",
            "authorized_person_issue_place": "Nơi cấp CCCD người nhận ủy quyền",
            "authorized_person_contact_address": "Địa chỉ liên lạc người nhận ủy quyền",
            "authorized_person_phone": "Điện thoại người nhận ủy quyền",
        }
        issues = [f"Chưa có: {label}" for key, label in required.items() if not values.get(key, "").strip()]
        if values.get("household_subject_type", "individual") == "family":
            issues.append("Mẫu hiện chưa có vùng vàng cho dữ liệu thành viên hộ gia đình; chưa thể xuất nhánh này an toàn")
        line_keys = [key for key, value in values.items() if re.fullmatch(r"household_line_\d+_name", key) and value.strip()]
        if not line_keys:
            issues.append("Chưa có ngành nghề kinh doanh")
        if line_keys and sum(_selected(values.get(key.replace("_name", "_is_main"))) for key in line_keys) != 1:
            issues.append("Phải chọn đúng một ngành nghề kinh doanh chính")
        try:
            datetime.strptime("/".join(values.get(k, "") for k in ("document_day", "document_month", "document_year")), "%d/%m/%Y")
        except ValueError:
            issues.append("Ngày ký không hợp lệ")
        return issues

    def generate(
        self,
        values: dict[str, str],
        _case_name: str = "",
        output_dir: Path | None = None,
    ) -> GenerationResult:
        template_issues = self.validate_templates()
        destination = output_dir or self.export_root
        if template_issues:
            return GenerationResult(destination, [], list(template_issues), template_issues)
        issues = self.validation_issues(values)
        if issues:
            return GenerationResult(destination, [], [], {"Dữ liệu hồ sơ": issues})
        destination.mkdir(parents=True, exist_ok=True)
        generated: list[GeneratedDocument] = []
        for name, filler in ((REQUEST_TEMPLATE, self._fill_request), (AUTHORIZATION_TEMPLATE, self._fill_authorization)):
            source = self.template_dir / TEMPLATE_SOURCES[name]
            target = destination / name
            shutil.copy2(source, target)
            document = Document(target)
            filler(document, values)
            document.save(target)
            generated.append(GeneratedDocument(name, target))
        return GenerationResult(destination, generated, [], {})

    def _fill_request(self, document: Document, values: dict[str, str]) -> None:
        p = document.paragraphs
        _write_yellow(p[1], [values["document_place"], values["document_day"], values["document_month"], values["document_year"]])
        for index, key in ((4, "household_registration_office"), (5, "household_owner_full_name"), (6, "household_owner_date_of_birth"), (7, "household_owner_gender"), (8, "household_owner_id_number")):
            _write_yellow(p[index], [values[key]])
        _write_yellow(p[13], [values["household_business_name"].upper()])
        _write_yellow(p[14], [values.get("household_foreign_name") or None])
        _write_yellow(p[15], [values.get("household_short_name") or None])
        for index, key in ((17, "household_address_detail"), (18, "household_ward"), (19, "household_province"), (20, "household_phone")):
            _write_yellow(p[index], [values[key]])
        _write_yellow(p[21], [values.get("household_email") or None])
        _write_yellow(p[25], [_money_text(values["household_capital"])])
        _write_yellow(p[33], [values["household_labor_count"]])
        self._fill_industries(document.tables[1], values)
        subject = values.get("household_subject_type", "individual")
        _write_yellow(document.tables[3].cell(0, 0).paragraphs[0], ["☒" if subject == "individual" else "☐"])
        _write_yellow(document.tables[3].cell(0, 1).paragraphs[0], ["☒" if subject == "family" else "☐"])
        _write_yellow(
            document.tables[5].cell(0, 1).paragraphs[6],
            [values["household_owner_full_name"].upper()],
        )

    @staticmethod
    def _fill_industries(table, values: dict[str, str]) -> None:
        indices = sorted({int(match.group(1)) for key in values if (match := re.fullmatch(r"household_line_(\d+)_name", key)) and values[key].strip()})
        prototype = deepcopy(table.rows[-1]._tr)
        for row in list(table.rows[1:]):
            table._tbl.remove(row._tr)
        for position, index in enumerate(indices, 1):
            table._tbl.append(deepcopy(prototype))
            row = table.rows[-1]
            name = values.get(f"household_line_{index}_name", "").strip()
            detail = values.get(f"household_line_{index}_detail", "").strip()
            name_and_detail = f"{name}\n{detail}" if detail else name
            is_main = _selected(values.get(f"household_line_{index}_is_main"))
            data = [
                str(position),
                name_and_detail,
                values.get(f"household_line_{index}_code", ""),
                "X" if is_main else "",
            ]
            for column, (cell, value) in enumerate(zip(row.cells, data)):
                runs = _highlighted_runs(cell.paragraphs[0])
                if not runs:
                    raise ValueError("Dòng ngành nghề không còn là vùng vàng")
                runs[0].text = value
                if column == 1:
                    cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
                if column == 3:
                    runs[0].bold = is_main
                for extra in runs[1:]:
                    extra.text = ""

    def _fill_authorization(self, document: Document, values: dict[str, str]) -> None:
        p = document.paragraphs
        authorized_person_name = uppercase_authorized_person_name(
            values.get("authorized_person_full_name", "")
        )
        _write_yellow(p[5], [values["household_owner_full_name"]])
        _write_yellow(p[6], [values["household_owner_id_number"]])
        _write_yellow(p[7], [values.get("household_owner_issue_date", ""), values.get("household_owner_issue_place", "")])
        _write_yellow(p[8], [values.get("household_owner_contact_address", "")])
        _write_yellow(p[10], [authorized_person_name])
        _write_yellow(p[11], [values["authorized_person_id_number"]])
        _write_yellow(p[12], [values.get("authorized_person_issue_date", ""), values.get("authorized_person_issue_place", "")])
        _write_yellow(p[13], [values.get("authorized_person_contact_address", "")])
        _write_yellow(p[14], [values.get("authorized_person_phone", ""), values.get("authorized_person_email", "")])
        _write_yellow(p[16], [values["household_registration_office"], "", values["household_business_name"].upper()])
        _write_yellow(p[24], [values["document_place"], values["document_day"], values["document_month"], values["document_year"]])
        _write_yellow(document.tables[0].cell(0, 0).paragraphs[5], [authorized_person_name])
        _write_yellow(document.tables[0].cell(0, 1).paragraphs[5], [values["household_owner_full_name"].upper()])

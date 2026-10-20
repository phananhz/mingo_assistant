"""Template-safe generation for dependent-unit procedures."""
from __future__ import annotations

import copy
import re
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from mingo_assistant.domains.dependent_unit.location_changes import (
    entered_location_changes, normalize_location_update_tax_values,
)
from mingo_assistant.services.documents.docx_template_engine import DocxTemplateEngine
from mingo_assistant.services.documents.generation_result import GeneratedDocument, GenerationResult
from mingo_assistant.services.documents.template_manifest import TemplateManifest


class DependentUnitTemplateGenerator(DocxTemplateEngine):
    """Change only highlighted runs explicitly declared in a procedure manifest."""

    FOREIGN_AUTHORIZATION_TEMPLATE = "2. Giay uy quyen dai dien phap luat nuoc ngoai.docx"

    _TAX_OPTIONAL_TEXT_FIELDS = (
        "tax_accountant_full_name",
        "tax_accountant_date_of_birth",
        "tax_accountant_gender",
        "tax_accountant_id_number",
        "tax_accountant_phone",
        "tax_notification_address_detail",
        "tax_notification_ward",
        "tax_notification_province",
        "tax_notification_phone",
        "tax_notification_fax",
        "tax_notification_email",
    )
    _NOTIFICATION_CHANGE_TARGETS = {
        "new_location_business_name": "change_name_selected",
        "new_location_business_english_name": "change_name_selected",
        "new_location_business_short_name": "change_name_selected",
        "new_location_address_detail": "change_address_selected",
        "new_location_ward": "change_address_selected",
        "new_location_province": "change_address_selected",
        "new_location_phone": "change_address_selected",
        "new_location_fax": "change_address_selected",
        "new_location_email": "change_address_selected",
        "new_location_website": "change_address_selected",
        "location_manager_full_name": "change_manager_selected",
        "location_manager_date_of_birth": "change_manager_selected",
        "location_manager_gender": "change_manager_selected",
        "location_manager_id_number": "change_manager_selected",
        "location_manager_address_detail": "change_manager_selected",
        "location_manager_ward": "change_manager_selected",
        "location_manager_province": "change_manager_selected",
        "location_manager_nationality": "change_manager_selected",
        "location_manager_phone": "change_manager_selected",
        "location_manager_email": "change_manager_selected",
        "tax_accountant_full_name": "change_tax_selected",
        "tax_accountant_date_of_birth": "change_tax_selected",
        "tax_accountant_gender": "change_tax_selected",
        "tax_accountant_id_number": "change_tax_selected",
        "tax_accountant_phone": "change_tax_selected",
        "tax_notification_address_detail": "change_tax_selected",
        "tax_notification_ward": "change_tax_selected",
        "tax_notification_province": "change_tax_selected",
        "tax_notification_phone": "change_tax_selected",
        "tax_notification_email": "change_tax_selected",
        "tax_accounting_independent_x": "change_tax_selected",
        "tax_accounting_consolidated_x": "change_tax_selected",
        "tax_accounting_dependent_x": "change_tax_selected",
        "tax_financial_year_start": "change_tax_selected",
        "tax_financial_year_end": "change_tax_selected",
        "tax_labor_count": "change_tax_selected",
        "supplemental_registration_content_1": "change_supplemental_selected",
        "supplemental_registration_content_2": "change_supplemental_selected",
        "supplemental_registration_content_3": "change_supplemental_selected",
    }

    def __init__(self, template_dir: Path, export_root: Path) -> None:
        self.template_dir = template_dir
        self.export_root = export_root
        self.manifest = TemplateManifest(template_dir / "template_manifest.json")

    def generate(self, values: dict[str, str], case_name: str, output_dir: Path | None = None) -> GenerationResult:
        if output_dir is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = self.export_root / f"{self._safe_filename(case_name)}_{stamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        generated: list[GeneratedDocument] = []
        unresolved: dict[str, list[str]] = {}
        for template in self._templates(values):
            output_path = output_dir / self._output_filename(template.name, values, case_name)
            shutil.copy2(template, output_path)
            if self._mode(template.name) == "fill_highlighted":
                self._replace_highlighted_runs(output_path, template.name, values)
                remaining = self.unresolved_placeholders(output_path)
                if remaining:
                    unresolved[template.name] = remaining
            generated.append(GeneratedDocument(template.name, output_path))
        return GenerationResult(output_dir, generated, [], unresolved)

    def validate_templates(self, values: dict[str, str]) -> dict[str, list[str]]:
        if not self.template_dir.exists():
            return {"Th\u01b0 m\u1ee5c m\u1eabu": [str(self.template_dir)]}
        report: dict[str, list[str]] = {}
        with tempfile.TemporaryDirectory(dir=self.export_root if self.export_root.exists() else None) as temporary:
            for template in self._templates(values):
                if self._mode(template.name) != "fill_highlighted":
                    continue
                candidate = Path(temporary) / template.name
                shutil.copy2(template, candidate)
                self._replace_highlighted_runs(candidate, template.name, values)
                remaining = self.unresolved_placeholders(candidate)
                if remaining:
                    report[template.name] = remaining
        return report

    def _output_filename(self, template_name: str, values: dict[str, str], case_name: str) -> str:
        folded_template_name = self._fold(template_name)
        label = (
            'Thong bao thay doi' if folded_template_name.startswith('thong bao thay doi') else
            'Thong bao lap dia diem' if template_name.startswith('1.') else
            'Giay uy quyen' if template_name.startswith('2.') or folded_template_name.startswith('giay uy quyen') else
            'Huong dan ky'
        )
        name = values.get('parent_entity_name') or values.get('company_name') or case_name
        name = self._fold(name)
        name = re.sub(r'^(cong ty|doanh nghiep)\s*', '', name)
        name = re.sub(r'^(tnhh|co phan|hop danh|tu nhan)\s*', '', name)
        name = re.sub(r'^(mot thanh vien|hai thanh vien)\s*', '', name)
        suffix = ''.join(word.capitalize() for word in re.findall(r'[a-zA-Z0-9]+', name)) or 'HoSo'
        return f'{label}_{suffix}.docx'

    def unresolved_placeholders(self, docx_path: Path) -> list[str]:
        """Report placeholder text, not drawing metadata that happens to use brackets."""
        matches: list[str] = []
        with zipfile.ZipFile(docx_path, "r") as archive:
            for entry in archive.infolist():
                if not entry.filename.startswith("word/") or not entry.filename.endswith(".xml"):
                    continue
                xml = archive.read(entry.filename).decode("utf-8", "ignore")
                for text_node in re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", xml, flags=re.DOTALL):
                    matches.extend(re.findall(r"\[([^\[\]\r\n]{1,120})\]", text_node))
        return sorted(set(matches))

    def _templates(self, values: dict[str, str] | None = None) -> list[Path]:
        if not self.template_dir.exists():
            return []
        foreign_legal_representative = self._is_foreign_legal_representative(values or {})
        templates: list[Path] = []
        for path in sorted(self.template_dir.iterdir()):
            if path.suffix.lower() != ".docx" or path.name.startswith("~$"):
                continue
            if path.name == self.FOREIGN_AUTHORIZATION_TEMPLATE:
                if not foreign_legal_representative:
                    continue
            elif path.name.startswith("2.") and foreign_legal_representative:
                continue
            templates.append(path)
        return templates

    def _is_foreign_legal_representative(self, values: dict[str, str]) -> bool:
        return self._fold(str(values.get("legal_representative_person_type", "") or "")).strip() == "nguoi nuoc ngoai"

    def _manifest(self) -> dict[str, object]:
        manifest = getattr(self, "manifest", None)
        if manifest is None:
            manifest = TemplateManifest(self.template_dir / "template_manifest.json")
            self.manifest = manifest
        return manifest.load()

    def _config(self, template_name: str) -> dict[str, object]:
        manifest = getattr(self, "manifest", None)
        if manifest is None:
            self._manifest()
            manifest = self.manifest
        return manifest.template(template_name)

    def _mode(self, template_name: str) -> str:
        return str(self._config(template_name).get("mode", "copy"))

    def _template_part_manifest(self, template_name: str, part_name: str) -> dict[str, object]:
        """Adapt this procedure's compact manifest to the shared DOCX engine."""
        if part_name != "word/document.xml":
            return {}
        return self._config(template_name)

    @classmethod
    def _notification_selection_flag(cls, target: str) -> str:
        return cls._NOTIFICATION_CHANGE_TARGETS.get(target, "")

    def _should_preserve_highlighted_placeholder(
        self, template_name: str, target: str, values: dict[str, str]
    ) -> bool:
        """Fill notification runs from entered data, never from UI visibility state."""
        if self._fold(template_name).startswith("thong bao thay doi"):
            selection_flag = self._notification_selection_flag(target)
            if selection_flag:
                # The checkbox only opens or hides its UI form. A supplied
                # value must always replace its own yellow template run.
                return not str(self._value_for_template_target(target, values) or "").strip()
        return template_name.startswith("1.") and target in {
            "tax_accounting_dependent_x",
            "tax_bot_project_x",
            "tax_vat_deduction_x",
        }

    def _assert_notification_highlight_count(self, document: Document, template_name: str) -> None:
        """Fail clearly when a protected notification template no longer matches its manifest."""
        if not self._fold(template_name).startswith("thong bao thay doi"):
            return
        config = self._config(template_name)
        expected = config.get("expected_highlight_count")
        if expected is None:
            return
        actual = sum(
            1
            for paragraph in self._iter_paragraphs(document)
            for run in paragraph.runs
            if run.font.highlight_color == WD_COLOR_INDEX.YELLOW
        )
        if actual != int(expected):
            raise ValueError(
                f"Template {template_name} has {actual} yellow-highlight runs; "
                f"the manifest expects {expected}. Update the mapping before export."
            )

    def _empty_highlighted_placeholder(self, run, target: str, values: dict[str, str]) -> str:
        """Keep untouched yellow template runs exactly as supplied."""
        if target == "__clear" or target.endswith("_x") or target.endswith("_is_main"):
            return ""
        template_text = str(getattr(run, "text", "") or "")
        stripped = template_text.strip()
        if stripped and re.fullmatch(r"[\s.\u2026/\u00b7_-]+", stripped):
            return template_text
        if any(part in target for part in ("date", "day", "month", "year")):
            return "\u2026\u2026/\u2026\u2026/\u2026\u2026"
        width = min(max(len(stripped), 10), 48)
        return "." * width

    def _replace_highlighted_runs(self, docx_path: Path, template_name: str, values: dict[str, str]) -> None:
        """Use the company-dossier writer, then apply this form's protected tables."""
        is_update_notification = self._fold(template_name).startswith('thong bao thay doi')
        if is_update_notification:
            values = normalize_location_update_tax_values(values)
        document = Document(docx_path)
        highlighted_values = dict(values)
        foreign_location_manager = (
            self._fold(str(values.get("location_manager_person_type", "") or "")).strip()
            == "nguoi nuoc ngoai"
        )
        if template_name.startswith("1.") and foreign_location_manager:
            # Section 4 has one identity-number slot.  For a foreign manager
            # that slot is the passport number, while the contact-address
            # slots remain the same for both person types.
            highlighted_values["location_manager_id_number"] = values.get(
                "location_manager_passport_number", ""
            )
            if not str(highlighted_values.get("location_manager_address_detail", "") or "").strip():
                highlighted_values["location_manager_address_detail"] = values.get(
                    "location_manager_foreign_address_detail", ""
                )
            if not str(highlighted_values.get("location_manager_nationality", "") or "").strip():
                highlighted_values["location_manager_nationality"] = values.get(
                    "location_manager_foreign_country", ""
                )
        if highlighted_values.get('legal_representative_person_type') == 'Người nước ngoài':
            highlighted_values['legal_representative_id_number'] = values.get('legal_representative_passport_number', '')
        if template_name.startswith('H'):
            highlighted_values['legal_representative_full_name'] = str(values.get('legal_representative_full_name', '')).title()
        # Symbol checkboxes are completed manually in the final Word file.
        # Never write an X automatically into a highlighted checkbox slot.
        for key in (
            "tax_accounting_independent_x",
            "tax_accounting_consolidated_x",
            "tax_accounting_dependent_x",
            "tax_bot_project_x",
            "tax_vat_deduction_x",
        ):
            highlighted_values[key] = ""
        if is_update_notification:
            # The protected template still has three legacy yellow slots for
            # Part B, but the form now supplies one unrestricted plain-text
            # statement. Put the complete content into the first slot and
            # clear the legacy slots so their spare paragraphs can be removed.
            supplemental_content = self._notification_supplemental_content(values)
            highlighted_values["supplemental_registration_content"] = supplemental_content
            highlighted_values["supplemental_registration_content_1"] = supplemental_content
            highlighted_values["supplemental_registration_content_2"] = ""
            highlighted_values["supplemental_registration_content_3"] = ""
        self._assert_notification_highlight_count(document, template_name)
        self._active_template_name = template_name
        try:
            DocxTemplateEngine._replace_highlighted_runs(self, document, template_name, highlighted_values)
        finally:
            self._active_template_name = ""
        if is_update_notification:
            self._normalize_notification_entered_value_fonts(document, template_name, highlighted_values)
            self._remove_name_tab_stops_for_entered_values(document, values)
            self._remove_address_contact_dotted_fillers(document, values)
            self._fill_notification_person_fields(document, values)
            self._remove_notification_inline_dotted_leaders(document, values)
            self._collapse_notification_supplemental_lines(document, highlighted_values)
            self._repair_notification_manager_email_label(document)
            self._remove_manager_date_separators_for_entered_value(document, values)
        if template_name.startswith('2.') and values.get('legal_representative_person_type') == 'Người nước ngoài':
            for paragraph in self._iter_paragraphs(document):
                if self._fold(paragraph.text).startswith('so dinh danh ca nhan'):
                    for run in paragraph.runs:
                        run.text = run.text.replace('Số định danh cá nhân', 'Số hộ chiếu')
                    break
        if not is_update_notification or self._business_lines(values):
            business_line_values = dict(values)
            DocxTemplateEngine._replace_business_lines_tables_v2(
                self,
                document,
                business_line_values,
                keep_file1_business_line_numbers_on_one_line=True,
            )
            self._remove_empty_business_line_rows(document, values)
        self._restore_foreign_permanent_address_placeholder(document, template_name)
        if template_name.startswith('H'):
            signer = str(values.get('legal_representative_full_name', '')).strip()
            if signer:
                for paragraph in self._iter_paragraphs(document):
                    for run in paragraph.runs:
                        if run.font.highlight_color == WD_COLOR_INDEX.YELLOW and run.text.strip().casefold() == signer.casefold():
                            run.text = signer.title()
        if template_name.startswith('1.'):
            for paragraph in self._iter_paragraphs(document):
                folded = self._fold(paragraph.text)
                if '6. thong tin dang ky thue' in folded:
                    for run in paragraph.runs:
                        run.font.size = Pt(13)
                        run.font.bold = True
                elif 'ca nhan duoi day' in folded:
                    for run in paragraph.runs:
                        run.font.size = Pt(13)
        if is_update_notification:
            self._remove_empty_notification_sections(document, values)
        document.save(docx_path)

    def _remove_empty_notification_sections(self, document: Document, values: dict[str, str]) -> None:
        """Prune whole unused blocks only after all original slots are filled.

        A populated block retains its blank child fields, labels and tables.
        UI checkbox state never controls export. The retired correction block
        is always removed, while the common commitments and signer are kept.
        """
        headings = (
            ("dang ky thay doi ten dia diem kinh doanh", "change_name_selected"),
            ("dang ky thay doi dia chi dia diem kinh doanh", "change_address_selected"),
            ("dang ky thay doi nganh, nghe kinh doanh/noi dung hoat dong", "change_business_lines_selected"),
            ("dang ky thay doi nguoi dung dau dia diem kinh doanh", "change_manager_selected"),
            ("dang ky thay doi thong tin dang ky thue", "change_tax_selected"),
            ("b. bo sung, cap nhat thong tin dang ky hoat dong", "change_supplemental_selected"),
            ("c. de nghi hieu dinh thong tin dang ky hoat dong", "change_correction_selected"),
        )
        elements = list(document.element.body)
        boundaries: list[tuple[int, str]] = []
        text_by_index: dict[int, str] = {}
        for index, element in enumerate(elements):
            if element.tag != qn("w:p"):
                continue
            text = re.sub(r"\s+", " ", self._fold("".join(element.xpath(".//w:t/text()")))).strip()
            text_by_index[index] = text
            for prefix, section in headings:
                if text.startswith(prefix):
                    boundaries.append((index, section))
                    break
        if not boundaries:
            return
        closing = next((
            index for index, text in text_by_index.items()
            if index > boundaries[-1][0]
            and text.startswith("doanh nghiep cam ket hoan toan chiu trach nhiem")
        ), None)
        if closing is None:
            raise ValueError("Không xác định được phần cam kết cuối mẫu Thông báo thay đổi; chưa xóa đầu mục.")

        populated = set(entered_location_changes(values))
        remove_indices: set[int] = set()
        for position, (start, section) in enumerate(boundaries):
            stop = boundaries[position + 1][0] if position + 1 < len(boundaries) else closing
            if section not in populated:
                remove_indices.update(range(start, stop))
        # Part A is only a wrapper for its five change sections. Do not leave
        # an empty Part A heading when the user only provides Part B content.
        if not populated.intersection({section for _prefix, section in headings[:5]}):
            part_a = next((
                index for index, text in text_by_index.items()
                if index < boundaries[0][0] and text.startswith("a. dang ky thay doi noi dung")
            ), None)
            if part_a is not None:
                remove_indices.update(range(part_a, boundaries[0][0]))
        for index in sorted(remove_indices, reverse=True):
            element = elements[index]
            if element.xpath(".//w:sectPr"):
                raise ValueError("Đầu mục cần xóa chứa thiết lập trang; cần kiểm tra lại cấu trúc mẫu Word.")
            document.element.body.remove(element)
        # The source has nine padding paragraphs after the signing table.
        # Once sections are pruned they can spill onto a completely blank last
        # page. Keep one final paragraph after the table; never alter its rows,
        # signature space, or any paragraph containing runs/section settings.
        trailing = []
        for element in reversed(list(document.element.body)):
            if element.tag == qn("w:sectPr"):
                continue
            if element.tag != qn("w:p") or any(child.tag != qn("w:pPr") for child in element):
                break
            if element.xpath(".//w:sectPr"):
                break
            trailing.append(element)
        for element in trailing[1:]:
            document.element.body.remove(element)

    def _normalize_notification_entered_value_fonts(
        self, document: Document, template_name: str, values: dict[str, str]
    ) -> None:
        """Keep every entered yellow notification value at the template's 12.5pt size."""
        highlighted_fields = self._config(template_name).get("highlighted_fields", {})
        highlighted_index = 0
        for paragraph in self._iter_paragraphs(document):
            for run in paragraph.runs:
                if run.font.highlight_color != WD_COLOR_INDEX.YELLOW:
                    continue
                target = highlighted_fields.get(str(highlighted_index), "")
                highlighted_index += 1
                if not target:
                    continue
                value = str(self._value_for_template_target(target, values) or "").strip()
                if not value:
                    continue
                properties = run._r.get_or_add_rPr()
                for tag in (qn("w:sz"), qn("w:szCs")):
                    for element in list(properties.findall(tag)):
                        properties.remove(element)
                    size = OxmlElement("w:sz" if tag == qn("w:sz") else "w:szCs")
                    size.set(qn("w:val"), "25")
                    properties.append(size)

    def _fill_notification_person_fields(self, document: Document, values: dict[str, str]) -> None:
        """Fill the protected person blocks using the template's own 12.5pt runs.

        A few yellow-looking slots in this legacy form are shading rather than
        Word ``highlight`` runs, so they cannot safely be addressed by the
        ordinal highlight manifest.  Replace only their dotted runs, retain the
        source run properties, and remove tab leaders once a value exists.
        """
        paragraphs = list(self._iter_paragraphs(document))
        manager_start = next(
            (index for index, paragraph in enumerate(paragraphs)
             if "dang ky thay doi nguoi dung dau dia diem kinh doanh" in self._fold(paragraph.text)),
            None,
        )
        manager_end = next(
            (index for index, paragraph in enumerate(paragraphs)
             if "dang ky thay doi thong tin dang ky thue" in self._fold(paragraph.text)),
            len(paragraphs),
        )
        if manager_start is not None:
            manager_fields = (
                ("ho chu dem va ten", "location_manager_full_name"),
                ("ngay thang nam sinh", "location_manager_date_of_birth"),
                ("gioi tinh", "location_manager_gender"),
                ("so dinh danh ca nhan", "location_manager_id_number"),
                ("so nha/phong", "location_manager_address_detail"),
                ("xa/phuong", "location_manager_ward"),
                ("tinh/thanh pho", "location_manager_province"),
                ("quoc gia", "location_manager_nationality"),
            )
            manager_paragraphs = paragraphs[manager_start:manager_end]
            for label, target in manager_fields:
                self._fill_notification_inline_field(manager_paragraphs, label, values.get(target, ""))

        accountant_paragraphs = []
        for table in document.tables:
            table_text = "\n".join(cell.text for row in table.rows for cell in row.cells)
            if "thong tin ve ke toan truong" not in self._fold(table_text):
                continue
            accountant_paragraphs = [
                paragraph for row in table.rows for cell in row.cells for paragraph in cell.paragraphs
            ]
            break
        if not accountant_paragraphs:
            return
        accountant_fields = (
            ("ho chu dem va ten ke toan truong", "tax_accountant_full_name"),
            ("ngay thang nam sinh", "tax_accountant_date_of_birth"),
            ("gioi tinh", "tax_accountant_gender"),
            ("so dinh danh ca nhan", "tax_accountant_id_number"),
            ("dien thoai", "tax_accountant_phone"),
        )
        for label, target in accountant_fields:
            self._fill_notification_inline_field(accountant_paragraphs, label, values.get(target, ""))

    def _remove_notification_inline_dotted_leaders(self, document: Document, values: dict[str, str]) -> None:
        """Remove a legacy dotted tab leader before an entered inline person value."""
        fields = (
            ("ho, chu dem va ten (ghi bang chu in hoa)", "location_manager_full_name"),
            ("ho, chu dem va ten ke toan truong", "tax_accountant_full_name"),
        )
        for label, target in fields:
            value = str(values.get(target, "") or "").strip()
            if not value:
                continue
            paragraph = next(
                (item for item in self._iter_paragraphs(document) if label in self._fold(item.text)),
                None,
            )
            if paragraph is None:
                continue
            value_index = next(
                (index for index, run in enumerate(paragraph.runs) if value in str(run.text or "")),
                None,
            )
            if value_index is not None:
                for run in paragraph.runs[:value_index]:
                    if "\t" in str(run.text or ""):
                        run.text = run.text.replace("\t", "")
            for tab in paragraph._p.xpath(".//w:tab"):
                tab.attrib.pop(qn("w:leader"), None)

    def _fill_notification_inline_field(self, paragraphs, label: str, raw_value: object) -> None:
        value = str(raw_value or "").strip()
        if not value:
            return
        paragraph = next(
            (item for item in paragraphs if label in self._fold(item.text)),
            None,
        )
        if paragraph is None:
            return
        runs = paragraph.runs
        value_index = next(
            (index for index, run in enumerate(runs) if value in str(run.text or "")),
            None,
        )
        if value_index is None:
            value_index = next(
                (index for index in range(len(runs) - 1, -1, -1)
                 if re.search(r"[.\u2026]{3,}", str(runs[index].text or ""))),
                None,
            )
            if value_index is None:
                value_index = next(
                    (index for index in range(len(runs) - 1, -1, -1)
                     if "\t" in str(runs[index].text or "")),
                    None,
                )
            if value_index is None:
                return
            runs[value_index].text = value
        value_run = runs[value_index]
        self._copy_notification_label_format(paragraph, value_run)

        for preceding in reversed(runs[:value_index]):
            text = str(preceding.text or "")
            if "\t" in text:
                preceding.text = text.replace("\t", "")
                continue
            if ":" in text and re.search(r"[.\u2026]+$", text):
                preceding.text = re.sub(r"[.\u2026]+$", "", text)
                break
            if not text.strip():
                preceding.text = ""
                continue
            break
        for following in runs[value_index + 1:]:
            text = str(following.text or "")
            if re.fullmatch(r"[\s.\u2026]+", text):
                following.text = re.sub(r"[.\u2026]", "", text)
                continue
            break
        p_pr = paragraph._p.pPr
        if p_pr is not None:
            tabs = p_pr.find(qn("w:tabs"))
            if tabs is not None:
                for tab in tabs.findall(qn("w:tab")):
                    tab.attrib.pop(qn("w:leader"), None)

    @staticmethod
    def _copy_notification_label_format(paragraph, value_run) -> None:
        """Give an inserted value the adjacent template label's font/size."""
        source_run = next(
            (run for run in paragraph.runs
             if run is not value_run and str(run.text or "").strip()
             and not re.fullmatch(r"[\s.\u2026/]+", str(run.text or ""))),
            None,
        )
        if source_run is None or source_run._r.rPr is None:
            return
        original_properties = value_run._r.rPr
        retained = []
        if original_properties is not None:
            retained = [
                copy.deepcopy(child) for child in original_properties
                if child.tag in {qn("w:highlight"), qn("w:shd")}
            ]
        properties = value_run._r.get_or_add_rPr()
        for child in list(properties):
            properties.remove(child)
        properties.extend(copy.deepcopy(child) for child in source_run._r.rPr)
        properties.extend(retained)

    @staticmethod
    def _notification_supplemental_content(values: dict[str, str]) -> str:
        """Return Part B as one unrestricted statement with line breaks intact."""
        raw_content = str(values.get("supplemental_registration_content", "") or "")
        if raw_content.strip():
            return raw_content.strip()
        # Accept old saved/exported values that used three separate template
        # slots, joining them without imposing the former three-line limit.
        legacy_lines = [
            str(values.get(f"supplemental_registration_content_{index}", "") or "").strip()
            for index in range(1, 4)
        ]
        return "\n".join(line for line in legacy_lines if line)

    def _collapse_notification_supplemental_lines(self, document: Document, values: dict[str, str]) -> None:
        """Keep one expandable Part B paragraph and remove spare template rows."""
        if not self._notification_supplemental_content(values):
            return
        paragraphs = list(self._iter_paragraphs(document))
        heading_index = next(
            (index for index, paragraph in enumerate(paragraphs)
             if "bo sung, cap nhat thong tin dang ky hoat dong dia diem kinh doanh" in self._fold(paragraph.text)),
            None,
        )
        if heading_index is None:
            return
        spare_lines = []
        for paragraph in paragraphs[heading_index + 1:]:
            if "de nghi hieu dinh" in self._fold(paragraph.text):
                break
            if any(run.font.highlight_color == WD_COLOR_INDEX.YELLOW for run in paragraph.runs):
                spare_lines.append(paragraph)
        for paragraph in spare_lines[1:]:
            paragraph._element.getparent().remove(paragraph._element)

    def _remove_name_tab_stops_for_entered_values(self, document: Document, values: dict[str, str]) -> None:
        """Let entered location names wrap naturally after their labels."""
        if not any(
            str(values.get(key, "") or "").strip()
            for key in (
                "new_location_business_name",
                "new_location_business_english_name",
                "new_location_business_short_name",
            )
        ):
            return
        labels = (
            "T\u00ean \u0111\u1ecba \u0111i\u1ec3m kinh doanh vi\u1ebft b\u1eb1ng ti\u1ebfng Vi\u1ec7t sau khi thay \u0111\u1ed5i",
            "T\u00ean \u0111\u1ecba \u0111i\u1ec3m kinh doanh vi\u1ebft b\u1eb1ng ti\u1ebfng n\u01b0\u1edbc ngo\u00e0i sau khi thay \u0111\u1ed5i",
            "T\u00ean \u0111\u1ecba \u0111i\u1ec3m kinh doanh vi\u1ebft t\u1eaft sau khi thay \u0111\u1ed5i",
        )
        for paragraph in self._iter_paragraphs(document):
            if not any(label in paragraph.text for label in labels):
                continue
            for run in paragraph.runs:
                if run.text == "\t":
                    run.text = ""

    def _remove_address_contact_dotted_fillers(self, document: Document, values: dict[str, str]) -> None:
        """Clear only the dotted filler belonging to an entered address contact value.

        The notification template deliberately places phone/fax and email/website
        in the same paragraph.  Clearing an entire paragraph would collapse that
        prescribed two-column line, so replace dots only in the run immediately
        following each populated yellow field and stop at the next label.
        """
        contact_lines = (
            ("Điện thoại (nếu có)", "Số fax", "new_location_phone"),
            ("Điện thoại (nếu có)", "", "new_location_fax"),
            ("Thư điện tử (nếu có)", "Website", "new_location_email"),
            ("Thư điện tử (nếu có)", "", "new_location_website"),
        )
        for paragraph in self._iter_paragraphs(document):
            paragraph_text = paragraph.text
            entered_pair_value = False
            for line_label, stop_label, target in contact_lines:
                value = str(values.get(target, "") or "").strip()
                if not value or line_label not in paragraph_text:
                    continue
                entered_pair_value = True
                value_run_index = next(
                    (index for index, run in enumerate(paragraph.runs) if value in str(run.text or "")),
                    None,
                )
                if value_run_index is None:
                    continue
                preceding_run = paragraph.runs[value_run_index - 1] if value_run_index else None
                if preceding_run is not None and re.fullmatch(r"\s+", str(preceding_run.text or "")):
                    # The template stores the first slot's tab in a separate
                    # yellow-shaded run.  Its dotted leader was the blank form
                    # field; once a value is present, remove the tab itself so
                    # the highlight begins exactly at the entered value.
                    preceding_run.text = ""
                for run in paragraph.runs[value_run_index + 1 :]:
                    if stop_label and stop_label in str(run.text or ""):
                        break
                    text = str(run.text or "")
                    if re.fullmatch(r"[\s.\u2026]+", text):
                        # Preserve tabs/spaces so both template columns remain
                        # on their original single line.
                        run.text = re.sub(r"[.\u2026]", "", text)
                        continue
                    break
            if not entered_pair_value:
                continue
            p_pr = paragraph._p.pPr
            if p_pr is None:
                continue
            # These template tabs use dotted leaders. Once a yellow slot is
            # filled, the leader is no longer a placeholder; leaving it visible
            # creates apparent trailing dots even though the run itself changed.
            # Retain the tabs and their positions, so phone/fax and
            # email/website remain prescribed pairs on one physical line.
            tabs = p_pr.find(qn("w:tabs"))
            if tabs is not None:
                for index, tab in enumerate(tabs.findall(qn("w:tab"))):
                    tab.attrib.pop(qn("w:leader"), None)
                    if index == 0:
                        tab.set(qn("w:pos"), "4100")
            justification = p_pr.find(qn("w:jc"))
            if justification is not None:
                justification.set(qn("w:val"), "left")

    def _repair_notification_manager_email_label(self, document: Document) -> None:
        """Repair the damaged manager-email label while retaining the template font."""
        source_run = None
        for paragraph in self._iter_paragraphs(document):
            for run in paragraph.runs:
                if run.text.startswith("Th\u01b0 "):
                    source_run = run
                    break
            if source_run is not None:
                break
        if source_run is None:
            return
        for paragraph in self._iter_paragraphs(document):
            for index, run in enumerate(paragraph.runs):
                if "Th? ?i?n t?" not in run.text:
                    continue
                runs = paragraph.runs
                if index + 4 >= len(runs):
                    return
                spacer, email_run, optional_run, colon_run = runs[index + 1:index + 5]
                if "(n\u1ebfu c\u00f3)" not in optional_run.text or not colon_run.text.startswith(":"):
                    return
                run.text = "    Th\u01b0 \u0111i\u1ec7n t\u1eed"
                properties = run._r.get_or_add_rPr()
                for child in list(properties):
                    properties.remove(child)
                source_properties = source_run._r.rPr
                if source_properties is not None:
                    properties.extend(copy.deepcopy(child) for child in source_properties)
                spacer.text = " "
                colon_run.text = ": "
                email_run._r.addprevious(optional_run._r)
                email_run._r.addprevious(colon_run._r)
                return

    def _remove_manager_date_separators_for_entered_value(self, document: Document, values: dict[str, str]) -> None:
        """The manager date occupies one yellow slot, so remove the obsolete split separators."""
        if not str(values.get("location_manager_date_of_birth", "") or "").strip():
            return
        for paragraph in self._iter_paragraphs(document):
            if "Ng\u00e0y, th\u00e1ng, n\u0103m sinh" not in paragraph.text:
                continue
            for index, run in enumerate(paragraph.runs):
                if index < 3 or not str(run.text or "").strip():
                    continue
                previous = paragraph.runs[index - 3:index]
                if [item.text for item in previous] == ["\t/", "\t/", "\t"]:
                    for item in previous:
                        item.text = ""
                    return

    def _restore_foreign_permanent_address_placeholder(self, document: Document, template_name: str) -> None:
        """Keep the template label ``Nơi thường trú:`` unchanged."""
        # The template already provides the label; do not append generated dots.
        return

    def _remove_empty_business_line_rows(self, document: Document, values: dict[str, str]) -> None:
        """A location dossier must not retain the template's spare industry rows."""
        if self._business_lines(values):
            return
        for table in self._iter_tables(document):
            header_index = self._business_line_header_index(table)
            if header_index is None or len(table.rows[header_index].cells) != 4:
                continue
            for row in list(table.rows[header_index + 1 :]):
                table._tbl.remove(row._tr)

    def _iter_paragraphs(self, document: Document):
        yield from document.paragraphs
        yield from self._table_paragraphs(document.tables)
        for section in document.sections:
            yield from section.header.paragraphs
            yield from self._table_paragraphs(section.header.tables)
            yield from section.footer.paragraphs
            yield from self._table_paragraphs(section.footer.tables)

    def _table_paragraphs(self, tables):
        for table in tables:
            for row in table.rows:
                for cell in row.cells:
                    yield from cell.paragraphs
                    yield from self._table_paragraphs(cell.tables)

    @staticmethod
    def _set_symbol_checkbox_value(run, value: str) -> None:
        """Use the template's Wingdings 2 checked-box symbol (clipboard: S)."""
        selected = bool(str(value or "").strip())
        for symbol in run._r.findall(qn("w:sym")):
            symbol.set(qn("w:font"), "Wingdings 2" if selected else "Webdings")
            symbol.set(qn("w:char"), "F053" if selected else "F063")
    @staticmethod
    def _safe_filename(value: str) -> str:
        cleaned = re.sub(r'[<>:"/\\|?*]', " ", value or "Ho so dia diem kinh doanh")
        return re.sub(r"\s+", " ", cleaned).strip(" .")[:120] or "Ho so dia diem kinh doanh"

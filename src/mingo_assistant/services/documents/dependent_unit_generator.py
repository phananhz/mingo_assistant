"""Template-safe generation for dependent-unit procedures."""
from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml.ns import qn

from mingo_assistant.services.documents.docx_generator import DocxTemplateGenerator, GeneratedDocument, GenerationResult
from mingo_assistant.services.documents.template_manifest import TemplateManifest


class DependentUnitTemplateGenerator(DocxTemplateGenerator):
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
        label = ('Thong bao lap dia diem' if template_name.startswith('1.') else
                 'Giay uy quyen' if template_name.startswith('2.') else 'Huong dan ky')
        name = values.get('parent_entity_name') or values.get('company_name') or case_name
        name = self._fold(name)
        name = re.sub(r'^(cong ty|doanh nghiep)\s*', '', name)
        name = re.sub(r'^(tnhh|co phan|hop danh|tu nhan)\s*', '', name)
        name = re.sub(r'^(mot thanh vien|hai thanh vien)\s*', '', name)
        suffix = ''.join(word.capitalize() for word in re.findall(r'[a-zA-Z0-9]+', name)) or 'HoSo'
        return f'{label}_{suffix}.docx'

    def unresolved_placeholders(self, docx_path: Path) -> list[str]:
        matches: list[str] = []
        with zipfile.ZipFile(docx_path, "r") as archive:
            for entry in archive.infolist():
                if entry.filename.startswith("word/") and entry.filename.endswith(".xml"):
                    matches.extend(re.findall(r"\[([^\[\]\r\n]{1,120})\]", archive.read(entry.filename).decode("utf-8", "ignore")))
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

    def _should_preserve_highlighted_placeholder(
        self, template_name: str, target: str, values: dict[str, str]
    ) -> bool:
        """Keep Section 6 optional fields exactly as the protected template shows them."""
        return target in self._TAX_OPTIONAL_TEXT_FIELDS and not str(values.get(target, "") or "").strip()

    def _empty_highlighted_placeholder(self, run, target: str, values: dict[str, str]) -> str:
        """Keep visible dotted placeholders for empty location-dossier fields."""
        if target == "__clear" or target.endswith("_x") or target.endswith("_is_main"):
            return ""
        template_text = str(getattr(run, "text", "") or "")
        stripped = template_text.strip()
        if stripped and re.fullmatch(r"[\s.…/·_-]+", stripped):
            return template_text
        if any(part in target for part in ("date", "day", "month", "year")):
            return "……/……/……"
        width = min(max(len(stripped), 10), 48)
        return "." * width
    def _replace_highlighted_runs(self, docx_path: Path, template_name: str, values: dict[str, str]) -> None:
        """Use the company-dossier writer, then apply this form's protected tables."""
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
        highlighted_values["tax_accounting_dependent_x"] = (
            "X" if values.get("tax_accounting_method") == "H\u1ea1ch to\u00e1n ph\u1ee5 thu\u1ed9c" else ""
        )
        highlighted_values["tax_bot_project_x"] = "" if str(values.get("tax_bot_project", "") or "").strip() else "X"
        highlighted_values["tax_vat_deduction_x"] = (
            "X" if values.get("tax_vat_method") == "Kh\u1ea5u tr\u1eeb" else ""
        )
        DocxTemplateGenerator._replace_highlighted_runs(self, document, template_name, highlighted_values)
        if template_name.startswith('2.') and values.get('legal_representative_person_type') == 'Người nước ngoài':
            for paragraph in self._iter_paragraphs(document):
                if self._fold(paragraph.text).startswith('so dinh danh ca nhan'):
                    for run in paragraph.runs:
                        run.text = run.text.replace('Số định danh cá nhân', 'Số hộ chiếu')
                    break
        DocxTemplateGenerator._replace_business_lines_tables_v2(
            self,
            document,
            values,
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
                if '6. thong tin dang ky thue' in folded or 'ca nhan duoi day' in folded:
                    for run in paragraph.runs:
                        run.font.size = Pt(13)
        document.save(docx_path)

    def _restore_foreign_permanent_address_placeholder(self, document: Document, template_name: str) -> None:
        """Restore the missing dotted line in the foreign-person address block."""
        if not template_name.startswith("1."):
            return
        for paragraph in self._iter_paragraphs(document):
            if self._fold(paragraph.text).strip().rstrip(":") != "noi thuong tru":
                continue
            placeholder = paragraph.add_run(" " + "." * 60)
            source_properties = paragraph.runs[-2]._r.rPr if len(paragraph.runs) > 1 else None
            if source_properties is not None:
                placeholder._r.insert(0, deepcopy(source_properties))
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
        """Use the two glyphs already used by the protected template."""
        selected = bool(str(value or "").strip())
        for symbol in run._r.findall(qn("w:sym")):
            symbol.set(qn("w:font"), "Wingdings 2" if selected else "Webdings")
            symbol.set(qn("w:char"), "F053" if selected else "F063")
    @staticmethod
    def _safe_filename(value: str) -> str:
        cleaned = re.sub(r'[<>:"/\\|?*]', " ", value or "Ho so dia diem kinh doanh")
        return re.sub(r"\s+", " ", cleaned).strip(" .")[:120] or "Ho so dia diem kinh doanh"

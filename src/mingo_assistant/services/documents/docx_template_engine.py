"""Shared, procedure-neutral helpers for template-safe DOCX generation."""

from __future__ import annotations

import unicodedata
from copy import deepcopy

from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from mingo_assistant.services.documents.context_builder import DocumentContextBuilder
from mingo_assistant.services.documents.value_formatter import DocumentValueFormatter
from mingo_assistant.services.normalization.administrative_place_matcher import AdministrativePlaceMatcher


class DocxTemplateEngine:
    """Common DOCX mechanics shared by otherwise independent procedures.

    Subclasses keep ownership of their manifest, template selection, field
    rules, signing rules, and dossier-specific post-processing.
    """

    UPPERCASE_BOLD_FIELDS = {
        "company_name",
        "company_short_name",
        "company_english_name",
        "legal_representative_full_name",
        "director_full_name",
        "applicant_full_name",
        "authorized_person_full_name",
        "beneficial_owner_full_name",
        "organization_owner_name",
    }
    DETAIL_ADDRESS_FIELDS = {
        "company_address_detail",
        "applicant_address_detail",
        "legal_representative_address_detail",
        "organization_owner_address_detail",
    }
    WARD_FIELDS = {
        "company_ward",
        "applicant_ward",
        "legal_representative_ward",
        "organization_owner_ward",
    }
    PROVINCE_FIELDS = {
        "company_province",
        "applicant_province",
        "legal_representative_province",
        "organization_owner_province",
    }

    def _new_context_builder(self, formatter: DocumentValueFormatter) -> DocumentContextBuilder:
        return DocumentContextBuilder(
            formatter,
            uppercase_fields=self.UPPERCASE_BOLD_FIELDS,
            detail_address_fields=self.DETAIL_ADDRESS_FIELDS,
            ward_fields=self.WARD_FIELDS,
            province_fields=self.PROVINCE_FIELDS,
        )

    def _context_builder(self) -> DocumentContextBuilder:
        builder = getattr(self, "context_builder", None)
        if builder is None:
            builder = self._new_context_builder(self._value_formatter())
            self.context_builder = builder
        return builder

    def _value_formatter(self) -> DocumentValueFormatter:
        formatter = getattr(self, "value_formatter", None)
        if formatter is None:
            formatter = DocumentValueFormatter(AdministrativePlaceMatcher().canonical_province_name)
            self.value_formatter = formatter
        return formatter

    def _value_for_template_target(self, target: str, values: dict[str, str]) -> str:
        return self._context_builder().value_for_target(target, values)

    def _date_component(self, value: object, component: int) -> str:
        return self._value_formatter().date_component(value, component)

    def _company_address_part(self, values: dict[str, str], part: str) -> str:
        return self._value_formatter().company_address_part(values, part)

    def _capital_total_ratio(self, values: dict[str, str]) -> str:
        return self._value_formatter().capital_total_ratio(values)

    def _member_count(self, values: dict[str, str]) -> int:
        return self._value_formatter().member_count(values)

    def _with_vnd(self, value: str) -> str:
        return self._value_formatter().with_vnd(value)

    def _address_detail_only(self, value: str) -> str:
        return self._value_formatter().address_detail_only(value)

    def _administrative_part_only(self, value: str, allowed_prefixes: set[str]) -> str:
        return self._value_formatter().administrative_part_only(value, allowed_prefixes)

    def _normalize_province(self, value: str) -> str:
        return self._value_formatter().normalize_province(value)

    def _replace_highlighted_runs(
        self, document: Document, template_name: str, values: dict[str, str]
    ) -> bool:
        part_manifest = self._template_part_manifest(template_name, "word/document.xml")
        field_map = part_manifest.get("highlighted_fields", {})
        if not isinstance(field_map, dict) or not field_map:
            return False

        highlighted_index = 0
        for paragraph in self._iter_paragraphs(document):
            for run_index, run in enumerate(paragraph.runs):
                if run.font.highlight_color != WD_COLOR_INDEX.YELLOW:
                    continue
                target = field_map.get(str(highlighted_index))
                if target is not None and not self._should_preserve_highlighted_placeholder(
                    template_name, str(target), values
                ):
                    replacement = (
                        ""
                        if self._should_clear_highlighted_target(template_name, str(target), values)
                        else self._value_for_template_target(str(target), values)
                    )
                    if not str(replacement or "").strip():
                        replacement = self._empty_highlighted_placeholder(run, str(target), values)
                    if str(target) == "company_english_name":
                        prefix = "".join(previous_run.text for previous_run in paragraph.runs[:run_index])
                        suffix = "".join(next_run.text for next_run in paragraph.runs[run_index + 1 :])
                        replacement = self._replacement_with_boundary_spacing(replacement, prefix, suffix)
                    if run._r.findall(qn("w:sym")):
                        self._set_symbol_checkbox_value(run, replacement)
                    else:
                        run.text = replacement
                highlighted_index += 1
        return True

    def _should_preserve_highlighted_placeholder(
        self, template_name: str, target: str, values: dict[str, str]
    ) -> bool:
        """Allow a procedure to retain a highlighted template default unchanged."""
        return False

    def _should_clear_highlighted_target(
        self, template_name: str, target: str, values: dict[str, str]
    ) -> bool:
        """Allow a procedure to clear a mapped target without changing the engine."""
        return False

    def _empty_highlighted_placeholder(self, run, target: str, values: dict[str, str]) -> str:
        """Return a procedure-specific fallback when an editable field is empty."""
        return ""

    def _set_symbol_checkbox_value(self, run, value: str) -> None:
        """Preserve a Word symbol checkbox while selecting or clearing it."""
        checkbox_code = "F053" if str(value or "").strip() else "F052"
        for symbol in run._r.findall(qn("w:sym")):
            symbol.set(qn("w:char"), checkbox_code)

    def _replace_business_lines_tables_v2(
        self,
        document: Document,
        values: dict[str, str],
        *,
        keep_file1_business_line_numbers_on_one_line: bool = False,
    ) -> None:
        business_lines = self._business_lines(values)
        for table in self._iter_tables(document):
            if not table.rows:
                continue
            header_index = self._business_line_header_index(table)
            if header_index is None or len(table.rows[header_index].cells) != 4:
                continue
            widths = self._business_line_widths_v2(table)
            self._prepare_business_line_table_v2(table, header_index, widths)
            source_row = deepcopy(table.rows[header_index + 1]._tr) if len(table.rows) > header_index + 1 else None
            for row in list(table.rows[header_index + 1 :]):
                table._tbl.remove(row._tr)
            rows_to_write = business_lines or [{"name": "", "code": "", "is_main": False}]
            for index, line in enumerate(rows_to_write, start=1):
                row_xml = deepcopy(source_row) if source_row is not None else self._new_business_line_row_xml_v2(widths)
                self._strip_business_line_row_content_v2(row_xml)
                table._tbl.append(row_xml)
                self._write_business_line_row_v2(
                    table.rows[-1],
                    index,
                    line,
                    widths,
                    keep_stt_on_one_line=keep_file1_business_line_numbers_on_one_line,
                )

    def _business_line_widths_v2(self, table) -> list[int]:
        widths = [int(column.get(qn("w:w")) or 0) for column in table._tbl.tblGrid.gridCol_lst[:4]]
        if len(widths) != 4 or not all(widths):
            raise ValueError("Bảng ngành nghề phải có geometry hợp lệ cho 4 cột.")
        return widths

    def _prepare_business_line_table_v2(self, table, header_index: int, widths: list[int]) -> None:
        table.autofit = False
        tbl_pr = table._tbl.tblPr
        tbl_w = tbl_pr.find(qn("w:tblW"))
        if tbl_w is None:
            tbl_w = OxmlElement("w:tblW")
            tbl_pr.insert(0, tbl_w)
        tbl_w.set(qn("w:w"), str(sum(widths)))
        tbl_w.set(qn("w:type"), "dxa")
        tbl_layout = tbl_pr.find(qn("w:tblLayout"))
        if tbl_layout is None:
            tbl_layout = OxmlElement("w:tblLayout")
            tbl_pr.append(tbl_layout)
        tbl_layout.set(qn("w:type"), "fixed")
        for column, width in zip(table._tbl.tblGrid.gridCol_lst[:4], widths):
            column.set(qn("w:w"), str(width))

        header = table.rows[header_index]
        self._remove_row_height_v2(header._tr)
        self._unmark_repeating_table_header_v2(header)
        for cell, width in zip(header.cells[:4], widths):
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is not None:
                tc_w.set(qn("w:w"), str(width))
                tc_w.set(qn("w:type"), "dxa")

    def _unmark_repeating_table_header_v2(self, row) -> None:
        """Keep the industry table header on the first page only."""
        tr_pr = row._tr.find(qn("w:trPr"))
        if tr_pr is None:
            return
        for header_flag in tr_pr.findall(qn("w:tblHeader")):
            tr_pr.remove(header_flag)

    def _new_business_line_row_xml_v2(self, widths: list[int]):
        row = OxmlElement("w:tr")
        for width in widths:
            cell = OxmlElement("w:tc")
            tc_pr = OxmlElement("w:tcPr")
            tc_w = OxmlElement("w:tcW")
            tc_w.set(qn("w:w"), str(width))
            tc_w.set(qn("w:type"), "dxa")
            tc_pr.append(tc_w)
            cell.append(tc_pr)
            row.append(cell)
        return row

    def _strip_business_line_row_content_v2(self, row_xml) -> None:
        self._remove_row_height_v2(row_xml)
        tr_pr = row_xml.find(qn("w:trPr"))
        if tr_pr is not None:
            for element in list(tr_pr):
                if element.tag in {qn("w:trHeight"), qn("w:cantSplit")}:
                    tr_pr.remove(element)

    def _remove_row_height_v2(self, row_xml) -> None:
        tr_pr = row_xml.find(qn("w:trPr"))
        if tr_pr is not None:
            for element in tr_pr.findall(qn("w:trHeight")):
                tr_pr.remove(element)

    def _write_business_line_row_v2(
        self,
        row,
        index: int,
        line: dict[str, str | bool],
        widths: list[int],
        *,
        keep_stt_on_one_line: bool = False,
    ) -> None:
        self._remove_row_height_v2(row._tr)
        self._write_business_line_cell_v2(
            row.cells[0], str(index), widths[0], "center", no_wrap=keep_stt_on_one_line
        )
        self._write_business_line_cell_v2(row.cells[1], str(line["name"]), widths[1], "left")
        self._write_business_line_cell_v2(
            row.cells[2], str(line["code"]), widths[2], "center", bold=bool(line["is_main"])
        )
        self._write_business_line_cell_v2(
            row.cells[3], "X" if line["is_main"] else "", widths[3], "center", bold=bool(line["is_main"])
        )

    def _write_business_line_cell_v2(
        self,
        cell,
        value: str,
        width: int,
        alignment: str,
        bold: bool = False,
        *,
        no_wrap: bool = False,
    ) -> None:
        """Replace text while retaining spacing from the approved template row."""
        tc = cell._tc
        tc_pr = tc.get_or_add_tcPr()
        tc_w = tc_pr.find(qn("w:tcW"))
        if tc_w is None:
            tc_w = OxmlElement("w:tcW")
            tc_pr.insert(0, tc_w)
        tc_w.set(qn("w:w"), str(width))
        tc_w.set(qn("w:type"), "dxa")
        v_align = tc_pr.find(qn("w:vAlign"))
        if v_align is None:
            v_align = OxmlElement("w:vAlign")
            tc_pr.append(v_align)
        v_align.set(qn("w:val"), "center")
        if no_wrap:
            no_wrap_element = tc_pr.find(qn("w:noWrap"))
            if no_wrap_element is None:
                tc_pr.append(OxmlElement("w:noWrap"))

        source_paragraph = next((child for child in tc if child.tag == qn("w:p")), None)
        source_p_pr = deepcopy(source_paragraph.find(qn("w:pPr"))) if source_paragraph is not None else None
        source_r_pr = None
        if source_paragraph is not None:
            source_run = source_paragraph.find(qn("w:r"))
            if source_run is not None:
                source_r_pr = deepcopy(source_run.find(qn("w:rPr")))
        for child in list(tc):
            if child.tag != qn("w:tcPr"):
                tc.remove(child)

        paragraph = OxmlElement("w:p")
        p_pr = source_p_pr if source_p_pr is not None else OxmlElement("w:pPr")
        for justification in p_pr.findall(qn("w:jc")):
            p_pr.remove(justification)
        for numbering in p_pr.findall(qn("w:numPr")):
            p_pr.remove(numbering)
        if alignment != "left" or no_wrap:
            for indentation in p_pr.findall(qn("w:ind")):
                p_pr.remove(indentation)
            for tab_stops in p_pr.findall(qn("w:tabs")):
                p_pr.remove(tab_stops)
        justification = OxmlElement("w:jc")
        justification.set(qn("w:val"), alignment)
        p_pr.append(justification)
        paragraph.append(p_pr)
        for line_index, line in enumerate(str(value or "").splitlines() or [""]):
            if line_index:
                break_run = OxmlElement("w:r")
                break_run.append(OxmlElement("w:br"))
                paragraph.append(break_run)
            run = OxmlElement("w:r")
            r_pr = deepcopy(source_r_pr) if source_r_pr is not None else OxmlElement("w:rPr")
            for element in list(r_pr.findall(qn("w:b"))):
                r_pr.remove(element)
            if bold:
                r_pr.append(OxmlElement("w:b"))

            fonts = r_pr.find(qn("w:rFonts"))
            if fonts is None:
                fonts = OxmlElement("w:rFonts")
                r_pr.insert(0, fonts)
            for font_name in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                fonts.set(qn(font_name), "Times New Roman")
            for tag in ("w:sz", "w:szCs"):
                for element in list(r_pr.findall(qn(tag))):
                    r_pr.remove(element)
                size = OxmlElement(tag)
                size.set(qn("w:val"), "25")
                r_pr.append(size)
            for element in list(r_pr.findall(qn("w:color"))):
                r_pr.remove(element)
            color = OxmlElement("w:color")
            color.set(qn("w:val"), "000000")
            r_pr.append(color)
            for hidden_tag in (qn("w:vanish"), qn("w:specVanish")):
                for element in list(r_pr.findall(hidden_tag)):
                    r_pr.remove(element)
            run.append(r_pr)
            text_node = OxmlElement("w:t")
            text_node.text = line
            if line[:1].isspace() or line[-1:].isspace():
                text_node.set(qn("xml:space"), "preserve")
            run.append(text_node)
            paragraph.append(run)
        tc.append(paragraph)

    def _iter_tables(self, container):
        for table in container.tables:
            yield table
            for row in table.rows:
                for cell in row.cells:
                    yield from self._iter_tables(cell)

    def _business_line_header_index(self, table) -> int | None:
        for index, row in enumerate(table.rows[:3]):
            folded_header = self._fold(" ".join(cell.text for cell in row.cells))
            compact_header = folded_header.replace(" ", "")
            has_name = "ten nganh" in folded_header or "tennganh" in compact_header
            has_code = "ma nganh" in folded_header or "manganh" in compact_header
            if has_name and has_code:
                return index
        return None

    @staticmethod
    def _business_line_indices(values: dict[str, str]) -> list[int]:
        return DocumentValueFormatter.business_line_indices(values)

    def _business_lines(self, values: dict[str, str]) -> list[dict[str, str | bool]]:
        return self._value_formatter().business_lines(values)

    def _normalize_business_line_text(self, value: str) -> str:
        return self._value_formatter().normalize_business_line_text(value)

    @staticmethod
    def _replacement_with_boundary_spacing(replacement: str, prefix: str, suffix: str) -> str:
        text = replacement or ""
        if prefix and text and not prefix[-1].isspace() and prefix[-1] not in "([{":
            text = " " + text
        if suffix and text and not suffix[0].isspace() and suffix[0] not in ".,;:)]}":
            text = text + " "
        return text

    @staticmethod
    def _fold(value: str) -> str:
        value = value.replace(chr(273), "d").replace(chr(272), "D")
        text = value.strip().lower().replace("đ", "d")
        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        return text.replace("đ", "d")

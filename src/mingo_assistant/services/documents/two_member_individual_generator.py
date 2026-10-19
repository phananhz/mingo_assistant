"""DOCX generator for two-member companies with individual members only."""

from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_COLOR_INDEX
from docx.shared import Inches, Pt
from docx.text.paragraph import Paragraph

from mingo_assistant.services.documents.business_registration_generator import DocxTemplateGenerator
from mingo_assistant.services.documents.business_registration_variants import (
    TWO_MEMBER_INDIVIDUAL_FILE1,
    TWO_MEMBER_INDIVIDUAL_FILE2,
    TWO_MEMBER_INDIVIDUAL_FILE3,
    TWO_MEMBER_INDIVIDUAL_FILE4,
)

class TwoMemberIndividualFile1DocxTemplateGenerator(DocxTemplateGenerator):
    """Generate only File 1 for the all-individual 2-member-company workflow.

    This bundle deliberately has its own manifest and selection rule. The
    legacy one-member generator therefore keeps selecting and filling its
    original five templates unchanged.
    """

    def _selected_templates(self, values: dict[str, str]) -> list[Path]:
        templates = [
            self.template_dir / TWO_MEMBER_INDIVIDUAL_FILE1,
            self.template_dir / TWO_MEMBER_INDIVIDUAL_FILE2,
            self.template_dir / TWO_MEMBER_INDIVIDUAL_FILE3,
            self.template_dir / TWO_MEMBER_INDIVIDUAL_FILE4,
            self.template_dir.parent.parent / "4. Giấy ủy quyền.docx",
            self.template_dir / "6. Huong dan ky.docx",
        ]
        missing = next((template for template in templates if not template.is_file()), None)
        if missing is not None:
            raise FileNotFoundError(f"Missing Word template: {missing}")
        return templates

    def _output_filename(self, template_name: str, values: dict[str, str]) -> str:
        """Keep the supplied two-member dossier names exactly as delivered."""
        if template_name == "4. Giấy ủy quyền.docx":
            return "5. Giay uy quyen.docx"
        return template_name

    def _replace_placeholders(self, docx_path: Path, values: dict[str, str]) -> None:
        if docx_path.name == "4. Giấy ủy quyền.docx":
            # Use the one-member manifest and full authorization pipeline.
            legacy = DocxTemplateGenerator(self.template_dir.parent.parent, self.export_root)
            legacy._replace_placeholders(docx_path, values)
            return
        if docx_path.name == TWO_MEMBER_INDIVIDUAL_FILE4:
            document = Document(docx_path)
            self._apply_two_member_file4_fields(document, values)
            date_values = [str(values.get(key, "") or "").strip() for key in
                           ("document_place", "document_day", "document_month", "document_year")]
            if all(date_values):
                for paragraph in self._iter_paragraphs(document):
                    folded = self._fold(paragraph.text)
                    if not all(word in folded for word in ("ngay", "thang", "nam")):
                        continue
                    groups = []
                    active = False
                    for run in paragraph.runs:
                        if run.font.highlight_color == WD_COLOR_INDEX.YELLOW:
                            if not active:
                                groups.append([])
                            groups[-1].append(run)
                            active = True
                        elif run.text:
                            active = False
                    if len(groups) == 4:
                        for runs, value in zip(groups, date_values):
                            runs[0].text = value
                            for run in runs[1:]:
                                run.text = ""
            document.save(docx_path)
            return
        if docx_path.name == "6. Huong dan ky.docx":
            document = Document(docx_path)
            # File 6 is a signing guide, so use normal name capitalization even
            # when the profile stores names in all caps for legal forms.
            name = str(values.get("legal_representative_full_name", "") or "").strip().title()
            for paragraph in self._iter_paragraphs(document):
                in_highlight = False
                for run in paragraph.runs:
                    if run.font.highlight_color == WD_COLOR_INDEX.YELLOW:
                        run.text = "" if in_highlight else name
                        in_highlight = True
                    elif run.text:
                        in_highlight = False
            member_names = [
                member["full_name"].title()
                for member in self._two_member_file2_members(values)
                if member["full_name"]
            ]
            for table in self._iter_tables(document):
                for row in table.rows:
                    if len(row.cells) < 4 or "danh sach thanh vien" not in self._fold(row.cells[1].text):
                        continue
                    member_instruction = next(
                        (
                            paragraph
                            for paragraph in row.cells[3].paragraphs
                            if "thanh vien la ca nhan" in self._fold(paragraph.text)
                        ),
                        None,
                    )
                    if member_instruction is None:
                        continue
                    highlighted = [
                        run
                        for run in member_instruction.runs
                        if run.font.highlight_color == WD_COLOR_INDEX.YELLOW
                    ]
                    if highlighted:
                        highlighted[0].text = ", ".join(member_names)
                        for run in highlighted[1:]:
                            run.text = ""
                        # The template keeps a literal comma immediately after
                        # the highlighted sample name. Commas already separate
                        # member names above, so remove only that trailing one.
                        after_names = False
                        for run in member_instruction.runs:
                            if run._r is highlighted[0]._r:
                                after_names = True
                                continue
                            if after_names and run.text:
                                run.text = re.sub(r"^\s*,\s*", " ", run.text, count=1)
                                break
                    break
            document.save(docx_path)
            return
        super()._replace_placeholders(docx_path, values)

    @staticmethod
    def _fill_beneficial_owner_template_cell(cell, value: str) -> None:
        # Some source cells begin with an empty paragraph. Copy the actual
        # sample text's style, not that empty paragraph's default 14pt font.
        paragraphs = list(cell.paragraphs)
        target = next((p for p in paragraphs if p.text.strip()), paragraphs[-1])
        exemplar = next((r for p in paragraphs for r in p.runs if r.text.strip()), None)
        properties = deepcopy(exemplar._r.rPr) if exemplar is not None else None
        for paragraph in paragraphs:
            for run in paragraph.runs:
                run.text = ""
        if not value:
            return
        run = target.add_run(value)
        if properties is not None:
            run._r.insert(0, properties)
        else:
            run.font.name = "Times New Roman"
            run.font.size = Pt(11)
        run.font.highlight_color = WD_COLOR_INDEX.YELLOW

    def _replace_case_type_text(self, document: Document, values: dict[str, str]) -> None:
        # The supplied File 1 already contains the legally correct 2-member
        # wording. Do not apply legacy one-member text substitutions here.
        return

    def _remove_file1_owner_name_spacer(
        self, document: Document, template_name: str, values: dict[str, str]
    ) -> None:
        # This template has a different section structure from the old File 1.
        return

    def _apply_template_checkbox_rules(
        self, document: Document, template_name: str, values: dict[str, str]
    ) -> None:
        # Preserve source-template checkbox glyphs and table geometry.
        if template_name == TWO_MEMBER_INDIVIDUAL_FILE1:
            self._apply_two_member_file1_contact_and_gender_fields(document, values)
        elif template_name == TWO_MEMBER_INDIVIDUAL_FILE2:
            self._apply_two_member_file2_fields(document, values)
        elif template_name == TWO_MEMBER_INDIVIDUAL_FILE3:
            self._apply_two_member_file3_fields(document, values)
        elif template_name == TWO_MEMBER_INDIVIDUAL_FILE4:
            self._apply_two_member_file4_fields(document, values)
        return

    def _apply_two_member_file1_contact_and_gender_fields(
        self, document: Document, values: dict[str, str]
    ) -> None:
        """Fill the non-highlighted File 1 fields without rebuilding template tables."""
        company_phone = str(values.get("company_phone", "") or "").strip()
        company_fax = str(values.get("company_fax", "") or "").strip()
        company_email = str(values.get("company_email", "") or "").strip()
        company_website = str(values.get("company_website", "") or "").strip()
        director_gender = str(
            values.get("director_gender") or values.get("legal_representative_gender") or ""
        ).strip()

        def placeholder(value: str) -> str:
            return value or ".................."

        def write_pair(paragraph, left_label: str, left_value: str, right_label: str, right_value: str) -> None:
            self._replace_paragraph_with_highlighted_values(
                paragraph,
                (
                    (left_label, False),
                    (placeholder(left_value), bool(left_value)),
                    ("\t" + right_label, False),
                    (placeholder(right_value), bool(right_value)),
                ),
            )
            try:
                paragraph.paragraph_format.tab_stops.add_tab_stop(Inches(4.1))
            except Exception:
                pass

        in_company_address = False
        in_tax_director = False
        in_tax_notice_address = False
        for paragraph in self._iter_paragraphs(document):
            folded = self._fold(paragraph.text)
            if folded.startswith("3. dia chi tru so chinh"):
                in_company_address = True
            elif in_company_address and folded.startswith("4."):
                in_company_address = False

            if "thong tin ve giam doc" in folded:
                in_tax_director = True
            elif folded.startswith("9.2"):
                in_tax_director = False
            if "dia chi nhan thong bao thue" in folded:
                in_tax_notice_address = True
            elif folded.startswith("9.4"):
                in_tax_notice_address = False

            if in_company_address and "dien thoai" in folded and "so fax" in folded:
                write_pair(
                    paragraph,
                    "\u0110i\u1ec7n tho\u1ea1i: ",
                    company_phone,
                    "S\u1ed1 fax (n\u1ebfu c\u00f3): ",
                    company_fax,
                )
                continue
            if in_company_address and "thu dien tu" in folded and "website" in folded:
                write_pair(
                    paragraph,
                    "Th\u01b0 \u0111i\u1ec7n t\u1eed (n\u1ebfu c\u00f3): ",
                    company_email,
                    "Website (n\u1ebfu c\u00f3): ",
                    company_website,
                )
                continue
            if in_tax_director and folded.startswith("gioi tinh"):
                self._replace_paragraph_with_highlighted_values(
                    paragraph,
                    (("Gi\u1edbi t\u00ednh: ", False), (placeholder(director_gender), bool(director_gender))),
                )
                continue
            if in_tax_director and folded.startswith("dien thoai"):
                self._replace_paragraph_with_highlighted_values(
                    paragraph,
                    (("\u0110i\u1ec7n tho\u1ea1i: ", False), (placeholder(company_phone), bool(company_phone))),
                )
                continue
            if in_tax_notice_address and "dien thoai" in folded and "so fax" in folded:
                write_pair(
                    paragraph,
                    "\u0110i\u1ec7n tho\u1ea1i (n\u1ebfu c\u00f3): ",
                    company_phone,
                    "S\u1ed1 fax (n\u1ebfu c\u00f3): ",
                    company_fax,
                )
                try:
                    paragraph.paragraph_format.tab_stops.add_tab_stop(Inches(3.25))
                except Exception:
                    pass
                continue
            if in_tax_notice_address and folded.startswith("thu dien tu"):
                self._replace_paragraph_with_highlighted_values(
                    paragraph,
                    (("Th\u01b0 \u0111i\u1ec7n t\u1eed (n\u1ebfu c\u00f3): ", False), (placeholder(company_email), bool(company_email))),
                )


    def _apply_two_member_file2_fields(self, document: Document, values: dict[str, str]) -> None:
        """Fill the all-individual charter without changing its source layout."""
        company_name = str(values.get("company_name", "") or "").strip()
        company_english_name = str(values.get("company_english_name", "") or "").strip()
        company_short_name = str(values.get("company_short_name", "") or "").strip()
        company_address = str(values.get("company_address", "") or "").strip()
        capital_number = str(values.get("charter_capital_number", "") or "").strip()
        if capital_number and "dong" not in self._fold(capital_number):
            capital_number = f"{capital_number} \u0111\u1ed3ng"
        capital_text = str(values.get("charter_capital_text", "") or "").strip()

        def replace_highlights(paragraph: Paragraph, replacement: str) -> None:
            highlighted = [run for run in paragraph.runs if run.font.highlight_color == WD_COLOR_INDEX.YELLOW]
            if not highlighted:
                return
            highlighted[0].text = replacement
            for run in highlighted[1:]:
                run.text = ""

        legal_signature_heading = "nguoi dai dien theo phap luat cua doanh nghiep"
        awaiting_legal_signature = False
        for paragraph in self._iter_paragraphs(document):
            folded = self._fold(paragraph.text)
            if awaiting_legal_signature and folded:
                legal_name = str(values.get("legal_representative_full_name", "") or "").strip()
                # Reuse the yellow, bold signature-name run in the template.
                # Rebuilding the paragraph would lose its required bold formatting.
                highlighted = [
                    run
                    for run in paragraph.runs
                    if run.font.highlight_color == WD_COLOR_INDEX.YELLOW
                ]
                if highlighted:
                    highlighted[0].text = legal_name
                    highlighted[0].bold = True
                    for run in highlighted[1:]:
                        run.text = ""
                else:
                    self._replace_paragraph_with_highlighted_values(
                        paragraph, ((legal_name, bool(legal_name)),)
                    )
                    for run in paragraph.runs:
                        run.bold = True
                awaiting_legal_signature = False
                continue
            # The same phrase occurs in the charter body. Only the standalone,
            # all-caps-equivalent final heading introduces the signature block.
            if folded == legal_signature_heading:
                awaiting_legal_signature = True
                continue
            if folded.startswith("cong ty tnhh") and "ten cong ty" not in folded:
                replace_highlights(paragraph, company_name)
            elif "cac thanh vien cung dong y" in folded:
                replace_highlights(paragraph, company_name)
            elif "ten cong ty viet bang tieng viet" in folded:
                replace_highlights(paragraph, company_name)
            elif "ten cong ty viet bang tieng nuoc ngoai" in folded:
                replace_highlights(paragraph, company_english_name)
            elif "ten cong ty viet tat" in folded:
                replace_highlights(paragraph, company_short_name)
            elif folded.startswith("dia chi tru so chinh"):
                replace_highlights(paragraph, company_address)
            elif folded.startswith("1. so luong nguoi dai dien"):
                replace_highlights(paragraph, str(values.get("legal_representative_position", "") or ""))
            elif folded.startswith("ho, chu dem va ten"):
                replace_highlights(paragraph, str(values.get("legal_representative_full_name", "") or ""))
            elif folded.startswith("ngay, thang, nam sinh"):
                replace_highlights(paragraph, str(values.get("legal_representative_date_of_birth", "") or ""))
            elif folded.startswith("gioi tinh"):
                replace_highlights(paragraph, str(values.get("legal_representative_gender", "") or ""))
            elif folded.startswith("so dinh danh ca nhan"):
                replace_highlights(paragraph, str(values.get("legal_representative_id_number", "") or ""))
            elif folded.startswith("so nha/phong"):
                replace_highlights(paragraph, str(values.get("legal_representative_address_detail", "") or ""))
            elif folded.startswith("xa/phuong/dac khu"):
                replace_highlights(paragraph, str(values.get("legal_representative_ward", "") or ""))
            elif folded.startswith("tinh/thanh pho"):
                replace_highlights(paragraph, str(values.get("legal_representative_province", "") or ""))
            elif folded.startswith("quoc gia"):
                replace_highlights(paragraph, str(values.get("legal_representative_nationality", "") or "Vi\u1ec7t Nam"))
            elif "dien thoai (neu co)" in folded and "thu dien tu (neu co)" in folded:
                phone = str(values.get("company_phone", "") or "").strip()
                email = str(values.get("company_email", "") or "").strip()
                self._replace_paragraph_with_highlighted_values(
                    paragraph,
                    (("\u0110i\u1ec7n tho\u1ea1i (n\u1ebfu c\u00f3): ", False), (phone or "..................", bool(phone)), ("\tTh\u01b0 \u0111i\u1ec7n t\u1eed (n\u1ebfu c\u00f3): ", False), (email or "..................", bool(email))),
                )
                try:
                    paragraph.paragraph_format.tab_stops.add_tab_stop(Inches(3.5))
                except Exception:
                    pass
            elif folded.startswith("1. von dieu le cua cong ty la"):
                self._replace_paragraph_with_highlighted_values(paragraph, (("1. V\u1ed1n \u0111i\u1ec1u l\u1ec7 c\u1ee7a c\u00f4ng ty l\u00e0: ", False), (capital_number, bool(capital_number)), (" (Ghi b\u1eb1ng ch\u1eef: ", False), (capital_text, bool(capital_text)), (")", False)))
            elif ", ngay" in folded and "thang" in folded and "nam" in folded:
                highlighted = [run for run in paragraph.runs if run.font.highlight_color == WD_COLOR_INDEX.YELLOW]
                if len(highlighted) >= 4:
                    for run, date_value in zip(highlighted, (str(values.get("document_place", "") or ""), str(values.get("document_day", "") or ""), str(values.get("document_month", "") or ""), str(values.get("document_year", "") or ""))):
                        run.text = date_value

        members = self._two_member_file2_members(values)
        for table in self._iter_tables(document):
            header = self._fold(" ".join(cell.text for row in table.rows[:2] for cell in row.cells))
            if len(table.rows) >= 2 and len(table.rows[0].cells) == 6 and "ten thanh vien" in header and "dia chi lien lac" in header:
                self._replace_two_member_file2_identity_table(table, members)
            elif len(table.rows) >= 3 and len(table.rows[0].cells) == 6 and "phan von gop" in header and "ty le" in header:
                self._replace_two_member_file2_capital_table(table, members)
            elif len(table.rows) >= 1 and len(table.rows[0].cells) == 2 and "thanh vien" in header:
                self._replace_two_member_file2_signature_table(table, members)

    def _apply_two_member_file3_fields(self, document: Document, values: dict[str, str]) -> None:
        """Fill File 3 data rows without touching its header rows or cell formatting."""
        members = self._two_member_file2_members(values)
        source_document = Document(self.template_dir / TWO_MEMBER_INDIVIDUAL_FILE3)
        source_table = next(
            table
            for table in self._iter_tables(source_document)
            if table.rows and len(table.rows[0].cells) == 14
        )
        source_numbering_row = deepcopy(source_table.rows[2]._tr)

        def write_value(cell, value: str, *, prefer_highlight: bool = True) -> None:
            value = str(value or "")
            highlighted = [
                run for paragraph in cell.paragraphs for run in paragraph.runs
                if run.font.highlight_color == WD_COLOR_INDEX.YELLOW
            ]
            if highlighted:
                highlighted[0].text = value
                for run in highlighted[1:]:
                    run.text = ""
                return
            target = next((paragraph for paragraph in reversed(cell.paragraphs) if paragraph.text.strip()), None)
            if target is not None and target.runs:
                target.runs[0].text = value
                if prefer_highlight and value:
                    target.runs[0].font.highlight_color = WD_COLOR_INDEX.YELLOW
                for run in target.runs[1:]:
                    run.text = ""
                return
            if not value:
                return
            paragraph = cell.paragraphs[-1] if cell.paragraphs else cell.add_paragraph()
            run = paragraph.add_run(value)
            if prefer_highlight:
                run.font.highlight_color = WD_COLOR_INDEX.YELLOW

        for table in self._iter_tables(document):
            if not table.rows or len(table.rows[0].cells) != 14:
                continue
            # The generic highlighted-run pass can mistake the numbered header
            # cells for capital placeholders. Restore the File 3 rows from its
            # own template before applying this workflow's member mapping.
            table._tbl.replace(table.rows[2]._tr, deepcopy(source_numbering_row))
            source_data_row = deepcopy(table.rows[3]._tr)
            for row in list(table.rows[3:]):
                table._tbl.remove(row._tr)
            for index, member in enumerate(members, start=1):
                table._tbl.append(deepcopy(source_data_row))
                row = table.rows[-1]
                row_values = (
                    str(index), member["full_name"], member["date_of_birth"], member["gender"],
                    member["id_number"], str(values.get(f"member_{index}_nationality", "") or ""),
                    str(values.get(f"member_{index}_ethnicity", "") or ""), member["address"],
                    member["capital_amount"], member["capital_ratio"].rstrip("%"),
                    member["capital_asset_type"], member["capital_deadline"],
                    str(values.get(f"member_{index}_signature", "") or ""),
                    str(values.get(f"member_{index}_note", "") or ""),
                )
                for column, value in enumerate(row_values):
                    write_value(row.cells[column], value, prefer_highlight=column != 0)
                    if column == 7:
                        # The sample address is split across highlighted runs
                        # with literal comma separators. Keep the first run's
                        # formatting, but remove separators left by the sample.
                        first_value_run = next(
                            (
                                run
                                for paragraph in row.cells[column].paragraphs
                                for run in paragraph.runs
                                if run.text == value
                            ),
                            None,
                        )
                        if first_value_run is not None:
                            for paragraph in row.cells[column].paragraphs:
                                for run in paragraph.runs:
                                    if run._r is not first_value_run._r:
                                        run.text = ""
                    row.cells[column].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            break

        legal_name = str(values.get("legal_representative_full_name", "") or "").strip()
        for table in self._iter_tables(document):
            if len(table.rows) != 1 or len(table.rows[0].cells) != 1:
                continue
            cell = table.rows[0].cells[0]
            if "nguoi dai dien theo phap luat" not in self._fold(cell.text):
                continue
            for paragraph in reversed(cell.paragraphs):
                highlighted = [run for run in paragraph.runs if run.font.highlight_color == WD_COLOR_INDEX.YELLOW]
                if not highlighted:
                    continue
                highlighted[0].text = legal_name
                highlighted[0].bold = True
                for run in highlighted[1:]:
                    run.text = ""
                return

    def _apply_two_member_file4_fields(self, document: Document, values: dict[str, str]) -> None:
        """Fill File 4 from the visible beneficial-owner rows in the form."""
        try:
            owner_count = max(1, int(str(values.get("beneficial_owner_list_count", "1") or "1")))
        except ValueError:
            owner_count = 1

        owner_suffixes = (
            "number", "full_name", "date_of_birth", "gender", "identity", "nationality", "ethnicity", "address",
            "capital_direct", "capital_indirect", "capital_total", "voting_direct", "voting_indirect", "voting_total",
            "general_partner", "related_group", "control", "manager",
        )
        for table in self._iter_tables(document):
            numbering_row_index = next(
                (
                    index for index, row in enumerate(table.rows)
                    if len(row.cells) >= 18 and row.cells[0].text.strip() == "1" and row.cells[17].text.strip() == "18"
                ),
                None,
            )
            if numbering_row_index is None:
                continue

            source_row = deepcopy(table.rows[numbering_row_index + 1]._tr)
            for row in list(table.rows[numbering_row_index + 1:]):
                table._tbl.remove(row._tr)
            for index in range(1, owner_count + 1):
                table._tbl.append(deepcopy(source_row))
                row = table.rows[-1]
                row_values = [
                    str(values.get(f"beneficial_owner_list_{index}_number", "") or str(index)).strip(),
                    str(values.get(f"beneficial_owner_list_{index}_full_name", "") or "").strip(),
                    str(values.get(f"beneficial_owner_list_{index}_date_of_birth", "") or "").strip(),
                    str(values.get(f"beneficial_owner_list_{index}_gender", "") or "").strip(),
                    self._beneficial_owner_identity_number(str(values.get(f"beneficial_owner_list_{index}_identity", "") or "").strip()),
                    str(values.get(f"beneficial_owner_list_{index}_nationality", "") or "").strip(),
                    str(values.get(f"beneficial_owner_list_{index}_ethnicity", "") or "").strip(),
                    str(values.get(f"beneficial_owner_list_{index}_address", "") or "").strip(),
                ]
                row_values.extend(
                    self._beneficial_owner_percentage(str(values.get(f"beneficial_owner_list_{index}_{suffix}", "") or "").strip())
                    if position < 6
                    else str(values.get(f"beneficial_owner_list_{index}_{suffix}", "") or "").strip()
                    for position, suffix in enumerate(owner_suffixes[8:])
                )
                for column, (cell, value) in enumerate(zip(row.cells[:18], row_values, strict=True), start=1):
                    self._fill_beneficial_owner_template_cell(cell, value)
            break

        legal_name = str(values.get("legal_representative_full_name", "") or "").strip().upper()
        if not legal_name:
            return
        for table in self._iter_tables(document):
            if len(table.rows) != 1 or len(table.rows[0].cells) != 1:
                continue
            cell = table.rows[0].cells[0]
            if "nguoi dai dien theo phap luat" not in self._fold(cell.text):
                continue
            for paragraph in reversed(cell.paragraphs):
                highlighted = [run for run in paragraph.runs if run.font.highlight_color == WD_COLOR_INDEX.YELLOW]
                if not highlighted:
                    continue
                highlighted[0].text = legal_name
                highlighted[0].bold = True
                for run in highlighted[1:]:
                    run.text = ""
                return

    @staticmethod
    def _format_two_member_capital_amount(value: object) -> str:
        digits = re.sub(r"\D", "", str(value or ""))
        return f"{int(digits):,}".replace(",", ".") if digits else ""

    def _normalize_capital_asset_type(self, value: object) -> str:
        asset_type = str(value or "").strip()
        if not asset_type or self._fold(asset_type) == "tien mat":
            return "Đồng Việt Nam"
        return asset_type

    def _two_member_file2_members(self, values: dict[str, str]) -> list[dict[str, str]]:
        count = max(2, self._member_count(values))
        return [
            {
                "full_name": str(values.get(f"member_{index}_full_name", "") or "").strip(),
                "date_of_birth": str(values.get(f"member_{index}_date_of_birth", "") or "").strip(),
                "gender": str(values.get(f"member_{index}_gender", "") or "").strip(),
                "id_number": str(values.get(f"member_{index}_id_number", "") or "").strip(),
                "address": str(values.get(f"member_{index}_permanent_address", "") or "").strip(),
                "capital_amount": self._format_two_member_capital_amount(
                    values.get(f"member_{index}_capital_amount", "")
                ),
                "capital_ratio": str(values.get(f"member_{index}_capital_ratio", "") or "").strip().rstrip("%"),
                "capital_asset_type": self._normalize_capital_asset_type(
                    values.get(f"member_{index}_capital_asset_type", "")
                ),
                "capital_deadline": str(
                    values.get(f"member_{index}_capital_deadline", "")
                    or "Trong th\u1eddi h\u1ea1n 90 ng\u00e0y k\u1ec3 t\u1eeb ng\u00e0y \u0111\u01b0\u1ee3c c\u1ea5p Gi\u1ea5y ch\u1ee9ng nh\u1eadn \u0111\u0103ng k\u00fd doanh nghi\u1ec7p"
                ).strip(),
            }
            for index in range(1, count + 1)
        ]

    def _replace_two_member_file2_identity_table(self, table, members: list[dict[str, str]]) -> None:
        template = Document(self.template_dir / TWO_MEMBER_INDIVIDUAL_FILE2)
        source_row = deepcopy(template.tables[0].rows[1]._tr)
        for row in list(table.rows[1:]):
            table._tbl.remove(row._tr)
        for index, member in enumerate(members, start=1):
            table._tbl.append(deepcopy(source_row))
            row = table.rows[-1]
            for cell, cell_value in zip(row.cells, (str(index), member["full_name"], member["date_of_birth"], member["gender"], f"S\u1ed1 \u0111\u1ecbnh danh c\u00e1 nh\u00e2n: {member['id_number']}", member["address"])):
                self._set_cell_text_with_highlight(cell, cell_value)
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

    def _replace_two_member_file2_capital_table(self, table, members: list[dict[str, str]]) -> None:
        template = Document(self.template_dir / TWO_MEMBER_INDIVIDUAL_FILE2)
        source_row = deepcopy(template.tables[2].rows[2]._tr)
        for row in list(table.rows[2:]):
            table._tbl.remove(row._tr)
        for index, member in enumerate(members, start=1):
            table._tbl.append(deepcopy(source_row))
            row = table.rows[-1]
            row_values = (str(index), member["full_name"], member["capital_amount"], member["capital_ratio"], member["capital_asset_type"], member["capital_deadline"])
            for cell, cell_value in zip(row.cells, row_values):
                self._set_cell_text_with_highlight(cell, cell_value)
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

    def _replace_two_member_file2_signature_table(self, table, members: list[dict[str, str]]) -> None:
        source_row = deepcopy(table.rows[0]._tr)
        for row in list(table.rows):
            table._tbl.remove(row._tr)
        for offset in range(0, len(members), 2):
            table._tbl.append(deepcopy(source_row))
            row = table.rows[-1]
            for column, member in enumerate(members[offset:offset + 2]):
                cell = row.cells[column]
                # Preserve the template's "Th?nh vi?n" label and blank signing
                # space. Only replace its existing yellow, bold name run.
                name_paragraph = next(
                    (paragraph for paragraph in reversed(cell.paragraphs) if paragraph.text.strip()),
                    None,
                )
                if name_paragraph is not None:
                    highlighted = [
                        run
                        for run in name_paragraph.runs
                        if run.font.highlight_color == WD_COLOR_INDEX.YELLOW
                    ]
                    if highlighted:
                        highlighted[0].text = member["full_name"]
                        highlighted[0].bold = True
                        for run in highlighted[1:]:
                            run.text = ""
                    else:
                        self._replace_paragraph_with_highlighted_values(
                            name_paragraph,
                            ((member["full_name"], bool(member["full_name"])),),
                        )
                        for run in name_paragraph.runs:
                            run.bold = True
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

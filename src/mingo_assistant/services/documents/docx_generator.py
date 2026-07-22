from __future__ import annotations

import re
import shutil
import tempfile
import unicodedata
import zipfile
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.text.paragraph import Paragraph
from lxml import etree


@dataclass(frozen=True)
class GeneratedDocument:
    source_name: str
    output_path: Path


@dataclass(frozen=True)
class GenerationResult:
    output_dir: Path
    generated: list[GeneratedDocument]
    skipped: list[str]
    unresolved: dict[str, list[str]]


class DocxTemplateGenerator:
    def __init__(self, template_dir: Path, export_root: Path) -> None:
        self.template_dir = template_dir
        self.export_root = export_root

    def generate(self, values: dict[str, str], case_name: str) -> GenerationResult:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{self._safe_filename(case_name or 'ho_so_thanh_lap')}_{timestamp}"
        output_dir = self.export_root / folder_name
        output_dir.mkdir(parents=True, exist_ok=True)

        generated: list[GeneratedDocument] = []
        skipped: list[str] = []
        unresolved: dict[str, list[str]] = {}

        for template in sorted(self.template_dir.iterdir()):
            if template.suffix.lower() == ".docx":
                output_path = output_dir / template.name
                shutil.copy2(template, output_path)
                self._replace_placeholders(output_path, values)
                remaining = self.unresolved_placeholders(output_path)
                if remaining:
                    unresolved[template.name] = remaining
                generated.append(GeneratedDocument(template.name, output_path))
            elif template.suffix.lower() == ".doc":
                skipped.append(f"{template.name} chưa được điền tự động vì đang là .doc")

        return GenerationResult(output_dir=output_dir, generated=generated, skipped=skipped, unresolved=unresolved)

    def validate_templates(self, values: dict[str, str]) -> dict[str, list[str]]:
        report: dict[str, list[str]] = {}
        with tempfile.TemporaryDirectory(dir=self.export_root if self.export_root.exists() else None) as temp_dir:
            temp_path = Path(temp_dir)
            for template in sorted(self.template_dir.iterdir()):
                if template.suffix.lower() != ".docx":
                    continue
                candidate = temp_path / template.name
                shutil.copy2(template, candidate)
                self._replace_placeholders(candidate, values)
                unresolved = self.unresolved_placeholders(candidate)
                if unresolved:
                    report[template.name] = sorted(set(unresolved))
        return report

    def unresolved_placeholders(self, docx_path: Path) -> list[str]:
        placeholders: list[str] = []
        with zipfile.ZipFile(docx_path, "r") as package:
            for item in package.infolist():
                if not item.filename.startswith("word/") or not item.filename.endswith(".xml"):
                    continue
                data = package.read(item.filename)
                if b"[" not in data or b"]" not in data:
                    continue
                placeholders.extend(self._extract_placeholders_from_xml(data))
        return sorted(set(placeholders))

    def _replace_placeholders(self, docx_path: Path, values: dict[str, str]) -> None:
        document = Document(docx_path)
        self._replace_known_sample_text(document, values)
        self._replace_case_type_text(document, values)
        self._replace_business_lines_tables(document, values)
        self._replace_in_container(document, values)
        for section in document.sections:
            self._replace_in_container(section.header, values)
            self._replace_in_container(section.footer, values)
        document.save(docx_path)
        self._replace_split_placeholders_in_package(docx_path, values)

    def _replace_known_sample_text(self, document: Document, values: dict[str, str]) -> None:
        replacements: dict[str, str] = {}
        company_name = values.get("company_name", "").strip()
        company_short_name = values.get("company_short_name", "").strip()
        legal_name = values.get("legal_representative_full_name", "").strip()
        if company_name:
            for sample in [
                "CÔNG TY TNHH THƯƠNG MẠI VÀ DỊCH VỤ THOMAS",
                "CÔNG TY TNHH THƯƠNG MẠI VÀ DỊCH VỤ EDITION",
                "CÔNG TY TNHH THƯƠNG MẠI VÀ DỊCH VỤ EDITON",
                "CÔNG   TY   TNHH   THƯƠNG   MẠI   VÀ   DỊCH   VỤ   EDTION",
            ]:
                replacements[sample] = company_name
        short_replacement = company_short_name or company_name
        if short_replacement:
            replacements["THOMAS EDITION"] = short_replacement
            replacements["THOMAS EDITON"] = short_replacement
        if legal_name:
            replacements["NGUYỄN THANH HÓA"] = legal_name
        if not replacements:
            return
        self._replace_plain_text_in_container(document, replacements)
        for section in document.sections:
            self._replace_plain_text_in_container(section.header, replacements)
            self._replace_plain_text_in_container(section.footer, replacements)

    def _replace_case_type_text(self, document: Document, values: dict[str, str]) -> None:
        try:
            member_count = int(values.get("company_member_count", "1") or "1")
        except ValueError:
            member_count = 1
        if member_count <= 1:
            return
        replacements = {
            "CÔNG TY TNHH MỘT THÀNH VIÊN": "CÔNG TY TNHH HAI THÀNH VIÊN TRỞ LÊN",
            "Công ty TNHH Một thành viên": "Công ty TNHH Hai thành viên trở lên",
            "Công ty trách nhiệm hữu hạn một thành viên": "Công ty trách nhiệm hữu hạn hai thành viên trở lên",
            "công ty trách nhiệm hữu hạn một thành viên": "công ty trách nhiệm hữu hạn hai thành viên trở lên",
            "trách nhiệm hữu hạn một thành viên": "trách nhiệm hữu hạn hai thành viên trở lên",
            "một thành viên": "hai thành viên trở lên",
        }
        self._replace_plain_text_in_container(document, replacements)
        for section in document.sections:
            self._replace_plain_text_in_container(section.header, replacements)
            self._replace_plain_text_in_container(section.footer, replacements)

    def _replace_plain_text_in_container(self, container, replacements: dict[str, str]) -> None:
        element = getattr(container, "_element", None)
        if element is None:
            element = getattr(container, "element", None)
        if element is None:
            return
        for paragraph_element in element.xpath(".//w:p"):
            paragraph = Paragraph(paragraph_element, container)
            original = paragraph.text
            replaced = original
            for source, target in replacements.items():
                replaced = replaced.replace(source, target)
            if replaced == original:
                continue
            for run in paragraph.runs:
                run.text = ""
            if paragraph.runs:
                paragraph.runs[0].text = replaced
            else:
                paragraph.add_run(replaced)

    def _replace_business_lines_tables(self, document: Document, values: dict[str, str]) -> None:
        business_lines = self._business_lines(values)

        for table in self._iter_tables(document):
            if not table.rows:
                continue
            header_index = self._business_line_header_index(table)
            if header_index is None:
                continue
            if len(table.rows[header_index].cells) < 4:
                continue

            template_index = min(header_index + 1, len(table.rows) - 1)
            template_row = deepcopy(table.rows[template_index]._tr)
            for row in list(table.rows[header_index + 1 :]):
                table._tbl.remove(row._tr)

            rows_to_write = business_lines or [{"name": "", "code": "", "is_main": False}]
            for index, line in enumerate(rows_to_write, start=1):
                table._tbl.append(deepcopy(template_row))
                row = table.rows[-1]
                self._set_cell_text(row.cells[0], str(index))
                self._set_cell_text(row.cells[1], line["name"])
                self._set_cell_text(row.cells[2], line["code"])
                self._set_cell_text(row.cells[3], "X" if line["is_main"] else "")

    def _iter_tables(self, container):
        for table in container.tables:
            yield table
            for row in table.rows:
                for cell in row.cells:
                    yield from self._iter_tables(cell)

    def _business_line_header_index(self, table) -> int | None:
        for index, row in enumerate(table.rows[:3]):
            folded_header = self._fold(" ".join(cell.text for cell in row.cells))
            if "ten nganh" in folded_header and "ma nganh" in folded_header:
                return index
        return None

    def _business_lines(self, values: dict[str, str]) -> list[dict[str, str | bool]]:
        lines: list[dict[str, str | bool]] = []
        for index in range(1, 11):
            name = self._normalize_business_line_text(values.get(f"business_line_{index}_name", ""))
            code = values.get(f"business_line_{index}_code", "").strip()
            is_main = bool(values.get(f"business_line_{index}_is_main", "").strip())
            if name or code or is_main:
                lines.append({"name": name, "code": code, "is_main": is_main})
        return lines

    def _normalize_business_line_text(self, value: str) -> str:
        text = "\n".join(part.strip() for part in value.replace("\r", "\n").split("\n") if part.strip())
        text = re.sub(r"\s+(Chi\s*tiết\s*:)", r"\n\1", text, flags=re.IGNORECASE)
        text = re.sub(r"(?i)chi\s*tiết\s*:", "Chi tiết:", text)
        return text

    def _set_cell_text(self, cell, value: str) -> None:
        cell.text = ""
        paragraph = cell.paragraphs[0]
        lines = value.splitlines() or [""]
        run = paragraph.add_run(lines[0])
        for line in lines[1:]:
            run.add_break()
            run.add_text(line)

    def _replace_in_container(self, container, values: dict[str, str]) -> None:
        element = getattr(container, "_element", None)
        if element is None:
            element = getattr(container, "element", None)
        if element is None:
            return
        for paragraph_element in element.xpath(".//w:p"):
            self._replace_in_paragraph(Paragraph(paragraph_element, container), values)

    def _replace_in_paragraph(self, paragraph, values: dict[str, str]) -> None:
        original = paragraph.text
        if "[" not in original or "]" not in original:
            return
        replaced = self._replace_text(original, values)
        if replaced == original:
            return

        for run in paragraph.runs:
            run.text = ""
        if paragraph.runs:
            paragraph.runs[0].text = replaced
        else:
            paragraph.add_run(replaced)

    def _replace_split_placeholders_in_package(self, docx_path: Path, values: dict[str, str]) -> None:
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".docx", dir=docx_path.parent)
        tmp_path = Path(tmp_file.name)
        tmp_file.close()

        try:
            with zipfile.ZipFile(docx_path, "r") as source_zip:
                with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as target_zip:
                    for item in source_zip.infolist():
                        data = source_zip.read(item.filename)
                        if item.filename.startswith("word/") and item.filename.endswith(".xml"):
                            data = self._replace_split_placeholders_in_xml(data, values)
                        target_zip.writestr(item, data)
            tmp_path.replace(docx_path)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise

    def _replace_split_placeholders_in_xml(self, data: bytes, values: dict[str, str]) -> bytes:
        if b"[" not in data or b"]" not in data:
            return data

        root = etree.fromstring(data)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        text_nodes = root.xpath(".//w:t", namespaces=namespace)
        if not text_nodes:
            return data

        segments = []
        chunks = []
        cursor = 0
        for node in text_nodes:
            text = node.text or ""
            start = cursor
            cursor += len(text)
            segments.append((start, cursor, node, text))
            chunks.append(text)

        joined = "".join(chunks)
        matches = list(re.finditer(r"\[([^\[\]]{1,300})\]", joined))
        if not matches:
            return data

        for match in reversed(matches):
            placeholder = match.group(1).strip()
            context_start = max(0, match.start() - 200)
            context_end = min(len(joined), match.end() + 200)
            replacement = self._value_for_placeholder(placeholder, values, joined[context_start:context_end])
            if replacement is None:
                continue

            affected = [segment for segment in segments if segment[0] < match.end() and segment[1] > match.start()]
            if not affected:
                continue

            first_start, first_end, first_node, first_text = affected[0]
            last_start, last_end, last_node, last_text = affected[-1]
            prefix = first_text[: max(0, match.start() - first_start)]
            suffix = last_text[max(0, match.end() - last_start) :] if last_node is not first_node else first_text[max(0, match.end() - first_start) :]

            first_node.text = prefix + replacement + suffix if first_node is last_node else prefix + replacement
            for _, _, node, _ in affected[1:-1]:
                node.text = ""
            if last_node is not first_node:
                last_node.text = suffix

        return etree.tostring(root, encoding="UTF-8", xml_declaration=True, standalone=True)

    def _extract_placeholders_from_xml(self, data: bytes) -> list[str]:
        try:
            root = etree.fromstring(data)
        except etree.XMLSyntaxError:
            return []
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        text_nodes = root.xpath(".//w:t", namespaces=namespace)
        joined = "".join(node.text or "" for node in text_nodes)
        return [match.group(1).strip() for match in re.finditer(r"\[([^\[\]]{1,300})\]", joined)]

    def _replace_text(self, text: str, values: dict[str, str]) -> str:
        def replacement(match: re.Match[str]) -> str:
            placeholder = match.group(0)
            key_or_sample = match.group(1).strip()
            value = self._value_for_placeholder(key_or_sample, values, text)
            return placeholder if value is None else value

        return re.sub(r"\[([^\[\]]+)\]", replacement, text)

    def _value_for_placeholder(self, placeholder: str, values: dict[str, str], context: str = "") -> str | None:
        normalized = self._normalize_key(placeholder)
        known_direct_keys = {
            "business_registration_office",
            "company_name",
            "company_short_name",
            "company_address",
            "company_address_detail",
            "company_ward",
            "company_province",
            "company_phone",
            "company_email",
            "company_member_count",
            "company_type_label",
            "business_lines",
            "charter_capital_number",
            "charter_capital_text",
            "charter_capital_full_text",
            "cash_capital_text",
            "asset_capital_text",
            "member_capital_amount",
            "member_capital_ratio",
            "capital_zero",
            "legal_representative_full_name",
            "legal_representative_id_number",
            "legal_representative_date_of_birth",
            "legal_representative_gender",
            "legal_representative_nationality",
            "legal_representative_permanent_address",
            "legal_representative_address_detail",
            "legal_representative_ward",
            "legal_representative_province",
            "legal_representative_contact_address",
            "legal_representative_place_of_origin",
            "legal_representative_issue_date",
            "legal_representative_expiry_date",
            "legal_representative_position",
            "director_full_name",
            "director_date_of_birth",
            "director_gender",
            "director_id_number",
            "director_phone",
            "director_position",
            "applicant_full_name",
            "applicant_date_of_birth",
            "applicant_gender",
            "applicant_id_number",
            "applicant_address_detail",
            "applicant_ward",
            "applicant_province",
            "authorized_person_full_name",
            "authorized_person_date_of_birth",
            "authorized_person_gender",
            "authorized_person_id_number",
            "authorized_person_contact_address",
            "authorized_person_phone",
            "authorized_person_email",
            "beneficial_owner_full_name",
            "beneficial_owner_date_of_birth",
            "beneficial_owner_gender",
            "beneficial_owner_id_number",
            "beneficial_owner_issue_date",
            "beneficial_owner_address",
            "document_place",
            "document_day",
            "document_month",
            "document_year",
            "document_place_date",
        }
        for index in range(1, 21):
            known_direct_keys.update(
                {
                    f"business_line_{index}_name",
                    f"business_line_{index}_code",
                    f"business_line_{index}_is_main",
                    f"member_{index}_full_name",
                    f"member_{index}_id_number",
                    f"member_{index}_date_of_birth",
                    f"member_{index}_gender",
                    f"member_{index}_permanent_address",
                    f"member_{index}_capital_amount",
                    f"member_{index}_capital_ratio",
                }
            )
        if normalized in known_direct_keys:
            return values.get(normalized, "").strip()

        for key, value in values.items():
            if self._normalize_key(key) == normalized and value.strip():
                return value.strip()

        aliases = {
            "phong_dang_ky_kinh_doanh": "business_registration_office",
            "ten_doanh_nghiep": "company_name",
            "ten_cong_ty": "company_name",
            "ten_viet_tat": "company_short_name",
            "dia_chi_tru_so": "company_address",
            "so_dien_thoai_cong_ty": "company_phone",
            "email_cong_ty": "company_email",
            "nganh_nghe_kinh_doanh": "business_lines",
            "von_dieu_le_bang_so": "charter_capital_number",
            "von_dieu_le_bang_chu": "charter_capital_text",
            "ho_ten": "legal_representative_full_name",
            "ho_va_ten": "legal_representative_full_name",
            "member_full_name": "member_1_full_name",
            "member_id_number": "member_1_id_number",
            "member_date_of_birth": "member_1_date_of_birth",
            "member_permanent_address": "member_1_permanent_address",
            "so_cccd": "legal_representative_id_number",
            "so_dinh_danh_ca_nhan": "legal_representative_id_number",
            "ngay_sinh": "legal_representative_date_of_birth",
            "gioi_tinh": "legal_representative_gender",
            "quoc_tich": "legal_representative_nationality",
            "dia_chi_thuong_tru": "legal_representative_permanent_address",
            "que_quan": "legal_representative_place_of_origin",
            "ngay_cap": "legal_representative_issue_date",
            "ngay_het_han": "legal_representative_expiry_date",
            "chuc_danh": "legal_representative_position",
            "noi_ky": "document_place",
            "ngay_ky": "document_day",
            "thang_ky": "document_month",
            "nam_ky": "document_year",
        }
        alias_key = aliases.get(normalized)
        if alias_key:
            return values.get(alias_key, "").strip()

        return self._guess_value_from_sample(placeholder, values, context)

    def _guess_value_from_sample(self, placeholder: str, values: dict[str, str], context: str = "") -> str | None:
        lowered = placeholder.lower()
        folded_placeholder = self._fold(placeholder)
        folded_context = self._fold(context)
        digits = re.sub(r"\D", "", placeholder)

        direct_sample_map = {
            "0": "capital_zero",
            "100": "member_capital_ratio",
            "ba_ty_dong": "charter_capital_text",
            "x": "business_line_1_is_main",
            "nguyen_thi_khanh_haha": "authorized_person_full_name",
            "22_12_1111": "authorized_person_date_of_birth",
            "098765434567": "authorized_person_id_number",
            "thon_lam_xa_hai_ba_tinh_bon_nam": "authorized_person_contact_address",
            "09876545678": "authorized_person_phone",
            "fsgdhfjg_gmail_com": "authorized_person_email",
            "nguyen_thanh_hoa": "legal_representative_full_name",
            "080177011933": "legal_representative_id_number",
            "12_07_1977": "legal_representative_date_of_birth",
            "ap_hau_quoi_hau_my_dong_thap": "legal_representative_permanent_address",
            "thon_hai_xa_ba_tinh_bon_nam": "beneficial_owner_address",
            "09876654311": "company_phone",
            "09876543": "director_phone",
            "so_nha_13": "company_address_detail",
            "tinh_ha_giang": "legal_representative_province",
        }
        mapped_key = direct_sample_map.get(self._normalize_key(placeholder))
        if mapped_key:
            return values.get(mapped_key, "").strip()

        business_line_map = {
            "ban_buon_gao_lua_my_san_pham_tu_ngu_coc_khac_bot_mychi_tiet_ban_buon_gao": "business_line_1_name",
            "4631": "business_line_1_code",
            "ban_buon_thuc_pham": "business_line_2_name",
            "4632": "business_line_2_code",
            "ban_buon_nong_lam_san_nguyen_lieu_tru_go_tre_nua_va_dong_vat_song_chi_tiet_ban_buon_lua_tam_cam_lua_giong_va_cac_mat_hang_nong_lam_san_nguyen_lieu_tru_go_tre_nua": "business_line_3_name",
            "4620": "business_line_3_code",
            "dai_ly_moi_gioi_dau_gia_hang_hoa_chi_tiet_tru_dau_gia_hang_hoa": "business_line_4_name",
            "dai_ly_moi_gioi_dau_gia_hang_hoachi_tiet_tru_dau_gia_hang_hoa": "business_line_4_name",
            "4610": "business_line_4_code",
            "ban_le_luong_thuc": "business_line_5_name",
            "4721": "business_line_5_code",
            "hoat_dong_dich_vu_ho_tro_khac_lien_quan_den_van_tai_chi_tiet_hoat_dong_cua_cac_dai_ly_ban_ve_may_bay_tru_hoa_long_khi_de_van_chuyen_va_hoat_dong_lien_quan_den_van_tai_duong_hang_khong": "business_line_6_name",
            "hoat_dong_dich_vu_ho_tro_kinh_doanh_khac_con_lai_chua_duoc_phan_vao_dau_chi_tiet_xuat_nhap_khau_cac_mat_hang_doanh_nghiep_kinh_doanh": "business_line_6_name",
            "8299": "business_line_6_code",
            "kho_bai_va_luu_giu_hang_hoa_chi_tiet_luu_giu_hang_hoa_tru_kinh_doanh_kho_bai": "business_line_7_name",
            "5210": "business_line_7_code",
            "5229": "business_line_8_code",
            "hoat_dong_tu_van_quan_ly_kinh_doanh_va_hoat_dong_tu_van_quan_ly_khac_tru_tu_van_tai_chinh_ke_toan_phap_luat": "business_line_8_name",
            "7020": "business_line_9_code",
            "quang_cao_chi_tiet_tru_quang_cao_thuoc_la": "business_line_9_name",
            "7310": "business_line_10_code",
        }
        business_key = business_line_map.get(self._normalize_key(placeholder))
        if business_key:
            return values.get(business_key, "").strip()

        if folded_placeholder == "x" and "nganh nghe kinh doanh chinh" in folded_context:
            for index in range(1, 11):
                if values.get(f"business_line_{index}_is_main"):
                    return "X"
            return ""
        if "phong dang ky kinh doanh" in folded_placeholder or "phong dang ky kinh doanh" in folded_context:
            return values.get("business_registration_office", "")
        if "von bang tai san" in folded_context or "khong co" in folded_placeholder:
            return values.get("asset_capital_text", "")
        if "von bang tien mat" in folded_context:
            return values.get("cash_capital_text", "") or values.get("charter_capital_full_text", "")
        if "von dieu le" in folded_context:
            if "bang chu" in folded_context:
                return values.get("charter_capital_text", "")
            if "bang so" in folded_context or "vnd" in folded_context:
                return values.get("charter_capital_number", "")
            return values.get("charter_capital_full_text", "") or values.get("charter_capital_number", "")
        if "dong" in folded_placeholder or "vnd" in folded_placeholder:
            return values.get("charter_capital_number", "")
        if folded_context.startswith("[") and "ngay" in folded_placeholder and "thang" in folded_placeholder:
            return values.get("document_place_date", "")
        if folded_placeholder.startswith("ngay") and "thang" in folded_placeholder and "nam" in folded_placeholder:
            return values.get("document_place_date", "")
        if "noi ky" in folded_context:
            return values.get("document_place", "")
        if "ngay [" in folded_context and "thang [" in folded_context and "nam [" in folded_context:
            if len(digits) == 4:
                return values.get("document_year", "")
            if placeholder.strip() == values.get("document_month", ""):
                return values.get("document_month", "")
            return values.get("document_day", "")
        if "ngay cap" in folded_context:
            return values.get("legal_representative_issue_date", "") or values.get("beneficial_owner_issue_date", "")
        if "ngay, thang, nam sinh" in lowered or "ngay thang nam sinh" in folded_context:
            if "22/12/1111" in placeholder:
                return values.get("authorized_person_date_of_birth", "")
            return values.get("legal_representative_date_of_birth", "") or values.get("applicant_date_of_birth", "")
        if "tinh/thanh pho truc thuoc trung uong" in folded_context:
            if "tinh ha giang" in folded_placeholder:
                return values.get("legal_representative_province", "") or values.get("applicant_province", "")
            return values.get("company_province", "") or values.get("applicant_province", "")
        if "xa/phuong" in folded_context or "dac khu" in folded_context:
            return values.get("company_ward", "") or values.get("applicant_ward", "") or values.get("legal_representative_ward", "")
        if "so nha/phong" in folded_context:
            if "thôn" in lowered or "thon" in folded_placeholder:
                return values.get("applicant_address_detail", "") or values.get("legal_representative_address_detail", "")
            return values.get("company_address_detail", "") or values.get("legal_representative_address_detail", "")
        if "dia chi lien lac" in folded_context:
            return values.get("authorized_person_contact_address", "") or values.get("legal_representative_contact_address", "")
        if "dia chi thuong tru" in folded_context:
            return values.get("legal_representative_permanent_address", "")
        if "giam doc" in folded_context:
            if "dien thoai" in folded_context:
                return values.get("director_phone", "")
            return values.get("director_full_name", "") or values.get("legal_representative_full_name", "")
        if "so dinh danh ca nhan" in folded_context or re.fullmatch(r"\d{9,12}", digits):
            if "098765434567" in placeholder:
                return values.get("authorized_person_id_number", "")
            return values.get("legal_representative_id_number", "") or values.get("applicant_id_number", "")
        if "gioi tinh" in folded_context or folded_placeholder in {"nam", "nu"}:
            return values.get("legal_representative_gender", "") or values.get("applicant_gender", "")
        if "quoc gia" in folded_context or "viet nam" in folded_placeholder:
            return values.get("legal_representative_nationality", "")
        if "dien thoai" in folded_context:
            return values.get("company_phone", "") or values.get("authorized_person_phone", "")
        if "email" in folded_context:
            return values.get("company_email", "") or values.get("authorized_person_email", "")
        if "ten cong ty viet bang tieng viet" in folded_context or "cong ty tnhh" in folded_placeholder:
            return values.get("company_name", "")
        if "tru so cong ty" in folded_context:
            return values.get("company_address", "")
        if "toi la" in folded_context:
            return values.get("applicant_full_name", "") or values.get("legal_representative_full_name", "")
        if "ho chu dem va ten" in folded_context or "ho, chu dem va ten" in lowered:
            return values.get("legal_representative_full_name", "") or values.get("applicant_full_name", "")
        if "thomas" in folded_placeholder:
            if "viet tat" in folded_context or "ten viet tat" in folded_context:
                return values.get("company_short_name", "") or values.get("company_name", "")
            if "cong ty" in folded_context or "doanh nghiep" in folded_context:
                return values.get("company_name", "")
            return values.get("company_short_name", "") or values.get("company_name", "")
        if re.search(r"\d{1,2}/\d{1,2}/\d{4}", placeholder):
            return values.get("legal_representative_date_of_birth", "") or values.get("document_place_date", "")
        if any(word in lowered for word in ["tỉnh", "xã", "phường", "thôn", "số nhà"]):
            return values.get("legal_representative_permanent_address", "") or values.get("company_address", "")
        return None

    def _normalize_key(self, value: str) -> str:
        text = self._fold(value)
        text = re.sub(r"[^a-z0-9]+", "_", text)
        return text.strip("_")

    def _fold(self, value: str) -> str:
        text = unicodedata.normalize("NFD", value.strip().lower())
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        return text.replace("đ", "d")

    def _safe_filename(self, value: str) -> str:
        text = re.sub(r"[^\w\s.-]", "", value, flags=re.UNICODE).strip()
        text = re.sub(r"\s+", "_", text)
        return text[:80] or "ho_so"

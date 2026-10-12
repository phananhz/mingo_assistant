"""Fill reviewed yellow inputs and explicit fax/website exceptions in form 12."""
from __future__ import annotations

import hashlib
import re
import shutil
import zipfile
from copy import deepcopy
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from lxml import etree

from mingo_assistant.services.documents.business_amendment_fields import CHANGE_GROUPS, LINE_CAPACITIES, SHARE_FIELDS, SLOTS, YellowSlot, line_row_count
from mingo_assistant.services.documents.package_editor import DocxPackageEditor
from mingo_assistant.domains.business_registration.money import VietnameseMoneyFormatter
from mingo_assistant.services.documents.docx_generator import (
    DocxTemplateGenerator, GeneratedDocument, GenerationResult,
)

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = "{" + NS["w"] + "}"
SHARE_VALUE_KEYS = (
    {"new_share_par_value"}
    | {
        f"amendment_share_{i}_{suffix}"
        for i in range(1, 6)
        for suffix in ("count", "amount", "ratio")
    }
    | {f"amendment_share_total_{suffix}" for suffix in ("count", "amount", "ratio")}
)


def selected(value: str) -> bool:
    return str(value).strip().lower() in {"1", "x", "true", "yes", "có"}


def shares_entered(values: dict[str, str]) -> bool:
    return selected(values.get("change_capital_selected", "")) and any(values.get(key, "").strip() for key, _ in SHARE_FIELDS)


def inferred_change_selections(values: dict[str, str]) -> set[str]:
    """Return every change section explicitly selected or containing user data."""
    active: set[str] = set()
    for selection, _title, fields in CHANGE_GROUPS:
        if selected(values.get(selection, "")):
            active.add(selection)
            continue
        if selection == "change_beneficial_selected":
            # Both dropdowns have a default value, so only the explicit choice
            # can distinguish an intended beneficial-owner notification.
            continue
        if selection == "change_business_lines_selected":
            entered = any(
                re.fullmatch(r"amendment_line_(?:add|remove|detail)_\d+_(?:name|detail|code|main|note)", key)
                and str(value or "").strip()
                for key, value in values.items()
            )
        else:
            ignored = (
                {"registered_capital", "amendment_source_2_amount", "amendment_asset_1_amount"}
                if selection == "change_capital_selected"
                else set()
            )
            entered = any(
                key not in ignored and str(values.get(key, "") or "").strip()
                for key, _label in fields
            )
        if entered:
            active.add(selection)
    return active


def money_number(value: str) -> int:
    if not re.fullmatch(r"(?:\d+|\d{1,3}(?:[.,\s]\d{3})+)", value.strip()):
        raise ValueError("Số tiền/số lượng phải là số nguyên không âm")
    return int(re.sub(r"[.,\s]", "", value))


def ratio_number(value: str) -> Decimal:
    try:
        number = Decimal(value.strip().rstrip("%").strip().replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError("Tỷ lệ phải là số từ 0 đến 100") from exc
    if not number.is_finite() or not 0 <= number <= 100:
        raise ValueError("Tỷ lệ phải là số từ 0 đến 100")
    return number


def compose_share_values(values: dict[str, str]) -> dict[str, str]:
    formatter = VietnameseMoneyFormatter()
    result = {}
    for suffix in ("count", "amount", "ratio"):
        total = Decimal(0)
        populated = False
        for i in range(1, 6):
            key = f"amendment_share_{i}_{suffix}"
            raw = values.get(key, "").strip()
            if not raw:
                continue
            populated = True
            number = ratio_number(raw) if suffix == "ratio" else money_number(raw)
            total += number
            result[key] = format(number, "f").replace(".", ",") if suffix == "ratio" else formatter.format_digits(str(number))
        result[f"amendment_share_total_{suffix}"] = (
            format(total, "f").replace(".", ",") if suffix == "ratio" else formatter.format_digits(str(int(total)))
        ) if populated else ""
    return result


class BusinessAmendmentTemplateGenerator(DocxTemplateGenerator):
    TEMPLATE_NAME = "Thong bao thay doi.docx"
    # An unreviewed template revision must not reuse these paragraph offsets.
    TEMPLATE_SHA256 = "041fbcfd3e1987aac6c027b9018ed28c539429d1c41375889eb60221074833fd"

    def __init__(self, template_dir: Path, export_root: Path) -> None:
        self.template_dir = template_dir
        self.export_root = export_root

    def validate_templates(self, values: dict[str, str]) -> dict[str, list[str]]:
        template = self.template_dir / self.TEMPLATE_NAME
        try:
            if hashlib.sha256(template.read_bytes()).hexdigest() != self.TEMPLATE_SHA256:
                return {self.TEMPLATE_NAME: ["Mẫu đã thay đổi; cần kiểm tra lại bản đồ vùng vàng trước khi điền"]}
            with zipfile.ZipFile(template) as package:
                root = etree.fromstring(package.read("word/document.xml"))
            paragraphs = root.findall(".//w:p", NS)
            for slot in SLOTS:
                self._slot_nodes(paragraphs[slot.paragraph], slot)
        except (OSError, zipfile.BadZipFile, KeyError, IndexError, ValueError, etree.XMLSyntaxError):
            return {self.TEMPLATE_NAME: ["Không tìm thấy mẫu Word hợp lệ hoặc vị trí nhập không còn bôi vàng"]}
        return {}

    @staticmethod
    def validation_issues(values: dict[str, str]) -> list[str]:
        active_changes = inferred_change_selections(values)
        required = {
            "parent_entity_name": "Tên doanh nghiệp", "parent_entity_registration_number": "Mã số doanh nghiệp",
            "business_registration_office": "Cơ quan tiếp nhận", "document_place": "Nơi ký",
            "document_day": "Ngày ký", "document_month": "Tháng ký", "document_year": "Năm ký",
            "legal_representative_full_name": "Tên người đại diện/người ký",
        }
        if "change_name_selected" in active_changes:
            required["new_company_name"] = "Tên tiếng Việt sau thay đổi"
        if "change_address_selected" in active_changes:
            required.update({"new_company_address_detail": "Địa chỉ mới", "new_company_ward": "Xã/Phường mới", "new_company_province": "Tỉnh/Thành phố mới"})
        if "change_capital_selected" in active_changes:
            required.update({"registered_capital": "Vốn đã đăng ký", "new_capital": "Vốn sau thay đổi"})
        issues = [f"Chưa có: {label}" for key, label in required.items() if not values.get(key, "").strip()]
        if not active_changes:
            issues.append("Chọn ít nhất một nội dung thay đổi có vùng vàng để điền")
        code = values.get("parent_entity_registration_number", "").strip()
        if code and not re.fullmatch(r"\d{10}(?:\d{3})?", code):
            issues.append("Mã số doanh nghiệp phải có 10 hoặc 13 chữ số, giữ nguyên số 0 đầu")
        parts = [values.get(key, "").strip() for key in ("document_day", "document_month", "document_year")]
        if all(parts):
            try:
                datetime.strptime("/".join(parts), "%d/%m/%Y")
            except ValueError:
                issues.append("Ngày ký không hợp lệ")
        for selection, title, fields in CHANGE_GROUPS:
            if selection not in active_changes:
                continue
            if selection == "change_tax_selected" and not any(values.get(key, "").strip() for key, _ in fields):
                issues.append(f"Chưa có dữ liệu: {title}")
            for key, label in fields:
                value = values.get(key, "").strip()
                if not value:
                    continue
                if key in {"amendment_source_2_amount", "amendment_asset_1_amount"}:
                    # These are derived from new_capital during composition;
                    # ignore stale values saved by older app versions.
                    continue
                try:
                    if key.endswith("_ratio"):
                        ratio_number(value)
                    elif key.endswith(("_amount", "_count", "_par_value")) or key in {"registered_capital", "new_capital"}:
                        money_number(value)
                except ValueError as exc:
                    issues.append(f"{label}: {exc}")
                if (key.endswith("_date") or key.endswith("_date_of_birth")) and key != "capital_change_date":
                    try:
                        datetime.strptime(value, "%d/%m/%Y")
                    except ValueError:
                        issues.append(f"{label}: nhập ngày hợp lệ theo dd/mm/yyyy")
                if key in {"tax_financial_year_start", "tax_financial_year_end"}:
                    try:
                        datetime.strptime(value + "/2000", "%d/%m/%Y")
                    except ValueError:
                        issues.append(f"{label}: nhập ngày/tháng hợp lệ theo dd/mm")
            if selection == "change_business_lines_selected":
                populated, main_count = False, 0
                for kind in LINE_CAPACITIES:
                    capacity = line_row_count(values, kind)
                    for i in range(1, capacity + 1):
                        prefix = f"amendment_line_{kind}_{i}_"
                        name, code = values.get(prefix + "name", "").strip(), values.get(prefix + "code", "").strip()
                        other = values.get(prefix + ("note" if kind == "remove" else "main"), "").strip()
                        if name or code or other:
                            populated = True
                            if not name or not re.fullmatch(r"\d{4}", code):
                                issues.append(f"Ngành nghề {kind}, dòng {i}: cần tên và mã ngành 4 chữ số")
                        if kind != "remove":
                            if other and other.upper() != "X":
                                issues.append(f"Ngành nghề {kind}, dòng {i}: ngành chính chỉ nhập X hoặc để trống")
                            main_count += int(bool(other))
                if not populated:
                    issues.append("Chưa có ngành nghề bổ sung/bỏ/sửa chi tiết")
                if main_count > 1:
                    issues.append("Chỉ chọn một ngành nghề chính trong các bảng bổ sung/sửa chi tiết")
        return list(dict.fromkeys(issues))

    @staticmethod
    def composed_values(values: dict[str, str]) -> dict[str, str]:
        result = dict(values)
        # Older drafts can contain reviewed values but miss their selection
        # flags. Export every section that contains actual user-entered data.
        for selection in inferred_change_selections(result):
            result[selection] = "X"
        formatter = VietnameseMoneyFormatter()
        for key in ("parent_entity_name", "new_company_name", "legal_representative_full_name"):
            result[key] = result.get(key, "").upper()
        if selected(result.get("change_beneficial_selected", "")):
            for suffix in ("a", "b"):
                status = result.get(f"beneficial_notice_{suffix}_status", "").strip()
                if status:
                    result[f"beneficial_notice_{suffix}_text"] = status.rstrip(".") + "."
        for key in ("registered_capital", "new_capital"):
            if selected(result.get("change_capital_selected", "")) and (value := result.get(key, "").strip()):
                amount = money_number(value)
                result[key + "_text"] = f"{formatter.format_digits(str(amount))} VNĐ ({formatter.to_words(amount).capitalize()} đồng)"
        # The foreign-display checkboxes are UI-only in this phase.
        result["capital_yes_symbol"] = ""
        if selected(result.get("change_capital_selected", "")):
            if value := result.get("new_capital", "").strip():
                new_capital = formatter.format_digits(str(money_number(value)))
                result["amendment_source_2_amount"] = new_capital
                result["amendment_asset_1_amount"] = new_capital
            for kind, count, active in (("source", 4, 2), ("asset", 6, 1)):
                for i in range(1, count + 1):
                    if i != active:
                        result[f"amendment_{kind}_{i}_amount"] = "0"
                    result[f"amendment_{kind}_{i}_ratio"] = "100%" if i == active else "0"
        if shares_entered(result):
            result.update(compose_share_values(result))
            for i in range(1, 6):
                key = f"amendment_share_{i}_count"
                if result.get(key, "").strip():
                    result[key] = formatter.format_digits(str(money_number(result[key])))
        for kind, count, suffixes in (("source", 4, ("amount", "ratio")), ("asset", 6, ("amount", "ratio"))):
            if not selected(result.get("change_capital_selected", "")):
                continue
            for suffix in suffixes:
                if kind in {"source", "asset"} and suffix == "amount" and not result.get(f"amendment_{kind}_{2 if kind == 'source' else 1}_amount", "").strip():
                    result.pop(f"amendment_{kind}_total_amount", None)
                    continue
                keys = [f"amendment_{kind}_{i}_{suffix}" for i in range(1, count + 1)]
                if not any(result.get(key, "").strip() for key in keys):
                    continue
                total = Decimal(0)
                for key in keys:
                    number = ratio_number(result.get(key, "") or "0") if suffix == "ratio" else money_number(result.get(key, "") or "0")
                    total += number
                    if suffix == "ratio":
                        ratio = str(number).replace(".", ",")
                        result[key] = ratio + ("%" if number == 100 else "")
                    else:
                        result[key] = formatter.format_digits(str(number))
                result[f"amendment_{kind}_total_{suffix}"] = (
                    str(total).replace(".", ",") + "%"
                    if suffix == "ratio"
                    else formatter.format_digits(str(int(total)))
                )
        if shares_entered(result) and (value := result.get("new_share_par_value", "").strip()):
            result["new_share_par_value"] = formatter.format_digits(str(money_number(value)))
        for kind in LINE_CAPACITIES:
            capacity = line_row_count(result, kind)
            suffixes = ("name", "code", "note" if kind == "remove" else "main")
            rows = []
            for i in range(1, capacity + 1):
                prefix = f"amendment_line_{kind}_{i}_"
                row = {suffix: result.get(prefix + suffix, "") for suffix in suffixes}
                if any(value.strip() for value in row.values()):
                    rows.append(row)
            # Empty UI rows and stale values beyond the saved count never add
            # empty rows or phantom industries to the exported document.
            prefix = f"amendment_line_{kind}_"
            for key in list(result):
                if key.startswith(prefix):
                    result.pop(key)
            result[prefix + "row_count"] = str(len(rows))
            number = 0
            for i, row in enumerate(rows, 1):
                result.update({f"{prefix}{i}_{suffix}": value for suffix, value in row.items()})
                populated = bool(row["name"].strip())
                number += int(populated)
                result[f"{prefix}{i}_number"] = str(number) if populated else ""
                if kind != "remove":
                    result[f"{prefix}{i}_main"] = row["main"].upper()
        return result

    @staticmethod
    def _slot_nodes(paragraph, slot: YellowSlot) -> list:
        groups, current = [], []
        for run in paragraph.findall("w:r", NS):
            yellow = bool(run.xpath('./w:rPr/w:highlight[@w:val="yellow"]', namespaces=NS))
            nodes = run.findall("w:t", NS)
            if yellow:
                current.extend(nodes)
            elif nodes and current:
                groups.append(current)
                current = []
        if current:
            groups.append(current)
        if slot.paragraph == 225 and groups:
            return groups[0]
        if not groups and paragraph.xpath('./w:pPr/w:rPr/w:highlight[@w:val="yellow"]', namespaces=NS):
            return []
        if slot.segment >= len(groups):
            raise ValueError("Vị trí nhập không bôi vàng")
        return groups[slot.segment]

    @staticmethod
    def _replace_range(nodes: list, start: int, end: int, value: str) -> None:
        offset, inserted = 0, False
        for node in nodes:
            text = node.text or ""
            node_end = offset + len(text)
            if node_end > start and offset < end:
                left, right = max(0, start - offset), min(len(text), end - offset)
                node.text = text[:left] + (value if not inserted else "") + text[right:]
                node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                inserted = True
            offset = node_end
        if not inserted:
            raise ValueError("Vùng vàng không có nội dung thay thế")

    @staticmethod
    def _force_regular_text(run) -> None:
        """Override bold inherited from the template for entered share values."""
        properties = run.find("w:rPr", NS)
        if properties is None:
            properties = etree.Element(W + "rPr")
            run.insert(0, properties)

        bold_cs = properties.find("w:bCs", NS)
        bold = properties.find("w:b", NS)
        if bold is None:
            bold = etree.Element(W + "b")
            if bold_cs is not None:
                properties.insert(properties.index(bold_cs), bold)
            else:
                fonts = properties.find("w:rFonts", NS)
                properties.insert(properties.index(fonts) + 1 if fonts is not None else 0, bold)
        if bold_cs is None:
            bold_cs = etree.Element(W + "bCs")
            properties.insert(properties.index(bold) + 1, bold_cs)
        bold.set(W + "val", "0")
        bold_cs.set(W + "val", "0")

    @staticmethod
    def _force_bold_text(run) -> None:
        """Make an entered main-industry marker explicitly bold."""
        properties = run.find("w:rPr", NS)
        if properties is None:
            properties = etree.Element(W + "rPr")
            run.insert(0, properties)

        bold_cs = properties.find("w:bCs", NS)
        bold = properties.find("w:b", NS)
        if bold is None:
            bold = etree.Element(W + "b")
            if bold_cs is not None:
                properties.insert(properties.index(bold_cs), bold)
            else:
                fonts = properties.find("w:rFonts", NS)
                properties.insert(properties.index(fonts) + 1 if fonts is not None else 0, bold)
        if bold_cs is None:
            bold_cs = etree.Element(W + "bCs")
            properties.insert(properties.index(bold) + 1, bold_cs)
        bold.set(W + "val", "1")
        bold_cs.set(W + "val", "1")

    @staticmethod
    def _set_paragraph_alignment(paragraph, alignment: str) -> None:
        properties = paragraph.find("w:pPr", NS)
        if properties is None:
            properties = etree.Element(W + "pPr")
            paragraph.insert(0, properties)
        justification = properties.find("w:jc", NS)
        if justification is None:
            justification = etree.Element(W + "jc")
            run_properties = properties.find("w:rPr", NS)
            properties.insert(
                properties.index(run_properties) if run_properties is not None else len(properties),
                justification,
            )
        justification.set(W + "val", alignment)

    @staticmethod
    def _collapse_empty_paragraph(paragraph) -> None:
        """Keep template paragraph indexes stable while hiding an unused line."""
        properties = paragraph.find("w:pPr", NS)
        if properties is None:
            properties = etree.Element(W + "pPr")
            paragraph.insert(0, properties)
        spacing = properties.find("w:spacing", NS)
        if spacing is None:
            spacing = etree.Element(W + "spacing")
            run_properties = properties.find("w:rPr", NS)
            properties.insert(properties.index(run_properties) if run_properties is not None else len(properties), spacing)
        for key, value in (("before", "0"), ("after", "0"), ("line", "1"), ("lineRule", "exact")):
            spacing.set(W + key, value)
        paragraph_mark = properties.find("w:rPr", NS)
        if paragraph_mark is None:
            paragraph_mark = etree.SubElement(properties, W + "rPr")
        if paragraph_mark.find("w:vanish", NS) is None:
            etree.SubElement(paragraph_mark, W + "vanish")
        for run in paragraph.findall("w:r", NS):
            run_properties = run.find("w:rPr", NS)
            if run_properties is None:
                run_properties = etree.Element(W + "rPr")
                run.insert(0, run_properties)
            if run_properties.find("w:vanish", NS) is None:
                etree.SubElement(run_properties, W + "vanish")

    @staticmethod
    def _align_address_pair(paragraph, right_label_run_index: int) -> None:
        """Start the second address field at the middle of the writable line."""
        properties = paragraph.find("w:pPr", NS)
        if properties is None:
            properties = etree.Element(W + "pPr")
            paragraph.insert(0, properties)
        tabs = properties.find("w:tabs", NS)
        if tabs is None:
            tabs = etree.Element(W + "tabs")
            properties.insert(0, tabs)
        tab_stop = etree.SubElement(tabs, W + "tab")
        tab_stop.set(W + "val", "left")
        tab_stop.set(W + "pos", "4800")

        runs = paragraph.findall("w:r", NS)
        if right_label_run_index >= len(runs):
            raise ValueError("Vị trí trường bên phải không khớp mẫu đã kiểm tra")
        right_label_run = runs[right_label_run_index]
        label = right_label_run.find("w:t", NS)
        if label is None or not (label.text or "").startswith(" "):
            raise ValueError("Nhãn trường bên phải không khớp mẫu đã kiểm tra")
        label.text = label.text.lstrip()
        label.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        right_label_run.insert(right_label_run.index(label), etree.Element(W + "tab"))

    def fill_xml(self, data: bytes, values: dict[str, str]) -> bytes:
        root = etree.fromstring(data)
        paragraphs = root.findall(".//w:p", NS)
        line_tables = {}
        if selected(values.get("change_business_lines_selected", "")):
            for kind, start in (("add", 158), ("remove", 167), ("detail", 176)):
                table = paragraphs[start].getparent().getparent().getparent()
                line_tables[kind] = (table, deepcopy(table.findall("w:tr", NS)[-1]))
        for slot in SLOTS:
            if slot.selection and not selected(values.get(slot.selection, "")):
                continue
            value = values.get(slot.key, "").strip()
            if not value:
                continue
            paragraph = paragraphs[slot.paragraph]
            nodes = self._slot_nodes(paragraph, slot)
            if slot.continuation:
                value = ""
            if not nodes:
                run = etree.SubElement(paragraph, W + "r")
                run.append(deepcopy(paragraph.find("w:pPr/w:rPr", NS)))
                etree.SubElement(run, W + "t").text = value
                value_runs = [run]
            else:
                old = "".join(node.text or "" for node in nodes)
                start, end = 0, len(old)
                if slot.paragraph == 225:
                    marker = " đến ngày "
                    split = old.index(marker)
                    start, end = (0, split) if slot.segment == 0 else (split + len(marker), len(old))
                self._replace_range(nodes, start, end, value)
                value_runs = list({node.getparent() for node in nodes})
            if slot.key in SHARE_VALUE_KEYS:
                for run in value_runs:
                    self._force_regular_text(run)
        # These three inputs use continuation lines in the blank template. Once
        # populated, let Word wrap the value naturally and remove the unused
        # continuation paragraph so it cannot create a visible blank line.
        if selected(values.get("change_name_selected", "")):
            for value_key, paragraph_index in (("new_company_name", 27), ("new_company_english_name", 29)):
                if values.get(value_key, "").strip():
                    paragraph = paragraphs[paragraph_index]
                    self._collapse_empty_paragraph(paragraph)
            if values.get("new_company_short_name", "").strip():
                label_paragraph = paragraphs[30]
                label_runs = label_paragraph.findall("w:r", NS)
                label_node = label_runs[-1].find("w:t", NS) if label_runs else None
                if label_node is None or not re.fullmatch(r"\): [.…]+", label_node.text or ""):
                    raise ValueError("Vị trí tên viết tắt không khớp mẫu đã kiểm tra")
                label_node.text = "): "
                label_node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                value_paragraph = paragraphs[31]
                value_run = value_paragraph.find("w:r", NS)
                if value_run is None or value_run.find("w:rPr/w:highlight[@w:val='yellow']", NS) is None:
                    raise ValueError("Vị trí tên viết tắt không còn bôi vàng")
                label_paragraph.append(value_run)
                self._collapse_empty_paragraph(value_paragraph)
        # User-authorized variable rows: clone only the reviewed blank data row,
        # keeping headers, cell/paragraph/run formatting and the rest of the form.
        for kind, (table, blank_row) in line_tables.items():
            count = max(1, line_row_count(values, kind))
            rows = table.findall("w:tr", NS)
            for row in rows[count + 1:]:
                table.remove(row)
            for i in range(len(rows), count + 1):
                row = deepcopy(blank_row)
                suffixes = ("number", "name", "code", "note" if kind == "remove" else "main")
                for cell, suffix in zip(row.findall("w:tc", NS), suffixes):
                    value = values.get(f"amendment_line_{kind}_{i}_{suffix}", "").strip()
                    if not value:
                        continue
                    paragraph = cell.find("w:p", NS)
                    nodes = self._slot_nodes(paragraph, YellowSlot(0, suffix))
                    if nodes:
                        self._replace_range(nodes, 0, len(''.join(node.text or '' for node in nodes)), value)
                    else:
                        run = etree.SubElement(paragraph, W + "r")
                        run.append(deepcopy(paragraph.find("w:pPr/w:rPr", NS)))
                        etree.SubElement(run, W + "t").text = value
                table.append(row)
            # Apply alignment only to populated data rows. Template headers and
            # the single untouched blank row retain their original formatting.
            suffixes = ("number", "name", "code", "note" if kind == "remove" else "main")
            for i, row in enumerate(table.findall("w:tr", NS)[1:], 1):
                if not any(values.get(f"amendment_line_{kind}_{i}_{suffix}", "").strip() for suffix in suffixes):
                    continue
                alignments = ("center", "left", "center", "left" if kind == "remove" else "center")
                cells = row.findall("w:tc", NS)
                for cell, alignment in zip(cells, alignments):
                    for paragraph in cell.findall("w:p", NS):
                        self._set_paragraph_alignment(paragraph, alignment)
                if kind != "remove" and selected(values.get(f"amendment_line_{kind}_{i}_main", "")):
                    for run in cells[3].findall(".//w:r", NS):
                        if "".join(run.xpath(".//w:t/text()", namespaces=NS)).strip():
                            self._force_bold_text(run)
        # User-approved exception: optional fax and website are not yellow.
        # Replace only their dotted inputs, preserving labels and run formatting.
        if selected(values.get("change_address_selected", "")):
            for paragraph_index, run_index, key in ((37, 6, "new_company_fax"), (38, 10, "new_company_website")):
                value = values.get(key, "").strip()
                if not value:
                    continue
                run = paragraphs[paragraph_index].findall("w:r", NS)[run_index]
                node = run.find("w:t", NS)
                if node is None or not re.fullmatch(r"\): [.…]+", node.text or "") or run.find("w:rPr/w:highlight", NS) is not None:
                    raise ValueError("Vị trí fax/website bổ sung không khớp mẫu đã kiểm tra")
                self._replace_range([node], 3, len(node.text), value)
            if values.get("new_company_phone", "").strip() or values.get("new_company_fax", "").strip():
                self._align_address_pair(paragraphs[37], 2)
            if values.get("new_company_email", "").strip() or values.get("new_company_website", "").strip():
                self._align_address_pair(paragraphs[38], 6)
        # Word requires explicit breaks; literal newlines in w:t render as spaces.
        # Keep all inserted text and breaks inside the original yellow run.
        for node in root.findall('.//w:t', NS):
            if "\n" not in (node.text or "") or not node.getparent().xpath('./w:rPr/w:highlight[@w:val="yellow"]', namespaces=NS):
                continue
            parts = node.text.replace("\r\n", "\n").split("\n")
            node.text = parts[0]
            parent, index = node.getparent(), node.getparent().index(node) + 1
            for part in parts[1:]:
                parent.insert(index, etree.Element(W + "br"))
                text = etree.Element(W + "t")
                text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                text.text = part
                parent.insert(index + 1, text)
                index += 2
        return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)

    def generate(self, values: dict[str, str], case_name: str, output_dir: Path | None = None) -> GenerationResult:
        template_issues = self.validate_templates(values)
        issues = self.validation_issues(values)
        if template_issues or issues:
            raise ValueError("\n".join(template_issues.get(self.TEMPLATE_NAME, []) + issues))
        composed = self.composed_values(values)
        if output_dir is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            output_dir = self.export_root / f"thay_doi_dkdn_{stamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / self.TEMPLATE_NAME
        shutil.copy2(self.template_dir / self.TEMPLATE_NAME, output_path)
        try:
            DocxPackageEditor.rewrite_xml_parts(output_path, lambda name, data: self.fill_xml(data, composed) if name == "word/document.xml" else data)
        except Exception:
            output_path.unlink(missing_ok=True)
            raise
        return GenerationResult(output_dir, [GeneratedDocument(self.TEMPLATE_NAME, output_path)], [], {})

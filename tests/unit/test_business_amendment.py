from __future__ import annotations

import tempfile
import time
import unittest
import zipfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton, QScrollArea
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtTest import QTest
from lxml import etree

from mingo_assistant.app.container import AppContainer
from mingo_assistant.app.paths import AppPaths
from mingo_assistant.services.documents.business_amendment_generator import BusinessAmendmentTemplateGenerator
from mingo_assistant.ui.main_window import MainWindow
from mingo_assistant.ui.views.business_amendment_workspace import (
    BUSINESS_AMENDMENT_CASE_TYPE, BusinessAmendmentWorkspace,
)
from mingo_assistant.services.documents.business_amendment_fields import AMENDMENT_FIELD_GROUPS
from mingo_assistant.models.case import CaseSummary
from mingo_assistant.ui.views.business_registration_workspace import BusinessRegistrationWorkspace


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = PROJECT_ROOT / "assets" / "templates" / "word" / "business_amendment"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def sample_values():
    return {"parent_entity_name": "CÔNG TY TNHH KIỂM THỬ", "parent_entity_registration_number": "0319291466",
            "business_registration_office": "Phòng Đăng ký kinh doanh Thành phố Hồ Chí Minh",
            "document_place": "TP. Hồ Chí Minh", "document_day": "08", "document_month": "10", "document_year": "2026",
            "legal_representative_full_name": "NGUYỄN THỊ KIỂM THỬ", "change_name_selected": "X",
            "new_company_name": "CÔNG TY TNHH TÊN MỚI"}


def sample_line_values():
    values = sample_values() | {"change_business_lines_selected": "X"}
    for kind, codes in (("add", ("6201", "6311", "7020")), ("remove", ("4690", "7490")), ("detail", ("6209",))):
        for i, code in enumerate(codes, 1):
            prefix = f"amendment_line_{kind}_{i}_"
            values[prefix + "name"] = f"Ngành kiểm thử {kind} {i}\nChi tiết: nội dung thử nghiệm {i}"
            values[prefix + "code"] = code
            if kind == "remove":
                values[prefix + "note"] = f"Bỏ ngành {i}\nGhi chú kiểm thử"
    values["amendment_line_detail_1_main"] = "X"
    return values


def node_text(node) -> str:
    return "".join(node.xpath(".//w:t/text()", namespaces=NS))


def paragraph_containing(root, marker: str):
    return next(paragraph for paragraph in root.findall(".//w:p", NS) if marker in node_text(paragraph))


def table_containing(root, marker: str):
    return next(table for table in root.findall(".//w:tbl", NS) if marker in node_text(table))


class BusinessAmendmentGeneratorTests(unittest.TestCase):
    def test_entered_company_names_export_when_saved_selection_flag_is_missing(self):
        values = sample_values() | {
            "change_name_selected": "",
            "new_company_name": "Công ty TNHH ABC",
            "new_company_english_name": "ABC Company",
            "new_company_short_name": "ABC CO.,LTD",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            result = BusinessAmendmentTemplateGenerator(TEMPLATE_DIR, Path(temp_dir)).generate(values, "name-change")
            with zipfile.ZipFile(result.generated[0].output_path) as package:
                root = etree.fromstring(package.read("word/document.xml"))
        paragraphs = ["".join(paragraph.xpath(".//w:t/text()", namespaces=NS))
                      for paragraph in root.findall(".//w:p", NS)]
        text = "\n".join(paragraphs)
        self.assertIn("CÔNG TY TNHH ABC", text)
        self.assertIn("ABC Company", text)
        self.assertIn("ABC CO.,LTD", text)
        self.assertIn("ĐĂNG KÝ THAY ĐỔI TÊN DOANH NGHIỆP", paragraphs)
        self.assertNotIn("ĐĂNG KÝ THAY ĐỔI ĐỊA CHỈ TRỤ SỞ CHÍNH", paragraphs)
        self.assertIn("Tên doanh nghiệp viết tắt sau khi thay đổi (nếu có): ABC CO.,LTD", paragraphs)
        short_name_paragraph = next(
            paragraph for paragraph in root.findall(".//w:p", NS)
            if "Tên doanh nghiệp viết tắt sau khi thay đổi" in "".join(paragraph.xpath(".//w:t/text()", namespaces=NS))
        )
        self.assertEqual(
            "preserve",
            short_name_paragraph.findall("w:r", NS)[-2].find("w:t", NS).get(
                "{http://www.w3.org/XML/1998/namespace}space"
            ),
        )
        short_name_run = next(
            run for run in root.findall(".//w:r", NS)
            if "ABC CO.,LTD" in "".join(run.xpath(".//w:t/text()", namespaces=NS))
        )
        self.assertIsNotNone(short_name_run.find("w:rPr/w:highlight[@w:val='yellow']", NS))

    def test_inactive_industry_is_removed_and_active_group_keeps_all_three_tables(self):
        cases = [sample_values(), sample_values() | {
            "change_business_lines_selected": "X", "amendment_line_add_row_count": "0",
            "amendment_line_remove_row_count": "0", "amendment_line_detail_row_count": "1",
            "amendment_line_detail_1_name": "Ngành sửa chi tiết", "amendment_line_detail_1_code": "6201",
            "amendment_line_add_1_name": "STALE MUST NOT EXPORT", "amendment_line_add_1_code": "9999",
        }]
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = BusinessAmendmentTemplateGenerator(TEMPLATE_DIR, Path(temp_dir))
            for values in cases:
                with self.subTest(active=values.get("change_business_lines_selected")):
                    result = generator.generate(values, "empty-industry-tables")
                    with zipfile.ZipFile(result.generated[0].output_path) as package:
                        root = etree.fromstring(package.read("word/document.xml"))
                    self.assertNotIn("STALE MUST NOT EXPORT", ''.join(root.xpath('.//w:t/text()', namespaces=NS)))
                    document_text = node_text(root)
                    if values == cases[0]:
                        self.assertNotIn("THÔNG BÁO THAY ĐỔI NGÀNH, NGHỀ KINH DOANH", document_text)
                        continue
                    for heading in ("được bổ sung", "được bỏ khỏi", "được sửa đổi chi tiết"):
                        table = table_containing(root, heading)
                        rows = table.findall('w:tr', NS)
                        self.assertEqual(2, len(rows))
                        if heading != "được sửa đổi chi tiết":
                            self.assertEqual("", node_text(rows[1]))

    def test_all_three_tables_export_one_thousand_industries_without_a_limit(self):
        values = sample_values() | {"change_business_lines_selected": "X"}
        for kind in ("add", "remove", "detail"):
            values[f"amendment_line_{kind}_row_count"] = "1000"
            for index in range(1, 1001):
                values[f"amendment_line_{kind}_{index}_name"] = f"Ngành {kind} {index}"
                values[f"amendment_line_{kind}_{index}_code"] = "6201"
        with tempfile.TemporaryDirectory() as temp_dir:
            result = BusinessAmendmentTemplateGenerator(TEMPLATE_DIR, Path(temp_dir)).generate(values, "large-dossier")
            with zipfile.ZipFile(result.generated[0].output_path) as package:
                root = etree.fromstring(package.read("word/document.xml"))
        for kind, heading in (("add", "được bổ sung"), ("remove", "được bỏ khỏi"), ("detail", "được sửa đổi chi tiết")):
            table = next(table for table in root.findall('.//w:tbl', NS)
                         if heading in ''.join(table.xpath('w:tr[1]//w:t/text()', namespaces=NS)))
            rows = table.findall('w:tr', NS)
            self.assertEqual(1001, len(rows))
            self.assertIsNotNone(rows[0].find('w:trPr/w:cantSplit', NS))
            self.assertIsNotNone(rows[0].find('w:trPr/w:tblHeader', NS))
            self.assertEqual("1000", ''.join(rows[-1].find('w:tc', NS).xpath('.//w:t/text()', namespaces=NS)))
            self.assertIn(f"Ngành {kind} 1000", ''.join(rows[-1].xpath('.//w:t/text()', namespaces=NS)))

    def test_variable_line_rows_clone_format_and_support_all_three_tables(self):
        values = sample_line_values() | {"amendment_line_add_row_count": "5", "amendment_line_remove_row_count": "1", "amendment_line_detail_row_count": "3"}
        for kind, indices in (("add", (4, 5)), ("detail", (2, 3))):
            for i in indices:
                values[f"amendment_line_{kind}_{i}_name"] = f"Ngành mở rộng {i}\nChi tiết: dòng thêm"
                values[f"amendment_line_{kind}_{i}_code"] = "6201"
        self.assertEqual([], BusinessAmendmentTemplateGenerator.validation_issues(values))
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = BusinessAmendmentTemplateGenerator(TEMPLATE_DIR, Path(temp_dir))
            result = generator.generate(values, "variable-rows")
            with zipfile.ZipFile(result.generated[0].output_path) as package:
                final = etree.fromstring(package.read('word/document.xml'))
            for kind, heading, count in (("add", "Tên ngành, nghề kinh doanh được bổ sung", 5), ("remove", "Tên ngành, nghề kinh doanh được bỏ khỏi danh sách đã đăng ký", 1), ("detail", "Tên ngành, nghề kinh doanh được sửa đổi chi tiết", 3)):
                table = next(t for t in final.findall('.//w:tbl', NS) if heading in ''.join(t.xpath('.//w:t/text()', namespaces=NS)))
                rows = table.findall('w:tr', NS)
                self.assertEqual(count + 1, len(rows))
                for i, row in enumerate(rows[1:], 1):
                    cells = row.findall('w:tc', NS)
                    self.assertEqual(str(i), ''.join(cells[0].xpath('.//w:t/text()', namespaces=NS)))
                    self.assertTrue(cells[1].findall('.//w:br', NS))
                    self.assertTrue(cells[1].xpath('.//w:rPr/w:highlight[@w:val="yellow"]', namespaces=NS))
                    alignments = ("center", "left", "center", "left" if kind == "remove" else "center")
                    for cell, expected in zip(cells, alignments):
                        for paragraph in cell.findall('w:p', NS):
                            self.assertEqual(
                                expected,
                                paragraph.find('w:pPr/w:jc', NS).get(f"{{{NS['w']}}}val"),
                            )
                self.assertNotIn("Bỏ ngành 2", ''.join(table.xpath('.//w:t/text()', namespaces=NS)))
            self.assertIn("Doanh nghiệp cam kết đáp ứng điều kiện tiếp cận thị trường", ''.join(final.xpath('.//w:t/text()', namespaces=NS)))

    def test_all_three_line_tables_export_and_preserve_non_input_content(self):
        values = sample_line_values()
        self.assertEqual([], BusinessAmendmentTemplateGenerator.validation_issues(values))
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = BusinessAmendmentTemplateGenerator(TEMPLATE_DIR, Path(temp_dir))
            result = generator.generate(values, "industry-test")
            with zipfile.ZipFile(TEMPLATE_DIR / generator.TEMPLATE_NAME) as before, zipfile.ZipFile(result.generated[0].output_path) as after:
                final_root = etree.fromstring(after.read('word/document.xml'))
                line_tables = [table for table in final_root.findall('.//w:tbl', NS)
                               if any(heading in ''.join(table.xpath('w:tr[1]//w:t/text()', namespaces=NS))
                                      for heading in ("được bổ sung", "được bỏ khỏi", "được sửa đổi chi tiết"))]
                for kind, table in zip(("add", "remove", "detail"), line_tables):
                    for i, row in enumerate(table.findall('w:tr', NS)[1:], 1):
                        for cell, suffix in zip(row.findall('w:tc', NS), ("number", "name", "code", "note" if kind == "remove" else "main")):
                            text = BusinessAmendmentTemplateGenerator.composed_values(values).get(f"amendment_line_{kind}_{i}_{suffix}", "")
                            self.assertEqual(text.replace('\n', ''), ''.join(cell.xpath('.//w:t/text()', namespaces=NS)))
                fixed_text = node_text(final_root)
                self.assertIn("1. Bổ sung ngành, nghề kinh doanh sau", fixed_text)
                self.assertIn("2. Bỏ ngành, nghề kinh doanh", fixed_text)
                self.assertIn("3. Sửa đổi chi tiết ngành, nghề kinh doanh", fixed_text)
                self.assertIn("Doanh nghiệp cam kết đáp ứng điều kiện tiếp cận thị trường", fixed_text)
                for name in before.namelist():
                    if name != 'word/document.xml':
                        self.assertEqual(before.read(name), after.read(name))
        # Skipped input rows do not leave gaps in the exported STT sequence.
        values.pop("amendment_line_add_1_name")
        self.assertEqual("1", BusinessAmendmentTemplateGenerator.composed_values(values)["amendment_line_add_2_number"])
        self.assertTrue(BusinessAmendmentTemplateGenerator.validation_issues(values))

    def test_main_industry_x_is_bold_in_add_and_detail_tables(self):
        headings = {
            "add": "Tên ngành, nghề kinh doanh được bổ sung",
            "detail": "Tên ngành, nghề kinh doanh được sửa đổi chi tiết",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = BusinessAmendmentTemplateGenerator(TEMPLATE_DIR, Path(temp_dir))
            for kind, heading in headings.items():
                values = sample_line_values()
                for key in list(values):
                    if key.endswith("_main"):
                        values[key] = ""
                values[f"amendment_line_{kind}_1_main"] = "X"
                with self.subTest(kind=kind):
                    result = generator.generate(values, f"main-industry-{kind}")
                    with zipfile.ZipFile(result.generated[0].output_path) as package:
                        root = etree.fromstring(package.read("word/document.xml"))
                    table = next(
                        item for item in root.findall(".//w:tbl", NS)
                        if heading in "".join(item.xpath("w:tr[1]//w:t/text()", namespaces=NS))
                    )
                    main_cell = table.findall("w:tr", NS)[1].findall("w:tc", NS)[3]
                    x_run = next(
                        run for run in main_cell.findall(".//w:r", NS)
                        if "X" == "".join(run.xpath(".//w:t/text()", namespaces=NS)).strip()
                    )
                    self.assertEqual("1", x_run.xpath("string(w:rPr/w:b/@w:val)", namespaces=NS))
                    self.assertEqual("1", x_run.xpath("string(w:rPr/w:bCs/@w:val)", namespaces=NS))

    def test_share_inputs_export_verbatim_and_totals_preserve_template(self):
        values = sample_values() | {"change_capital_selected": "X", "registered_capital": "1000000000", "new_capital": "1000000000", "new_share_par_value": "10000",
                                   "amendment_share_1_count": "80000", "amendment_share_1_amount": "800000000", "amendment_share_1_ratio": "80",
                                   "amendment_share_2_count": "20000", "amendment_share_2_amount": "200000000", "amendment_share_2_ratio": "20"}
        self.assertEqual([], BusinessAmendmentTemplateGenerator.validation_issues(values))
        composed = BusinessAmendmentTemplateGenerator.composed_values(values)
        self.assertEqual("800.000.000", composed["amendment_share_1_amount"])
        self.assertEqual("80", composed["amendment_share_1_ratio"])
        self.assertEqual("100.000", composed["amendment_share_total_count"])
        self.assertEqual("1.000.000.000", composed["amendment_share_total_amount"])
        self.assertEqual("100", composed["amendment_share_total_ratio"])
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = BusinessAmendmentTemplateGenerator(TEMPLATE_DIR, Path(temp_dir))
            result = generator.generate(values, "shares-test")
            with zipfile.ZipFile(TEMPLATE_DIR / generator.TEMPLATE_NAME) as package:
                before = etree.fromstring(package.read("word/document.xml")).findall('.//w:p', NS)
            with zipfile.ZipFile(result.generated[0].output_path) as package:
                after_root = etree.fromstring(package.read("word/document.xml"))
            for text in ("10.000", "80.000", "800.000.000", "200.000.000", "100.000"):
                paragraph = paragraph_containing(after_root, text)
                self.assertTrue(paragraph.xpath('.//w:rPr/w:highlight[@w:val="yellow"]', namespaces=NS))
                value_runs = [run for run in paragraph.findall('w:r', NS) if text in ''.join(run.itertext())]
                self.assertEqual(1, len(value_runs))
                self.assertEqual("0", value_runs[0].xpath('string(w:rPr/w:b/@w:val)', namespaces=NS))
                self.assertEqual("0", value_runs[0].xpath('string(w:rPr/w:bCs/@w:val)', namespaces=NS))
            self.assertIn("Cổ phần phổ thông", node_text(after_root))
            self.assertIn("Tổng số", node_text(after_root))
        values["new_share_par_value"] = ""
        values["amendment_share_2_amount"] = ""
        values["amendment_share_2_ratio"] = "10"
        self.assertEqual([], BusinessAmendmentTemplateGenerator.validation_issues(values))

    def test_capital_tables_ignore_legacy_rows_and_force_fixed_ratios(self):
        values = sample_values() | {"change_capital_selected": "X", "registered_capital": "1.000.000.000",
                                   "new_capital": "8.000.000", "capital_change_date": "Sau khi hoàn tất góp vốn",
                                   "amendment_source_2_amount": "1", "amendment_asset_1_amount": "2",
                                   "amendment_source_1_amount": "invalid stale data", "amendment_asset_6_ratio": "invalid stale data",
                                   "amendment_source_2_ratio": "50", "amendment_asset_1_ratio": "20"}
        self.assertEqual([], BusinessAmendmentTemplateGenerator.validation_issues(values))
        composed = BusinessAmendmentTemplateGenerator.composed_values(values)
        self.assertEqual("1.000.000.000 VNĐ (Một tỷ đồng)", composed["registered_capital_text"])
        self.assertEqual("8.000.000", composed["amendment_source_total_amount"])
        self.assertEqual("8.000.000", composed["amendment_asset_total_amount"])
        for kind, count, active in (("source", 4, 2), ("asset", 6, 1)):
            for i in range(1, count + 1):
                self.assertEqual("100%" if i == active else "0", composed[f"amendment_{kind}_{i}_ratio"])
                self.assertEqual("8.000.000" if i == active else "0", composed[f"amendment_{kind}_{i}_amount"])
            self.assertEqual("100%", composed[f"amendment_{kind}_total_ratio"])

    def test_capital_export_auto_fills_tables_without_requiring_share_details(self):
        values = sample_values() | {
            "change_capital_selected": "X",
            "registered_capital": "1.000.000.000",
            "new_capital": "2.000.000.000",
            "capital_change_date": "12/10/2026",
            "capital_change_method": "Tăng vốn góp",
            # A provisional share value must not block an LLC capital export.
            "amendment_share_1_ratio": "10",
        }
        self.assertEqual([], BusinessAmendmentTemplateGenerator.validation_issues(values))
        with tempfile.TemporaryDirectory() as temp_dir:
            result = BusinessAmendmentTemplateGenerator(TEMPLATE_DIR, Path(temp_dir)).generate(values, "capital-only")
            with zipfile.ZipFile(result.generated[0].output_path) as package:
                root = etree.fromstring(package.read("word/document.xml"))
        document_text = node_text(root)
        self.assertGreaterEqual(document_text.count("2.000.000.000"), 5)
        self.assertGreaterEqual(document_text.count("100%"), 4)

    def test_optional_fax_website_keep_unhighlighted_format_and_blank_template(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = BusinessAmendmentTemplateGenerator(TEMPLATE_DIR, Path(temp_dir))
            values = sample_values() | {"change_address_selected": "X", "new_company_address_detail": "123 đường Kiểm Thử",
                                       "new_company_ward": "Phường Kiểm Thử", "new_company_province": "Hà Nội"}
            with zipfile.ZipFile(TEMPLATE_DIR / generator.TEMPLATE_NAME) as package:
                original = etree.fromstring(package.read("word/document.xml")).findall('.//w:p', NS)
            for extra in ({}, {"new_company_fax": "02412345678", "new_company_website": "https://example.com"}):
                result = generator.generate(values | extra, "test")
                with zipfile.ZipFile(result.generated[0].output_path) as package:
                    final_root = etree.fromstring(package.read("word/document.xml"))
                for marker, paragraph, index, key in (("Điện thoại", 37, 6, "new_company_fax"), ("Thư điện tử", 38, 10, "new_company_website")):
                    before = original[paragraph].findall('w:r', NS)[index]
                    after = paragraph_containing(final_root, marker).findall('w:r', NS)[index]
                    self.assertEqual(etree.tostring(before.find('w:rPr', NS)), etree.tostring(after.find('w:rPr', NS)))
                    self.assertIsNone(after.find('w:rPr/w:highlight', NS))
                    self.assertEqual('): '+extra[key] if key in extra else before.find('w:t', NS).text,
                                     after.find('w:t', NS).text)

    def test_all_entered_address_fields_replace_dots_and_blank_fields_keep_template(self):
        filled = sample_values() | {
            "change_address_selected": "X",
            "new_company_address_detail": "123 Đường Kiểm Thử",
            "new_company_ward": "Phường Kiểm Thử",
            "new_company_province": "Thành phố Hồ Chí Minh",
            "new_company_phone": "0901234567",
            "new_company_fax": "0281234567",
            "new_company_email": "contact@example.com",
            "new_company_website": "https://example.com",
        }
        required_only = {
            **filled,
            "new_company_phone": "",
            "new_company_fax": "",
            "new_company_email": "",
            "new_company_website": "",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = BusinessAmendmentTemplateGenerator(TEMPLATE_DIR, Path(temp_dir))
            with zipfile.ZipFile(TEMPLATE_DIR / generator.TEMPLATE_NAME) as package:
                original = etree.fromstring(package.read("word/document.xml")).findall(".//w:p", NS)
            filled_result = generator.generate(filled, "filled-address")
            blank_result = generator.generate(required_only, "blank-optionals")
            with zipfile.ZipFile(filled_result.generated[0].output_path) as package:
                filled_root = etree.fromstring(package.read("word/document.xml"))
            with zipfile.ZipFile(blank_result.generated[0].output_path) as package:
                blank_root = etree.fromstring(package.read("word/document.xml"))

        for value in ("123 Đường Kiểm Thử", "Phường Kiểm Thử", "Thành phố Hồ Chí Minh", "0901234567", "contact@example.com", "0281234567", "https://example.com"):
            self.assertIn(value, node_text(filled_root))
        for marker, right_label_run in (("Điện thoại", 2), ("Thư điện tử", 6)):
            paragraph = paragraph_containing(filled_root, marker)
            tab_stop = paragraph.find("w:pPr/w:tabs/w:tab", NS)
            self.assertIsNotNone(tab_stop)
            self.assertEqual("4800", tab_stop.get("{" + NS["w"] + "}pos"))
            self.assertIsNotNone(paragraph.findall("w:r", NS)[right_label_run].find("w:tab", NS))
        for marker in ("Số nhà/phòng", "Xã/Phường", "Tỉnh/Thành phố", "Điện thoại", "Thư điện tử"):
            self.assertNotIn("…", node_text(paragraph_containing(filled_root, marker)))
        for marker, paragraph, run_index in (("Điện thoại", 37, 1), ("Điện thoại", 37, 6), ("Thư điện tử", 38, 5), ("Thư điện tử", 38, 10)):
            self.assertEqual(
                etree.tostring(original[paragraph].findall("w:r", NS)[run_index]),
                etree.tostring(paragraph_containing(blank_root, marker).findall("w:r", NS)[run_index]),
            )

    def test_capital_checkboxes_and_multiline_text_stay_inside_yellow_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = BusinessAmendmentTemplateGenerator(TEMPLATE_DIR, Path(temp_dir))
            values = sample_values() | {"change_capital_selected": "X", "registered_capital": "100", "new_capital": "200",
                                       "capital_change_date": "08/10/2026", "capital_change_method": "Tăng vốn",
                                       "change_business_lines_selected": "X", "amendment_line_add_1_name": "Lập trình\nChi tiết: phần mềm",
                                       "amendment_line_add_1_code": "6201"}
            for choice, yes, no in (("Có", "□", "F053"), ("Không", "□", "F053")):
                result = generator.generate(values | {"capital_show_foreign_equivalent": choice}, "test")
                with zipfile.ZipFile(result.generated[0].output_path) as package:
                    root = etree.fromstring(package.read("word/document.xml"))
                capital_choice = paragraph_containing(root, "Có hiển thị thông tin")
                self.assertEqual(yes, capital_choice.findall('w:r', NS)[1].find('w:t', NS).text)
                self.assertEqual(no, capital_choice.find('w:r/w:sym', NS).get('{'+NS['w']+'}char'))
                breaks = paragraph_containing(root, "Lập trình").findall('.//w:br', NS)
                self.assertTrue(breaks)
                for br in breaks:
                    self.assertTrue(br.getparent().xpath('./w:rPr/w:highlight[@w:val="yellow"]', namespaces=NS))

    def test_export_changes_only_allowlisted_yellow_text_and_preserves_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = BusinessAmendmentTemplateGenerator(TEMPLATE_DIR, Path(temp_dir))
            values = sample_values()
            values.update({"change_business_lines_selected": "X", "amendment_line_add_1_name": "Lập trình máy vi tính",
                           "amendment_line_add_1_code": "6201", "amendment_line_add_1_main": "X",
                           "change_tax_selected": "X", "tax_financial_year_start": "01/01", "tax_financial_year_end": "31/12"})
            original = (TEMPLATE_DIR / generator.TEMPLATE_NAME).read_bytes()
            result = generator.generate(values, "test")
            self.assertEqual(1, len(result.generated))
            self.assertEqual([], result.skipped)
            self.assertEqual({}, result.unresolved)
            self.assertEqual(original, (TEMPLATE_DIR / generator.TEMPLATE_NAME).read_bytes())
            with zipfile.ZipFile(TEMPLATE_DIR / generator.TEMPLATE_NAME) as source, zipfile.ZipFile(result.generated[0].output_path) as final:
                self.assertEqual(source.namelist(), final.namelist())
                for name in source.namelist():
                    if name != "word/document.xml":
                        self.assertEqual(source.read(name), final.read(name), name)
                before = etree.fromstring(source.read("word/document.xml"))
                after = etree.fromstring(final.read("word/document.xml"))
            text = " ".join(after.xpath('//w:t/text()', namespaces=NS))
            self.assertIn("CÔNG TY TNHH TÊN MỚI", text)
            self.assertIn("Lập trình máy vi tính", text)
            self.assertIn("01/01", text)
            self.assertIn("31/12", text)
            self.assertIn(" đến ngày ", node_text(paragraph_containing(after, "đến ngày")))
            self.assertNotIn("CÔNG TY TNHH XYZ", text)
            self.assertNotIn("NGUYỄN VĂN A", text)
            self.assertNotIn("ĐĂNG KÝ THAY ĐỔI ĐỊA CHỈ TRỤ SỞ CHÍNH", text)
            self.assertNotIn("ĐĂNG KÝ THAY ĐỔI VỐN ĐIỀU LỆ", text)
            self.assertNotIn("ĐĂNG KÝ THAY ĐỔI THÀNH VIÊN", text)
            self.assertNotIn("B. BỔ SUNG, CẬP NHẬT", text)
            self.assertNotIn("C. ĐỀ NGHỊ HIỆU ĐÍNH", text)

    def test_full_tax_table_values_reach_reviewed_yellow_slots(self) -> None:
        tax_values = {
            "change_tax_selected": "X",
            "tax_director_full_name": "TRẦN GIÁM ĐỐC",
            "tax_director_date_of_birth": "01/02/1985",
            "tax_director_gender": "Nam",
            "tax_director_id_number": "012345678901",
            "tax_director_phone": "0901000001",
            "tax_accountant_full_name": "LÊ KẾ TOÁN",
            "tax_accountant_date_of_birth": "03/04/1990",
            "tax_accountant_gender": "Nữ",
            "tax_accountant_id_number": "012345678902",
            "tax_accountant_phone": "0901000002",
            "tax_notification_address_detail": "12 đường Kiểm Thử",
            "tax_notification_ward": "Phường Kiểm Thử",
            "tax_notification_province": "Thành phố Hà Nội",
            "tax_notification_phone": "0241234567",
            "tax_notification_email": "thue@example.com",
            "tax_start_date": "08/10/2026",
            "tax_financial_year_start": "01/01",
            "tax_financial_year_end": "31/12",
            "tax_labor_count": "25",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = BusinessAmendmentTemplateGenerator(TEMPLATE_DIR, Path(temp_dir))
            result = generator.generate(sample_values() | tax_values, "test")
            with zipfile.ZipFile(result.generated[0].output_path) as package:
                root = etree.fromstring(package.read("word/document.xml"))
        document_text = " ".join(root.xpath("//w:t/text()", namespaces=NS))
        for expected in (
            "TRẦN GIÁM ĐỐC", "LÊ KẾ TOÁN", "12 đường Kiểm Thử", "Phường Kiểm Thử",
            "Thành phố Hà Nội", "thue@example.com", "08/10/2026", "01/01", "31/12", "25",
        ):
            self.assertIn(expected, document_text)
        self.assertIn("THÔNG BÁO THAY ĐỔI THÔNG TIN ĐĂNG KÝ THUẾ", document_text)

    def test_beneficial_notice_choices_replace_only_their_yellow_template_text(self) -> None:
        values = sample_values() | {
            "change_beneficial_selected": "X",
            "beneficial_notice_a_status": "Không có",
            "beneficial_notice_b_status": "Gửi kèm",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = BusinessAmendmentTemplateGenerator(TEMPLATE_DIR, Path(temp_dir))
            result = generator.generate(values, "beneficial-notice")
            with zipfile.ZipFile(result.generated[0].output_path) as package:
                after = etree.fromstring(package.read("word/document.xml"))
        self.assertTrue(node_text(paragraph_containing(after, "bao gồm người quản lý doanh nghiệp")).endswith("Không có."))
        self.assertTrue(node_text(paragraph_containing(after, "Đối với doanh nghiệp được thành lập")).endswith("Gửi kèm."))
        for marker in ("bao gồm người quản lý doanh nghiệp", "Đối với doanh nghiệp được thành lập"):
            self.assertTrue(paragraph_containing(after, marker).xpath('.//w:rPr/w:highlight[@w:val="yellow"]', namespaces=NS))

    def test_validation_rejects_blank_invalid_dates_and_industry_overflow(self):
        self.assertTrue(BusinessAmendmentTemplateGenerator.validation_issues({}))
        for extra in ({"document_day": "31", "document_month": "02"},
                      {"change_business_lines_selected": "X", "amendment_line_add_4_name": "overflow"}):
            self.assertTrue(BusinessAmendmentTemplateGenerator.validation_issues(sample_values() | extra))

    def test_current_registered_capital_does_not_activate_an_unentered_capital_change(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            values = sample_values() | {
                "registered_capital": "1.000.000.000",
                "beneficial_notice_a_status": "Không có",
                "beneficial_notice_b_status": "Không có",
            }
            generator = BusinessAmendmentTemplateGenerator(TEMPLATE_DIR, Path(temp_dir))
            result = generator.generate(values, "test")
            with zipfile.ZipFile(result.generated[0].output_path) as package:
                root = etree.fromstring(package.read("word/document.xml"))
            text = node_text(root)
            self.assertNotIn("1.000.000.000", text)
            self.assertNotIn("ĐĂNG KÝ THAY ĐỔI VỐN ĐIỀU LỆ", text)
            self.assertNotIn("CHỦ SỞ HỮU HƯỞNG LỢI", text)

    def test_checkboxes_do_not_export_empty_sections_and_unsupported_blocks_are_removed(self):
        values = sample_values() | {
            "change_name_selected": "",
            "new_company_name": "CÔNG TY TNHH CHỈ ĐỔI TÊN",
            "change_address_selected": "X",
            "change_capital_selected": "X",
            "registered_capital": "1.000.000.000",
            "change_business_lines_selected": "X",
            "change_tax_selected": "X",
            "change_beneficial_selected": "X",
            "beneficial_notice_a_status": "Không có",
            "beneficial_notice_b_status": "Không có",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            result = BusinessAmendmentTemplateGenerator(TEMPLATE_DIR, Path(temp_dir)).generate(values, "data-only")
            with zipfile.ZipFile(result.generated[0].output_path) as package:
                root = etree.fromstring(package.read("word/document.xml"))
        text = node_text(root)
        self.assertIn("ĐĂNG KÝ THAY ĐỔI TÊN DOANH NGHIỆP", text)
        for removed in (
            "Doanh nghiệp đăng ký thay đổi trên cơ sở",
            "ĐĂNG KÝ THAY ĐỔI ĐỊA CHỈ TRỤ SỞ CHÍNH",
            "ĐĂNG KÝ THAY ĐỔI THÀNH VIÊN",
            "ĐĂNG KÝ THAY ĐỔI VỐN ĐIỀU LỆ",
            "THÔNG BÁO THAY ĐỔI NGÀNH, NGHỀ KINH DOANH",
            "THÔNG BÁO THAY ĐỔI THÔNG TIN ĐĂNG KÝ THUẾ",
            "CHỦ SỞ HỮU HƯỞNG LỢI",
            "B. BỔ SUNG, CẬP NHẬT",
            "C. ĐỀ NGHỊ HIỆU ĐÍNH",
        ):
            self.assertNotIn(removed, text)

    def test_entered_address_and_capital_export_together_when_saved_flags_are_missing(self):
        values = sample_values() | {
            "change_name_selected": "",
            "change_address_selected": "",
            "new_company_address_detail": "Số nhà 13 Thôn 4",
            "new_company_ward": "Xã Hòa Lạc",
            "new_company_province": "Thành phố Hà Nội",
            "new_company_phone": "0987654321",
            "change_capital_selected": "",
            "registered_capital": "1.000.000.000",
            "new_capital": "20.000.000.000",
            "change_business_lines_selected": "",
            "amendment_line_add_1_name": "Ngành đã nhập trước đó",
            "amendment_line_add_1_code": "6201",
            "change_tax_selected": "",
            "tax_director_full_name": "NGUYỄN GIÁM ĐỐC",
        }
        self.assertEqual([], BusinessAmendmentTemplateGenerator.validation_issues(values))
        with tempfile.TemporaryDirectory() as temp_dir:
            result = BusinessAmendmentTemplateGenerator(TEMPLATE_DIR, Path(temp_dir)).generate(values, "combined")
            with zipfile.ZipFile(result.generated[0].output_path) as package:
                root = etree.fromstring(package.read("word/document.xml"))
        document_text = node_text(root)
        for expected in ("Số nhà 13 Thôn 4", "20.000.000.000", "Ngành đã nhập trước đó", "NGUYỄN GIÁM ĐỐC"):
            self.assertIn(expected, document_text)
        for heading in ("ĐĂNG KÝ THAY ĐỔI ĐỊA CHỈ TRỤ SỞ CHÍNH", "ĐĂNG KÝ THAY ĐỔI VỐN ĐIỀU LỆ", "THÔNG BÁO THAY ĐỔI NGÀNH, NGHỀ KINH DOANH", "THÔNG BÁO THAY ĐỔI THÔNG TIN ĐĂNG KÝ THUẾ"):
            self.assertIn(heading, document_text)

    def test_revised_template_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / BusinessAmendmentTemplateGenerator.TEMPLATE_NAME
            target.write_bytes((TEMPLATE_DIR / target.name).read_bytes() + b"revision")
            generator = BusinessAmendmentTemplateGenerator(root, root / "exports")
            self.assertTrue(generator.validate_templates(sample_values()))
            with self.assertRaises(ValueError):
                generator.generate(sample_values(), "test")
            self.assertFalse((root / "exports").exists())

    def test_missing_or_invalid_template_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            generator = BusinessAmendmentTemplateGenerator(root, root / "exports")
            self.assertTrue(generator.validate_templates({}))
            (root / generator.TEMPLATE_NAME).write_text("invalid DOCX", encoding="utf-8")
            self.assertTrue(generator.validate_templates({}))
            with self.assertRaises(ValueError):
                generator.generate({}, "test")


class BusinessAmendmentWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        paths = AppPaths(PROJECT_ROOT, root / "appdata", root / "exports")
        container = AppContainer.build(paths)
        self.window = MainWindow(
            app_paths=paths,
            case_repository=container.case_repository,
            case_use_cases=container.case_use_cases,
            authorized_person_repository=container.authorized_person_repository,
            authorized_person_use_cases=container.authorized_person_use_cases,
            registration_services=container.registration_services,
            industry_catalog=container.industry_catalog,
        )

    def tearDown(self) -> None:
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        self.temp.cleanup()

    def test_new_tables_start_empty_and_delete_last_row_stays_empty_after_save(self):
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace
        workspace.fields["change_business_lines_selected"].setChecked(True)
        for kind, table in workspace.amendment_line_tables.items():
            self.assertEqual(0, table.rowCount())
            page = table.parentWidget()
            button = next(button for button in page.findChildren(QPushButton) if button.text() == "+ Thêm dòng trống")
            button.click()
            self.assertEqual(1, table.rowCount())
            table.business_line_rows[0].delete_button.click()
            self.assertEqual(0, table.rowCount())
        with patch("mingo_assistant.ui.views.business_registration_workspace.QMessageBox.information"):
            workspace._save_draft()
        case = self.window.case_use_cases.get(workspace.case_id)
        self.window._open_case_workspace(case)
        restored = self.window.current_workspace
        for kind, table in restored.amendment_line_tables.items():
            self.assertEqual(0, table.rowCount())
            self.assertEqual("0", restored.form_values()[f"amendment_line_{kind}_row_count"])
            self.assertNotIn(f"amendment_line_{kind}_1_name", restored.fields)

    def test_populated_industry_rows_require_confirmation_before_delete(self):
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace
        for kind, table in workspace.amendment_line_tables.items():
            workspace._append_amendment_line_row(kind)
            workspace._set_field(f"amendment_line_{kind}_1_name", f"Ngành cần giữ {kind}")
            workspace._set_field(f"amendment_line_{kind}_1_code", "6201")
            with patch("mingo_assistant.ui.views.business_amendment_workspace.QMessageBox.question", return_value=QMessageBox.No) as question:
                table.business_line_rows[0].delete_button.click()
            question.assert_called_once()
            self.assertEqual(1, table.rowCount())
            self.assertEqual(f"Ngành cần giữ {kind}", workspace._field_value(f"amendment_line_{kind}_1_name"))
            with patch("mingo_assistant.ui.views.business_amendment_workspace.QMessageBox.question", return_value=QMessageBox.Yes):
                table.business_line_rows[0].delete_button.click()
            self.assertEqual(0, table.rowCount())

    def test_deleting_industry_row_keeps_outer_workspace_scroll_position(self):
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace
        workspace.fields["change_business_lines_selected"].setChecked(True)
        workspace._select_form_section(3)
        workspace.amendment_line_tabs.setCurrentIndex(1)
        for index in range(6):
            workspace._append_amendment_line_row("remove")
            workspace._set_field(f"amendment_line_remove_{index + 1}_name", f"Ngành bỏ {index + 1}")
            workspace._set_field(f"amendment_line_remove_{index + 1}_code", f"{6200 + index}")

        self.window.resize(1000, 650)
        self.window.show()
        self.app.processEvents()
        scroll = workspace.findChild(QScrollArea, "BusinessWorkspaceScroll")
        self.assertIsNotNone(scroll)
        bar = scroll.verticalScrollBar()
        self.assertGreater(bar.maximum(), 0)
        target = max(1, bar.maximum() // 2)
        bar.setValue(target)
        delete_button = workspace.amendment_line_tables["remove"].business_line_rows[2].delete_button
        delete_button.setFocus()

        with patch(
            "mingo_assistant.ui.views.business_amendment_workspace.QMessageBox.question",
            return_value=QMessageBox.Yes,
        ):
            delete_button.click()
        self.app.processEvents()

        self.assertEqual(5, workspace.amendment_line_tables["remove"].rowCount())
        self.assertEqual(min(target, bar.maximum()), bar.value())

    def test_adding_industry_does_not_force_outer_workspace_to_scroll(self):
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace
        workspace.fields["change_business_lines_selected"].setChecked(True)
        workspace._select_form_section(3)

        self.window.resize(1000, 650)
        self.window.show()
        self.app.processEvents()
        scroll = workspace.findChild(QScrollArea, "BusinessWorkspaceScroll")
        self.assertIsNotNone(scroll)
        bar = scroll.verticalScrollBar()
        self.assertGreater(bar.maximum(), 0)
        target = max(1, bar.maximum() // 3)
        bar.setValue(target)

        workspace._open_amendment_industry_lookup("add")
        industry = next(
            row for row in workspace.industry_catalog.display_rows
            if workspace._industry_row_code(row)
        )
        workspace.industry_search_input.setText(workspace._industry_row_code(industry))
        self.app.processEvents()
        workspace.industry_results_table.selectRow(0)
        workspace._add_selected_industry_row()
        self.app.processEvents()

        self.assertEqual(min(target, bar.maximum()), bar.value())

    def test_legacy_empty_template_rows_are_removed_without_losing_entered_industries(self):
        values = {"amendment_schema_version": "3", "amendment_line_add_row_count": "3",
                  "amendment_line_add_1_name": "", "amendment_line_add_1_code": "",
                  "amendment_line_add_2_name": "Ngành cũ\nChi tiết đã lưu", "amendment_line_add_2_code": "6201",
                  "amendment_line_add_2_main": "X", "amendment_line_add_3_name": "",
                  "amendment_line_remove_row_count": "2", "amendment_line_remove_1_name": "",
                  "amendment_line_remove_2_note": "Ghi chú đang nhập dở", "amendment_line_detail_row_count": "1",
                  "amendment_line_detail_1_name": ""}
        case = CaseSummary("legacy-lines", "COMPANY TEST", BUSINESS_AMENDMENT_CASE_TYPE, "REP", "12/10/2026",
                           "Bản nháp", "", 1, "", form_values=values)
        original = deepcopy(case.to_dict())
        self.window._open_case_workspace(case)
        workspace = self.window.current_workspace
        self.assertEqual({"add": 1, "remove": 1, "detail": 0},
                         {kind: table.rowCount() for kind, table in workspace.amendment_line_tables.items()})
        self.assertEqual("Ngành cũ\nChi tiết đã lưu", workspace._field_value("amendment_line_add_1_name"))
        self.assertEqual("X", workspace._field_value("amendment_line_add_1_main"))
        self.assertEqual("Ghi chú đang nhập dở", workspace._field_value("amendment_line_remove_1_note"))
        self.assertEqual(original, case.to_dict())

    def test_existing_office_completion_fills_signing_place(self):
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace
        field = workspace.fields["business_registration_office"]
        self.assertIsNotNone(field.completer())
        field.textEdited.emit("lam")
        suggestions = workspace.registration_office_completion_model.stringList()
        self.assertTrue(suggestions)
        field.completer().activated[str].emit(suggestions[0])
        self.assertEqual(suggestions[0], field.text())
        self.assertEqual("Lâm Đồng", workspace.fields["document_place"].text())
        self.assertIn("Lâm Đồng, ngày", workspace.fields["document_place_date"].text())

    def test_capital_preview_tables_and_free_text_restore(self):
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace
        workspace.fields["registered_capital"].setText("1000000000")
        self.assertEqual("1.000.000.000", workspace.fields["registered_capital"].text())
        self.assertEqual("1.000.000.000 VNĐ (Một tỷ đồng)", workspace.fields["registered_capital_text"].text())
        self.assertTrue(workspace.fields["registered_capital_text"].isReadOnly())
        workspace.fields["new_capital"].setText("8000000")
        self.assertEqual("8.000.000", workspace.fields["amendment_source_2_amount"].text())
        self.assertEqual("8.000.000", workspace.fields["amendment_asset_1_amount"].text())
        self.assertTrue(workspace.fields["amendment_source_2_amount"].isReadOnly())
        self.assertTrue(workspace.fields["amendment_asset_1_amount"].isReadOnly())
        workspace.fields["capital_change_date"].setText("Sau khi hoàn tất góp vốn")
        workspace.fields["capital_foreign_yes_checked"].setChecked(True)
        for kind in ("source", "asset"):
            table = workspace.amendment_capital_tables[kind]
            self.assertEqual(1, sum(table.cellWidget(row, column) is not None for row in range(table.rowCount()) for column in range(table.columnCount())))
            self.assertEqual("100%", table.item(table.rowCount() - 1, table.columnCount() - 1).text())
        self.window._open_case_workspace(workspace.build_case_summary())
        restored = self.window.current_workspace
        self.assertEqual("8.000.000", restored.fields["amendment_source_2_amount"].text())
        self.assertEqual("8.000.000", restored.fields["amendment_asset_1_amount"].text())
        self.assertEqual("Sau khi hoàn tất góp vốn", restored.fields["capital_change_date"].text())
        self.assertTrue(restored.fields["capital_foreign_yes_checked"].isChecked())
        restored.fields["registered_capital"].clear()
        self.assertEqual("", restored.fields["registered_capital_text"].text())

    def test_editing_saved_case_restores_all_entered_change_sections(self):
        values = sample_values() | {
            "change_name_selected": "",
            "change_address_selected": "",
            "new_company_address_detail": "Số nhà 13 Thôn 4",
            "new_company_ward": "Xã Hòa Lạc",
            "new_company_province": "Thành phố Hà Nội",
            "change_capital_selected": "",
            "registered_capital": "1.000.000.000",
            "new_capital": "20.000.000.000",
        }
        case = CaseSummary(
            "combined-saved-case", "CÔNG TY HIỆN TẠI", BUSINESS_AMENDMENT_CASE_TYPE,
            "NGUYỄN VĂN A", "12/10/2026", "Bản nháp", "", 1, "", form_values=values,
        )
        self.window._open_case_workspace(case)
        workspace = self.window.current_workspace
        workspace._select_form_section(3)
        self.window.show()
        self.app.processEvents()
        for key in ("change_name_selected", "change_address_selected", "change_capital_selected"):
            self.assertTrue(workspace.fields[key].isChecked())
            self.assertFalse(workspace.amendment_change_forms[key].isHidden())
        saved = workspace.build_case_summary()
        self.assertEqual("X", saved.form_values["change_address_selected"])
        self.assertEqual("X", saved.form_values["change_capital_selected"])
        self.assertEqual("20.000.000.000", saved.form_values["new_capital"])
        self.assertEqual("20.000.000.000", saved.form_values["amendment_source_2_amount"])
        self.assertEqual("20.000.000.000", saved.form_values["amendment_asset_1_amount"])

        # Clicking the empty area of another option card must select it too.
        tax_card = workspace.amendment_choice_cards["change_tax_selected"]
        QTest.mouseClick(tax_card, Qt.LeftButton, pos=tax_card.rect().center())
        self.app.processEvents()
        self.assertTrue(workspace.fields["change_tax_selected"].isChecked())
        self.assertFalse(workspace.amendment_change_forms["change_tax_selected"].isHidden())

    def test_tax_table_quick_fill_and_draft_restore(self):
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace
        workspace.fields["change_tax_selected"].setChecked(True)
        workspace._set_fields_from_mapping({
            "legal_representative_full_name": "NGUYỄN VĂN KIỂM TRA",
            "legal_representative_date_of_birth": "01/02/1990",
            "legal_representative_gender": "Nam",
            "legal_representative_id_number": "012345678901",
        })
        workspace.ocr_people[0].name = "LÊ KẾ TOÁN"
        workspace.ocr_people[0].data = {
            "legal_representative_full_name": "LÊ KẾ TOÁN",
            "legal_representative_date_of_birth": "03/04/1990",
            "legal_representative_gender": "Nữ",
            "legal_representative_id_number": "012345678902",
            "personal_phone": "0901000002",
        }
        workspace._refresh_person_fill_selectors()
        director_selector = workspace.tax_person_selectors["director"]
        accountant_selector = workspace.tax_person_selectors["accountant"]
        self.assertEqual("Chọn profile đã lưu", director_selector.itemText(0))
        director_selector.setCurrentIndex(director_selector.findData("representative"))
        self.assertEqual("NGUYỄN VĂN KIỂM TRA", workspace._field_value("tax_director_full_name"))
        self.assertEqual("01/02/1990", workspace._field_value("tax_director_date_of_birth"))
        accountant_selector.setCurrentIndex(accountant_selector.findData("person:0"))
        self.assertEqual("LÊ KẾ TOÁN", workspace._field_value("tax_accountant_full_name"))
        self.assertEqual("0901000002", workspace._field_value("tax_accountant_phone"))
        workspace._fill_tax_standard_financial_year()
        self.assertEqual("01/01", workspace._field_value("tax_financial_year_start"))
        self.assertEqual("31/12", workspace._field_value("tax_financial_year_end"))
        workspace._set_fields_from_mapping({
            "tax_notification_address_detail": "12 đường Nhập Tay",
            "tax_notification_ward": "Phường Kiểm Thử",
            "tax_notification_province": "Thành phố Hà Nội",
        })
        self.assertEqual(9, len(workspace.tax_registration_cards))
        self.assertEqual(
            [str(index) for index in range(1, 10)],
            [label.text() for label in workspace.tax_registration_numbers],
        )
        saved = workspace.build_case_summary()
        self.window._open_case_workspace(saved)
        restored = self.window.current_workspace
        self.assertTrue(restored.fields["change_tax_selected"].isChecked())
        self.assertEqual("NGUYỄN VĂN KIỂM TRA", restored._field_value("tax_director_full_name"))
        self.assertEqual("LÊ KẾ TOÁN", restored._field_value("tax_accountant_full_name"))
        self.assertEqual("12 đường Nhập Tay", restored._field_value("tax_notification_address_detail"))
        self.assertEqual("31/12", restored._field_value("tax_financial_year_end"))
        self.assertGreaterEqual(restored.tax_person_selectors["director"].findData("person:0"), 0)

    def test_beneficial_notice_defaults_are_independent_and_restore_in_old_cases(self):
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace
        self.assertIn("change_beneficial_selected", workspace.fields)
        self.assertEqual("Không có", workspace._field_value("beneficial_notice_a_status"))
        self.assertEqual("Không có", workspace._field_value("beneficial_notice_b_status"))
        workspace.fields["change_beneficial_selected"].setChecked(True)
        workspace.beneficial_notice_selectors["beneficial_notice_a_status"].setCurrentText("Gửi kèm")
        self.assertEqual("Không có", workspace._field_value("beneficial_notice_b_status"))
        saved = workspace.build_case_summary()
        self.window._open_case_workspace(saved)
        restored = self.window.current_workspace
        self.assertTrue(restored.fields["change_beneficial_selected"].isChecked())
        self.assertEqual("Gửi kèm", restored._field_value("beneficial_notice_a_status"))
        self.assertEqual("Không có", restored._field_value("beneficial_notice_b_status"))

        legacy = CaseSummary(
            "legacy-beneficial", "LEGACY", BUSINESS_AMENDMENT_CASE_TYPE, "REP", "08/10/2026",
            "Bản nháp", "", 1, "", form_values={"custom_old_field": "KEEP OLD"},
        )
        self.window._open_case_workspace(legacy)
        old_workspace = self.window.current_workspace
        self.assertFalse(old_workspace.fields["change_beneficial_selected"].isChecked())
        self.assertEqual("Không có", old_workspace._field_value("beneficial_notice_a_status"))
        self.assertEqual("Không có", old_workspace._field_value("beneficial_notice_b_status"))
        self.assertEqual(-1, old_workspace.tax_person_selectors["director"].findData("person:0"))
        self.assertEqual("KEEP OLD", old_workspace.build_case_summary().form_values["custom_old_field"])

    def test_completion_ticks_follow_meaningful_data_not_visibility_checkboxes(self):
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace

        workspace._set_field("registered_capital", "1.000.000.000")
        workspace.fields["change_capital_selected"].setChecked(True)
        workspace.fields["change_beneficial_selected"].setChecked(True)
        workspace._refresh_amendment_change_choices()
        self.assertTrue(workspace.amendment_choice_indicators["change_capital_selected"].isHidden())
        self.assertTrue(workspace.amendment_choice_indicators["change_beneficial_selected"].isHidden())

        workspace._set_field("new_capital", "2.000.000.000")
        workspace._set_field("beneficial_notice_b_status", "Gửi kèm")
        workspace.fields["change_capital_selected"].setChecked(False)
        workspace.fields["change_beneficial_selected"].setChecked(False)
        workspace._refresh_amendment_change_choices()
        self.assertFalse(workspace.amendment_choice_indicators["change_capital_selected"].isHidden())
        self.assertFalse(workspace.amendment_choice_indicators["change_beneficial_selected"].isHidden())

    def test_share_table_all_data_cells_editable_and_restore(self):
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace
        self.assertNotIn("change_shares_selected", workspace.fields)
        workspace.fields["change_capital_selected"].setChecked(True)
        self.assertTrue(workspace.amendment_change_forms["change_capital_selected"].isAncestorOf(workspace.amendment_share_table))
        table = workspace.amendment_share_table
        for row in range(5):
            for column in range(2, 5):
                self.assertFalse(table.cellWidget(row, column).isReadOnly())
        for key, value in {"new_share_par_value": "10000", "amendment_share_1_count": "80000", "amendment_share_1_amount": "800000000",
                           "amendment_share_1_ratio": "80,5", "amendment_share_2_count": "20000", "amendment_share_2_amount": "200000000",
                           "amendment_share_2_ratio": "19,5"}.items():
            workspace.fields[key].setText(value)
        self.assertEqual("800.000.000", workspace.fields["amendment_share_1_amount"].text())
        self.assertEqual(["100.000", "1.000.000.000", "100,0"], [table.item(5, column).text() for column in range(2, 5)])
        self.window._open_case_workspace(workspace.build_case_summary())
        restored = self.window.current_workspace
        self.assertEqual("80,5", restored.fields["amendment_share_1_ratio"].text())
        self.assertEqual("1.000.000.000", restored.amendment_share_table.item(5, 3).text())
        restored.fields["amendment_share_2_amount"].clear()
        self.assertEqual("800.000.000", restored.amendment_share_table.item(5, 3).text())

    def test_three_line_tables_main_selection_multiline_and_draft_restore(self):
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace
        workspace._set_fields_from_mapping(sample_line_values())
        self.assertEqual({"add": 3, "remove": 2, "detail": 1}, {kind: table.rowCount() for kind, table in workspace.amendment_line_tables.items()})
        workspace.fields["amendment_line_add_2_main"].setChecked(True)
        self.assertFalse(workspace.fields["amendment_line_detail_1_main"].isChecked())
        self.assertEqual("X", workspace.form_values()["amendment_line_add_2_main"])
        saved = workspace.build_case_summary()
        self.window._open_case_workspace(saved)
        restored = self.window.current_workspace
        self.assertEqual("Bỏ ngành 2\nGhi chú kiểm thử", restored.fields["amendment_line_remove_2_note"].toPlainText())
        self.assertTrue(restored.fields["amendment_line_add_2_main"].isChecked())
        self.assertEqual("3", restored.amendment_line_tables["add"].number_labels[2].text())
        restored.fields["amendment_line_add_1_name"].clear()
        restored.fields["amendment_line_add_1_detail"].clear()
        self.assertEqual("1", restored.amendment_line_tables["add"].number_labels[1].text())
        restored.fields["change_business_lines_selected"].setChecked(False)
        restored.fields["change_business_lines_selected"].setChecked(True)
        self.assertEqual("7490", restored.fields["amendment_line_remove_2_code"].text())

    def test_reused_industry_lookup_and_row_builder_keep_tables_independent(self):
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace
        table = workspace.amendment_line_tables["add"]
        self.assertIs(table._add_business_line_row.__func__, BusinessRegistrationWorkspace._add_business_line_row)
        self.assertEqual(0, table.rowCount())
        self.assertTrue(workspace.industry_catalog.is_available)
        industry = next(row for row in workspace.industry_catalog.display_rows if workspace._industry_row_code(row))
        code = workspace._industry_row_code(industry)
        workspace.industry_search_input.setText(code)
        self.assertGreater(workspace.industry_results_table.rowCount(), 0)
        workspace.industry_results_table.selectRow(0)
        selected = workspace._selected_industry_row()
        selected_code = workspace._industry_row_code(selected)
        workspace._add_selected_industry_row()
        row = table.business_line_rows[0]
        self.assertEqual("BusinessLineRow", row.cells[0].objectName())
        self.assertIn("border: 2px solid #557fae", row.cells[0].styleSheet())
        self.assertEqual(156, row.cells[0].height())
        self.assertEqual(selected_code, workspace._field_value("amendment_line_add_1_code"))
        self.assertEqual(selected.name.strip(), workspace._field_value("amendment_line_add_1_name"))
        self.assertTrue(workspace.fields["amendment_line_add_1_main"].isChecked())
        with patch("mingo_assistant.ui.views.business_amendment_workspace.QMessageBox.warning") as warning:
            workspace._add_selected_industry_row()
            warning.assert_called_once()
        workspace.amendment_industry_target.setCurrentIndex(1)
        workspace._add_selected_industry_row()
        self.assertEqual(selected_code, workspace._field_value("amendment_line_remove_1_code"))
        self.assertEqual("", workspace._field_value("amendment_line_detail_1_code"))
        workspace.fields["amendment_line_add_1_detail"].setPlainText("Chi tiết: nội dung kiểm thử\nDòng tiếp theo")
        saved = workspace.build_case_summary()
        self.window._open_case_workspace(saved)
        restored = self.window.current_workspace
        self.assertEqual(selected.name.strip(), restored.fields["amendment_line_add_1_name"].text())
        self.assertEqual("Chi tiết: nội dung kiểm thử\nDòng tiếp theo", restored.fields["amendment_line_add_1_detail"].toPlainText())

    def test_only_remove_industry_uses_legacy_catalog(self):
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace

        workspace._open_amendment_industry_lookup("add")
        self.assertIs(workspace._industry_lookup_catalog(), self.window.industry_catalog)
        self.assertIn("36/2025/QĐ-TTg", workspace.industry_lookup_source.text())

        workspace._open_amendment_industry_lookup("remove")
        self.assertIs(workspace._industry_lookup_catalog(), self.window.legacy_industry_catalog)
        self.assertEqual(464, workspace.industry_results_table.rowCount())
        self.assertIn("27/2018/QĐ-TTg", workspace.industry_lookup_source.text())
        self.assertIn("ngành cũ", workspace.industry_search_input.placeholderText())

        workspace._open_amendment_industry_lookup("detail")
        self.assertIs(workspace._industry_lookup_catalog(), self.window.industry_catalog)
        self.assertEqual(495, workspace.industry_results_table.rowCount())
        self.assertIn("36/2025/QĐ-TTg", workspace.industry_lookup_source.text())

    def test_industry_picker_mouse_selection_adds_to_visible_tab(self):
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace
        workspace.fields["change_business_lines_selected"].setChecked(True)
        workspace._select_form_section(3)
        self.window.show()
        self.app.processEvents()
        industry = next(row for row in workspace.industry_catalog.display_rows if workspace._industry_row_code(row))
        code = workspace._industry_row_code(industry)
        for kind in ("add", "remove", "detail"):
            workspace._open_amendment_industry_lookup(kind)
            workspace.industry_search_input.setText(code)
            self.app.processEvents()
            table = workspace.industry_results_table
            item = table.item(min(1, table.rowCount() - 1), 1)
            table.scrollToItem(item)
            QTest.mouseClick(table.viewport(), Qt.LeftButton, pos=table.visualItemRect(item).center())
            self.app.processEvents()
            selected = workspace._selected_industry_row()
            self.assertIsNotNone(selected)
            expected = workspace._industry_row_code(selected)
            QTest.mouseClick(workspace.amendment_industry_add_button, Qt.LeftButton)
            self.app.processEvents()
            self.assertFalse(workspace.amendment_industry_dialog.isVisible())
            self.assertEqual(expected, workspace._field_value(f"amendment_line_{kind}_1_code"))
            self.assertEqual(selected.name.strip(), workspace._field_value(f"amendment_line_{kind}_1_name"))
            self.assertEqual(kind, workspace.amendment_industry_target.currentData())
        # Searching for no match must clear the current selection.
        workspace.industry_search_input.setText("no-such-industry-xyz-123")
        self.assertIsNone(workspace._selected_industry_row())

    def test_legacy_industry_workspace_keeps_its_own_fields_and_actions(self):
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace
        legacy = BusinessRegistrationWorkspace(lambda: None, lambda case: None, bundle_root=PROJECT_ROOT, default_export_root=Path(self.temp.name))
        try:
            old_row = legacy.business_line_rows[0]
            old_row.name_field.setText("Ngành cũ độc lập")
            old_row.code_field.setText("6201")
            old_row.main_checkbox.setChecked(True)
            workspace._append_amendment_line_row("add")
            workspace._set_field("amendment_line_add_1_name", "Ngành mới\nChi tiết: độc lập")
            workspace._set_field("amendment_line_add_1_code", "6202")
            workspace.fields["amendment_line_add_1_main"].setChecked(True)
            workspace._delete_amendment_line_row("add", 0)
            self.assertEqual("Ngành cũ độc lập", old_row.name_field.text())
            self.assertEqual("6201", old_row.code_field.text())
            self.assertTrue(old_row.main_checkbox.isChecked())
            self.assertNotIn("business_line_1_name", workspace.fields)
            self.assertNotIn("amendment_line_add_1_name", legacy.fields)
        finally:
            legacy.close()
            legacy.deleteLater()

    def test_add_delete_line_rows_keep_values_and_restore_counts(self):
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace
        workspace._set_fields_from_mapping(sample_line_values())
        for kind in ("add", "remove", "detail"):
            table = workspace.amendment_line_tables[kind]
            count = table.rowCount()
            workspace._append_amendment_line_row(kind)
            workspace._set_field(f"amendment_line_{kind}_{count + 1}_name", "Dòng thêm\nChi tiết: mới")
            workspace._set_field(f"amendment_line_{kind}_{count + 1}_code", "6201")
            workspace._delete_amendment_line_row(kind, 0)
            self.assertEqual(count, table.rowCount())
            self.assertEqual("Dòng thêm\nChi tiết: mới", workspace._field_value(f"amendment_line_{kind}_{count}_name"))
            self.assertNotIn(f"amendment_line_{kind}_{count + 1}_name", workspace.form_values())
        workspace.fields["amendment_line_detail_1_main"].setChecked(True)
        saved = workspace.build_case_summary()
        self.window._open_case_workspace(saved)
        restored = self.window.current_workspace
        self.assertEqual("Dòng thêm\nChi tiết: mới", restored._field_value("amendment_line_add_3_name"))
        self.assertTrue(restored.fields["amendment_line_detail_1_main"].isChecked())
        for _ in range(4):
            restored._append_amendment_line_row("add")
        saved = restored.build_case_summary()
        self.window._open_case_workspace(saved)
        self.assertEqual(7, self.window.current_workspace.amendment_line_tables["add"].rowCount())
        self.window.current_workspace._delete_amendment_line_row("detail", 0)
        self.assertEqual(0, self.window.current_workspace.amendment_line_tables["detail"].rowCount())
        self.assertNotIn("amendment_line_detail_1_name", self.window.current_workspace.fields)

    def test_legacy_share_draft_merges_without_mutating_saved_case(self):
        case = CaseSummary("old-shares", "COMPANY TEST", BUSINESS_AMENDMENT_CASE_TYPE, "REP", "08/10/2026",
                           "Bản nháp", "", 1, "", form_values={"amendment_schema_version": "2", "change_shares_selected": "X",
                           "change_capital_selected": "", "new_share_par_value": "10000", "amendment_share_1_count": "100",
                           "amendment_share_1_amount": "1000000", "amendment_share_1_ratio": "100"})
        original = deepcopy(case.to_dict())
        self.window._open_case_workspace(case)
        workspace = self.window.current_workspace
        self.assertTrue(workspace.fields["change_capital_selected"].isChecked())
        self.assertNotIn("change_shares_selected", workspace.amendment_choice_cards)
        self.assertEqual("1.000.000", workspace.fields["amendment_share_1_amount"].text())
        self.assertEqual(original, case.to_dict())
        saved = workspace.build_case_summary()
        self.assertNotIn("change_shares_selected", saved.form_values)
        self.assertEqual(4, saved.form_schema_version)
        self.assertEqual("4", saved.form_values["amendment_schema_version"])
        workspace.fields["change_capital_selected"].setChecked(False)
        self.window._open_case_workspace(workspace.build_case_summary())
        restored = self.window.current_workspace
        self.assertTrue(restored.fields["change_capital_selected"].isChecked())
        self.assertEqual("100", restored.fields["amendment_share_1_count"].text())

    def test_both_create_buttons_open_workspace_without_modal(self) -> None:
        buttons = self.window.business_amendment_page.findChildren(QPushButton)
        for label in ("+ Tạo hồ sơ mới", "Tạo hồ sơ"):
            with self.subTest(label=label):
                next(button for button in buttons if button.text() == label).click()
                workspace = self.window.current_workspace
                self.assertIsInstance(workspace, BusinessAmendmentWorkspace)
                self.assertEqual([title for title, _ in AMENDMENT_FIELD_GROUPS], list(workspace.form_sections))
                self.assertNotIn("authorized_person_full_name", workspace.fields)
                self.assertTrue(workspace._validation_issues(workspace.form_values()))
                workspace.on_back()
                self.assertIs(self.window.stack.currentWidget(), self.window.business_amendment_page)

    def test_draft_reopens_in_section_two_with_provisional_inputs(self) -> None:
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace
        workspace.fields["parent_entity_name"].setText("COMPANY TEST")
        workspace.fields["change_address_selected"].setChecked(True)
        workspace.fields["new_company_phone"].setText("0900000000")
        with patch("mingo_assistant.ui.views.business_registration_workspace.QMessageBox.information"):
            workspace._save_draft()
        case = self.window.case_use_cases.get(workspace.case_id)
        self.assertEqual(BUSINESS_AMENDMENT_CASE_TYPE, case.case_type)
        self.assertNotIn(case, self.window._filtered_cases())
        self.assertFalse(self.window._is_dependent_case(case))
        self.assertEqual("1 hồ sơ", self.window.amendment_cases_count_label.text())
        self.window._open_case_workspace(case)
        restored = self.window.current_workspace
        self.assertIsInstance(restored, BusinessAmendmentWorkspace)
        self.assertEqual("COMPANY TEST", restored.fields["parent_entity_name"].text())
        self.assertTrue(restored.fields["change_address_selected"].isChecked())
        self.assertEqual("0900000000", restored.fields["new_company_phone"].text())

    def test_filled_form_exports_via_worker_and_documents_return_to_section_two(self) -> None:
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace
        workspace._set_fields_from_mapping(sample_values())
        case_id = workspace.case_id
        with patch("mingo_assistant.ui.views.business_registration_workspace.QMessageBox.information"), \
                patch("mingo_assistant.ui.views.business_registration_workspace.QMessageBox.critical") as critical, \
                patch("mingo_assistant.ui.views.business_registration_workspace.QMessageBox.warning") as warning:
            workspace._export_documents()
            deadline = time.monotonic() + 10
            while self.window.current_documents_view is None and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(0.01)
            critical.assert_not_called()
            warning.assert_not_called()
        self.assertIsNotNone(self.window.current_documents_view)
        case = self.window.case_use_cases.get(case_id)
        self.assertEqual([BusinessAmendmentTemplateGenerator.TEMPLATE_NAME], case.generated_documents)
        self.assertEqual("Đã nhập thông tin", case.condition)
        output_dir = Path(case.export_versions[0]["export_dir"])
        self.assertNotEqual(
            (TEMPLATE_DIR / case.generated_documents[0]).read_bytes(),
            (output_dir / case.generated_documents[0]).read_bytes(),
        )
        self.window.current_documents_view.on_back()
        self.assertIs(self.window.stack.currentWidget(), self.window.business_amendment_page)

    def test_cases_are_independent_and_legacy_hidden_values_are_preserved(self):
        legacy = CaseSummary("legacy-amendment", "LEGACY", BUSINESS_AMENDMENT_CASE_TYPE, "REP", "08/10/2026",
                             "Bản nháp", "", 1, "", form_values={"authorized_person_full_name": "KEEP HIDDEN",
                                                                    "custom_old_field": "KEEP OLD"})
        original = deepcopy(legacy.to_dict())
        first = BusinessAmendmentWorkspace(lambda: None, lambda case: None, case=legacy,
                                           bundle_root=PROJECT_ROOT, default_export_root=Path(self.temp.name))
        second = BusinessAmendmentWorkspace(lambda: None, lambda case: None, bundle_root=PROJECT_ROOT,
                                            default_export_root=Path(self.temp.name))
        first._set_fields_from_mapping(sample_values())
        second._set_fields_from_mapping(sample_values())
        first.fields["new_company_name"].setText("ONLY FIRST")
        self.assertEqual("CÔNG TY TNHH TÊN MỚI", second.fields["new_company_name"].text())
        self.assertNotEqual(first._case_export_folder_name(first.form_values()), second._case_export_folder_name(second.form_values()))
        saved = first.build_case_summary()
        self.assertEqual("KEEP HIDDEN", saved.form_values["authorized_person_full_name"])
        self.assertEqual("KEEP OLD", saved.form_values["custom_old_field"])
        self.assertEqual(original, legacy.to_dict())
        first.close()
        second.close()

    def test_pdf_confirmation_and_representative_selection_are_explicit(self):
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace
        self.assertEqual({"organization_owner_name", "organization_owner_registration_number"},
                         set(workspace.organization_card_fields))
        workspace.fields["registered_capital"].setText("9000000000")
        data = {"organization_owner_name": "PDF COMPANY", "organization_owner_registration_number": "0319291466",
                "organization_owner_address_detail": "ADDRESS", "legal_representative_full_name": "PDF REPRESENTATIVE",
                "organization_capital": "1000000000", "amendment_recognition_confirmed": ""}
        workspace._apply_organization_values_to_current_person(data, "PDF", "ocr")
        workspace._update_organization_result_fields(data)
        self.assertEqual("", workspace.fields["parent_entity_name"].text())
        with patch("mingo_assistant.ui.views.business_amendment_workspace.QMessageBox.warning") as warning:
            workspace._save_organization_profile()
            warning.assert_called_once()
        workspace.organization_review_checkbox.setChecked(True)
        with patch("mingo_assistant.ui.views.business_amendment_workspace.QMessageBox.information"):
            workspace._save_organization_profile()
        self.assertEqual("", workspace.fields["parent_entity_name"].text())
        selector = workspace.update_organization_selector
        selector.setCurrentIndex(selector.findData("profile:0"))
        self.assertEqual("PDF COMPANY", workspace.fields["parent_entity_name"].text())
        self.assertEqual("9.000.000.000", workspace.fields["registered_capital"].text())
        self.assertEqual("", workspace.fields["legal_representative_full_name"].text())
        self.assertNotIn("organization_owner_address_detail", workspace._selected_update_organization)
        self.assertNotIn("legal_representative_full_name", workspace._selected_update_organization)
        self.assertNotIn("Điền người đại diện từ PDF doanh nghiệp đã chọn",
                         [button.text() for button in workspace.findChildren(QPushButton)])
        workspace.fields["legal_representative_full_name"].setText("MANUAL REPRESENTATIVE")
        saved = workspace.build_case_summary()
        self.window._open_case_workspace(saved)
        restored = self.window.current_workspace
        self.assertEqual("PDF COMPANY", restored.fields["parent_entity_name"].text())
        self.assertEqual("MANUAL REPRESENTATIVE", restored.fields["legal_representative_full_name"].text())
        self.assertEqual("1", restored._selected_update_organization["amendment_recognition_confirmed"])
        self.assertEqual("", restored._representative_company_code)
        restored.fields["legal_representative_full_name"].setText("MANUALLY REVIEWED REPRESENTATIVE")
        self.assertEqual("", restored._representative_company_code)

    def test_switching_pdf_clears_absent_values_and_detects_stale_representative(self):
        self.window._open_business_amendment_modal()
        workspace = self.window.current_workspace
        workspace._selected_update_organization = {
            "organization_owner_registration_number": "0319291466",
            "legal_representative_full_name": "OLD PERSON", "legal_representative_id_number": "012345678901",
        }
        workspace._fill_representative_from_pdf()
        workspace._set_fields_from_mapping({"parent_entity_registration_number": "3702806484", "company_email": ""})
        self.assertIn("Người đại diện lấy từ PDF của doanh nghiệp khác; cần chọn lại",
                      workspace._missing_required_fields(workspace.form_values()))
        workspace._selected_update_organization = {
            "organization_owner_registration_number": "3702806484", "legal_representative_full_name": "NEW PERSON",
        }
        workspace._fill_representative_from_pdf()
        self.assertEqual("", workspace.fields["legal_representative_id_number"].text())
        self.assertEqual("3702806484", workspace._representative_company_code)

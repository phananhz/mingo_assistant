"""Fill the verified highlighted slots in the no-revenue tax commitment."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

from mingo_assistant.services.documents.generation_result import GeneratedDocument, GenerationResult
from mingo_assistant.services.registration_offices import signing_place_for_province


class TaxRevenueCommitmentGenerator:
    MISSING_VALUES_MESSAGE = "Chưa đủ thông tin để điền biểu mẫu cam kết chưa phát sinh doanh thu."
    FILENAME = "Cam ket_chua phat sinh doanh thu, nghia vu khac.docx"
    TEMPLATE_SHA256 = "7205901f9dc91ae747be71a2225bb46b44cfcb06b2c5abfe02a8811119b05368"
    REQUIRED_KEYS = (
        "tax_company_name",
        "tax_signing_place",
        "tax_receiving_authority",
        "tax_registration_number",
        "tax_issue_place",
        "tax_issue_date",
        "tax_address",
        "tax_taxpayer",
        "tax_business_industry",
    )
    NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

    def __init__(self, template_dir, export_root):
        self.template_dir = Path(template_dir)
        self.export_root = Path(export_root)

    def validate_templates(self, values):
        path = self.template_dir / self.FILENAME
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != self.TEMPLATE_SHA256:
            return {
                self.FILENAME: [
                    "Mẫu Word đã thay đổi hoặc bị thiếu. Cần kiểm tra lại mapping trước khi xuất."
                ]
            }
        return {}

    @staticmethod
    def _split_company_heading(value: str) -> tuple[str, str]:
        value = " ".join(value.split())
        folded = value.casefold()
        for legal_form in (
            "công ty trách nhiệm hữu hạn",
            "công ty tnhh",
            "công ty cổ phần",
            "doanh nghiệp tư nhân",
            "công ty hợp danh",
        ):
            if folded.startswith(legal_form + " "):
                cut = len(legal_form)
                return value[:cut].strip(), value[cut:].strip()
        words = value.split()
        if len(words) < 2:
            return value, ""
        split_at = min(
            range(1, len(words)),
            key=lambda index: abs(len(" ".join(words[:index])) - len(" ".join(words[index:]))),
        )
        return " ".join(words[:split_at]), " ".join(words[split_at:])

    @staticmethod
    def _split_signing_place(value: str) -> tuple[str, str]:
        value = " ".join(value.split())
        for prefix in ("Thành phố ", "Tỉnh "):
            if value.casefold().startswith(prefix.casefold()):
                return value[:len(prefix)], value[len(prefix):]
        return value, ""

    def _replacement_values(self, values: dict[str, str]) -> tuple[str, ...]:
        company_line_1, company_line_2 = self._split_company_heading(values["tax_company_name"])
        place_part_1, place_part_2 = self._split_signing_place(values["tax_signing_place"])
        return (
            company_line_1,
            company_line_2,
            place_part_1,
            place_part_2,
            values["tax_receiving_authority"],
            values["tax_company_name"],
            values["tax_registration_number"],
            values["tax_registration_number"],
            values["tax_issue_place"],
            values["tax_issue_date"],
            values["tax_address"],
            values["tax_taxpayer"],
            values["tax_business_industry"],
            values["tax_company_name"],
            values["tax_taxpayer"],
        )

    def _replace_run_text(self, run, value: str) -> None:
        texts = run.xpath("w:t", namespaces=self.NS)
        if not texts:
            raise ValueError("Vùng nhập không có nội dung văn bản.")
        normalized = str(value).replace("\r\n", "\n").replace("\r", "\n")
        lines = normalized.split("\n")
        texts[0].text = lines[0]
        texts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        for text in texts[1:]:
            text.getparent().remove(text)
        cursor = texts[0]
        for line in lines[1:]:
            line_break = etree.Element(self.W + "br")
            next_text = etree.Element(self.W + "t")
            next_text.text = line
            next_text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            cursor.addnext(line_break)
            line_break.addnext(next_text)
            cursor = next_text

    def _highlighted_runs(self, paragraph):
        return paragraph.xpath(
            ".//w:r[w:rPr/w:highlight[@w:val='green']]", namespaces=self.NS
        )

    def _replace_group(self, runs, value: str) -> None:
        if not runs:
            raise ValueError("Vùng nhập của mẫu Word không đúng mapping.")
        self._replace_run_text(runs[0], value)
        for run in runs[1:]:
            self._replace_run_text(run, "")

    def _apply_values(self, xml, values: dict[str, str]) -> None:
        replacements = self._replacement_values(values)
        runs = xml.xpath("//w:r[w:rPr/w:highlight[@w:val='green']]", namespaces=self.NS)
        if len(runs) != len(replacements):
            raise ValueError("Cấu trúc vùng nhập của mẫu Word không đúng mapping.")
        for run, value in zip(runs, replacements):
            self._replace_run_text(run, value)

    def generate(self, values, case_name, output_dir=None):
        values = dict(values)
        if values.get("tax_signing_place"):
            values["tax_signing_place"] = signing_place_for_province(
                values["tax_signing_place"]
            )
        issues = self.validate_templates(values)
        if issues:
            raise ValueError(next(iter(issues.values()))[0])
        if any(not str(values.get(key, "")).strip() for key in self.REQUIRED_KEYS):
            raise ValueError(self.MISSING_VALUES_MESSAGE)
        output_dir = Path(output_dir or self.export_root)
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / self.FILENAME
        source = self.template_dir / self.FILENAME
        if output.resolve() == source.resolve():
            raise ValueError("Không được ghi đè mẫu Word gốc.")
        with ZipFile(source) as original:
            xml = etree.fromstring(original.read("word/document.xml"))
            self._apply_values(xml, values)
            with ZipFile(output, "w") as generated:
                for member in original.infolist():
                    data = (
                        etree.tostring(xml, xml_declaration=True, encoding="UTF-8", standalone=True)
                        if member.filename == "word/document.xml"
                        else original.read(member.filename)
                    )
                    generated.writestr(member, data)
        return GenerationResult(output_dir, [GeneratedDocument(self.FILENAME, output)], [], {})

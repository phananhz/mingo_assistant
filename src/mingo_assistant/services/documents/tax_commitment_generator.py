"""Fill only the nine verified highlighted runs in the supplied tax form."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile
from lxml import etree

from mingo_assistant.services.documents.generation_result import GeneratedDocument, GenerationResult


class TaxCommitmentGenerator:
    FILENAME = "Cam ket chung khi cham dut MST.docx"
    TEMPLATE_SHA256 = "630d76256b65128d4b032173627244494bb401ceba47b29cdef3ab24b650846b"
    KEYS = (
        "tax_company_name", "tax_receiving_authority", "tax_company_name", "tax_registration_number",
        "tax_issue_date", "tax_issue_place", "tax_address", "tax_receiving_authority", "tax_taxpayer",
    )
    REQUIRED_KEYS = tuple(dict.fromkeys(KEYS))
    NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

    def __init__(self, template_dir, export_root):
        self.template_dir = Path(template_dir)
        self.export_root = Path(export_root)

    def validate_templates(self, values):
        path = self.template_dir / self.FILENAME
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != self.TEMPLATE_SHA256:
            return {self.FILENAME: ["Mẫu Word đã thay đổi hoặc bị thiếu. Cần kiểm tra lại mapping trước khi xuất."]}
        return {}

    def generate(self, values, case_name, output_dir=None):
        issues = self.validate_templates(values)
        if issues:
            raise ValueError(next(iter(issues.values()))[0])
        if any(not str(values.get(key, "")).strip() for key in self.REQUIRED_KEYS):
            raise ValueError("Chưa đủ thông tin để điền biểu mẫu cam kết.")
        output_dir = Path(output_dir or self.export_root)
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / self.FILENAME
        source = self.template_dir / self.FILENAME
        if output.resolve() == source.resolve():
            raise ValueError("Không được ghi đè mẫu Word gốc.")
        with ZipFile(source) as original:
            xml = etree.fromstring(original.read("word/document.xml"))
            runs = xml.xpath("//w:r[w:rPr/w:highlight[@w:val='green']]", namespaces=self.NS)
            if len(runs) != len(self.KEYS):
                raise ValueError("Cấu trúc vùng nhập của mẫu Word không đúng mapping.")
            for run, key in zip(runs, self.KEYS):
                texts = run.xpath("w:t", namespaces=self.NS)
                if not texts:
                    raise ValueError("Vùng nhập không có nội dung văn bản.")
                texts[0].text = str(values[key]).strip()
                texts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                for text in texts[1:]:
                    text.text = ""
            with ZipFile(output, "w") as generated:
                for member in original.infolist():
                    data = etree.tostring(xml, xml_declaration=True, encoding="UTF-8", standalone=True) if member.filename == "word/document.xml" else original.read(member.filename)
                    generated.writestr(member, data)
        return GenerationResult(output_dir, [GeneratedDocument(self.FILENAME, output)], [], {})

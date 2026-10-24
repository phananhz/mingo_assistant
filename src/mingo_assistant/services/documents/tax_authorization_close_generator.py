"""Fill the yellow/green slots of the converted tax-closure authorization."""
from mingo_assistant.services.documents.tax_revenue_commitment_generator import (
    TaxRevenueCommitmentGenerator,
)


class TaxAuthorizationCloseGenerator(TaxRevenueCommitmentGenerator):
    FILENAME = "Giay uy quyen giai the (Thue).docx"
    TEMPLATE_SHA256 = "3c19e0036cf35d9fd0b35c905225e979f32296e971726abeda4b70f0d12f87a1"
    MISSING_VALUES_MESSAGE = "Chưa đủ thông tin để điền giấy ủy quyền giải thể (thuế)."
    KEYS = (
        "tax_company_name", "tax_registration_number", "tax_address", "tax_taxpayer",
        "authorized_person_full_name", "authorized_person_id_number",
        "authorized_person_issue_date", "authorized_person_issue_place",
        "authorized_person_phone", "authorized_person_email",
        "tax_company_name", "tax_receiving_authority", "tax_signing_place", "tax_taxpayer",
    )
    REQUIRED_KEYS = tuple(key for key in dict.fromkeys(KEYS) if key != "authorized_person_email")

    def _apply_values(self, xml, values: dict[str, str]) -> None:
        runs = xml.xpath(
            "//w:r[w:rPr/w:highlight[@w:val='yellow' or @w:val='green']]",
            namespaces=self.NS,
        )
        colors = [run.xpath("w:rPr/w:highlight/@w:val", namespaces=self.NS)[0] for run in runs]
        if colors != ["yellow"] * 4 + ["green"] * 6 + ["yellow"] * 4:
            raise ValueError("Cấu trúc vùng nhập của mẫu Word không đúng mapping.")
        for run, key in zip(runs, self.KEYS):
            self._replace_run_text(run, values.get(key, ""))
        # The legacy template pads this row with 15 spaces. Reclaim that
        # space for a long issuing authority without reducing the font size.
        paragraph = runs[6].getparent()
        if paragraph is not runs[7].getparent():
            raise ValueError("Ngày cấp và nơi cấp không cùng dòng trong mẫu Word.")
        before_date = True
        for run in paragraph.findall(self.W + "r"):
            if run is runs[6]:
                before_date = False
            if run is runs[7]:
                break
            for text in run.findall(self.W + "t"):
                if text.text and text.text.isspace():
                    text.text = " " if before_date else "   "

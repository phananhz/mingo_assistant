"""Fill the highlighted slots in the no-ecommerce-activity tax commitment."""
from mingo_assistant.services.documents.tax_revenue_commitment_generator import (
    TaxRevenueCommitmentGenerator,
)


class TaxEcommerceCommitmentGenerator(TaxRevenueCommitmentGenerator):
    FILENAME = "Cam ket_khong co hoat dong TMĐT.docx"
    TEMPLATE_SHA256 = "6b9a0999d860f54a4292ccb999cbacdcf25c7e4f1854bca1b1c1a512afb19f82"

    def _apply_values(self, xml, values: dict[str, str]) -> None:
        all_runs = xml.xpath(
            "//w:r[w:rPr/w:highlight[@w:val='green']]", namespaces=self.NS
        )
        paragraphs = xml.xpath(
            "//w:p[.//w:r[w:rPr/w:highlight[@w:val='green']]]", namespaces=self.NS
        )
        if len(all_runs) != 50 or len(paragraphs) != 12:
            raise ValueError("Cấu trúc vùng nhập của mẫu Word không đúng mapping.")

        company_line_1, company_line_2 = self._split_company_heading(
            values["tax_company_name"]
        )
        simple_values = (
            company_line_1,
            company_line_2,
            values["tax_signing_place"],
            values["tax_receiving_authority"],
            values["tax_company_name"],
            values["tax_registration_number"],
        )
        for paragraph, value in zip(paragraphs[:6], simple_values):
            self._replace_group(self._highlighted_runs(paragraph), value)

        certificate_runs = self._highlighted_runs(paragraphs[6])
        if len(certificate_runs) != 5:
            raise ValueError("Dòng giấy chứng nhận của mẫu Word không đúng mapping.")
        self._replace_group(certificate_runs[:1], values["tax_registration_number"])
        self._replace_group(certificate_runs[1:4], values["tax_issue_place"])
        self._replace_group(certificate_runs[4:], values["tax_issue_date"])

        remaining_values = (
            values["tax_address"],
            values["tax_taxpayer"],
            values["tax_business_industry"],
            values["tax_company_name"],
            values["tax_taxpayer"],
        )
        for paragraph, value in zip(paragraphs[7:], remaining_values):
            self._replace_group(self._highlighted_runs(paragraph), value)

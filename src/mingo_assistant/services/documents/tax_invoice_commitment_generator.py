"""Fill the highlighted slots in the no-invoice-issuance tax commitment."""
from mingo_assistant.services.documents.tax_revenue_commitment_generator import (
    TaxRevenueCommitmentGenerator,
)


class TaxInvoiceCommitmentGenerator(TaxRevenueCommitmentGenerator):
    FILENAME = "Cam ket_khong phat hanh hoa don.docx"
    TEMPLATE_SHA256 = "467a58bd7d6b5752c6e77429212035a10f3bbbed7baf939a4bf4abaef4d84565"
    REQUIRED_KEYS = (
        "tax_company_name",
        "tax_signing_place",
        "tax_receiving_authority",
        "tax_registration_number",
        "tax_issue_place",
        "tax_issue_date",
        "tax_address",
        "tax_taxpayer",
        "tax_invoice_notice_commitment",
        "tax_einvoice_registration_commitment",
    )

    def _apply_values(self, xml, values: dict[str, str]) -> None:
        runs = xml.xpath(
            "//w:r[w:rPr/w:highlight[@w:val='green']]", namespaces=self.NS
        )
        paragraphs = xml.xpath(
            "//w:p[.//w:r[w:rPr/w:highlight[@w:val='green']]]", namespaces=self.NS
        )
        if len(runs) != 12 or len(paragraphs) != 11:
            raise ValueError("Cấu trúc vùng nhập của mẫu Word không đúng mapping.")

        for paragraph, value in zip(
            paragraphs[:5],
            (
                values["tax_company_name"],
                values["tax_signing_place"],
                values["tax_receiving_authority"],
                values["tax_company_name"],
                values["tax_registration_number"],
            ),
        ):
            self._replace_group(self._highlighted_runs(paragraph), value)

        certificate_runs = self._highlighted_runs(paragraphs[5])
        if len(certificate_runs) != 2:
            raise ValueError("Dòng cấp ngày/nơi cấp của mẫu Word không đúng mapping.")
        self._replace_group(certificate_runs[:1], values["tax_issue_date"])
        self._replace_group(certificate_runs[1:], values["tax_issue_place"])

        self._replace_group(
            self._highlighted_runs(paragraphs[6]), values["tax_address"]
        )
        self._replace_group(
            self._highlighted_runs(paragraphs[7]), values["tax_receiving_authority"]
        )
        self._replace_group(
            self._highlighted_runs(paragraphs[8]), values["tax_invoice_notice_commitment"]
        )
        self._replace_group(
            self._highlighted_runs(paragraphs[9]), values["tax_einvoice_registration_commitment"]
        )
        self._replace_group(
            self._highlighted_runs(paragraphs[10]), values["tax_taxpayer"]
        )

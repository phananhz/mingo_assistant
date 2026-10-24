"""Fill the highlighted text slots of Form 24 while preserving its drawing."""
from mingo_assistant.services.documents.tax_revenue_commitment_generator import (
    TaxRevenueCommitmentGenerator,
)


class TaxTerminationGenerator(TaxRevenueCommitmentGenerator):
    FILENAME = "MS 24_Van ban cham dut MST.docx"
    TEMPLATE_SHA256 = "7e47113097b009941835cd610ba95f0533f186c68e0d7446b304b3ec277c4aa0"
    MISSING_VALUES_MESSAGE = "Chưa đủ thông tin để điền văn bản chấm dứt hiệu lực mã số thuế."
    REQUIRED_KEYS = (
        "tax_company_name", "tax_signing_place", "tax_receiving_authority",
        "tax_registration_number", "tax_address", "tax_termination_reason",
        "tax_attached_documents", "tax_taxpayer",
    )

    def _apply_values(self, xml, values: dict[str, str]) -> None:
        # One highlighted run contains an anchored line, not a text field.
        # Leave that entire run intact, including its drawing/fallback.
        runs = xml.xpath(
            "//w:r[w:rPr/w:highlight[@w:val='green'] and w:t]", namespaces=self.NS
        )
        heading = self._split_company_heading(values["tax_company_name"])
        replacements = (
            *heading, values["tax_signing_place"], values["tax_receiving_authority"],
            values["tax_company_name"], values["tax_registration_number"],
            values["tax_address"], values["tax_termination_reason"],
            values["tax_attached_documents"], values["tax_taxpayer"],
        )
        if len(runs) != len(replacements):
            raise ValueError("Cấu trúc vùng nhập của mẫu Word không đúng mapping.")
        for run, value in zip(runs, replacements):
            self._replace_run_text(run, value)

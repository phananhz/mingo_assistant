"""Fill only the five highlighted fields in the tax refund refusal form."""
from mingo_assistant.services.documents.tax_revenue_commitment_generator import (
    TaxRevenueCommitmentGenerator,
)


class TaxRefundRefusalGenerator(TaxRevenueCommitmentGenerator):
    FILENAME = "Cong van_tu choi hoan tien_MS01.ĐNKHT TT 89.2026.docx"
    TEMPLATE_SHA256 = "f4fadc04d9348ad89bd3e3d1e1790c5a1ab13fe2a8a3fb7a2f3d150a70e34e29"
    REQUIRED_KEYS = (
        "tax_receiving_authority",
        "tax_company_name",
        "tax_registration_number",
        "tax_taxpayer",
    )
    MISSING_VALUES_MESSAGE = "Chưa đủ thông tin để điền công văn từ chối hoàn tiền."

    def _apply_values(self, xml, values: dict[str, str]) -> None:
        runs = xml.xpath(
            "//w:r[w:rPr/w:highlight[@w:val='green']]", namespaces=self.NS
        )
        if len(runs) != 5:
            raise ValueError("Cấu trúc vùng nhập của mẫu Word không đúng mapping.")
        replacements = (
            *(values[key] for key in self.REQUIRED_KEYS),
            values.get("tax_taxpayer_position", ""),
        )
        for run, value in zip(runs, replacements):
            self._replace_run_text(run, value)

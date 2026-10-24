"""Fill the highlighted slots in the no-customs-tax-debt confirmation request."""
from mingo_assistant.services.documents.tax_revenue_commitment_generator import (
    TaxRevenueCommitmentGenerator,
)


class TaxCustomsConfirmationGenerator(TaxRevenueCommitmentGenerator):
    FILENAME = "VB xac nhan_khong no thue Hai quan.docx"
    TEMPLATE_SHA256 = "6ad8b015f2115cdfa592f5e95cac5a678009551ab9cc0449761f8e7213ae1a6e"
    MISSING_VALUES_MESSAGE = "Chưa đủ thông tin để điền văn bản xác nhận không nợ thuế hải quan."
    REQUIRED_KEYS = (
        "tax_company_name", "tax_signing_place", "tax_receiving_authority",
        "tax_registration_number", "tax_address", "authorized_person_full_name",
        "authorized_person_phone", "tax_taxpayer",
    )

    def _replacement_values(self, values: dict[str, str]) -> tuple[str, ...]:
        return (
            *self._split_company_heading(values["tax_company_name"]),
            values["tax_signing_place"], values["tax_receiving_authority"],
            values["tax_company_name"], values["tax_registration_number"],
            values["tax_address"], values["tax_receiving_authority"],
            values["authorized_person_full_name"], values["authorized_person_phone"],
            values["tax_taxpayer"],
        )

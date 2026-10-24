"""Independent workflow for the no-ecommerce-activity tax commitment."""
from mingo_assistant.services.documents.tax_ecommerce_commitment_generator import (
    TaxEcommerceCommitmentGenerator,
)
from mingo_assistant.ui.views.tax_revenue_commitment_workspace import (
    TaxRevenueCommitmentWorkspace,
)


class TaxEcommerceCommitmentWorkspace(TaxRevenueCommitmentWorkspace):
    def _document_generator_class(self):
        return TaxEcommerceCommitmentGenerator

    def _export_case_name(self, values):
        return self._field_value("tax_dossier_name") or values.get(
            "tax_company_name", "Cam kết không có hoạt động thương mại điện tử"
        )

"""ERC-based tax-code termination with two independent multiline inputs."""
from mingo_assistant.services.documents.tax_termination_generator import TaxTerminationGenerator
from mingo_assistant.ui.views.tax_invoice_commitment_workspace import TaxInvoiceCommitmentWorkspace


class TaxTerminationWorkspace(TaxInvoiceCommitmentWorkspace):
    MANUAL_FIELDS = (
        ("tax_termination_reason", "Lý do chấm dứt hiệu lực mã số thuế"),
        ("tax_attached_documents", "Hồ sơ đính kèm"),
    )

    def _document_generator_class(self):
        return TaxTerminationGenerator

    def _export_case_name(self, values):
        return self._field_value("tax_dossier_name") or values.get(
            "tax_company_name", "Văn bản chấm dứt mã số thuế"
        )

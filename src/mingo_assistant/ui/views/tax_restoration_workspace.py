"""Form 25 reuses the ERC workflow with a single multiline restoration reason."""
from mingo_assistant.services.documents.tax_restoration_generator import TaxRestorationGenerator
from mingo_assistant.ui.views.tax_termination_workspace import TaxTerminationWorkspace


class TaxRestorationWorkspace(TaxTerminationWorkspace):
    MANUAL_FIELDS = (("tax_restoration_reason", "Lý do đề nghị khôi phục mã số thuế"),)

    def _document_generator_class(self):
        return TaxRestorationGenerator

    def _export_case_name(self, values):
        return self._field_value("tax_dossier_name") or values.get(
            "tax_company_name", "Văn bản khôi phục mã số thuế"
        )

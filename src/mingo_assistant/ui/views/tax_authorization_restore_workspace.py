"""Independent tax-code restoration dossier using the shared authorization UI."""
from mingo_assistant.services.documents.tax_authorization_restore_generator import (
    TaxAuthorizationRestoreGenerator,
)
from mingo_assistant.ui.views.tax_authorization_close_workspace import (
    TaxAuthorizationCloseWorkspace,
)


class TaxAuthorizationRestoreWorkspace(TaxAuthorizationCloseWorkspace):
    def _document_generator_class(self):
        return TaxAuthorizationRestoreGenerator

    def _template_and_export_dirs(self):
        return (
            self.bundle_root / "assets/templates/word/tax/authorization_restore",
            self.selected_export_root or self.default_export_root,
        )

    def _export_case_name(self, values):
        return self._field_value("tax_dossier_name") or values.get(
            "tax_company_name", "Giấy ủy quyền khôi phục mã số thuế"
        )

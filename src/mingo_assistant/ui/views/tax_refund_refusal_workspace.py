"""Independent ERC workflow for the tax refund refusal form."""
from PySide6.QtWidgets import QLabel, QLineEdit

from mingo_assistant.services.documents.tax_refund_refusal_generator import (
    TaxRefundRefusalGenerator,
)
from mingo_assistant.ui.views.tax_commitment_workspace import TaxCommitmentWorkspace


class TaxRefundRefusalWorkspace(TaxCommitmentWorkspace):
    def _build_form_section(self):
        panel = super()._build_form_section()
        section = self.form_sections["Thông tin cơ quan tiếp nhận và người nộp thuế"]
        position = QLineEdit()
        position.setPlaceholderText("Nhập chức vụ (không bắt buộc)")
        position.textChanged.connect(self._refresh_preview)
        self.fields["tax_taxpayer_position"] = position
        row = section.layout().rowCount()
        section.layout().addWidget(QLabel("Chức vụ (không bắt buộc)"), row, 0)
        section.layout().addWidget(position, row, 1, 1, 3)
        return panel

    def _seed_from_case(self, case):
        super()._seed_from_case(case)
        values = case.form_values if case else {}
        self._set_field("tax_taxpayer_position", values.get("tax_taxpayer_position", ""))

    def form_values(self, apply_defaults=True):
        values = super().form_values(apply_defaults)
        values["tax_taxpayer_position"] = self._field_value("tax_taxpayer_position")
        return values

    def _document_generator_class(self):
        return TaxRefundRefusalGenerator

    def _export_case_name(self, values):
        return self._field_value("tax_dossier_name") or values.get(
            "tax_company_name", "Công văn từ chối hoàn tiền"
        )

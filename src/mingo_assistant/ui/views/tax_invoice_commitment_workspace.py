"""Independent workflow for the no-invoice-issuance tax commitment."""
from PySide6.QtWidgets import QLabel, QTextEdit

from mingo_assistant.services.documents.tax_invoice_commitment_generator import (
    TaxInvoiceCommitmentGenerator,
)
from mingo_assistant.services.registration_offices import signing_place_for_province
from mingo_assistant.ui.views.tax_commitment_workspace import TaxCommitmentWorkspace
from mingo_assistant.ui.views.tax_revenue_commitment_workspace import (
    TaxRevenueCommitmentWorkspace,
)


class TaxInvoiceCommitmentWorkspace(TaxRevenueCommitmentWorkspace):
    MANUAL_FIELDS = (
        (
            "tax_invoice_notice_commitment",
            "Không thông báo phát hành hóa đơn theo NĐ 51/2010/NĐ-CP",
        ),
        (
            "tax_einvoice_registration_commitment",
            "Không đăng ký hóa đơn điện tử theo NĐ 123/2020/NĐ-CP",
        ),
    )

    def _build_form_section(self):
        panel = super()._build_form_section()
        section = self.form_sections["Thông tin cơ quan tiếp nhận và người nộp thuế"]
        grid = section.layout()
        industry = self.fields.pop("tax_business_industry")
        industry_row = next(
            grid.getItemPosition(index)[0]
            for index in range(grid.count())
            if grid.itemAt(index).widget() is industry
        )
        for index in reversed(range(grid.count())):
            row, _, _, _ = grid.getItemPosition(index)
            if row == industry_row:
                item = grid.takeAt(index)
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()

        for key, label_text in self.MANUAL_FIELDS:
            label = QLabel(label_text)
            label.setWordWrap(True)
            field = QTextEdit()
            field.setPlaceholderText(
                "Chỉ nhập nội dung thay phần tô màu trong Word; "
                "câu cố định phía trước được giữ nguyên."
            )
            field.setMinimumHeight(110)
            field.setLineWrapMode(QTextEdit.WidgetWidth)
            field.textChanged.connect(self._refresh_preview)
            self.fields[key] = field
            row = grid.rowCount()
            grid.addWidget(label, row, 0)
            grid.addWidget(field, row, 1, 1, 3)
        return panel

    def _seed_from_case(self, case):
        super()._seed_from_case(case)
        values = case.form_values if case else {}
        for key, _ in self.MANUAL_FIELDS:
            self._set_field(key, values.get(key, ""))

    def form_values(self, apply_defaults=True):
        values = TaxCommitmentWorkspace.form_values(self, apply_defaults)
        values["tax_signing_place"] = signing_place_for_province(
            self._field_value("tax_signing_place")
        )
        for key, _ in self.MANUAL_FIELDS:
            values[key] = self._field_value(key)
        return values

    def _validation_issues(self, values):
        issues = TaxCommitmentWorkspace._validation_issues(self, values)
        if not values.get("tax_signing_place", "").strip():
            issues.append("Chưa có: Tỉnh/Thành phố")
        for key, label in self.MANUAL_FIELDS:
            if not values.get(key, "").strip():
                issues.append(f"Chưa có: {label}")
        return issues

    def _document_generator_class(self):
        return TaxInvoiceCommitmentGenerator

    def _export_case_name(self, values):
        return self._field_value("tax_dossier_name") or values.get(
            "tax_company_name", "Cam kết không phát hành hóa đơn"
        )

"""Independent workflow for the no-revenue and no-other-obligations commitment."""
from PySide6.QtCore import QSignalBlocker, QStringListModel, Qt
from PySide6.QtWidgets import QCompleter, QLabel, QLineEdit, QTextEdit

from mingo_assistant.services.documents.tax_revenue_commitment_generator import (
    TaxRevenueCommitmentGenerator,
)
from mingo_assistant.services.registration_offices import signing_place_for_province
from mingo_assistant.ui.views.tax_commitment_workspace import TaxCommitmentWorkspace


class TaxRevenueCommitmentWorkspace(TaxCommitmentWorkspace):
    INCLUDE_BUSINESS_INDUSTRY = True

    def _build_form_section(self):
        panel = super()._build_form_section()
        section = self.form_sections["Thông tin cơ quan tiếp nhận và người nộp thuế"]
        signing_place = QLineEdit()
        signing_place.setPlaceholderText("Nhập hoặc chọn tỉnh/thành phố")
        provinces = sorted(
            {
                signing_place_for_province(office.province)
                for office in self.registration_office_catalog.offices
                if office.province
            }
        )
        self.signing_place_completion_model = QStringListModel(provinces, signing_place)
        signing_place_completer = QCompleter(self.signing_place_completion_model, signing_place)
        signing_place_completer.setCaseSensitivity(Qt.CaseInsensitive)
        signing_place_completer.setCompletionMode(QCompleter.PopupCompletion)
        signing_place_completer.setFilterMode(Qt.MatchContains)
        signing_place.setCompleter(signing_place_completer)
        signing_place.textEdited.connect(
            lambda text: self._refresh_signing_place_suggestions(signing_place, text)
        )
        signing_place.editingFinished.connect(self._normalize_signing_place_field)
        signing_place.textChanged.connect(self._refresh_preview)
        self.fields["tax_signing_place"] = signing_place
        row = section.layout().rowCount()
        section.layout().addWidget(QLabel("Tỉnh/Thành phố"), row, 0)
        section.layout().addWidget(signing_place, row, 1, 1, 3)
        if not self.INCLUDE_BUSINESS_INDUSTRY:
            return panel
        industry = QTextEdit()
        industry.setObjectName("TaxBusinessIndustryInput")
        industry.setPlaceholderText("Nhập đầy đủ ngành nghề kinh doanh")
        industry.setMinimumHeight(110)
        industry.setLineWrapMode(QTextEdit.WidgetWidth)
        industry.textChanged.connect(self._refresh_preview)
        self.fields["tax_business_industry"] = industry
        row = section.layout().rowCount()
        section.layout().addWidget(QLabel("Ngành nghề kinh doanh"), row, 0)
        section.layout().addWidget(industry, row, 1, 1, 3)
        return panel

    def _refresh_signing_place_suggestions(self, field: QLineEdit, text: str) -> None:
        office_names = self.registration_office_catalog.suggestions(text, limit=34)
        provinces = list(
            dict.fromkeys(
                province
                for office_name in office_names
                if (
                    province := signing_place_for_province(
                        self.registration_office_catalog.province_for_office(office_name)
                    )
                )
            )
        )
        self.signing_place_completion_model.setStringList(provinces)
        if provinces and field.completer():
            field.completer().complete()

    def _normalize_signing_place_field(self) -> None:
        field = self.fields.get("tax_signing_place")
        if not isinstance(field, QLineEdit):
            return
        normalized = signing_place_for_province(field.text())
        if normalized != field.text():
            with QSignalBlocker(field):
                field.setText(normalized)

    def _seed_from_case(self, case):
        super()._seed_from_case(case)
        values = case.form_values if case else {}
        self._set_field("tax_signing_place", values.get("tax_signing_place", ""))
        self._set_field("tax_business_industry", values.get("tax_business_industry", ""))

    def form_values(self, apply_defaults=True):
        values = super().form_values(apply_defaults)
        values["tax_business_industry"] = self._field_value("tax_business_industry")
        values["tax_signing_place"] = signing_place_for_province(
            self._field_value("tax_signing_place")
        )
        return values

    def _validation_issues(self, values):
        issues = super()._validation_issues(values)
        if not values.get("tax_business_industry", "").strip():
            issues.append("Chưa có: Ngành nghề kinh doanh")
        if not values.get("tax_signing_place", "").strip():
            issues.append("Chưa có: Tỉnh/Thành phố")
        return issues

    def _document_generator_class(self):
        return TaxRevenueCommitmentGenerator

    def _export_case_name(self, values):
        return self._field_value("tax_dossier_name") or values.get(
            "tax_company_name", "Cam kết chưa phát sinh doanh thu"
        )

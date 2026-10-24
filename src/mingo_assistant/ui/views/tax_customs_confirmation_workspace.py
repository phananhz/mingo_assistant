"""Independent customs request using the existing authorized-person selector."""
from mingo_assistant.services.documents.tax_customs_confirmation_generator import (
    TaxCustomsConfirmationGenerator,
)
from mingo_assistant.ui.views.tax_authorization_close_workspace import TaxAuthorizationCloseWorkspace
from mingo_assistant.ui.views.tax_commitment_workspace import TaxCommitmentWorkspace


class TaxCustomsConfirmationWorkspace(TaxAuthorizationCloseWorkspace):
    SECTION_TITLE = "Cơ quan tiếp nhận, người đại diện và người nhận"
    ORGANIZATION_SAVED_MESSAGE = (
        "Đã áp dụng dữ liệu ERC vào hồ sơ. Chọn người đại diện pháp luật, "
        "người nhận từ danh sách người được ủy quyền và điền cơ quan tiếp nhận, địa điểm ký."
    )
    RECIPIENT_FIELDS = (
        ("authorized_person_full_name", "Người nhận"),
        ("authorized_person_phone", "Số điện thoại người nhận"),
    )

    def _build_form_section(self):
        panel = super()._build_form_section()
        section = self.form_sections[self.SECTION_TITLE]
        section.layout().itemAtPosition(1, 0).widget().setText("Người đại diện pháp luật")
        return panel

    def _validation_issues(self, values):
        issues = TaxCommitmentWorkspace._validation_issues(self, values)
        issues = [issue.replace("Người nộp thuế", "Người đại diện pháp luật") for issue in issues]
        for key, label in (*self.RECIPIENT_FIELDS, ("tax_signing_place", "Tỉnh/Thành phố")):
            if not values.get(key, "").strip():
                issues.append(f"Chưa có: {label}")
        return issues

    def _document_generator_class(self):
        return TaxCustomsConfirmationGenerator

    def _template_and_export_dirs(self):
        return TaxCommitmentWorkspace._template_and_export_dirs(self)

    def _export_case_name(self, values):
        return self._field_value("tax_dossier_name") or values.get(
            "tax_company_name", "Văn bản xác nhận không nợ thuế hải quan"
        )

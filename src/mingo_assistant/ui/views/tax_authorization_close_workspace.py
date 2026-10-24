"""Tax authorization: ERC grantor and existing authorized-person profiles."""
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QLabel, QPushButton

from mingo_assistant.services.documents.tax_authorization_close_generator import (
    TaxAuthorizationCloseGenerator,
)
from mingo_assistant.services.registration_offices import signing_place_for_province
from mingo_assistant.ui.views.tax_commitment_workspace import TaxCommitmentWorkspace
from mingo_assistant.ui.views.tax_revenue_commitment_workspace import TaxRevenueCommitmentWorkspace


class TaxAuthorizationCloseWorkspace(TaxRevenueCommitmentWorkspace):
    ORGANIZATION_SAVED_MESSAGE = (
        "Đã áp dụng dữ liệu ERC cho bên ủy quyền. Chọn người đại diện bên A, "
        "người được ủy quyền và điền cơ quan tiếp nhận, địa điểm ký để xuất Word."
    )
    INCLUDE_BUSINESS_INDUSTRY = False
    SECTION_TITLE = "Người ủy quyền, người được ủy quyền và địa điểm"
    RECIPIENT_FIELDS = (
        ("authorized_person_full_name", "Họ tên người được ủy quyền"),
        ("authorized_person_id_number", "Số CCCD"),
        ("authorized_person_issue_date", "Ngày cấp CCCD"),
        ("authorized_person_issue_place", "Nơi cấp CCCD"),
        ("authorized_person_phone", "Điện thoại"),
        ("authorized_person_email", "Email (nếu có)"),
    )

    def _build_form_section(self):
        panel = super()._build_form_section()
        old_title = "Thông tin cơ quan tiếp nhận và người nộp thuế"
        section = self.form_sections.pop(old_title)
        section.setTitle(self.SECTION_TITLE)
        self.form_sections[self.SECTION_TITLE] = section
        for button in panel.findChildren(QPushButton):
            if button.text() == old_title:
                button.setText(self.SECTION_TITLE)
        grid = section.layout()
        grid.itemAtPosition(1, 0).widget().setText("Người ủy quyền (đại diện pháp luật)")
        selector = self._build_person_fill_selector("authorized_person", self.SECTION_TITLE)
        selector.findChild(QLabel).setText("Chọn người được ủy quyền")
        grid.addWidget(selector, grid.rowCount(), 0, 1, 4)
        for key, label in self.RECIPIENT_FIELDS:
            row = grid.rowCount()
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(self._create_field(key), row, 1, 1, 3)
        return panel

    def _seed_from_case(self, case):
        super()._seed_from_case(case)
        values = case.form_values if case else {}
        for key, _ in self.RECIPIENT_FIELDS:
            self._set_field(key, values.get(key, ""))
        self._restore_dossier_selectors()

    def _restore_dossier_selectors(self):
        # Restore the selection without reapplying a global profile over the
        # saved dossier's own field values (which may have been edited).
        values = self.case.form_values if self.case else {}
        selected_id = values.get("tax_authorized_profile_id", "")
        profiles = self.authorized_person_defaults.get("__profiles", [])
        selector = self.person_fill_selectors["authorized_person"]
        with QSignalBlocker(selector):
            selector.setCurrentIndex(0)
        if isinstance(profiles, list) and selected_id:
            for index, profile in enumerate(profiles):
                if isinstance(profile, dict) and profile.get("id") == selected_id:
                    with QSignalBlocker(selector):
                        selector.setCurrentIndex(selector.findData(f"authorized_profile:{index}"))
                    break

    def form_values(self, apply_defaults=True):
        values = TaxCommitmentWorkspace.form_values(self, apply_defaults)
        values["tax_signing_place"] = signing_place_for_province(self._field_value("tax_signing_place"))
        values.update({key: self._field_value(key) for key, _ in self.RECIPIENT_FIELDS})
        selected = str(self.person_fill_selectors["authorized_person"].currentData() or "")
        values["tax_authorized_profile_id"] = ""
        if selected.startswith("authorized_profile:"):
            index = int(selected.split(":", 1)[1])
            profiles = self.authorized_person_defaults.get("__profiles", [])
            if isinstance(profiles, list) and 0 <= index < len(profiles):
                values["tax_authorized_profile_id"] = str(profiles[index].get("id", ""))
        return values

    def _validation_issues(self, values):
        issues = TaxCommitmentWorkspace._validation_issues(self, values)
        issues = [issue.replace("Người nộp thuế", "Người ủy quyền") for issue in issues]
        for key, label in (*self.RECIPIENT_FIELDS[:-1], ("tax_signing_place", "Tỉnh/Thành phố")):
            if not values.get(key, "").strip():
                issues.append(f"Chưa có: {label}")
        return issues

    def _document_generator_class(self):
        return TaxAuthorizationCloseGenerator

    def _template_and_export_dirs(self):
        return (
            self.bundle_root / "assets/templates/word/tax/authorization_close",
            self.selected_export_root or self.default_export_root,
        )

    def _export_case_name(self, values):
        return self._field_value("tax_dossier_name") or values.get(
            "tax_company_name", "Giấy ủy quyền giải thể (thuế)"
        )

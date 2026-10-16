"""Organization recognition and representative selection for amendment cases."""
from __future__ import annotations

import json
from pathlib import Path
from time import monotonic
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from shiboken6 import isValid

from mingo_assistant.services.documents.business_amendment_fields import ORGANIZATION_MAPPING, REPRESENTATIVE_FIELDS
from mingo_assistant.services.organization_documents.business_amendment_document_service import BusinessAmendmentDocumentService
from mingo_assistant.ui.views.business_registration_workspace import BusinessRegistrationWorkspace

if TYPE_CHECKING:
    from mingo_assistant.ui.views.business_amendment_workspace import BusinessAmendmentWorkspace


class AmendmentOrganizationController:
    """Coordinate PDF recognition without owning organization result widgets."""

    def __init__(self, owner: "BusinessAmendmentWorkspace") -> None:
        self.owner = owner

    def result_values(self) -> dict[str, str]:
        owner = self.owner
        values = BusinessRegistrationWorkspace._organization_result_values(owner)
        person = owner.ocr_people[owner.current_person_index] if owner.ocr_people else None
        if person:
            for key, value in person.organization_data.items():
                if key.startswith("amendment_"):
                    values.setdefault(key, value)
        values["amendment_recognition_confirmed"] = "1" if owner.organization_review_checkbox.isChecked() else ""
        return values

    def update_result_fields(self, values: dict[str, str]) -> None:
        owner = self.owner
        BusinessRegistrationWorkspace._update_organization_result_fields(owner, values)
        owner.organization_review_checkbox.blockSignals(True)
        owner.organization_review_checkbox.setChecked(values.get("amendment_recognition_confirmed") == "1")
        owner.organization_review_checkbox.blockSignals(False)
        owner.organization_review_notice.setText(
            values.get("amendment_recognition_warnings")
            or "Đối chiếu PDF và sửa dữ liệu trước khi áp dụng vào hồ sơ."
        )

    def apply_values_to_current_person(self, values, raw_text: str, extraction_method: str) -> None:
        owner = self.owner
        BusinessRegistrationWorkspace._apply_organization_values_to_current_person(
            owner, dict(values), raw_text, extraction_method
        )
        owner._refresh_update_organization_selector()

    def fill_from_selector(self) -> None:
        owner = self.owner
        selected_source = str(owner.update_organization_selector.currentData() or "")
        values = next((dict(data) for source, data in owner._organization_sources() if source == selected_source), {})
        if not values:
            return
        owner._selected_update_organization = {
            key: value
            for key, value in values.items()
            if key in BusinessAmendmentDocumentService.RECOGNIZED_FIELDS or key.startswith("amendment_")
        }
        owner._set_fields_from_mapping({
            target: values.get(source, "")
            for target, source in ORGANIZATION_MAPPING.items()
            if source in BusinessAmendmentDocumentService.RECOGNIZED_FIELDS
        })
        owner._refresh_preview()

    def save_profile(self) -> None:
        owner = self.owner
        values = self.result_values()
        if not all(values.get(key, "").strip() for key in BusinessAmendmentDocumentService.RECOGNIZED_FIELDS):
            QMessageBox.warning(owner, "Cần kiểm tra dữ liệu", "Cần tên doanh nghiệp và mã số doanh nghiệp/mã số thuế.")
            return
        if values.get("amendment_recognition_confirmed") != "1":
            QMessageBox.warning(owner, "Cần đối chiếu PDF", "Kiểm tra, sửa dữ liệu và tích xác nhận đối chiếu trước khi áp dụng.")
            return
        code = values["organization_owner_registration_number"]
        owner.organization_profiles = [
            dict(profile)
            for profile in owner.organization_profiles
            if profile.get("organization_owner_registration_number") != code
        ]
        owner.organization_profiles.append(dict(values))
        self.apply_values_to_current_person(values, owner.raw_ocr_text.toPlainText(), "reviewed")
        owner._selected_update_organization = dict(values)
        owner._set_fields_from_mapping({
            target: values.get(source, "")
            for target, source in ORGANIZATION_MAPPING.items()
            if source in BusinessAmendmentDocumentService.RECOGNIZED_FIELDS
        })
        owner._refresh_preview()
        QMessageBox.information(
            owner,
            "Đã lưu dữ liệu tổ chức",
            "Đã lưu dữ liệu đã đối chiếu vào hồ sơ này và điền thông tin doanh nghiệp hiện tại.",
        )

    def fill_representative_from_pdf(self) -> None:
        owner = self.owner
        values = owner._selected_update_organization
        if not values.get("legal_representative_full_name"):
            QMessageBox.warning(
                owner,
                "Chưa có người đại diện",
                "Chọn doanh nghiệp có dữ liệu người đại diện hoặc nhập tay/chọn người đã quét.",
            )
            return
        owner._set_fields_from_mapping({key: values.get(key, "") for key, _ in REPRESENTATIVE_FIELDS})
        owner._representative_company_code = values.get("organization_owner_registration_number", "")
        owner._refresh_preview()

    def fill_representative_from_person(self, person) -> None:
        owner = self.owner
        data = owner._person_data_for_fill(person)
        owner._set_fields_from_mapping({key: data.get(key, "") for key, _ in REPRESENTATIVE_FIELDS})
        owner._representative_company_code = ""
        owner._refresh_preview()

    def scan_document(self, path: str) -> None:
        owner = self.owner
        if owner._scan_in_progress:
            return
        owner._scan_in_progress = True
        owner._scan_token += 1
        token = owner._scan_token
        person = owner.ocr_people[owner.current_person_index]
        case_id = owner.case_id
        start = monotonic()
        owner.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = owner.organization_document_service.extract_pdf(
                path,
                lambda percent, status: owner._update_ocr_progress(
                    percent, status, owner._format_elapsed(start)
                ) if isValid(owner) else None,
            )
        except Exception as exc:
            if isValid(owner):
                QMessageBox.critical(owner, "Không thể đọc tài liệu", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
            if isValid(owner):
                owner.setEnabled(True)
            owner._scan_in_progress = False
        if not isValid(owner):
            return
        if token != owner._scan_token or case_id != owner.case_id or person is not owner.ocr_people[owner.current_person_index]:
            return
        if hasattr(owner.window(), "current_workspace") and owner.window().current_workspace is not owner:
            return
        values = dict(result.values)
        values.update({
            "amendment_recognition_confirmed": "",
            "amendment_recognition_warnings": "\n".join(result.warnings),
            "amendment_recognition_sources": json.dumps(result.field_sources, ensure_ascii=False),
            "amendment_recognition_route": ", ".join(result.processing_route),
            "amendment_source_pdf": str(path),
        })
        self.apply_values_to_current_person(values, result.raw_text, result.extraction_method)
        self.update_result_fields(values)
        owner.raw_ocr_text.setPlainText(result.raw_text)
        owner.organization_document_label.setText(f"Tài liệu: {Path(path).name} — cần đối chiếu dữ liệu nhận diện")
        owner.recognition_result_stack.setCurrentIndex(1)
        owner._update_ocr_progress(100, "Đã nhận diện — cần đối chiếu PDF", owner._format_elapsed(start))

    def choose_document(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.owner,
            "Chọn giấy đăng ký doanh nghiệp",
            "",
            "Tài liệu PDF (*.pdf)",
        )
        if path:
            self.scan_document(path)

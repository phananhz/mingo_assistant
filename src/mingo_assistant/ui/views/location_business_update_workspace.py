"""Workspace for changing business-location registration content."""
from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QMessageBox, QScrollArea, QTextEdit, QVBoxLayout, QWidget,
)

from mingo_assistant.models.case import CaseSummary
from mingo_assistant.domains.dependent_unit.location_changes import (
    LOCATION_CHANGE_FIELDS, UPDATE_LABOR_INPUT_KEY, UPDATE_LEGACY_LABOR_KEY,
    entered_location_changes, location_change_has_data, normalize_location_update_tax_values,
)
from mingo_assistant.services.organization_documents.location_certificate_service import (
    LocationCertificateService,
)
from mingo_assistant.ui.views.location_certificate_recognition import (
    build_location_certificate_result_section,
)
from mingo_assistant.ui.views.location_business_workspace import LocationBusinessWorkspace
from mingo_assistant.ui.widgets.combo_box import NoWheelComboBox


LOCATION_UPDATE_CASE_TYPE = "\u0110\u1ecba \u0111i\u1ec3m kinh doanh - Thay \u0111\u1ed5i n\u1ed9i dung kinh doanh"
LOCATION_UPDATE_TEMPLATE_FOLDER = ("dependent_units", "ddkd_update")

UPDATE_FIELD_GROUPS = (
    ("Th\u00f4ng tin c\u01a1 quan ti\u1ebfp nh\u1eadn v\u00e0 th\u1eddi gian k\u00fd", (("business_registration_office", "Ph\u00f2ng \u0110\u0103ng k\u00fd kinh doanh"), ("document_place", "N\u01a1i k\u00fd"), ("document_day", "Ng\u00e0y k\u00fd"), ("document_month", "Th\u00e1ng k\u00fd"), ("document_year", "N\u0103m k\u00fd"), ("document_place_date", "D\u00f2ng \u0111\u1ecba \u0111i\u1ec3m/ng\u00e0y th\u00e1ng"))),
    ("Th\u00f4ng tin doanh nghi\u1ec7p", (("parent_entity_name", "T\u00ean doanh nghi\u1ec7p"), ("parent_entity_registration_number", "M\u00e3 s\u1ed1 doanh nghi\u1ec7p/M\u00e3 s\u1ed1 thu\u1ebf"))),
    ("Th\u00f4ng tin ng\u01b0\u1eddi \u0111\u1ea1i di\u1ec7n ph\u00e1p lu\u1eadt", (("legal_representative_full_name", "H\u1ecd t\u00ean ng\u01b0\u1eddi \u0111\u1ea1i di\u1ec7n ph\u00e1p lu\u1eadt"), ("legal_representative_id_number", "S\u1ed1 \u0111\u1ecbnh danh ng\u01b0\u1eddi \u0111\u1ea1i di\u1ec7n ph\u00e1p lu\u1eadt"), ("legal_representative_position", "Ch\u1ee9c danh ng\u01b0\u1eddi \u0111\u1ea1i di\u1ec7n ph\u00e1p lu\u1eadt"))),
    ("N\u1ed9i dung thay \u0111\u1ed5i", ()),
    ("Th\u00f4ng tin ng\u01b0\u1eddi \u0111\u01b0\u1ee3c \u1ee7y quy\u1ec1n", (("authorized_person_full_name", "H\u1ecd t\u00ean"), ("authorized_person_id_number", "S\u1ed1 CCCD"), ("authorized_person_issue_date", "Ng\u00e0y c\u1ea5p CCCD"), ("authorized_person_issue_place", "N\u01a1i c\u1ea5p CCCD"), ("authorized_person_contact_address", "\u0110\u1ecba ch\u1ec9 li\u00ean l\u1ea1c"), ("authorized_person_phone", "\u0110i\u1ec7n tho\u1ea1i"), ("authorized_person_email", "Email (n\u1ebfu c\u00f3)"))),
)


class LocationBusinessUpdateWorkspace(LocationBusinessWorkspace):
    """A reduced form for changing business-location registration content."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.organization_document_service = LocationCertificateService(
            self.address_parser, self.bundle_root
        )

    def _seed_from_case(self, case: CaseSummary | None) -> None:
        saved = normalize_location_update_tax_values(case.form_values) if case else {}
        super()._seed_from_case(replace(case, form_values=saved) if case else None)
        # Override the creation default even for saved dossiers. A legacy
        # unconfirmed 1 is not evidence that the user requested a tax change.
        self._set_field("tax_labor_count", saved.get("tax_labor_count", ""))
        self._legacy_tax_labor_count = saved.get(UPDATE_LEGACY_LABOR_KEY, "")
        field = self.fields.get("tax_labor_count")
        if isinstance(field, QLineEdit) and self._legacy_tax_labor_count:
            field.setToolTip(
                "Hồ sơ cũ có giá trị 1 chưa xác nhận, có thể do app tự điền. "
                "Nếu cần kê khai 1 lao động, vui lòng nhập lại 1."
            )

    def _build_organization_result_section(self) -> QWidget:
        return build_location_certificate_result_section(self)

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        back = QPushButton("\u2190 Quay l\u1ea1i")
        back.setObjectName("GhostButton")
        back.clicked.connect(self.on_back)
        text = QVBoxLayout()
        title = QLabel("Thay \u0111\u1ed5i n\u1ed9i dung \u0111\u1ecba \u0111i\u1ec3m kinh doanh")
        title.setObjectName("PageTitle")
        description = QLabel(
            "Qu\u00e9t gi\u1ea5y ch\u1ee9ng nh\u1eadn \u0111\u1ecba \u0111i\u1ec3m kinh doanh, ch\u1ecdn ng\u01b0\u1eddi \u0111\u1ea1i di\u1ec7n ph\u00e1p lu\u1eadt "
            "v\u00e0 ng\u01b0\u1eddi \u0111\u01b0\u1ee3c \u1ee7y quy\u1ec1n \u0111\u1ec3 t\u1ea1o h\u1ed3 s\u01a1 thay \u0111\u1ed5i."
        )
        description.setObjectName("PageDescription")
        description.setWordWrap(True)
        text.addWidget(title)
        text.addWidget(description)
        check = QPushButton("Ki\u1ec3m tra m\u1eabu Word")
        check.setObjectName("GhostButton")
        check.clicked.connect(self._check_templates)
        storage = QPushButton("Ch\u1ecdn n\u01a1i l\u01b0u")
        storage.setObjectName("GhostButton")
        storage.clicked.connect(self._choose_export_root)
        save = QPushButton("L\u01b0u nh\u00e1p")
        save.setObjectName("GhostButton")
        save.clicked.connect(self._save_draft)
        export = QPushButton("Xu\u1ea5t h\u1ed3 s\u01a1")
        export.setObjectName("PrimaryButton")
        export.clicked.connect(self._export_documents)
        header.addWidget(back)
        header.addLayout(text, 1)
        header.addWidget(check)
        header.addWidget(storage)
        header.addWidget(save)
        header.addWidget(export)
        return header

    def _build_form_section(self) -> QWidget:
        group = QGroupBox("Th\u00f4ng tin d\u00f9ng \u0111\u1ec3 \u0111i\u1ec1n v\u00e0o h\u1ed3 s\u01a1")
        layout = QVBoxLayout(group)
        nav = QWidget()
        nav.setObjectName("FormSectionNav")
        nav.setLayout(self.form_nav_layout)
        self.form_nav_widget = nav
        scroll = QScrollArea()
        scroll.setObjectName("FormSectionNavScroll")
        scroll.setWidgetResizable(False)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFixedHeight(66)
        scroll.setWidget(nav)
        layout.addWidget(scroll)
        layout.addWidget(self.form_stack)
        for index, (title, fields) in enumerate(UPDATE_FIELD_GROUPS):
            button = QPushButton(title)
            button.setObjectName("PrimaryButton" if index == 0 else "GhostButton")
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.setMinimumHeight(38)
            button.clicked.connect(lambda checked=False, selected=index: self._select_form_section(selected))
            self.form_button_group.addButton(button, index)
            self.form_nav_buttons[title] = button
            self.form_nav_layout.addWidget(button)
            if index == 1:
                section = self._build_organization_section(list(fields))
            elif index == 3:
                section = self._build_change_sections_section()
            else:
                section = self._build_regular_form_section(title, list(fields))
            self.form_sections[title] = section
            self.form_stack.addWidget(section)
        self.form_nav_layout.addStretch(1)
        nav.setFixedHeight(48)
        nav.setMinimumWidth(self.form_nav_layout.sizeHint().width())
        self._select_form_section(0)
        return group

    def _build_organization_section(self, fields: list[tuple[str, str]]) -> QWidget:
        section = QGroupBox("Th\u00f4ng tin doanh nghi\u1ec7p")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)
        selector_row = QHBoxLayout()
        selector_label = QLabel("T\u1ed5 ch\u1ee9c \u0111\u00e3 qu\u00e9t/\u0111\u00e3 l\u01b0u")
        selector_label.setObjectName("FilterLabel")
        self.update_organization_selector = NoWheelComboBox()
        self.update_organization_selector.currentIndexChanged.connect(self._fill_update_organization_from_selector)
        self.update_organization_selector.activated.connect(self._fill_update_organization_from_selector)
        selector_row.addWidget(selector_label)
        selector_row.addWidget(self.update_organization_selector, 1)
        layout.addLayout(selector_row)
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)
        for row, (key, label_text) in enumerate(fields):
            label = QLabel(label_text)
            label.setObjectName("FilterLabel")
            grid.addWidget(label, row, 0)
            grid.addWidget(self._create_field(key), row, 1)
        layout.addLayout(grid)
        self._refresh_update_organization_selector()
        return section

    def _organization_sources(self) -> list[tuple[str, dict[str, str]]]:
        sources: list[tuple[str, dict[str, str]]] = []
        seen: set[str] = set()
        for index, profile in enumerate(self.organization_profiles):
            values = dict(profile)
            identity = (
                values.get("organization_owner_registration_number", "")
                or values.get("parent_entity_registration_number", "")
                or f"profile:{index}"
            )
            if identity in seen:
                continue
            seen.add(identity)
            sources.append((f"profile:{index}", values))
        for index, person in enumerate(self.ocr_people):
            saved = person.saved_organization_data or (
                person.organization_data if person.recognition_saved else {}
            )
            if not saved:
                continue
            values = dict(saved)
            identity = (
                values.get("organization_owner_registration_number", "")
                or values.get("parent_entity_registration_number", "")
                or f"ocr:{index}"
            )
            if identity in seen:
                continue
            seen.add(identity)
            sources.append((f"ocr:{index}", values))
        return sources

    def _refresh_update_organization_selector(self) -> None:
        selector = getattr(self, "update_organization_selector", None)
        if selector is None:
            return
        current = str(selector.currentData() or "")
        selector.blockSignals(True)
        selector.clear()
        selector.addItem("Ch\u1ecdn t\u1ed5 ch\u1ee9c \u0111\u1ec3 \u0111i\u1ec1n", "")
        for source, values in self._organization_sources():
            name = (
                values.get("location_business_name", "")
                or values.get("organization_owner_name", "")
                or values.get("parent_entity_name", "")
                or "T\u1ed5 ch\u1ee9c ch\u01b0a c\u00f3 t\u00ean"
            )
            code = (
                values.get("location_business_code", "")
                or values.get("organization_owner_registration_number", "")
                or values.get("parent_entity_registration_number", "")
            )
            selector.addItem(f"{name} - {code}" if code else name, source)
        index = selector.findData(current)
        if index >= 0:
            selector.setCurrentIndex(index)
        selector.blockSignals(False)

    def _fill_update_organization_from_selector(self) -> None:
        selector = getattr(self, "update_organization_selector", None)
        if selector is None:
            return
        selected = str(selector.currentData() or "")
        values = next((data for source, data in self._organization_sources() if source == selected), {})
        self._selected_update_organization = dict(values)
        if values:
            self._set_fields_from_mapping({
                "parent_entity_name": (
                    values.get("parent_entity_name", "")
                    or values.get("organization_owner_name", "")
                ),
                "parent_entity_registration_number": (
                    values.get("parent_entity_registration_number", "")
                    or values.get("organization_owner_registration_number", "")
                ),
                "location_business_name": values.get("location_business_name", ""),
                "location_business_code": values.get("location_business_code", ""),
                "location_full_address": values.get("location_full_address", ""),
                "location_phone": values.get("location_phone", ""),
                "location_fax": values.get("location_fax", ""),
                "location_email": values.get("location_email", ""),
                "location_website": values.get("location_website", ""),
            })
        self._refresh_preview()

    def _apply_organization_values_to_current_person(
        self,
        values: dict[str, str],
        raw_text: str,
        extraction_method: str,
        *,
        document_type: str = "brc",
    ) -> None:
        super()._apply_organization_values_to_current_person(
            values,
            raw_text,
            extraction_method,
            document_type=document_type,
        )
        person = self.ocr_people[self.current_person_index]
        person.name = values.get("location_business_name") or values.get("parent_entity_name") or person.name
        self._refresh_people_buttons()

    def _organization_result_values(self) -> dict[str, str]:
        values = dict(self.ocr_people[self.current_person_index].organization_data)
        values.update(super()._organization_result_values())
        return values

    def _save_organization_profile(self) -> None:
        values = self._organization_result_values()
        required = {
            "parent_entity_name": "Tên doanh nghiệp",
            "parent_entity_registration_number": "Mã số thuế",
            "location_business_name": "Tên địa điểm kinh doanh",
            "location_business_code": "Mã số địa điểm kinh doanh",
            "location_full_address": "Địa chỉ địa điểm kinh doanh",
        }
        missing = [label for key, label in required.items() if not values.get(key, "").strip()]
        if missing:
            QMessageBox.warning(
                self,
                "Chưa thể lưu giấy chứng nhận",
                "Vui lòng kiểm tra và bổ sung:\n- " + "\n- ".join(missing),
            )
            return

        person = self.ocr_people[self.current_person_index]
        person.organization_data = dict(values)
        person.saved_organization_data = dict(values)
        person.recognition_type = "organization"
        person.document_type = "brc"
        person.recognition_saved = True
        person.data.clear()
        person.saved_data.clear()

        source = f"ocr:{self.current_person_index}"
        self._refresh_update_organization_selector()
        if self.update_organization_selector.currentData() == source:
            self._fill_update_organization_from_selector()
        self._refresh_preview()
        QMessageBox.information(
            self,
            "Đã lưu giấy chứng nhận",
            "Đã lưu dữ liệu BRC. Chọn profile trong dropdown để điền vào hồ sơ.",
        )

    def form_values(self, apply_defaults: bool = True) -> dict[str, str]:
        values = super().form_values(apply_defaults=apply_defaults)
        # Creation-only defaults/phone synchronization must not populate an
        # update section, or overwrite tax contacts actually entered here.
        values.update(self._change_input_values())
        values[UPDATE_LABOR_INPUT_KEY] = "1" if values.get("tax_labor_count", "").strip() else "0"
        legacy_labor = getattr(self, "_legacy_tax_labor_count", "")
        if legacy_labor:
            values[UPDATE_LEGACY_LABOR_KEY] = legacy_labor
        values["change_correction_selected"] = ""
        organization = getattr(self, "_selected_update_organization", {})
        if organization:
            values["company_name"] = (
                organization.get("parent_entity_name", "")
                or organization.get("organization_owner_name", "")
                or values.get("company_name", "")
            )
            company_address = ", ".join(part for part in (
                organization.get("organization_owner_address_detail", ""),
                organization.get("organization_owner_ward", ""),
                organization.get("organization_owner_province", ""),
                organization.get("organization_owner_country", ""),
            ) if part)
            if company_address:
                values["company_address"] = company_address
        supplemental_field = self.fields.get("supplemental_registration_content")
        if isinstance(supplemental_field, QTextEdit):
            # Keep the complete plain-text editor content, including explicit
            # line breaks. The first manifest slot is the expandable Part B
            # content area; the remaining legacy slots stay empty so the
            # generator can remove the template's spare yellow paragraphs.
            supplemental_text = supplemental_field.toPlainText()
            values["supplemental_registration_content"] = supplemental_text
        else:
            supplemental_text = str(values.get("supplemental_registration_content", "") or "")
        values["supplemental_registration_content_1"] = supplemental_text
        values["supplemental_registration_content_2"] = ""
        values["supplemental_registration_content_3"] = ""
        # Tax checkbox symbols still require manual completion in the exported Word file.
        for key in (
            "tax_accounting_independent_x",
            "tax_accounting_consolidated_x",
            "tax_accounting_dependent_x",
        ):
            values[key] = ""
        return values

    def _build_change_sections_section(self) -> QWidget:
        section = QGroupBox("N\u1ed9i dung thay \u0111\u1ed5i")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        common = QGroupBox("Th\u00f4ng tin \u0111\u1ecba \u0111i\u1ec3m kinh doanh hi\u1ec7n t\u1ea1i")
        common_layout = QGridLayout(common)
        common_layout.setHorizontalSpacing(18)
        common_layout.setVerticalSpacing(10)
        for row, (key, label_text) in enumerate((("location_business_name", "T\u00ean \u0111\u1ecba \u0111i\u1ec3m kinh doanh"), ("location_business_code", "M\u00e3 s\u1ed1 \u0111\u1ecba \u0111i\u1ec3m kinh doanh"))):
            label = QLabel(label_text)
            label.setObjectName("FilterLabel")
            common_layout.addWidget(label, row, 0)
            common_layout.addWidget(self._create_field(key), row, 1)
        layout.addWidget(common)

        instruction = QLabel(
            "Chọn đầu mục để mở hoặc thu gọn form nhập. Dấu ✓ cho biết đầu mục đã có dữ liệu. "
            "Khi xuất Word, chỉ giữ các đầu mục có dữ liệu, kể cả khi form đang thu gọn."
        )
        instruction.setObjectName("PageDescription")
        instruction.setWordWrap(True)
        layout.addWidget(instruction)

        choices = QWidget()
        choice_grid = QGridLayout(choices)
        choice_grid.setContentsMargins(0, 0, 0, 0)
        choice_grid.setHorizontalSpacing(28)
        choice_grid.setVerticalSpacing(6)
        self.change_options = (
            ("change_name_selected", "\u0110\u0103ng k\u00fd thay \u0111\u1ed5i t\u00ean \u0111\u1ecba \u0111i\u1ec3m kinh doanh", (("new_location_business_name", "T\u00ean \u0111\u1ecba \u0111i\u1ec3m kinh doanh b\u1eb1ng ti\u1ebfng Vi\u1ec7t sau khi thay \u0111\u1ed5i"), ("new_location_business_english_name", "T\u00ean \u0111\u1ecba \u0111i\u1ec3m kinh doanh b\u1eb1ng ti\u1ebfng n\u01b0\u1edbc ngo\u00e0i sau khi thay \u0111\u1ed5i"), ("new_location_business_short_name", "T\u00ean \u0111\u1ecba \u0111i\u1ec3m kinh doanh vi\u1ebft t\u1eaft sau khi thay \u0111\u1ed5i"))),
            ("change_address_selected", "\u0110\u0103ng k\u00fd thay \u0111\u1ed5i \u0111\u1ecba ch\u1ec9 \u0111\u1ecba \u0111i\u1ec3m kinh doanh", (("new_location_address_detail", "S\u1ed1 nh\u00e0/ph\u00f2ng, ng\u00e1ch/h\u1ebbm, ng\u00f5/ki\u1ec7t, \u0111\u01b0\u1eddng/ph\u1ed1/\u0111\u1ea1i l\u1ed9, t\u1ed5/x\u00f3m/\u1ea5p/th\u00f4n"), ("new_location_ward", "X\u00e3/Ph\u01b0\u1eddng/\u0110\u1eb7c khu"), ("new_location_province", "T\u1ec9nh/Th\u00e0nh ph\u1ed1 tr\u1ef1c thu\u1ed9c trung \u01b0\u01a1ng"), ("new_location_phone", "\u0110i\u1ec7n tho\u1ea1i (n\u1ebfu c\u00f3)"), ("new_location_fax", "S\u1ed1 fax (n\u1ebfu c\u00f3)"), ("new_location_email", "Th\u01b0 \u0111i\u1ec7n t\u1eed (n\u1ebfu c\u00f3)"), ("new_location_website", "Website (n\u1ebfu c\u00f3)"))),
            ("change_business_lines_selected", "\u0110\u0103ng k\u00fd thay \u0111\u1ed5i ng\u00e0nh, ngh\u1ec1 kinh doanh/n\u1ed9i dung ho\u1ea1t \u0111\u1ed9ng", ()),
            ("change_manager_selected", "\u0110\u0103ng k\u00fd thay \u0111\u1ed5i ng\u01b0\u1eddi \u0111\u1ee9ng \u0111\u1ea7u \u0111\u1ecba \u0111i\u1ec3m kinh doanh", (("location_manager_full_name", "H\u1ecd, ch\u1eef \u0111\u1ec7m v\u00e0 t\u00ean (ghi b\u1eb1ng ch\u1eef in hoa)"), ("location_manager_date_of_birth", "Ng\u00e0y, th\u00e1ng, n\u0103m sinh"), ("location_manager_gender", "Gi\u1edbi t\u00ednh"), ("location_manager_id_number", "S\u1ed1 \u0111\u1ecbnh danh c\u00e1 nh\u00e2n"), ("location_manager_address_detail", "S\u1ed1 nh\u00e0/ph\u00f2ng, ng\u00e1ch/h\u1ebbm, ng\u00f5/ki\u1ebft, \u0111\u01b0\u1eddng/ph\u1ed1/\u0111\u1ea1i l\u1ed9, t\u1ed5/x\u00f3m/\u1ea5p/th\u00f4n"), ("location_manager_ward", "X\u00e3/Ph\u01b0\u1eddng/\u0110\u1eb7c khu"), ("location_manager_province", "T\u1ec9nh/Th\u00e0nh ph\u1ed1 tr\u1ef1c thu\u1ed9c trung \u01b0\u01a1ng"), ("location_manager_nationality", "Qu\u1ed1c gia"), ("location_manager_phone", "\u0110i\u1ec7n tho\u1ea1i (n\u1ebfu c\u00f3)"), ("location_manager_email", "Th\u01b0 \u0111i\u1ec7n t\u1eed (n\u1ebfu c\u00f3)"))),
            ("change_tax_selected", "\u0110\u0103ng k\u00fd thay \u0111\u1ed5i th\u00f4ng tin \u0111\u0103ng k\u00fd thu\u1ebf", (("tax_accountant_full_name", "H\u1ecd, ch\u1eef \u0111\u1ec7m v\u00e0 t\u00ean K\u1ebf to\u00e1n tr\u01b0\u1edfng/Ph\u1ee5 tr\u00e1ch k\u1ebf to\u00e1n (n\u1ebfu c\u00f3)"), ("tax_accountant_date_of_birth", "Ng\u00e0y, th\u00e1ng, n\u0103m sinh"), ("tax_accountant_gender", "Gi\u1edbi t\u00ednh"), ("tax_accountant_id_number", "S\u1ed1 \u0111\u1ecbnh danh c\u00e1 nh\u00e2n"), ("tax_accountant_phone", "\u0110i\u1ec7n tho\u1ea1i"), ("tax_notification_address_detail", "\u0110\u1ecba ch\u1ec9 nh\u1eadn th\u00f4ng b\u00e1o thu\u1ebf (n\u1ebfu c\u00f3) - s\u1ed1 nh\u00e0/ph\u00f2ng, \u0111\u01b0\u1eddng/ph\u1ed1"), ("tax_notification_ward", "\u0110\u1ecba ch\u1ec9 nh\u1eadn th\u00f4ng b\u00e1o thu\u1ebf (n\u1ebfu c\u00f3) - x\u00e3/ph\u01b0\u1eddng/\u0111\u1eb7c khu"), ("tax_notification_province", "\u0110\u1ecba ch\u1ec9 nh\u1eadn th\u00f4ng b\u00e1o thu\u1ebf (n\u1ebfu c\u00f3) - t\u1ec9nh/th\u00e0nh ph\u1ed1"), ("tax_notification_phone", "\u0110i\u1ec7n tho\u1ea1i nh\u1eadn th\u00f4ng b\u00e1o thu\u1ebf (n\u1ebfu c\u00f3)"), ("tax_notification_email", "Th\u01b0 \u0111i\u1ec7n t\u1eed nh\u1eadn th\u00f4ng b\u00e1o thu\u1ebf (n\u1ebfu c\u00f3)"), ("tax_accounting_independent_x", "H\u1ea1ch to\u00e1n \u0111\u1ed9c l\u1eadp"), ("tax_accounting_consolidated_x", "C\u00f3 b\u00e1o c\u00e1o t\u00e0i ch\u00ednh h\u1ee3p nh\u1ea5t"), ("tax_accounting_dependent_x", "H\u1ea1ch to\u00e1n ph\u1ee5 thu\u1ed9c"), ("tax_financial_year_start", "N\u0103m t\u00e0i ch\u00ednh - \u00e1p d\u1ee5ng t\u1eeb ng\u00e0y"), ("tax_financial_year_end", "N\u0103m t\u00e0i ch\u00ednh - \u0111\u1ebfn ng\u00e0y"), ("tax_labor_count", "T\u1ed5ng s\u1ed1 lao \u0111\u1ed9ng"))),
            ("change_supplemental_selected", "\u0110\u0103ng k\u00fd b\u1ed5 sung, c\u1eadp nh\u1eadt th\u00f4ng tin \u0111\u0103ng k\u00fd ho\u1ea1t \u0111\u1ed9ng", (("supplemental_registration_content", "N\u1ed9i dung b\u1ed5 sung, c\u1eadp nh\u1eadt"),)),
        )
        self.change_option_cards: dict[str, QFrame] = {}
        self.change_option_indicators: dict[str, QLabel] = {}
        for index, (key, title, _fields) in enumerate(self.change_options):
            card = QFrame()
            card.setObjectName("ChangeOptionCard")
            card.setProperty("selected", False)
            card.setProperty("completed", False)
            card.setMinimumHeight(46)
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(10, 7, 10, 7)
            card_layout.setSpacing(8)
            checkbox = QCheckBox(title)
            checkbox.setObjectName("ChangeSectionOption")
            checkbox.setIconSize(QSize(18, 18))
            checkbox.setStyleSheet(
                "QCheckBox { background: transparent; border: none; padding: 0; } "
                "QCheckBox::indicator { image: none; width: 0px; height: 0px; margin: 0; padding: 0; }"
            )
            checkbox.stateChanged.connect(self._refresh_change_forms)
            indicator = QLabel("\u2713")
            indicator.setObjectName("ChangeOptionCompleteIndicator")
            indicator.setAlignment(Qt.AlignCenter)
            indicator.setFixedSize(22, 22)
            indicator.setToolTip("N\u1ed9i dung n\u00e0y \u0111\u00e3 c\u00f3 d\u1eef li\u1ec7u nh\u1eadp.")
            indicator.setVisible(False)
            card_layout.addWidget(checkbox, 1)
            card_layout.addWidget(indicator)
            self.fields[key] = checkbox
            self.change_option_cards[key] = card
            self.change_option_indicators[key] = indicator
            choice_grid.addWidget(card, index // 2, index % 2)
        layout.addWidget(choices)

        forms_label = QLabel("Th\u00f4ng tin c\u1ea7n \u0111i\u1ec1n")
        forms_label.setObjectName("FilterLabel")
        layout.addWidget(forms_label)
        self.change_forms_scroll = QScrollArea()
        self.change_forms_scroll.setObjectName("ChangeFormsScroll")
        self.change_forms_scroll.setWidgetResizable(True)
        self.change_forms_scroll.setMinimumHeight(360)
        forms_content = QWidget()
        self.change_forms_layout = QVBoxLayout(forms_content)
        self.change_forms_layout.setContentsMargins(2, 2, 2, 2)
        self.change_forms_layout.setSpacing(12)
        self.change_empty_label = QLabel("Ch\u1ecdn \u00edt nh\u1ea5t m\u1ed9t n\u1ed9i dung thay \u0111\u1ed5i \u0111\u1ec3 hi\u1ec3n th\u1ecb form t\u01b0\u01a1ng \u1ee9ng.")
        self.change_empty_label.setObjectName("PageDescription")
        self.change_empty_label.setWordWrap(True)
        self.change_forms_layout.addWidget(self.change_empty_label)
        self.change_forms: dict[str, QGroupBox] = {}
        self.change_form_order = tuple(key for key, _title, _fields in self.change_options)
        for form_index, (key, title, fields) in enumerate(self.change_options):
            form = QGroupBox(title)
            form.setObjectName("ChangeDetailFormDark" if form_index % 2 else "ChangeDetailFormLight")
            form_layout = QGridLayout(form)
            form_layout.setContentsMargins(16, 14, 16, 14)
            form_layout.setHorizontalSpacing(18)
            form_layout.setVerticalSpacing(10)
            first_field_row = 0
            if key == "change_business_lines_selected":
                main_line_note = QLabel(
                    "Ch\u1ecdn m\u1ed9t ng\u00e0nh, ngh\u1ec1 kinh doanh ch\u00ednh. D\u1ea5u X s\u1ebd \u0111\u01b0\u1ee3c ghi v\u00e0o file Word khi xu\u1ea5t h\u1ed3 s\u01a1."
                )
                main_line_note.setObjectName("ManualXNotice")
                main_line_note.setWordWrap(True)
                form_layout.addWidget(main_line_note, 0, 0, 1, 4)
                form_layout.addWidget(self._build_business_lines_section(max_rows=7), 1, 0, 1, 4)
                for row in self.business_line_rows:
                    row.main_checkbox.setEnabled(True)
                    row.main_checkbox.setToolTip("Ch\u1ec9 ch\u1ecdn m\u1ed9t ng\u00e0nh, ngh\u1ec1 kinh doanh ch\u00ednh.")
            else:
                fill_target = {
                    "change_manager_selected": "location_manager",
                    "change_tax_selected": "tax_accountant",
                }.get(key)
                if fill_target:
                    form_layout.addWidget(self._build_person_fill_selector(fill_target, title), 0, 0, 1, 4)
                    first_field_row = 1
                for index, (field_key, label_text) in enumerate(fields):
                    label = QLabel(label_text)
                    label.setObjectName("FilterLabel")
                    row = first_field_row + index // 2
                    form_layout.addWidget(label, row, (index % 2) * 2)
                    form_layout.addWidget(self._create_change_value_field(field_key), row, (index % 2) * 2 + 1)
                if key == "change_manager_selected":
                    self.location_manager_identity_warning = QLabel(
                        "Cần kiểm tra kĩ người đại diện pháp luật và người đứng đầu địa điểm kinh doanh vì CCCD đang trùng nhau."
                    )
                    self.location_manager_identity_warning.setObjectName("ManualXNotice")
                    self.location_manager_identity_warning.setWordWrap(True)
                    self.location_manager_identity_warning.setVisible(False)
                    warning_row = first_field_row + (len(fields) + 1) // 2
                    form_layout.addWidget(self.location_manager_identity_warning, warning_row, 0, 1, 4)
                    for identity_key in ("location_manager_id_number", "legal_representative_id_number"):
                        identity_field = self.fields.get(identity_key)
                        if isinstance(identity_field, QLineEdit):
                            identity_field.textChanged.connect(self._refresh_location_manager_identity_warning)
                    self._refresh_location_manager_identity_warning()
            form.setVisible(False)
            self.change_forms[key] = form
            self.change_forms_layout.addWidget(form)
        self.change_forms_layout.addStretch(1)
        self.change_forms_scroll.setWidget(forms_content)
        layout.addWidget(self.change_forms_scroll, 1)
        self._refresh_change_forms()
        return section

    def _create_change_value_field(self, key: str) -> QWidget:
        manual_x_keys = {"tax_accounting_independent_x", "tax_accounting_consolidated_x", "tax_accounting_dependent_x"}
        if key == "supplemental_registration_content":
            field = QTextEdit()
            field.setAcceptRichText(False)
            field.setFixedHeight(100)
            field.setPlaceholderText("Nhập nội dung bổ sung, cập nhật. Có thể xuống dòng không giới hạn.")
            field.textChanged.connect(self._on_supplemental_content_changed)
            self.fields[key] = field
            return field
        if key in {"tax_accountant_phone", "tax_notification_phone", "tax_notification_email"}:
            field = QLineEdit()
            field.textChanged.connect(self._refresh_preview)
            self.fields[key] = field
            return field
        if key in {"location_manager_date_of_birth", "tax_accountant_date_of_birth"}:
            field = QLineEdit()
            field.setPlaceholderText("dd/mm/yyyy")
            field.textChanged.connect(self._refresh_preview)
            self.fields[key] = field
            return field
        if key not in manual_x_keys:
            return self._create_field(key)
        field = QCheckBox("T\u00edch X \u2014 Ph\u1ea7n n\u00e0y c\u1ea7n \u0111i\u1ec1n th\u1ee7 c\u00f4ng v\u00e0o file \u0111\u00e3 xu\u1ea5t ho\u00e0n ch\u1ec9nh")
        field.setEnabled(False)
        field.setToolTip("C\u00e1c \u00f4 \u0111\u00e1nh d\u1ea5u X trong m\u1eabu Word ch\u01b0a \u0111\u01b0\u1ee3c t\u1ef1 \u0111\u1ed9ng \u0111i\u1ec1n.")
        self.fields[key] = field
        return field

    def _refresh_preview(self) -> None:
        """Keep each selected-change card current while the user types."""
        if hasattr(self, "change_option_cards"):
            self._refresh_change_option_cards()
        super()._refresh_preview()

    def _supplemental_content_lines(self) -> list[str]:
        field = self.fields.get("supplemental_registration_content")
        if isinstance(field, QTextEdit):
            return [line for line in field.toPlainText().splitlines() if line.strip()]
        if isinstance(field, QLineEdit) and field.text().strip():
            return [field.text().strip()]
        return []

    def _on_supplemental_content_changed(self) -> None:
        """Refresh the data-complete marker without changing form visibility."""
        self._refresh_preview()

    def _clear_person_fill_target(self, target: str) -> None:
        if target == "tax_accountant":
            for key in (
                "tax_accountant_full_name", "tax_accountant_date_of_birth", "tax_accountant_gender",
                "tax_accountant_id_number", "tax_accountant_phone",
            ):
                self._set_field(key, "")
            return
        super()._clear_person_fill_target(target)

    def _fill_section_from_person(self, target: str, person) -> None:
        if target != "tax_accountant":
            super()._fill_section_from_person(target, person)
            return
        data = self._person_data_for_fill(person)
        self._set_fields_from_mapping({
            "tax_accountant_full_name": data.get("legal_representative_full_name", ""),
            "tax_accountant_date_of_birth": data.get("legal_representative_date_of_birth", ""),
            "tax_accountant_gender": data.get("legal_representative_gender", ""),
            "tax_accountant_id_number": data.get("legal_representative_id_number", ""),
            "tax_accountant_phone": data.get("personal_phone", ""),
        })
        self._refresh_preview()

    def _refresh_location_manager_identity_warning(self, *_args) -> None:
        warning = getattr(self, "location_manager_identity_warning", None)
        if not isinstance(warning, QLabel):
            return
        manager_id = re.sub(r"\D", "", self._field_value("location_manager_id_number"))
        representative_id = re.sub(r"\D", "", self._field_value("legal_representative_id_number"))
        warning.setVisible(bool(manager_id and representative_id and manager_id == representative_id))

    def _change_input_values(self) -> dict[str, str]:
        values = {
            field: self._field_value(field)
            for fields in LOCATION_CHANGE_FIELDS.values() for field in fields
        }
        for index in range(1, len(self.business_line_rows) + 1):
            for part in ("name", "detail", "code"):
                key = f"business_line_{index}_{part}"
                values[key] = self._field_value(key)
        return values

    def _change_option_has_entered_data(self, key: str, fields: tuple[tuple[str, str], ...]) -> bool:
        return location_change_has_data(key, self._change_input_values())

    @staticmethod
    def _change_option_checkbox_icon(selected: bool) -> QIcon:
        """Draw the left selection control as an explicit square checkbox."""
        pixmap = QPixmap(18, 18)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        border = QColor("#0b6fb8") if selected else QColor("#526b86")
        painter.setPen(QPen(border, 2))
        painter.setBrush(QColor("#1686d9") if selected else QColor("#ffffff"))
        painter.drawRoundedRect(1, 1, 16, 16, 3, 3)
        if selected:
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.drawLine(4, 9, 7, 12)
            painter.drawLine(7, 12, 14, 5)
        painter.end()
        return QIcon(pixmap)

    def _refresh_change_option_cards(self) -> None:
        for key, _title, fields in self.change_options:
            checkbox = self.fields.get(key)
            selected = isinstance(checkbox, QCheckBox) and checkbox.isChecked()
            # Checkbox selection controls only whether the editing form is
            # visible.  The green marker is a persistent data-state indicator:
            # it remains shown after the form is collapsed and disappears only
            # once every field in that registration is cleared.
            completed = self._change_option_has_entered_data(key, fields)
            card = self.change_option_cards[key]
            indicator = self.change_option_indicators[key]
            card.setProperty("selected", selected)
            card.setProperty("completed", completed)
            checkbox.setIcon(self._change_option_checkbox_icon(selected))
            if selected and completed:
                card.setStyleSheet(
                    "QFrame#ChangeOptionCard { background: #edfdf5; border: 2px solid #21874b; "
                    "border-radius: 9px; } QCheckBox { background: transparent; border: none; } QCheckBox::indicator { width: 0px; height: 0px; }"
                )
            elif selected:
                card.setStyleSheet(
                    "QFrame#ChangeOptionCard { background: #f0edff; border: 2px solid #6f58c9; "
                    "border-radius: 9px; } QCheckBox { background: transparent; border: none; } QCheckBox::indicator { width: 0px; height: 0px; }"
                )
            else:
                card.setStyleSheet(
                    "QFrame#ChangeOptionCard { background: #f8fafc; border: 2px solid #879bb5; "
                    "border-radius: 9px; } QCheckBox { background: transparent; border: none; } QCheckBox::indicator { width: 0px; height: 0px; }"
                )
            indicator.setStyleSheet(
                "QLabel#ChangeOptionCompleteIndicator { background: #21874b; border: 1px solid #166534; "
                "border-radius: 4px; color: #ffffff; font-size: 14px; font-weight: 900; }"
            )
            indicator.setVisible(completed)

    def _refresh_change_forms(self, *_args) -> None:
        has_selection = False
        for key, _title, _fields in self.change_options:
            checkbox = self.fields.get(key)
            selected = isinstance(checkbox, QCheckBox) and checkbox.isChecked()
            self.change_forms[key].setVisible(selected)
            has_selection = has_selection or selected
        self.change_empty_label.setVisible(not has_selection)
        self._refresh_preview()

    def _template_and_export_dirs(self) -> tuple[Path, Path]:
        return (self.bundle_root / "assets" / "templates" / "word" / Path(*LOCATION_UPDATE_TEMPLATE_FOLDER), self.selected_export_root or self.default_export_root)

    @staticmethod
    def _has_entered_change_data(values: dict[str, str]) -> bool:
        """The Word notification is driven by entered values, not UI checkboxes."""
        return bool(entered_location_changes(values))

    def _missing_required_fields(self, values: dict[str, str]) -> list[str]:
        required = {
            "business_registration_office": "Ph\u00f2ng \u0110\u0103ng k\u00fd kinh doanh", "parent_entity_name": "T\u00ean doanh nghi\u1ec7p", "parent_entity_registration_number": "M\u00e3 s\u1ed1 doanh nghi\u1ec7p/M\u00e3 s\u1ed1 thu\u1ebf", "legal_representative_full_name": "H\u1ecd t\u00ean ng\u01b0\u1eddi \u0111\u1ea1i di\u1ec7n ph\u00e1p lu\u1eadt", "legal_representative_id_number": "S\u1ed1 \u0111\u1ecbnh danh ng\u01b0\u1eddi \u0111\u1ea1i di\u1ec7n ph\u00e1p lu\u1eadt", "legal_representative_position": "Ch\u1ee9c danh ng\u01b0\u1eddi \u0111\u1ea1i di\u1ec7n ph\u00e1p lu\u1eadt", "authorized_person_full_name": "H\u1ecd t\u00ean ng\u01b0\u1eddi \u0111\u01b0\u1ee3c \u1ee7y quy\u1ec1n", "authorized_person_id_number": "S\u1ed1 CCCD ng\u01b0\u1eddi \u0111\u01b0\u1ee3c \u1ee7y quy\u1ec1n", "authorized_person_contact_address": "\u0110\u1ecba ch\u1ec9 li\u00ean l\u1ea1c ng\u01b0\u1eddi \u0111\u01b0\u1ee3c \u1ee7y quy\u1ec1n",
        }
        missing = [label for key, label in required.items() if not values.get(key, "").strip()]
        if not values.get("location_business_name", "").strip(): missing.append("T\u00ean \u0111\u1ecba \u0111i\u1ec3m kinh doanh")
        if not values.get("location_business_code", "").strip(): missing.append("M\u00e3 s\u1ed1 \u0111\u1ecba \u0111i\u1ec3m kinh doanh")
        if not self._has_entered_change_data(values):
            missing.append("C\u1ea7n nh\u1eadp \u00edt nh\u1ea5t m\u1ed9t n\u1ed9i dung \u0111\u0103ng k\u00fd thay \u0111\u1ed5i")
        has_business_lines = any(
            values.get(f"business_line_{index}_{part}", "").strip()
            for index in LocationBusinessUpdateWorkspace._business_line_indices(values)
            for part in ("name", "detail", "code")
        )
        if has_business_lines:
            business_line_indices = LocationBusinessUpdateWorkspace._business_line_indices(values)
            if not any(values.get(f"business_line_{index}_name", "").strip() for index in business_line_indices):
                missing.append("\u00cdt nh\u1ea5t m\u1ed9t ng\u00e0nh ngh\u1ec1 kinh doanh thay \u0111\u1ed5i")
            elif not any(values.get(f"business_line_{index}_is_main", "").strip() for index in business_line_indices):
                missing.append("\u0110\u0103ng k\u00fd thay \u0111\u1ed5i ng\u00e0nh, ngh\u1ec1 kinh doanh ph\u1ea3i ch\u1ecdn m\u1ed9t ng\u00e0nh ngh\u1ec1 kinh doanh ch\u00ednh")
        for key, label in (
            ("location_manager_date_of_birth", "Ng\u00e0y sinh ng\u01b0\u1eddi \u0111\u1ee9ng \u0111\u1ea7u \u0111\u1ecba \u0111i\u1ec3m kinh doanh"),
            ("tax_accountant_date_of_birth", "Ng\u00e0y sinh K\u1ebf to\u00e1n tr\u01b0\u1edfng/Ph\u1ee5 tr\u00e1ch k\u1ebf to\u00e1n"),
        ):
            value = values.get(key, "").strip()
            if not value:
                continue
            try:
                datetime.strptime(value, "%d/%m/%Y")
            except ValueError:
                missing.append(f"{label} ph\u1ea3i theo d\u1ea1ng dd/mm/yyyy v\u00e0 l\u00e0 ng\u00e0y h\u1ee3p l\u1ec7")
        return missing

    def build_case_summary(self, *args, **kwargs) -> CaseSummary:
        return replace(super().build_case_summary(*args, **kwargs), case_type=LOCATION_UPDATE_CASE_TYPE)

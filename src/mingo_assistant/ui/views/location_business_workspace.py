"""Workspace for establishing a business location."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mingo_assistant.models.case import CaseSummary
from mingo_assistant.services.documents.dependent_unit_generator import DependentUnitTemplateGenerator
from mingo_assistant.ui.views.business_registration.export_worker import DocxExportWorker
from mingo_assistant.ui.views.business_registration_workspace import BusinessRegistrationWorkspace
from mingo_assistant.ui.widgets.combo_box import NoWheelComboBox


LOCATION_CASE_TYPE = "Địa điểm kinh doanh - Lập mới"
LOCATION_TEMPLATE_FOLDER = ("dependent_units", "ddkd_create")

LOCATION_FIELD_GROUPS = (
    ("Thông tin cơ quan tiếp nhận và thời gian ký", (
        ("business_registration_office", "Phòng Đăng ký kinh doanh"),
        ("document_place", "Nơi ký"),
        ("document_day", "Ngày ký"),
        ("document_month", "Tháng ký"),
        ("document_year", "Năm ký"),
        ("document_place_date", "Dòng địa điểm/ngày tháng"),
    )),
    ("Thông tin doanh nghiệp/chi nhánh chủ quản", (
        ("parent_entity_type", "Đơn vị chủ quản"),
        ("parent_entity_name", "Tên doanh nghiệp"),
        ("parent_entity_registration_number", "Mã số doanh nghiệp/Mã số thuế"),
        ("parent_entity_branch_name", "Tên chi nhánh chủ quản (nếu có)"),
        ("parent_entity_branch_number", "Mã số chi nhánh/Mã số thuế chi nhánh (nếu có)"),
    )),
    ("Thông tin địa điểm kinh doanh", (
        ("location_business_name", "Tên địa điểm bằng tiếng Việt"),
        ("location_business_english_name", "Tên bằng tiếng nước ngoài (nếu có)"),
        ("location_business_short_name", "Tên viết tắt (nếu có)"),
        ("location_full_address", "\u0110\u1ecba ch\u1ec9 \u0111\u1ea7y \u0111\u1ee7"),
        ("location_address_detail", "Số nhà/đường/thôn"),
        ("location_ward", "Xã/Phường/Đặc khu"),
        ("location_province", "Tỉnh/Thành phố"),
        ("location_phone", "Điện thoại (nếu có)"),
        ("location_email", "Thư điện tử (nếu có)"),
    )),
    ("Thông tin người đứng đầu địa điểm kinh doanh", (
        ("location_manager_person_type", "Người Việt Nam / người nước ngoài"),
        ("location_manager_full_name", "Họ, chữ đệm và tên"),
        ("location_manager_date_of_birth", "Ngày sinh"),
        ("location_manager_gender", "Giới tính"),
        ("location_manager_id_number", "Số định danh cá nhân"),
        ("location_manager_address_detail", "Số nhà/đường/thôn"),
        ("location_manager_ward", "Xã/Phường/Đặc khu"),
        ("location_manager_province", "Tỉnh/Thành phố"),
        ("location_manager_nationality", "Quốc gia"),
        ("location_manager_ethnicity", "Dân tộc"),
        ("location_manager_passport_number", "Số hộ chiếu"),
        ("location_manager_passport_issue_date", "Ngày cấp hộ chiếu"),
        ("location_manager_passport_issue_place", "Nơi cấp hộ chiếu"),
        ("location_manager_foreign_address_detail", "Địa chỉ thường trú"),
        ("location_manager_foreign_country", "Quốc gia"),
    )),
    ("Ngành nghề kinh doanh", ()),
    ("Thông tin đăng ký thuế và bảo hiểm xã hội", (
        ("tax_accountant_full_name", "Họ tên kế toán trưởng/phụ trách kế toán (nếu có)"),
        ("tax_accountant_date_of_birth", "Ngày sinh kế toán (nếu có)"),
        ("tax_accountant_gender", "Giới tính kế toán (nếu có)"),
        ("tax_accountant_id_number", "Số định danh kế toán (nếu có)"),
        ("tax_accountant_phone", "Điện thoại kế toán (nếu có)"),
        ("tax_notification_address_detail", "Địa chỉ nhận thông báo thuế - số nhà/đường (nếu khác)"),
        ("tax_notification_ward", "Địa chỉ nhận thông báo thuế - xã/phường"),
        ("tax_notification_province", "Địa chỉ nhận thông báo thuế - tỉnh/thành"),
        ("tax_notification_phone", "Điện thoại nhận thông báo thuế (nếu có)"),
        ("tax_notification_fax", "Fax nhận thông báo thuế (nếu có)"),
        ("tax_notification_email", "Email nhận thông báo thuế (nếu có)"),
        ("tax_accounting_method", "Hình thức hạch toán"),
        ("tax_consolidated_financial_statement", "Có báo cáo tài chính hợp nhất"),
        ("tax_labor_count", "Tổng số lao động dự kiến"),
        ("tax_bot_project", "Hoạt động theo dự án BOT/BTO/BT/BOO, BLT, BTL, O&M"),
        ("tax_vat_method", "Phương pháp tính thuế GTGT"),
    )),
    ("Thông tin người đại diện pháp luật", (
        ("legal_representative_full_name", "Họ tên người đại diện pháp luật"),
        ("legal_representative_id_number", "Số định danh người đại diện pháp luật"),
        ("legal_representative_position", "Chức danh người đại diện pháp luật"),
    )),
    ("Thông tin người được ủy quyền", (
        ("authorized_person_full_name", "Họ tên"),
        ("authorized_person_id_number", "Số CCCD"),
        ("authorized_person_issue_date", "Ngày cấp CCCD"),
        ("authorized_person_issue_place", "Nơi cấp CCCD"),
        ("authorized_person_contact_address", "Địa chỉ liên lạc"),
        ("authorized_person_phone", "Điện thoại"),
        ("authorized_person_email", "Email (nếu có)"),
    )),
)


class LocationBusinessWorkspace(BusinessRegistrationWorkspace):
    """Reuse CCCD/PDF scanning, profiles, drafts and versioned exports."""

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setObjectName("BusinessWorkspaceScroll")
        scroll.setWidgetResizable(True)
        page = QWidget()
        page.setObjectName("BusinessWorkspacePage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)
        layout.addLayout(self._build_header())
        layout.addWidget(self._build_ocr_section())
        layout.addWidget(self._build_form_section())
        scroll.setWidget(page)
        root.addWidget(scroll)

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        back = QPushButton("← Quay lại")
        back.setObjectName("GhostButton")
        back.clicked.connect(self.on_back)
        text = QVBoxLayout()
        title = QLabel("Tạo hồ sơ lập địa điểm kinh doanh")
        title.setObjectName("PageTitle")
        description = QLabel("Quét QR CCCD, nhận diện PDF, kiểm tra dữ liệu và xuất bộ mẫu địa điểm kinh doanh.")
        description.setObjectName("PageDescription")
        description.setWordWrap(True)
        text.addWidget(title)
        text.addWidget(description)
        check = QPushButton("Kiểm tra mẫu Word")
        check.setObjectName("GhostButton")
        check.clicked.connect(self._check_templates)
        storage = QPushButton("Chọn nơi lưu")
        storage.setObjectName("GhostButton")
        storage.clicked.connect(self._choose_export_root)
        save = QPushButton("Lưu nháp")
        save.setObjectName("GhostButton")
        save.clicked.connect(self._save_draft)
        export = QPushButton("Xuất Word")
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
        group = QGroupBox("Thông tin dùng để điền vào hồ sơ")
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
        for index, (title, fields) in enumerate(LOCATION_FIELD_GROUPS):
            button = QPushButton(title)
            button.setObjectName("PrimaryButton" if index == 0 else "GhostButton")
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.setMinimumHeight(38)
            button.clicked.connect(lambda checked=False, selected=index: self._select_form_section(selected))
            self.form_button_group.addButton(button, index)
            self.form_nav_buttons[title] = button
            self.form_nav_layout.addWidget(button)
            section = self._build_business_lines_section() if title == "Ngành nghề kinh doanh" else self._build_regular_form_section(title, list(fields))
            self.form_sections[title] = section
            self.form_stack.addWidget(section)
        self.form_nav_layout.addStretch(1)
        nav.setFixedHeight(48)
        nav.setMinimumWidth(self.form_nav_layout.sizeHint().width())
        self._select_form_section(0)
        return group

    def _build_regular_form_section(self, title: str, fields: list[tuple[str, str]]) -> QWidget:
        if not any(key == "location_manager_person_type" for key, _label in fields):
            return super()._build_regular_form_section(title, fields)
        return self._build_location_manager_form_section(title, fields)

    def _build_location_manager_form_section(self, title: str, fields: list[tuple[str, str]]) -> QWidget:
        section = QGroupBox(title)
        grid = QGridLayout(section)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)
        grid.setAlignment(Qt.AlignTop)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        selector = self._build_person_fill_selector("location_manager", title)
        grid.addWidget(selector, 0, 0, 1, 4)
        self._location_manager_vietnamese_widgets: list[QWidget] = []
        self._location_manager_foreign_widgets: list[QWidget] = []
        foreign_keys = {
            "location_manager_ethnicity",
            "location_manager_passport_number",
            "location_manager_passport_issue_date",
            "location_manager_passport_issue_place",
            "location_manager_foreign_address_detail",
            "location_manager_foreign_country",
        }
        vietnamese_keys = {
            "location_manager_id_number",
            "location_manager_address_detail",
            "location_manager_ward",
            "location_manager_province",
            "location_manager_nationality",
        }
        for index, (key, label_text) in enumerate(fields):
            row = 1 + index // 2
            column = (index % 2) * 2
            label = QLabel(label_text)
            label.setObjectName("FilterLabel")
            field = self._create_field(key)
            grid.addWidget(label, row, column)
            grid.addWidget(field, row, column + 1)
            if key in foreign_keys:
                self._location_manager_foreign_widgets.extend((label, field))
            elif key in vietnamese_keys:
                self._location_manager_vietnamese_widgets.extend((label, field))
        self._sync_location_manager_person_type()
        return section

    def _sync_location_manager_person_type(self) -> None:
        field = self.fields.get("location_manager_person_type")
        is_foreign = isinstance(field, QComboBox) and field.currentIndex() == 1
        for widget in getattr(self, "_location_manager_vietnamese_widgets", []):
            widget.setVisible(not is_foreign)
        for widget in getattr(self, "_location_manager_foreign_widgets", []):
            widget.setVisible(is_foreign)
        if is_foreign:
            self._clear_location_manager_fields((
                "location_manager_id_number", "location_manager_address_detail",
                "location_manager_ward", "location_manager_province", "location_manager_nationality",
            ))
        else:
            self._clear_location_manager_fields((
                "location_manager_ethnicity", "location_manager_passport_number",
                "location_manager_passport_issue_date", "location_manager_passport_issue_place",
                "location_manager_foreign_address_detail", "location_manager_foreign_country",
            ))

    def _clear_location_manager_fields(self, keys: tuple[str, ...]) -> None:
        for key in keys:
            self._set_field(key, "")

    def _person_fill_target_for_section(self, title: str) -> str:
        targets = {
            "Thông tin người đứng đầu địa điểm kinh doanh": "location_manager",
            "Thông tin người đại diện pháp luật": "legal_representative",
            "Thông tin người được ủy quyền": "authorized_person",
        }
        return targets.get(title, super()._person_fill_target_for_section(title))

    def _fill_section_from_person(self, target: str, person) -> None:
        if target != "location_manager":
            super()._fill_section_from_person(target, person)
            return
        data = self._person_data_for_fill(person)
        self._set_field("location_manager_person_type", "Ng\u01b0\u1eddi Vi\u1ec7t Nam")
        self._clear_location_manager_fields((
            "location_manager_ethnicity",
            "location_manager_passport_number",
            "location_manager_passport_issue_date",
            "location_manager_passport_issue_place",
            "location_manager_foreign_address_detail",
            "location_manager_foreign_country",
        ))
        address = self.address_parser.parse(data.get("legal_representative_permanent_address", ""))
        mapping = {
            "location_manager_full_name": data.get("legal_representative_full_name", ""),
            "location_manager_date_of_birth": data.get("legal_representative_date_of_birth", ""),
            "location_manager_gender": data.get("legal_representative_gender", ""),
            "location_manager_id_number": data.get("legal_representative_id_number", ""),
            "location_manager_address_detail": address.street_line or address.village,
            "location_manager_ward": address.ward,
            "location_manager_province": address.province,
            "location_manager_nationality": data.get("legal_representative_nationality", "Vi\u1ec7t Nam"),
        }
        self._set_fields_from_mapping(mapping)
        self._refresh_preview()

    def _activate_organization_owner_for_document(self) -> bool:
        """A location dossier has no organization-owner form to activate."""
        return True

    def _apply_organization_values_to_current_person(
        self,
        values: dict[str, str],
        raw_text: str,
        extraction_method: str,
    ) -> None:
        """Reuse PDF recognition, then put its company data in the location form."""
        super()._apply_organization_values_to_current_person(values, raw_text, extraction_method)
        self._set_fields_from_mapping({
            "parent_entity_name": values.get("organization_owner_name", ""),
            "parent_entity_registration_number": values.get("organization_owner_registration_number", ""),
        })
        self._refresh_preview()

    def _apply_cccd_values_to_current_person(
        self,
        card_values: dict[str, str],
        apply_to_form: bool = True,
    ) -> None:
        """Apply a scan to its selected role; organization data stays separate."""
        super()._apply_cccd_values_to_current_person(card_values, apply_to_form=False)
        if apply_to_form:
            person = self.ocr_people[self.current_person_index]
            target = person.role if person.role in {"legal_representative", "authorized_person"} else "location_manager"
            self._fill_section_from_person(target, person)

    def _save_organization_profile(self) -> None:
        """Save recognized organization data for this location dossier."""
        values = self._organization_result_values()
        required = {
            "organization_owner_name": "Tên tổ chức",
            "organization_owner_registration_number": "Mã số doanh nghiệp/Số quyết định thành lập",
            "organization_owner_address_detail": "Địa chỉ trụ sở chính",
        }
        missing = [label for key, label in required.items() if not values.get(key, "").strip()]
        if missing:
            QMessageBox.warning(self, "Cần kiểm tra dữ liệu tổ chức", "Chưa có:\n- " + "\n- ".join(missing))
            return

        registration_number = values["organization_owner_registration_number"].strip()
        existing = next(
            (
                profile
                for profile in self.organization_profiles
                if profile.get("organization_owner_registration_number", "") == registration_number
            ),
            None,
        )
        if existing is None:
            self.organization_profiles.append(dict(values))
        else:
            existing.update(values)
        self._apply_organization_values_to_current_person(values, self.raw_ocr_text.toPlainText(), "saved")
        QMessageBox.information(
            self,
            "Đã lưu dữ liệu tổ chức",
            "Đã lưu thông tin tổ chức và điền vào phần doanh nghiệp/chi nhánh chủ quản.",
        )

    def _sync_address_parts(self, source_key: str) -> None:
        if source_key != "location_full_address":
            super()._sync_address_parts(source_key)
            return
        if self.syncing_address_fields:
            return
        address = self._field_value(source_key)
        if not address:
            return
        parsed = self.address_parser.parse(address)
        detail = self._address_detail_from_result(parsed)
        if not any((detail, parsed.ward, parsed.province)):
            return
        self.syncing_address_fields = True
        try:
            self._set_field("location_address_detail", detail)
            self._set_field("location_ward", parsed.ward)
            self._set_field("location_province", parsed.province)
        finally:
            self.syncing_address_fields = False
        self._refresh_preview()
    def _create_field(self, key: str):
        if key == "location_manager_person_type":
            field = NoWheelComboBox()
            field.addItems(("Ng\u01b0\u1eddi Vi\u1ec7t Nam", "Ng\u01b0\u1eddi n\u01b0\u1edbc ngo\u00e0i"))
            field.currentIndexChanged.connect(lambda _index: self._sync_location_manager_person_type())
            field.currentTextChanged.connect(self._refresh_preview)
            self.fields[key] = field
            return field
        if key == "parent_entity_type":
            field = NoWheelComboBox()
            field.addItems(("Doanh nghi\u1ec7p", "Chi nhánh"))
            field.currentTextChanged.connect(self._refresh_preview)
            self.fields[key] = field
            return field
        if key in {"tax_notification_address_detail", "authorized_person_contact_address"}:
            field = QTextEdit()
            field.setFixedHeight(70)
            field.textChanged.connect(self._refresh_preview)
            self.fields[key] = field
            return field
        field = super()._create_field(key)
        if key == "location_full_address" and isinstance(field, QLineEdit):
            field.textChanged.connect(lambda: self._schedule_address_sync("location_full_address"))
        if key == "location_province" and isinstance(field, QLineEdit):
            field.textChanged.connect(self._fill_registration_office_from_location)
        if key in {"location_phone", "location_email"} and isinstance(field, QLineEdit):
            field.textChanged.connect(self._sync_location_contacts_to_tax_notification)
        if key in {"tax_notification_phone", "tax_notification_email"} and isinstance(field, QLineEdit):
            field.setReadOnly(True)
            field.setToolTip("Tự động lấy từ thông tin địa điểm kinh doanh")
            self._sync_location_contacts_to_tax_notification()
        return field

    def _sync_location_contacts_to_tax_notification(self) -> None:
        self._set_field("tax_notification_phone", self._field_value("location_phone"))
        self._set_field("tax_notification_email", self._field_value("location_email"))

    def _fill_registration_office_from_location(self) -> None:
        if self._initializing:
            return
        office = self.fields.get("business_registration_office")
        province = self._field_value("location_province")
        if isinstance(office, QLineEdit) and not office.text().strip() and province:
            suggestion = self.registration_office_catalog.display_name_for_province(province)
            if suggestion:
                office.setText(suggestion)

    def _organization_data_for_form(self) -> dict[str, str]:
        for person in reversed(self.ocr_people):
            if person.organization_data:
                return dict(person.organization_data)
        if self.organization_profiles:
            return dict(self.organization_profiles[-1])
        return {}
    def form_values(self, apply_defaults: bool = True) -> dict[str, str]:
        values = super().form_values(apply_defaults=False)
        organization = self._organization_data_for_form()
        organization_name = organization.get("organization_owner_name", "").strip()
        if organization_name:
            values["company_name"] = organization_name
        elif values.get("parent_entity_name", "").strip():
            values["company_name"] = values["parent_entity_name"].strip()
        organization_address_parts = [
            organization.get("organization_owner_address_detail", "").strip(),
            organization.get("organization_owner_ward", "").strip(),
            organization.get("organization_owner_province", "").strip(),
            organization.get("organization_owner_country", "").strip(),
        ]
        organization_address = ", ".join(part for part in organization_address_parts if part)
        if organization_address:
            values["company_address"] = organization_address
        values["signer_full_name"] = values.get("legal_representative_full_name", "").strip()
        if not apply_defaults:
            return values
        place = self._signing_place_for_office(values.get("business_registration_office", ""))
        if place:
            values["document_place"] = place
        if all(values.get(key, "").strip() for key in ("document_day", "document_month", "document_year")):
            values["document_place_date"] = f"{values.get('document_place', '').strip()}, ngày {values['document_day']} tháng {values['document_month']} năm {values['document_year']}".strip(", ")
        name = values.get("parent_entity_name", "").strip()
        upper = name.upper()
        prefixes = ("CÔNG TY TNHH", "CÔNG TY CỔ PHẦN", "CÔNG TY HỢP DANH", "DOANH NGHIỆP TƯ NHÂN")
        prefix = next((item for item in prefixes if upper.startswith(item)), "")
        values["parent_entity_name_prefix"] = prefix
        values["parent_entity_name_suffix"] = upper[len(prefix):].strip() if prefix else upper
        for index in range(1, 12):
            populated = any(values.get(f"business_line_{index}_{part}", "").strip() for part in ("name", "detail", "code"))
            values[f"business_line_{index}_number"] = str(index) if populated else ""
        values["tax_notification_phone"] = values.get("location_phone", "")
        values["tax_notification_email"] = values.get("location_email", "")
        values["tax_accounting_dependent_x"] = "X" if values.get("tax_accounting_method") == "Hạch toán phụ thuộc" else ""
        values["tax_bot_project_x"] = "" if values.get("tax_bot_project", "").strip() else "X"
        values["tax_vat_deduction_x"] = "X" if values.get("tax_vat_method") == "Khấu trừ" else ""
        foreign_keys = (
            "location_manager_ethnicity", "location_manager_passport_number",
            "location_manager_passport_issue_date", "location_manager_passport_issue_place",
            "location_manager_foreign_address_detail", "location_manager_foreign_country",
        )
        vietnamese_only_keys = (
            "location_manager_id_number", "location_manager_address_detail",
            "location_manager_ward", "location_manager_province", "location_manager_nationality",
        )
        if values.get("location_manager_person_type") == "Người nước ngoài":
            for key in vietnamese_only_keys:
                values[key] = ""
        else:
            for key in foreign_keys:
                values[key] = ""
            values.setdefault("location_manager_nationality", "Việt Nam")
        values.setdefault("tax_labor_count", "1")
        return values

    def _missing_required_fields(self, values: dict[str, str]) -> list[str]:
        required = {
            "business_registration_office": "Phòng Đăng ký kinh doanh",
            "parent_entity_name": "Tên doanh nghiệp chủ quản",
            "parent_entity_registration_number": "Mã số doanh nghiệp/Mã số thuế",
            "location_business_name": "Tên địa điểm kinh doanh",
            "location_address_detail": "Địa chỉ chi tiết địa điểm kinh doanh",
            "location_ward": "Xã/Phường địa điểm kinh doanh",
            "location_province": "Tỉnh/Thành phố địa điểm kinh doanh",
            "location_manager_full_name": "Họ tên người đứng đầu địa điểm",
            "legal_representative_full_name": "Họ tên người đại diện pháp luật",
            "legal_representative_id_number": "Số định danh người đại diện pháp luật",
            "legal_representative_position": "Chức danh người đại diện pháp luật",
        }
        missing = [label for key, label in required.items() if not values.get(key, "").strip()]
        if values.get("location_manager_person_type") == "Người nước ngoài":
            if not values.get("location_manager_passport_number", "").strip():
                missing.append("Số hộ chiếu người đứng đầu")
        elif not values.get("location_manager_id_number", "").strip():
            missing.append("Số định danh người đứng đầu địa điểm")
        if not any(values.get(f"business_line_{index}_name", "").strip() for index in range(1, 12)):
            missing.append("Ít nhất một ngành nghề kinh doanh")
        return missing
    def _document_generator_class(self) -> type:
        return DependentUnitTemplateGenerator

    def _template_and_export_dirs(self) -> tuple[Path, Path]:
        return (
            self.bundle_root / "assets" / "templates" / "word" / Path(*LOCATION_TEMPLATE_FOLDER),
            self.selected_export_root or self.default_export_root,
        )

    def _export_case_name(self, values: dict[str, str]) -> str:
        return values.get("location_business_name", "").strip() or "ho_so_dia_diem_kinh_doanh"

    def _case_export_folder_name(self, values: dict[str, str]) -> str:
        """Keep location dossier paths short: one folder named for the company."""
        parent_name = values.get("parent_entity_name", "").strip()
        folder_name = self._safe_export_folder_name(parent_name or "ho_so_dia_diem_kinh_doanh")
        return folder_name[:120].rstrip(" .") or "ho_so_dia_diem_kinh_doanh"

    def _export_version_label(self, case_export_dir: Path) -> str:
        return "H\u1ed3 s\u01a1 hi\u1ec7n t\u1ea1i"

    def _export_output_dir(
        self,
        case_export_dir: Path,
        values: dict[str, str],
        case_name: str,
        version_name: str,
    ) -> Path:
        """Write the three Word files directly into the company folder."""
        return case_export_dir

    def _next_export_versions(
        self,
        case_export_dir: str,
        version_export_dir: str,
        exported_at: str,
        documents: list[str],
        version_name: str,
    ) -> list[dict[str, object]]:
        return [{
            "name": version_name,
            "export_dir": version_export_dir,
            "exported_at": exported_at,
            "documents": documents,
        }]

    def build_case_summary(
        self,
        status: str = "Bản nháp",
        condition: str = "Thiếu thông tin",
        warning: str | None = "Cần kiểm tra dữ liệu trước khi xuất",
        export_dir: str | None = None,
        exported_at: str | None = None,
        generated_documents: list[str] | None = None,
        export_versions: list[dict[str, object]] | None = None,
    ) -> CaseSummary:
        values = self.form_values()
        existing = self.case
        return CaseSummary(
            id=self.case_id,
            company_name=self._export_case_name(values),
            case_type=LOCATION_CASE_TYPE,
            owner=(
                values.get("signer_full_name")
                or values.get("authorized_person_full_name")
                or (existing.owner if existing else "Chưa chọn người ký")
            ),
            updated_at=datetime.now().strftime("%d/%m/%Y"),
            status=status,
            condition=condition,
            members=1,
            capital="Không áp dụng",
            warning=warning,
            export_dir=export_dir if export_dir is not None else (existing.export_dir if existing else ""),
            exported_at=exported_at if exported_at is not None else (existing.exported_at if existing else ""),
            generated_documents=generated_documents if generated_documents is not None else (existing.generated_documents if existing else []),
            export_versions=export_versions if export_versions is not None else (existing.export_versions if existing else []),
            form_values=values,
        )
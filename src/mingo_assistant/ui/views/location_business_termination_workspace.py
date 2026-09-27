"""First stage of the business-location termination dossier."""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QTextEdit, QVBoxLayout, QWidget,
)

from mingo_assistant.models.case import CaseSummary
from mingo_assistant.services.documents.location_termination_generator import LocationTerminationTemplateGenerator
from mingo_assistant.services.organization_documents.location_certificate_service import LocationCertificateService
from mingo_assistant.ui.views.location_business_workspace import LocationBusinessWorkspace


LOCATION_TERMINATION_CASE_TYPE = "Địa điểm kinh doanh - Chấm dứt hoạt động"

TERMINATION_FIELD_GROUPS = (
    ("Thông tin cơ quan tiếp nhận và thời gian ký", (
        ("business_registration_office", "Phòng Đăng ký kinh doanh"),
        ("document_place", "Nơi ký"),
        ("document_day", "Ngày ký"),
        ("document_month", "Tháng ký"),
        ("document_year", "Năm ký"),
        ("document_place_date", "Dòng địa điểm/ngày tháng"),
    )),
    ("Thông tin người đại diện pháp luật", (
        ("legal_representative_full_name", "Họ tên người đại diện pháp luật"),
        ("legal_representative_id_number", "Số định danh cá nhân"),
        ("legal_representative_permanent_address", "Địa chỉ"),
        ("legal_representative_position", "Chức danh"),
    )),
    ("Thông tin doanh nghiệp", (
        ("parent_entity_name", "Tên doanh nghiệp"),
        ("parent_entity_registration_number", "Mã số doanh nghiệp/Mã số thuế"),
        ("location_business_name", "Tên địa điểm kinh doanh"),
        ("location_business_code", "Mã số địa điểm kinh doanh"),
        ("location_full_address", "Địa chỉ địa điểm kinh doanh"),
        ("location_phone", "Điện thoại (nếu có)"),
        ("location_fax", "Số fax (nếu có)"),
        ("location_email", "Thư điện tử (nếu có)"),
        ("location_website", "Website (nếu có)"),
    )),
    ("Lý do chấm dứt hoạt động", (
        ("termination_reason", "Lý do chấm dứt hoạt động"),
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

CERTIFICATE_FIELDS = (
    ("parent_entity_name", "Tên doanh nghiệp"),
    ("parent_entity_registration_number", "Mã số thuế"),
    ("location_business_name", "Tên địa điểm kinh doanh"),
    ("location_business_code", "Mã số địa điểm kinh doanh"),
    ("location_full_address", "Địa chỉ địa điểm kinh doanh"),
    ("location_phone", "Điện thoại (nếu có)"),
    ("location_fax", "Số fax (nếu có)"),
    ("location_email", "Thư điện tử (nếu có)"),
    ("location_website", "Website (nếu có)"),
)


class LocationBusinessTerminationWorkspace(LocationBusinessWorkspace):
    """Reuse person/CCCD scanning and export the termination notice."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.organization_document_service = LocationCertificateService(
            self.address_parser, self.bundle_root
        )

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        back = QPushButton("← Quay lại")
        back.setObjectName("GhostButton")
        back.clicked.connect(self.on_back)
        titles = QVBoxLayout()
        title = QLabel("Chấm dứt hoạt động địa điểm kinh doanh")
        title.setObjectName("PageTitle")
        description = QLabel("Quét giấy chứng nhận địa điểm kinh doanh, kiểm tra thông tin và lưu nháp hồ sơ.")
        description.setObjectName("PageDescription")
        description.setWordWrap(True)
        titles.addWidget(title)
        titles.addWidget(description)
        save = QPushButton("Lưu nháp")
        save.setObjectName("GhostButton")
        save.clicked.connect(self._save_draft)
        check = QPushButton("Kiểm tra mẫu Word")
        check.setObjectName("GhostButton")
        check.clicked.connect(self._check_templates)
        export = QPushButton("Xuất hồ sơ")
        export.setObjectName("PrimaryButton")
        export.clicked.connect(self._export_documents)
        header.addWidget(back)
        header.addLayout(titles, 1)
        header.addWidget(check)
        header.addWidget(save)
        header.addWidget(export)
        return header

    def _build_organization_result_section(self) -> QWidget:
        group = QGroupBox("Thông tin giấy chứng nhận địa điểm kinh doanh nhận diện")
        group.setObjectName("CccdResultCard")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        self.organization_document_label = QLabel("Chưa tải giấy chứng nhận địa điểm kinh doanh")
        self.organization_document_label.setObjectName("FilterLabel")
        self.organization_document_label.setWordWrap(True)
        grid.addWidget(self.organization_document_label, 0, 0, 1, 4)
        # A company name can be much longer than a tax code.  Give each of
        # these identity values its own full-width row so the company name is
        # never cramped against the tax-code field.
        positions = ((1, 0, 3), (2, 0, 3), (3, 0, 3), (4, 0, 1),
                     (5, 0, 3), (6, 0, 1), (6, 2, 1), (7, 0, 1), (7, 2, 1))
        for (key, label_text), (row, column, span) in zip(CERTIFICATE_FIELDS, positions):
            label = QLabel(label_text)
            label.setObjectName("FilterLabel")
            label.setWordWrap(True)
            field = QLineEdit()
            field.setPlaceholderText(label_text)
            self.organization_card_fields[key] = field
            grid.addWidget(label, row, column)
            grid.addWidget(field, row, column + 1, 1, span)
        save = QPushButton("Lưu dữ liệu giấy chứng nhận")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self._save_organization_profile)
        grid.addWidget(save, 8, 0, 1, 4, Qt.AlignRight)
        return group

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
        for index, (title, fields) in enumerate(TERMINATION_FIELD_GROUPS):
            button = QPushButton(title)
            button.setObjectName("PrimaryButton" if index == 0 else "GhostButton")
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.setMinimumHeight(38)
            button.clicked.connect(lambda checked=False, selected=index: self._select_form_section(selected))
            self.form_button_group.addButton(button, index)
            self.form_nav_buttons[title] = button
            self.form_nav_layout.addWidget(button)
            section = QGroupBox(title)
            grid = QGridLayout(section)
            grid.setHorizontalSpacing(18)
            grid.setVerticalSpacing(10)
            grid.setColumnStretch(1, 1)
            grid.setColumnStretch(3, 1)
            target = self._person_fill_target_for_section(title)
            offset = 0
            if target and target != "company_address":
                grid.addWidget(self._build_person_fill_selector(target, title), 0, 0, 1, 4)
                offset = 1
            for field_index, (key, label_text) in enumerate(fields):
                row = offset + field_index // 2
                column = (field_index % 2) * 2
                label = QLabel(label_text)
                label.setObjectName("FilterLabel")
                grid.addWidget(label, row, column)
                grid.addWidget(self._create_field(key), row, column + 1)
            if title == "Thông tin người được ủy quyền":
                export = QPushButton("Xuất hồ sơ")
                export.setObjectName("PrimaryButton")
                export.clicked.connect(self._export_documents)
                grid.addWidget(export, offset + (len(fields) + 1) // 2, 0, 1, 4, Qt.AlignRight)
            self.form_sections[title] = section
            self.form_stack.addWidget(section)
        self.form_nav_layout.addStretch(1)
        nav.setFixedHeight(48)
        nav.setMinimumWidth(self.form_nav_layout.sizeHint().width())
        self._select_form_section(0)
        return group

    def _create_field(self, key: str):
        """Use a multi-line field for the reason stated in the notice."""
        if key != "termination_reason":
            return super()._create_field(key)
        field = QTextEdit()
        field.setFixedHeight(70)
        field.setPlaceholderText("Nhập lý do chấm dứt hoạt động")
        field.textChanged.connect(self._refresh_preview)
        self.fields[key] = field
        return field

    def _apply_organization_values_to_current_person(
        self, values: dict[str, str], raw_text: str, extraction_method: str
    ) -> None:
        # The certificate's location manager is never inferred to be the
        # legal representative or authorized person.
        super(LocationBusinessWorkspace, self)._apply_organization_values_to_current_person(
            values, raw_text, extraction_method
        )
        person = self.ocr_people[self.current_person_index]
        person.name = values.get("location_business_name") or values.get("parent_entity_name") or person.name
        self._refresh_people_buttons()
        self._set_fields_from_mapping(values)
        self._refresh_preview()

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
                self, "Chưa thể lưu giấy chứng nhận",
                "Vui lòng kiểm tra và bổ sung:\n- " + "\n- ".join(missing),
            )
            return

        self._set_fields_from_mapping(values)
        person = self.ocr_people[self.current_person_index]
        self._apply_organization_values_to_current_person(
            values, self.raw_ocr_text.toPlainText(), person.organization_extraction_method or "ocr"
        )
        saved_case = self.build_case_summary()
        try:
            self.on_save(saved_case)
        except Exception as exc:
            QMessageBox.critical(self, "Không lưu được giấy chứng nhận", str(exc))
            return
        self.case = saved_case
        self.ocr_status_label.setText("Đã lưu dữ liệu giấy chứng nhận")
        QMessageBox.information(
            self,
            "Đã lưu giấy chứng nhận",
            "Đã lưu giấy chứng nhận",
        )

    def build_case_summary(self, *args, **kwargs) -> CaseSummary:
        return replace(super().build_case_summary(*args, **kwargs), case_type=LOCATION_TERMINATION_CASE_TYPE)

    def _fill_registration_office_from_location(self) -> None:
        """The receiving office must be explicitly selected by the user."""

    def form_values(self, apply_defaults: bool = True) -> dict[str, str]:
        values = super().form_values(apply_defaults)
        address = values.get("location_full_address", "").strip()
        if address:
            values.update(LocationCertificateService(self.address_parser, self.bundle_root)._address_fields(address))
        selected = next((person for person in self.ocr_people if person.role == "legal_representative" and person.data), None)
        if selected is not None:
            name = self._normalize_person_fill_data(selected.data).get("legal_representative_full_name", "").strip()
            if name:
                values["legal_representative_full_name"] = name
                values["signer_full_name"] = name
        return values

    def _validation_issues(self, values: dict[str, str]) -> list[str]:
        required = {
            "parent_entity_name": "Tên doanh nghiệp",
            "parent_entity_registration_number": "Mã số doanh nghiệp/Mã số thuế",
            "location_business_name": "Tên địa điểm kinh doanh",
            "location_business_code": "Mã số địa điểm kinh doanh",
            "location_address_detail": "Địa chỉ chi tiết địa điểm kinh doanh",
            "location_ward": "Xã/Phường địa điểm kinh doanh",
            "location_province": "Tỉnh/Thành phố địa điểm kinh doanh",
            "termination_reason": "Lý do chấm dứt hoạt động",
            "document_day": "Ngày ký",
            "document_month": "Tháng ký",
            "document_year": "Năm ký",
            "legal_representative_full_name": "Người đại diện pháp luật ký thông báo",
            "legal_representative_id_number": "Số định danh người đại diện pháp luật",
            "legal_representative_permanent_address": "Địa chỉ người đại diện pháp luật",
            "legal_representative_position": "Chức danh người đại diện pháp luật",
            "authorized_person_full_name": "Họ tên người nhận ủy quyền",
            "authorized_person_id_number": "Số định danh người nhận ủy quyền",
            "authorized_person_phone": "Điện thoại người nhận ủy quyền",
            "authorized_person_email": "Email người nhận ủy quyền",
        }
        issues = [label for key, label in required.items() if not values.get(key, "").strip()]
        if not any(person.role == "legal_representative" for person in self.ocr_people):
            issues.append("Chọn người đại diện pháp luật từ danh sách đã quét")
        province = values.get("location_province", "").strip()
        if province and province.casefold() != "thành phố hồ chí minh":
            issues.append("Mẫu Word số 1 đang ghi sẵn cơ quan tiếp nhận và nơi ký tại Thành phố Hồ Chí Minh")
        return issues

    def _document_generator_class(self) -> type:
        return LocationTerminationTemplateGenerator

    def _template_and_export_dirs(self):
        return (
            self.bundle_root / "assets" / "templates" / "word" / "dependent_units" / "ddkd_terminate",
            self.selected_export_root or self.default_export_root,
        )

    def _check_templates(self) -> None:
        template_dir, export_root = self._template_and_export_dirs()
        generator = self._document_generator_class()(template_dir, export_root)
        try:
            issues = generator.validate_templates(self.form_values())
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi kiểm tra mẫu Word", str(exc))
            return
        if issues:
            QMessageBox.warning(self, "Mẫu Word cần kiểm tra", self._format_template_issues(issues))
        else:
            QMessageBox.information(self, "Mẫu Word hợp lệ", "Đã kiểm tra thông báo chấm dứt hoạt động và giấy ủy quyền.")

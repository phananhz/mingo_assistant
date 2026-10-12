"""Independent amendment form; scan, review, save and fill only yellow inputs."""
from __future__ import annotations

from dataclasses import replace
from copy import deepcopy
from datetime import datetime
import json
import re
from pathlib import Path
from time import monotonic
from shiboken6 import isValid

from PySide6.QtCore import Qt, QSize, QRegularExpression
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QScrollArea, QTextEdit, QVBoxLayout, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QComboBox, QTabBar, QTabWidget, QDialog,
)

from mingo_assistant.models.case import CaseSummary
from mingo_assistant.services.documents.business_amendment_fields import (
    AMENDMENT_FIELD_GROUPS, CHANGE_GROUPS, ORGANIZATION_MAPPING, REPRESENTATIVE_FIELDS, UNSUPPORTED_GROUPS,
    CAPITAL_SOURCE_LABELS, ASSET_LABELS, LINE_CAPACITIES, line_row_count, migrate_legacy_line_rows,
)
from mingo_assistant.domains.business_registration.money import VietnameseMoneyFormatter
from mingo_assistant.services.documents.business_amendment_generator import money_number, compose_share_values, inferred_change_selections
from mingo_assistant.services.documents.business_amendment_generator import BusinessAmendmentTemplateGenerator
from mingo_assistant.services.organization_documents.business_amendment_document_service import BusinessAmendmentDocumentService
from mingo_assistant.ui.views.business_registration_workspace import BusinessRegistrationWorkspace
from mingo_assistant.ui.views.location_business_update_workspace import LocationBusinessUpdateWorkspace
from mingo_assistant.ui.views.amendment_industry_table import AmendmentIndustryTable


BUSINESS_AMENDMENT_CASE_TYPE = "Doanh nghiệp - Thay đổi nội dung ĐKDN"
BUSINESS_AMENDMENT_TEMPLATE_FOLDER = "business_amendment"


class _NoWheelTabBar(QTabBar):
    """Keep the three industry tables selectable only by clicking their tabs."""

    def wheelEvent(self, event):
        event.ignore()


class BusinessAmendmentWorkspace(LocationBusinessUpdateWorkspace):
    """Reuse scanning and storage mechanics without reusing location field rules."""

    def __init__(self, *args, **kwargs):
        case = kwargs.get("case") or (args[2] if len(args) > 2 else None)
        self._legacy_values = migrate_legacy_line_rows(case.form_values) if case else {}
        self._selected_update_organization = {}
        self._scan_in_progress = False
        self._scan_token = 0
        self._representative_company_code = self._legacy_values.get("amendment_representative_company_code", "")
        super().__init__(*args, **kwargs)
        self.organization_document_service = BusinessAmendmentDocumentService(self.address_parser, self.bundle_root)

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        back = QPushButton("← Quay lại")
        back.setObjectName("GhostButton")
        back.clicked.connect(self.on_back)
        text = QVBoxLayout()
        title = QLabel("Thay đổi nội dung đăng ký doanh nghiệp")
        title.setObjectName("PageTitle")
        description = QLabel("Quét giấy đăng ký doanh nghiệp, đối chiếu dữ liệu và điền các vùng vàng trong mẫu Word.")
        description.setObjectName("PageDescription")
        description.setWordWrap(True)
        text.addWidget(title)
        text.addWidget(description)
        header.addWidget(back)
        header.addLayout(text, 1)
        for label, callback in (
            ("Kiểm tra mẫu Word", self._check_templates),
            ("Chọn nơi lưu", self._choose_export_root),
            ("Lưu nháp", self._save_draft),
            ("Xuất hồ sơ", self._export_documents),
        ):
            button = QPushButton(label)
            button.setObjectName("PrimaryButton" if label == "Xuất hồ sơ" else "GhostButton")
            button.clicked.connect(callback)
            header.addWidget(button)
        return header

    def _build_form_section(self) -> QWidget:
        group = QGroupBox("Thông tin dùng để điền vào hồ sơ")
        layout = QVBoxLayout(group)
        note = QLabel("Điền vùng vàng và fax/website bổ sung nếu có; giữ nguyên nội dung cố định của mẫu Word.")
        note.setObjectName("PageDescription")
        note.setWordWrap(True)
        layout.addWidget(note)
        nav = QWidget()
        nav.setLayout(self.form_nav_layout)
        self.form_nav_widget = nav
        scroll = QScrollArea()
        scroll.setObjectName("FormSectionNavScroll")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFixedHeight(66)
        scroll.setWidget(nav)
        layout.addWidget(scroll)
        layout.addWidget(self.form_stack)
        for index, (title, fields) in enumerate(AMENDMENT_FIELD_GROUPS):
            button = QPushButton(title)
            button.setObjectName("PrimaryButton" if index == 0 else "GhostButton")
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.clicked.connect(lambda checked=False, selected=index: self._select_form_section(selected))
            self.form_button_group.addButton(button, index)
            self.form_nav_buttons[title] = button
            self.form_nav_layout.addWidget(button)
            if index == 1:
                section = self._build_organization_section(list(fields))
            elif index == 3:
                section = self._build_change_sections_section()
            else:
                section = self._build_amendment_fields(title, fields, representative=index == 2)
            self.form_sections[title] = section
            self.form_stack.addWidget(section)
        self.form_nav_layout.addStretch(1)
        nav.setFixedHeight(48)
        nav.setMinimumWidth(self.form_nav_layout.sizeHint().width())
        self._select_form_section(0)
        return group

    def _create_field(self, key):
        # Do not attach establishment/location synchronizers to amendment inputs.
        field = QTextEdit() if key.endswith(("original_address", "contact_address", "permanent_address")) or key.endswith("_name") and key.startswith("amendment_line_") else QLineEdit()
        if isinstance(field, QTextEdit):
            field.setAcceptRichText(False)
            field.setFixedHeight(76)
        field.textChanged.connect(self._refresh_preview)
        if key in {"legal_representative_full_name", "legal_representative_id_number", "legal_representative_passport_number"}:
            field.textChanged.connect(self._clear_representative_pdf_source)
        self.fields[key] = field
        if key == "business_registration_office":
            self._setup_registration_office_field(field)
            field.textChanged.connect(self._sync_document_place_from_registration_office)
        if key == "document_place_date":
            field.setReadOnly(True)
        return field

    def _clear_representative_pdf_source(self):
        if not getattr(self, "_initializing", True):
            self._representative_company_code = ""

    def _field_value(self, key):
        match = re.fullmatch(r"amendment_line_(add|remove|detail)_(\d+)_(name|detail|code|main|note)", key)
        if match and key not in self.fields:
            kind, index, suffix = match.groups()
            table = getattr(self, "amendment_line_tables", {}).get(kind)
            if table is not None and int(index) <= table.rowCount():
                row = table.rows[int(index) - 1]
                if suffix == "name":
                    return "\n".join(part for part in (row.get("name", ""), row.get("detail", "")) if part)
                return row.get(suffix, "")
        value = super()._field_value(key)
        if key.startswith("amendment_line_") and key.endswith("_name"):
            detail = super()._field_value(key[:-5] + "_detail")
            return "\n".join(part for part in (value, detail) if part)
        return value

    def _set_field(self, key, value):
        match = re.fullmatch(r"amendment_line_(add|remove|detail)_(\d+)_(name|detail|code|main|note)", key)
        if match:
            kind, index, suffix = match.groups()
            table = getattr(self, "amendment_line_tables", {}).get(kind)
            if table is not None and int(index) <= table.rowCount():
                row = table.rows[int(index) - 1]
                if suffix == "name":
                    name, _, detail = str(value or "").partition("\n")
                    row.update(name=name, detail=detail)
                else:
                    row[suffix] = str(value or "")
                if key not in self.fields:
                    return
        if key.startswith("amendment_line_") and key.endswith("_name") and key[:-5] + "_detail" in self.fields:
            name, _, detail = str(value or "").partition("\n")
            super()._set_field(key, name)
            super()._set_field(key[:-5] + "_detail", detail)
        else:
            super()._set_field(key, value)

    def _set_fields_from_mapping(self, mapping):
        # Blank values from a newly selected certificate must clear old data.
        initializing = self._initializing
        self._initializing = True
        try:
            self._ensure_amendment_line_rows(mapping)
            for key, value in mapping.items():
                self._set_field(key, value)
        finally:
            self._initializing = initializing
        if not initializing:
            self._refresh_amendment_line_numbers()
            self._refresh_preview()

    def _build_amendment_fields(self, title, fields, representative=False, vertical=False):
        section = QGroupBox(title)
        grid = QGridLayout(section)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 0 if vertical else 1)
        if vertical:
            grid.setColumnMinimumWidth(0, 230)
        start = 0
        if representative:
            grid.addWidget(self._build_person_fill_selector("legal_representative", title), start, 0, 1, 4)
            start += 1
            note = QLabel("Word chỉ điền tên người ký ở vùng vàng cuối mẫu. Thông tin khác được lưu để đối chiếu; giám đốc trong mục thuế được nhập riêng.")
            note.setWordWrap(True)
            grid.addWidget(note, start, 0, 1, 4)
            start += 1
        for index, (key, label) in enumerate(fields):
            if key in self.fields:
                continue
            row, column = (start + index, 0) if vertical else (start + index // 2, (index % 2) * 2)
            text = QLabel(label)
            text.setWordWrap(True)
            grid.addWidget(text, row, column)
            grid.addWidget(self._create_field(key), row, column + 1, 1, 3 if vertical else 1)
        return section

    def _build_change_sections_section(self):
        section = QGroupBox("Nội dung thay đổi")
        layout = QVBoxLayout(section)
        note = QLabel("Chọn mục cần điền. Các bảng ngành nghề cho phép thêm và xóa dòng. Fax/website có thể bổ sung, không bôi vàng; để trống sẽ giữ nguyên mẫu.")
        note.setWordWrap(True)
        layout.addWidget(note)
        choices = QWidget()
        grid = QGridLayout(choices)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(28)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        self.amendment_choice_cards = {}
        self.amendment_choice_indicators = {}
        options = [(key, title, True) for key, title, _ in CHANGE_GROUPS]
        options += [(key, "Đăng ký " + explanation.split(":", 1)[0][0].lower() + explanation.split(":", 1)[0][1:], False) for key, explanation in UNSUPPORTED_GROUPS]
        for index, (key, title, enabled) in enumerate(options):
            card = QFrame()
            card.setObjectName("ChangeOptionCard")
            card.setMinimumHeight(56)
            row = QHBoxLayout(card)
            row.setContentsMargins(18, 9, 12, 9)
            checkbox = QCheckBox()
            checkbox.setAccessibleName(title)
            checkbox.setIconSize(QSize(18, 18))
            checkbox.setStyleSheet("QCheckBox { background: transparent; border: none; padding: 0; } QCheckBox::indicator { width: 0px; height: 0px; }")
            checkbox.setEnabled(enabled)
            title_label = QLabel(title)
            title_label.setWordWrap(True)
            title_label.setEnabled(enabled)
            title_label.mousePressEvent = lambda event, box=checkbox: box.click() if event.button() == Qt.LeftButton else None
            if enabled:
                title_label.setCursor(Qt.PointingHandCursor)
                card.setCursor(Qt.PointingHandCursor)
                card.mousePressEvent = lambda event, box=checkbox: box.click() if event.button() == Qt.LeftButton else None
            indicator = QLabel()
            indicator.setObjectName("ChangeOptionCompleteIndicator")
            indicator.setAlignment(Qt.AlignCenter)
            indicator.setFixedSize(26, 26)
            tick = QPixmap(22, 22)
            tick.fill(Qt.transparent)
            painter = QPainter(tick)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(QColor("white"), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawLine(4, 11, 9, 16)
            painter.drawLine(9, 16, 18, 5)
            painter.end()
            indicator.setPixmap(tick)
            indicator.setToolTip("Nội dung này đã có dữ liệu nhập.")
            indicator.setStyleSheet("background: #21874b; color: white; border: 1px solid #166534; border-radius: 4px; font-weight: bold; font-size: 18px;")
            indicator.hide()
            row.addWidget(checkbox)
            row.addWidget(title_label, 1)
            row.addWidget(indicator)
            if enabled:
                self.fields[key] = checkbox
            else:
                card.setToolTip(dict(UNSUPPORTED_GROUPS)[key])
            self.amendment_choice_cards[key] = card
            self.amendment_choice_indicators[key] = indicator
            checkbox.setIcon(self._change_option_checkbox_icon(False))
            grid.addWidget(card, index // 2, index % 2)
        layout.addWidget(choices)
        label = QLabel("Thông tin cần điền")
        label.setObjectName("FilterLabel")
        layout.addWidget(label)
        self.amendment_change_empty_label = QLabel("Chọn ít nhất một nội dung thay đổi để hiển thị form tương ứng.")
        layout.addWidget(self.amendment_change_empty_label)
        self.amendment_change_forms = {}
        for key, title, fields in CHANGE_GROUPS:
            checkbox = self.fields[key]
            # Each input has one widget across the form tabs.
            form = (
                self._build_capital_section(title) if key == "change_capital_selected"
                else self._build_amendment_lines_section(title) if key == "change_business_lines_selected"
                else self._build_tax_section() if key == "change_tax_selected"
                else self._build_beneficial_notice_section() if key == "change_beneficial_selected"
                else self._build_amendment_fields(
                    title, tuple(item for item in fields if item[0] not in self.fields),
                    vertical=key in {"change_name_selected", "change_address_selected"},
                )
            )
            form.setVisible(False)
            checkbox.toggled.connect(form.setVisible)
            checkbox.toggled.connect(self._refresh_preview)
            layout.addWidget(form)
            self.amendment_change_forms[key] = form
        self._refresh_amendment_change_choices()
        return section

    def _build_tax_section(self):
        section = QGroupBox("THÔNG BÁO THAY ĐỔI THÔNG TIN ĐĂNG KÝ THUẾ")
        layout = QVBoxLayout(section)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 18, 14, 14)
        section.setStyleSheet(
            "QFrame#TaxRegistrationCard { background: #fbfcff; border: 1px solid #b9c8dc; border-radius: 10px; }"
            "QLabel#TaxNumberBadge { background: #6f58c9; color: white; border: none; border-radius: 8px; font-weight: 700; }"
            "QLabel#TaxRowTitle { color: #243247; border: none; font-weight: 600; }"
        )
        self.tax_person_selectors = {}
        self.tax_registration_cards = []
        self.tax_registration_numbers = []

        rows = (
            ("Thông tin về Giám đốc/Tổng giám đốc (nếu có)", self._build_tax_person_panel("director")),
            ("Thông tin về Kế toán trưởng/Phụ trách kế toán (nếu có)", self._build_tax_person_panel("accountant")),
            ("Địa chỉ nhận thông báo thuế", self._build_tax_address_panel()),
            ("Ngày bắt đầu hoạt động", self._build_tax_single_field("tax_start_date", "Ngày bắt đầu hoạt động", "dd/mm/yyyy")),
            ("Hình thức hạch toán", self._build_tax_fixed_choices(("Hạch toán độc lập", "Có báo cáo tài chính hợp nhất", "Hạch toán phụ thuộc"))),
            ("Năm tài chính", self._build_tax_financial_year_panel()),
            ("Tổng số lao động", self._build_tax_single_field("tax_labor_count", "Tổng số lao động", "Chỉ nhập số")),
            ("Hoạt động theo dự án BOT/BTO/BT/BOO, BLT, BTL, O&M", self._build_tax_fixed_choices(("Có", "Không"))),
            ("Phương pháp tính thuế GTGT", self._build_tax_fixed_choices(("Khấu trừ", "Trực tiếp trên GTGT", "Trực tiếp trên doanh số", "Không phải nộp thuế GTGT"))),
        )
        for number, (heading, content) in enumerate(rows, 1):
            card = self._build_tax_row_card(number, heading, content)
            self.tax_registration_cards.append(card)
            layout.addWidget(card)
        self._refresh_tax_quick_fill_selector()
        return section

    def _build_tax_row_card(self, number, heading, content):
        card = QFrame()
        card.setObjectName("TaxRegistrationCard")
        row = QHBoxLayout(card)
        row.setContentsMargins(12, 12, 14, 12)
        row.setSpacing(14)
        badge = QLabel(str(number))
        badge.setObjectName("TaxNumberBadge")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(42, 42)
        self.tax_registration_numbers.append(badge)
        row.addWidget(badge, 0, Qt.AlignTop)
        body = QVBoxLayout()
        body.setSpacing(9)
        title = QLabel(heading)
        title.setObjectName("TaxRowTitle")
        title.setWordWrap(True)
        body.addWidget(title)
        body.addWidget(content)
        row.addLayout(body, 1)
        return card

    def _build_tax_person_panel(self, role):
        labels = (
            ("full_name", "Họ, chữ đệm và tên"),
            ("date_of_birth", "Ngày, tháng, năm sinh"),
            ("gender", "Giới tính"),
            ("id_number", "Số định danh cá nhân"),
            ("phone", "Điện thoại"),
        )
        panel = QWidget()
        grid = QGridLayout(panel)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        selector = QComboBox()
        selector.setObjectName("TaxPersonProfileSelector")
        selector.setMinimumWidth(320)
        selector.currentIndexChanged.connect(lambda _index, selected_role=role: self._apply_tax_person_quick_fill(selected_role))
        self.tax_person_selectors[role] = selector
        source_row = QHBoxLayout()
        source_row.setContentsMargins(0, 0, 0, 2)
        source_label = QLabel("Điền nhanh từ CCCD trong hồ sơ này")
        source_label.setObjectName("FilterLabel")
        source_row.addWidget(source_label)
        source_row.addWidget(selector, 1)
        grid.addLayout(source_row, 0, 0, 1, 4)
        for index, (suffix, label) in enumerate(labels):
            key = f"tax_{role}_{suffix}"
            if index == 0:
                row, pair = 1, 0
                span = 3
            else:
                row, pair = divmod(index - 1, 2)
                row += 2
                span = 1
            field = self._create_field(key)
            if suffix == "date_of_birth":
                field.setPlaceholderText("dd/mm/yyyy")
            grid.addWidget(QLabel(label), row, pair * 2)
            grid.addWidget(field, row, pair * 2 + 1, 1, span)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        return panel

    def _build_tax_address_panel(self):
        panel = QWidget()
        grid = QGridLayout(panel)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        entries = (
            ("tax_notification_address_detail", "Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố, tổ/xóm/ấp/thôn", 0, 0, 1, 3),
            ("tax_notification_ward", "Xã/Phường/Đặc khu", 1, 0, 1, 1),
            ("tax_notification_province", "Tỉnh/Thành phố", 1, 2, 1, 1),
            ("tax_notification_phone", "Điện thoại (nếu có)", 2, 0, 1, 1),
            ("tax_notification_email", "Thư điện tử (nếu có)", 3, 0, 1, 3),
        )
        for key, label, row, column, row_span, column_span in entries:
            grid.addWidget(QLabel(label), row, column)
            grid.addWidget(self._create_field(key), row, column + 1, row_span, column_span)
        fax = QLineEdit()
        fax.setReadOnly(True)
        fax.setPlaceholderText("Giữ nguyên theo mẫu Word")
        fax.setToolTip("Vùng số fax trong mẫu Word không được bôi vàng.")
        grid.addWidget(QLabel("Số fax (nếu có)"), 2, 2)
        grid.addWidget(fax, 2, 3)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        return panel

    def _build_tax_single_field(self, key, label, placeholder):
        panel = QWidget()
        row = QHBoxLayout(panel)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QLabel(label))
        field = self._create_field(key)
        field.setPlaceholderText(placeholder)
        if key == "tax_labor_count":
            field.setValidator(QRegularExpressionValidator(QRegularExpression(r"[0-9]*"), field))
        row.addWidget(field, 1)
        if key == "tax_start_date":
            quick = QPushButton("Dùng ngày hiện tại")
            quick.setObjectName("GhostButton")
            quick.clicked.connect(self._fill_tax_start_date_today)
            row.addWidget(quick)
        return panel

    def _build_tax_financial_year_panel(self):
        panel = QWidget()
        row = QHBoxLayout(panel)
        row.setContentsMargins(0, 0, 0, 0)
        for key, label in (("tax_financial_year_start", "Áp dụng từ ngày"), ("tax_financial_year_end", "Đến ngày")):
            row.addWidget(QLabel(label))
            field = self._create_field(key)
            field.setPlaceholderText("dd/mm")
            row.addWidget(field, 1)
        quick = QPushButton("Dùng 01/01 – 31/12")
        quick.setObjectName("GhostButton")
        quick.clicked.connect(self._fill_tax_standard_financial_year)
        row.addWidget(quick)
        return panel

    def _build_tax_fixed_choices(self, labels):
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        for label in labels:
            box = QCheckBox(label)
            box.setEnabled(False)
            box.setToolTip("Ô đánh dấu này không được bôi vàng trong mẫu Word nên được giữ nguyên.")
            layout.addWidget(box)
        layout.addStretch(1)
        fixed = QLabel("Giữ nguyên theo mẫu Word")
        fixed.setObjectName("FilterLabel")
        layout.addWidget(fixed)
        return panel

    def _build_beneficial_notice_section(self):
        section = QGroupBox(
            "THÔNG BÁO THAY ĐỔI THÔNG TIN VỀ CHỦ SỞ HỮU HƯỞNG LỢI CỦA DOANH NGHIỆP/"
            "THÔNG BÁO THAY ĐỔI THÔNG TIN ĐỂ XÁC ĐỊNH CHỦ SỞ HỮU HƯỞNG LỢI"
        )
        layout = QVBoxLayout(section)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 18, 14, 14)
        section.setStyleSheet(
            "QFrame#BeneficialNoticeCard { background: #fbfcff; border: 1px solid #b9c8dc; border-radius: 10px; }"
            "QLabel#BeneficialNoticeMarker { background: #6f58c9; color: white; border: none; border-radius: 8px; font-weight: 700; }"
        )
        notices = (
            (
                "a)",
                "Trường hợp doanh nghiệp có sự thay đổi thông tin về chủ sở hữu hưởng lợi của doanh nghiệp "
                "(bao gồm người quản lý doanh nghiệp) đã kê khai với Cơ quan đăng ký kinh doanh cấp tỉnh thì "
                "doanh nghiệp kê khai theo Mẫu số 10 Phụ lục I ban hành kèm theo Thông tư này:",
                "beneficial_notice_a_status",
            ),
            (
                "b)",
                "Đối với doanh nghiệp được thành lập trước ngày 01/7/2025, doanh nghiệp bổ sung thông tin về "
                "chủ sở hữu hưởng lợi của doanh nghiệp theo quy định tại khoản 1 Điều 3 Luật số 76/2025/QH15 "
                "ngày 17/6/2025 sửa đổi, bổ sung một số điều của Luật Doanh nghiệp (kê khai theo Mẫu số 10 "
                "Phụ lục I ban hành kèm theo Thông tư này):",
                "beneficial_notice_b_status",
            ),
        )
        self.beneficial_notice_selectors = {}
        for marker, content, key in notices:
            card = QFrame()
            card.setObjectName("BeneficialNoticeCard")
            row = QHBoxLayout(card)
            row.setContentsMargins(12, 12, 14, 12)
            row.setSpacing(12)
            marker_label = QLabel(marker)
            marker_label.setObjectName("BeneficialNoticeMarker")
            marker_label.setAlignment(Qt.AlignCenter)
            marker_label.setFixedSize(42, 42)
            row.addWidget(marker_label, 0, Qt.AlignTop)
            text = QLabel(content)
            text.setWordWrap(True)
            text.setTextInteractionFlags(Qt.TextSelectableByMouse)
            row.addWidget(text, 1)
            selector = QComboBox()
            selector.addItems(("Không có", "Gửi kèm"))
            selector.setCurrentIndex(0)
            selector.setMinimumWidth(150)
            selector.currentTextChanged.connect(self._refresh_preview)
            self.fields[key] = selector
            self.beneficial_notice_selectors[key] = selector
            row.addWidget(selector, 0, Qt.AlignVCenter)
            layout.addWidget(card)
        note = QLabel("Lựa chọn chỉ được ghi vào đúng vùng vàng của mẫu Word; ứng dụng không tạo tài liệu gửi kèm.")
        note.setObjectName("FilterLabel")
        note.setWordWrap(True)
        layout.addWidget(note)
        return section

    def _refresh_tax_quick_fill_selector(self):
        for selector in getattr(self, "tax_person_selectors", {}).values():
            current = selector.currentData()
            selector.blockSignals(True)
            selector.clear()
            selector.addItem("Chọn profile đã lưu", "")
            if self._field_value("legal_representative_full_name") or self._field_value("legal_representative_id_number"):
                selector.addItem("Người đại diện pháp luật hiện tại", "representative")
            for display_index, (person_index, person) in enumerate(self._unique_saved_people(), start=1):
                selector.addItem(self._person_display_name(display_index, person), f"person:{person_index}")
            if current:
                match = selector.findData(current)
                if match >= 0:
                    selector.setCurrentIndex(match)
            selector.blockSignals(False)

    def _apply_tax_person_quick_fill(self, role):
        selector = getattr(self, "tax_person_selectors", {}).get(role)
        if selector is None:
            return
        source = str(selector.currentData() or "")
        if not source:
            return
        if source == "representative":
            data = {
                "legal_representative_full_name": self._field_value("legal_representative_full_name"),
                "legal_representative_date_of_birth": self._field_value("legal_representative_date_of_birth"),
                "legal_representative_gender": self._field_value("legal_representative_gender"),
                "legal_representative_id_number": self._field_value("legal_representative_id_number"),
                "personal_phone": self._field_value("legal_representative_phone"),
            }
        else:
            try:
                person_index = int(source.split(":", 1)[1])
                person = self.ocr_people[person_index]
            except (ValueError, IndexError):
                return
            data = self._person_data_for_fill(person)
        self._set_fields_from_mapping({
            f"tax_{role}_full_name": data.get("legal_representative_full_name", ""),
            f"tax_{role}_date_of_birth": data.get("legal_representative_date_of_birth", ""),
            f"tax_{role}_gender": data.get("legal_representative_gender", ""),
            f"tax_{role}_id_number": data.get("legal_representative_id_number", ""),
            f"tax_{role}_phone": data.get("personal_phone", ""),
        })
        selector.blockSignals(True)
        selector.setCurrentIndex(0)
        selector.blockSignals(False)
        self._refresh_preview()

    def _fill_tax_start_date_today(self):
        self._set_field("tax_start_date", datetime.now().strftime("%d/%m/%Y"))
        self._refresh_preview()

    def _fill_tax_standard_financial_year(self):
        self._set_fields_from_mapping({"tax_financial_year_start": "01/01", "tax_financial_year_end": "31/12"})

    def _refresh_person_fill_selectors(self):
        super()._refresh_person_fill_selectors()
        self._refresh_tax_quick_fill_selector()

    def _capital_money_field(self, key):
        field = self._create_field(key)
        field.setValidator(QRegularExpressionValidator(QRegularExpression(r"[0-9.]*"), field))
        field.textChanged.connect(self._refresh_capital_inputs)
        return field

    def _build_amendment_lines_section(self, title):
        section = QGroupBox(title)
        layout = QVBoxLayout(section)
        self.amendment_industry_target = QComboBox(section)
        self.amendment_industry_target.hide()
        for kind, label in (("add", "Bổ sung ngành nghề"), ("remove", "Bỏ ngành nghề"), ("detail", "Sửa chi tiết ngành nghề")):
            self.amendment_industry_target.addItem(label, kind)
        self.amendment_industry_dialog = QDialog(self)
        self.amendment_industry_dialog.setModal(True)
        self.amendment_industry_dialog.resize(1100, 720)
        dialog_layout = QVBoxLayout(self.amendment_industry_dialog)
        self.amendment_industry_destination = QLabel()
        dialog_layout.addWidget(self.amendment_industry_destination)
        lookup = self._build_industry_lookup_panel()
        dialog_layout.addWidget(lookup)
        self.amendment_industry_add_button = next(button for button in lookup.findChildren(QPushButton) if button.text() == "Thêm ngành đã chọn")
        self.industry_results_table.verticalHeader().hide()
        self.industry_results_table.setStyleSheet("QTableWidget::item:selected { background: #6f58c9; color: white; }")
        self.industry_results_table.currentCellChanged.connect(lambda *_: self._show_selected_industry_detail())
        self.industry_results_table.cellDoubleClicked.connect(lambda *_: self._add_selected_industry_row())
        self.industry_results_table.setMinimumHeight(220)
        self.industry_detail.setMinimumHeight(120)
        close = QPushButton("Đóng")
        close.setObjectName("GhostButton")
        close.clicked.connect(self.amendment_industry_dialog.reject)
        dialog_layout.addWidget(close, alignment=Qt.AlignRight)
        self.amendment_line_tabs = QTabWidget()
        self.amendment_line_tabs.setTabBar(_NoWheelTabBar(self.amendment_line_tabs))
        self.amendment_line_tabs.tabBar().setUsesScrollButtons(False)
        self.amendment_line_tabs.setDocumentMode(True)
        layout.addWidget(self.amendment_line_tabs)
        self.amendment_line_tables = {}
        self.amendment_main_line_boxes = {}
        for kind, heading in (("add", "1. Bổ sung ngành, nghề kinh doanh"), ("remove", "2. Bỏ ngành, nghề kinh doanh"), ("detail", "3. Sửa đổi chi tiết ngành, nghề kinh doanh")):
            page = QWidget()
            page_layout = QVBoxLayout(page)
            actions = QHBoxLayout()
            actions.addWidget(QLabel(heading), 1)
            lookup_button = QPushButton("Tra cứu và thêm ngành")
            lookup_button.setObjectName("PrimaryButton")
            lookup_button.clicked.connect(lambda checked=False, selected=kind: self._open_amendment_industry_lookup(selected))
            actions.addWidget(lookup_button)
            button = QPushButton("+ Thêm dòng trống")
            button.setObjectName("GhostButton")
            button.clicked.connect(lambda checked=False, selected=kind: self._append_amendment_line_row(selected))
            actions.addWidget(button)
            page_layout.addLayout(actions)
            table = AmendmentIndustryTable(self, kind, "Thông tin ngành nghề")
            self.amendment_line_tables[kind] = table
            page_layout.addWidget(table, 0, Qt.AlignTop)
            page_layout.addStretch()
            self.amendment_line_tabs.addTab(page, self.amendment_industry_target.itemText(self.amendment_line_tabs.count()))
        self.amendment_line_tabs.currentChanged.connect(self.amendment_industry_target.setCurrentIndex)
        self.amendment_industry_target.currentIndexChanged.connect(self.amendment_line_tabs.setCurrentIndex)
        self.amendment_line_tabs.currentChanged.connect(self._refresh_preview)
        self.amendment_line_tabs.currentChanged.connect(self._sync_amendment_line_tab_height)
        self._sync_amendment_line_tab_height()
        return section

    def _sync_amendment_line_tab_height(self):
        tabs = getattr(self, "amendment_line_tabs", None)
        if tabs is not None and tabs.currentWidget() is not None:
            height = tabs.currentWidget().layout().sizeHint().height() + tabs.tabBar().sizeHint().height() + 12
            tabs.setFixedHeight(height)

    def _open_amendment_industry_lookup(self, kind):
        self.amendment_industry_target.setCurrentIndex(self.amendment_industry_target.findData(kind))
        destination = self.amendment_industry_target.currentText()
        self.amendment_industry_dialog.setWindowTitle("Tra cứu ngành nghề — " + destination)
        self.amendment_industry_destination.setText("Ngành đã chọn sẽ được thêm vào: " + destination)
        self.amendment_industry_add_button.setText("Thêm vào bảng: " + destination)
        self.amendment_industry_dialog.open()
        self.industry_search_input.setFocus()

    def _selected_industry_row(self):
        # Keep the current row when focus moves from the results to the add button.
        item = self.industry_results_table.item(self.industry_results_table.currentRow(), 0)
        row = item.data(Qt.UserRole) if item is not None else None
        return row if hasattr(row, "levels") and hasattr(row, "name") else None

    def _append_amendment_line_row(self, kind):
        self.amendment_line_tables[kind].append_row()

    def _warn_amendment_line_duplicate(self, kind, index):
        code = self._field_value(f"amendment_line_{kind}_{index}_code")
        if code and any(i != index and self._field_value(f"amendment_line_{kind}_{i}_code") == code for i in range(1, self.amendment_line_tables[kind].rowCount() + 1)):
            QMessageBox.warning(self, "Mã ngành nghề đã tồn tại", f"Đã có mã ngành nghề này trong bảng: {code}.")

    def _add_selected_industry_row(self):
        row = self._selected_industry_row()
        if row is None:
            QMessageBox.information(self, "Chưa chọn ngành", "Bạn cần chọn một ngành nghề trong bảng tra cứu.")
            return
        code = self._industry_row_code(row)
        kind = self.amendment_industry_target.currentData()
        table = self.amendment_line_tables[kind]
        if not code:
            QMessageBox.warning(self, "Chưa có mã ngành", "Ngành đã chọn chưa có mã ngành cấp 4.")
            return
        if any(self._field_value(f"amendment_line_{kind}_{i}_code") == code for i in range(1, table.rowCount() + 1)):
            QMessageBox.warning(self, "Mã ngành nghề đã tồn tại", f"Đã có mã ngành nghề này trong bảng: {code}.")
            return
        suffixes = ("name", "code", "note" if kind == "remove" else "main")
        index = next((i for i in range(1, table.rowCount() + 1) if not any(self._field_value(f"amendment_line_{kind}_{i}_{suffix}") for suffix in suffixes)), table.rowCount() + 1)
        if index > table.rowCount():
            self._append_amendment_line_row(kind)
        prefix = f"amendment_line_{kind}_{index}_"
        self._set_field(prefix + "name", self._industry_row_form_text(row))
        self._set_field(prefix + "code", code)
        table.show_page((index - 1) // table.PAGE_SIZE)
        if kind != "remove" and not any(self._field_value(f"amendment_line_{other_kind}_{i}_main")
                for other_kind in ("add", "detail") for i in range(1, self.amendment_line_tables[other_kind].rowCount() + 1)):
            self.fields[prefix + "main"].setChecked(True)
        self.fields["change_business_lines_selected"].setChecked(True)
        self.amendment_industry_dialog.accept()
        self.fields[prefix + "name"].setFocus()
        self._refresh_preview()

    def _delete_amendment_line_row(self, kind, index):
        table = self.amendment_line_tables[kind]
        page = table.page
        rows = [row for i, row in enumerate(table.snapshot_rows()) if i != index]
        initializing = self._initializing
        self._initializing = True
        try:
            for registry in (self.fields, self.amendment_main_line_boxes, self._legacy_values):
                for key in list(registry):
                    if key.startswith(f"amendment_line_{kind}_"):
                        registry.pop(key)
            table.clear_rows()
            for row, values in enumerate(rows):
                self._append_amendment_line_row(kind)
                for suffix, value in values.items():
                    self._set_field(f"amendment_line_{kind}_{row + 1}_{suffix}", value)
            table.page = min(page, max(0, (table.rowCount() - 1) // table.PAGE_SIZE))
        finally:
            self._initializing = initializing
        if not initializing:
            self._refresh_amendment_line_numbers()
            self._refresh_preview()

    def _confirm_delete_amendment_line_row(self, kind, index):
        """Require confirmation only when the clicked card contains input."""
        table = self.amendment_line_tables[kind]
        rows = table.snapshot_rows()
        if not 0 <= index < len(rows):
            return
        suffixes = ("name", "detail", "code", "note" if kind == "remove" else "main")
        has_data = any(str(rows[index].get(suffix, "")).strip() for suffix in suffixes)
        if has_data:
            answer = QMessageBox.question(
                self,
                "Xác nhận xóa ngành nghề",
                f"Dòng {index + 1} đang có thông tin. Bạn có chắc muốn xóa dòng này không?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        self._delete_amendment_line_row(kind, index)

    def _ensure_amendment_line_rows(self, values):
        for kind, table in getattr(self, "amendment_line_tables", {}).items():
            if not any(key.startswith(f"amendment_line_{kind}_") for key in values):
                continue
            count = line_row_count(values, kind)
            table.resize_rows(count)

    def _select_amendment_main_line(self, key, checked):
        if checked and not getattr(self, "_initializing", True):
            self._initializing = True
            try:
                for kind in ("add", "detail"):
                    table = self.amendment_line_tables[kind]
                    table.snapshot_rows()
                    for index in range(1, table.rowCount() + 1):
                        other_key = f"amendment_line_{kind}_{index}_main"
                        if other_key != key:
                            self._set_field(other_key, "")
            finally:
                self._initializing = False
        self._refresh_preview()

    def _refresh_amendment_line_numbers(self):
        for kind, table in getattr(self, "amendment_line_tables", {}).items():
            table.refresh_page()
            table.snapshot_rows()
            number = 0
            labels = dict(zip(table.visible_indices, table.number_labels))
            for index, row in enumerate(table.rows, 1):
                populated = bool(row.get("name", "") or row.get("detail", ""))
                number += int(populated)
                if index in labels:
                    labels[index].setText(str(number) if populated else "")

    def _build_share_section(self, title):
        section = QGroupBox(title)
        layout = QVBoxLayout(section)
        layout.addWidget(QLabel("Thông tin về cổ phần (chỉ kê khai đối với công ty cổ phần):"))
        layout.addWidget(QLabel("Mệnh giá cổ phần (VNĐ)"))
        par = self._create_field("new_share_par_value")
        par.setValidator(QRegularExpressionValidator(QRegularExpression(r"[0-9.]*"), par))
        par.textChanged.connect(self._refresh_share_inputs)
        layout.addWidget(par)
        note = QLabel("Nhập số lượng, giá trị và tỷ lệ cho từng loại cổ phần. Dòng Tổng số tự cộng các hàng đã nhập.")
        note.setWordWrap(True)
        layout.addWidget(note)
        table = QTableWidget(6, 5)
        self.amendment_share_table = table
        table.setHorizontalHeaderLabels(["STT", "Loại cổ phần", "Số lượng", "Giá trị (bằng số, VNĐ)", "Tỷ lệ so với vốn\nđiều lệ (%)"])
        table.verticalHeader().hide()
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        table.setColumnWidth(0, 55)
        table.horizontalHeader().setFixedHeight(70)
        table.setStyleSheet("QTableWidget { gridline-color: #879bb5; border: 1px solid #879bb5; } QHeaderView::section { padding: 8px; border: 1px solid #879bb5; }")
        labels = ("Cổ phần phổ thông", "Cổ phần ưu đãi biểu quyết", "Cổ phần ưu đãi cổ tức", "Cổ phần ưu đãi hoàn lại", "Các cổ phần ưu đãi khác")
        for row, label in enumerate(labels):
            table.setRowHeight(row, 68)
            table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            table.setItem(row, 1, QTableWidgetItem(label))
            for column, suffix in enumerate(("count", "amount", "ratio"), 2):
                field = self._create_field(f"amendment_share_{row + 1}_{suffix}")
                pattern = r"[0-9.,]*" if suffix == "ratio" else r"[0-9.]*"
                field.setValidator(QRegularExpressionValidator(QRegularExpression(pattern), field))
                field.setAccessibleName(f"{label} — {table.horizontalHeaderItem(column).text()}")
                field.textChanged.connect(self._refresh_share_inputs)
                table.setCellWidget(row, column, field)
        table.setSpan(5, 0, 1, 2)
        table.setItem(5, 0, QTableWidgetItem("Tổng số"))
        table.setRowHeight(5, 68)
        for column in range(2, 5):
            table.setItem(5, column, QTableWidgetItem(""))
        table.setFixedHeight(70 + 6 * 68 + 4)
        layout.addWidget(table)
        return section

    def _refresh_share_inputs(self):
        table = getattr(self, "amendment_share_table", None)
        if table is None:
            return
        formatter = VietnameseMoneyFormatter()
        keys = ["new_share_par_value"] + [f"amendment_share_{i}_{suffix}" for i in range(1, 6) for suffix in ("count", "amount")]
        for key in keys:
            field = self.fields.get(key)
            if field is None or not field.text():
                continue
            raw = field.text().replace(".", "")
            if not raw.isdigit():
                continue
            formatted = formatter.format_digits(raw)
            if formatted != field.text():
                right_digits = sum(c.isdigit() for c in field.text()[field.cursorPosition():])
                field.blockSignals(True)
                field.setText(formatted)
                position = len(formatted)
                while position and right_digits:
                    position -= 1
                    right_digits -= int(formatted[position].isdigit())
                field.setCursorPosition(position)
                field.blockSignals(False)
        values = {key: self._field_value(key) for key in self.fields if key.startswith("amendment_share_")}
        try:
            totals = compose_share_values(values)
        except ValueError:
            totals = {}
        for column, suffix in enumerate(("count", "amount", "ratio"), 2):
            table.item(5, column).setText(totals.get(f"amendment_share_total_{suffix}", ""))

    def _build_capital_section(self, title):
        section = QGroupBox(title)
        layout = QVBoxLayout(section)
        for key, label in (("registered_capital", "Vốn điều lệ đã đăng ký (bằng số, VNĐ)"),
                           ("new_capital", "Vốn điều lệ sau thay đổi (bằng số, VNĐ)")):
            layout.addWidget(QLabel(label))
            layout.addWidget(self._capital_money_field(key))
            preview = self._create_field(key + "_text")
            preview.setReadOnly(True)
            preview.setPlaceholderText("Tự động hiển thị số tiền VNĐ và bằng chữ")
            layout.addWidget(preview)
        layout.addWidget(QLabel("Giá trị tương đương theo đơn vị tiền tệ nước ngoài (nếu có)"))
        layout.addWidget(self._create_field("capital_foreign_equivalent"))
        question = QLabel("Có hiển thị thông tin về giá trị tương đương theo đơn vị tiền tệ nước ngoài trên Giấy chứng nhận đăng ký doanh nghiệp hay không?")
        question.setWordWrap(True)
        layout.addWidget(question)
        choices = QHBoxLayout()
        for key, label in (("capital_foreign_yes_checked", "Có"), ("capital_foreign_no_checked", "Không")):
            box = QCheckBox(label)
            self.fields[key] = box
            choices.addWidget(box)
        choices.addStretch()
        layout.addLayout(choices)
        note = QLabel("Ô Có/Không hiện chỉ để chọn trên màn hình, chưa áp dụng vào Word.")
        note.setWordWrap(True)
        layout.addWidget(note)
        for key, label in (("capital_change_date", "Thời điểm thay đổi vốn"), ("capital_change_method", "Hình thức tăng, giảm vốn")):
            layout.addWidget(QLabel(label))
            layout.addWidget(self._create_field(key))
        self.amendment_capital_tables = {}
        for kind, title, labels, active in (
            ("source", "Nguồn vốn điều lệ sau khi thay đổi vốn điều lệ:", CAPITAL_SOURCE_LABELS, 2),
            ("asset", "Tài sản góp vốn sau khi thay đổi vốn điều lệ:", ASSET_LABELS, 1),
        ):
            layout.addWidget(QLabel(title))
            numbered = kind == "asset"
            table = QTableWidget(len(labels) + 1, 4 if numbered else 3)
            table.setHorizontalHeaderLabels((["STT"] if numbered else []) + ["Tài sản góp vốn" if numbered else "Loại nguồn vốn", "Giá trị vốn của từng tài sản\ntrong vốn điều lệ (bằng số, VNĐ)" if numbered else "Số tiền (bằng số; VNĐ) và giá trị tương đương\ntheo đơn vị tiền tệ nước ngoài, nếu có", "Tỷ lệ (%)"])
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.setSelectionMode(QAbstractItemView.NoSelection)
            table.verticalHeader().hide()
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            if numbered:
                table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(table.columnCount() - 1, QHeaderView.Fixed)
            table.setColumnWidth(table.columnCount() - 1, 120)
            table.horizontalHeader().setFixedHeight(70)
            table.setStyleSheet("QTableWidget { gridline-color: #879bb5; border: 1px solid #879bb5; } QHeaderView::section { padding: 10px; border: 1px solid #879bb5; }")
            for row, label in enumerate((*labels, "Tổng số" if numbered else "Tổng cộng")):
                table.setRowHeight(row, 68)
                if numbered and row == 1:
                    label = "Ngoại tệ tự do chuyển đổi (ghi rõ loại ngoại tệ, số tiền được góp bằng mỗi loại ngoại tệ)"
                elif numbered and row == 5:
                    label = "Các tài sản khác (ghi rõ loại tài sản, số lượng và giá trị còn lại của mỗi loại tài sản, có thể lập thành danh mục riêng kèm theo hồ sơ đăng ký doanh nghiệp)"
                if numbered:
                    table.setItem(row, 0, QTableWidgetItem(str(row + 1) if row < len(labels) else ""))
                table.setItem(row, int(numbered), QTableWidgetItem(label))
                amount_column = int(numbered) + 1
                if row + 1 == active:
                    amount = self._capital_money_field(f"amendment_{kind}_{active}_amount")
                    amount.setReadOnly(True)
                    amount.setPlaceholderText("Tự động lấy từ vốn điều lệ sau thay đổi")
                    amount.setStyleSheet("QLineEdit { background: #f8fafc; border: 1px solid #879bb5; padding: 8px; }")
                    table.setCellWidget(row, amount_column, amount)
                else:
                    table.setItem(row, amount_column, QTableWidgetItem("" if row == len(labels) else "0"))
                table.setItem(row, amount_column + 1, QTableWidgetItem("100%" if row + 1 == active or row == len(labels) else "0"))
            table.setFixedHeight(68 * (len(labels) + 1) + 72)
            self.amendment_capital_tables[kind] = table
            layout.addWidget(table)
        layout.addWidget(self._build_share_section("Thông tin về cổ phần (chỉ kê khai đối với công ty cổ phần)"))
        return section

    def _refresh_capital_inputs(self):
        formatter = VietnameseMoneyFormatter()
        for key in ("registered_capital", "new_capital", "amendment_source_2_amount", "amendment_asset_1_amount"):
            field = self.fields.get(key)
            if field is None:
                continue
            text = field.text().strip()
            try:
                number = money_number(text.replace(".", "")) if text else None
            except ValueError:
                number = None
            formatted = formatter.format_digits(str(number)) if number is not None else text
            if formatted != field.text():
                right_digits = sum(c.isdigit() for c in field.text()[field.cursorPosition():])
                field.blockSignals(True)
                field.setText(formatted)
                position = len(formatted)
                while position and right_digits:
                    position -= 1
                    right_digits -= int(formatted[position].isdigit())
                field.setCursorPosition(position)
                field.blockSignals(False)
            preview = self.fields.get(key + "_text")
            if preview is not None:
                value = f"{formatted} VNĐ ({formatter.to_words(number).capitalize()} đồng)" if number is not None else ""
                preview.blockSignals(True)
                preview.setText(value)
                preview.blockSignals(False)
        # Both reviewed template tables describe the full new charter capital:
        # private capital is 100% of the source and VND is 100% of the asset.
        new_capital = self._field_value("new_capital")
        for key in ("amendment_source_2_amount", "amendment_asset_1_amount"):
            field = self.fields.get(key)
            if field is not None and field.text() != new_capital:
                field.blockSignals(True)
                field.setText(new_capital)
                field.blockSignals(False)
        for kind, table in getattr(self, "amendment_capital_tables", {}).items():
            active = 2 if kind == "source" else 1
            table.item(table.rowCount() - 1, 2 if kind == "asset" else 1).setText(self._field_value(f"amendment_{kind}_{active}_amount"))

    def _refresh_amendment_change_choices(self):
        groups = {key: fields for key, _, fields in CHANGE_GROUPS}
        for key, card in self.amendment_choice_cards.items():
            checkbox = self.fields.get(key)
            checked = isinstance(checkbox, QCheckBox) and checkbox.isChecked()
            # Current registered capital is not newly entered change content.
            entered = any(self._field_value(field).strip() for field, _ in groups.get(key, ())
                          if field not in {"capital_foreign_yes_checked", "capital_foreign_no_checked"})
            if key == "change_business_lines_selected":
                entered = any(self._field_value(field).strip() for field in self.fields if field.startswith("amendment_line_"))
            if key == "change_beneficial_selected" and not checked:
                entered = False
            self.amendment_choice_indicators[key].setVisible(entered)
            if isinstance(checkbox, QCheckBox):
                checkbox.setIcon(self._change_option_checkbox_icon(checked))
            color, background = ("#21874b", "#edfdf5") if checked and entered else ("#6f58c9", "#f0edff") if checked else ("#879bb5", "#f8fafc")
            card.setStyleSheet(f"QFrame#ChangeOptionCard {{ background: {background}; border: 2px solid {color}; border-radius: 9px; }}")
        self.amendment_change_empty_label.setVisible(not any(self.fields[key].isChecked() for key in groups))

    def _build_organization_result_section(self):
        group = QGroupBox("Thông tin tổ chức nhận diện")
        grid = QGridLayout(group)
        self.organization_document_label = QLabel("Chưa có tài liệu tổ chức")
        grid.addWidget(self.organization_document_label, 0, 0, 1, 2)
        for row, (key, label) in enumerate((
            ("organization_owner_name", "Tên doanh nghiệp"),
            ("organization_owner_registration_number", "Mã số doanh nghiệp/Mã số thuế"),
        ), 1):
            grid.addWidget(QLabel(label), row, 0)
            field = QLineEdit()
            self.organization_card_fields[key] = field
            grid.addWidget(field, row, 1)
        grid.setColumnStretch(1, 1)
        row = 3
        self.organization_review_notice = QLabel("Đối chiếu tên và mã số doanh nghiệp với PDF trước khi áp dụng vào hồ sơ.")
        self.organization_review_notice.setWordWrap(True)
        grid.addWidget(self.organization_review_notice, row, 0, 1, 2)
        self.organization_review_checkbox = QCheckBox("Đã kiểm tra thông tin tổ chức")
        grid.addWidget(self.organization_review_checkbox, row + 1, 0, 1, 2)
        self.organization_review_checkbox.toggled.connect(self._refresh_preview)
        save = QPushButton("Lưu dữ liệu tổ chức")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self._save_organization_profile)
        grid.addWidget(save, row + 2, 0, 1, 2, Qt.AlignRight)
        for field in self.organization_card_fields.values():
            field.textChanged.connect(lambda: self.organization_review_checkbox.setChecked(False))
        return group

    def _organization_result_values(self):
        values = super()._organization_result_values()
        person = self.ocr_people[self.current_person_index] if self.ocr_people else None
        if person:
            for key, value in person.organization_data.items():
                if key.startswith("amendment_"):
                    values.setdefault(key, value)
        values["amendment_recognition_confirmed"] = "1" if self.organization_review_checkbox.isChecked() else ""
        return values

    def _update_organization_result_fields(self, values):
        super()._update_organization_result_fields(values)
        self.organization_review_checkbox.blockSignals(True)
        self.organization_review_checkbox.setChecked(values.get("amendment_recognition_confirmed") == "1")
        self.organization_review_checkbox.blockSignals(False)
        self.organization_review_notice.setText(values.get("amendment_recognition_warnings") or "Đối chiếu PDF và sửa dữ liệu trước khi áp dụng vào hồ sơ.")

    def _apply_organization_values_to_current_person(self, values, raw_text, extraction_method):
        BusinessRegistrationWorkspace._apply_organization_values_to_current_person(self, dict(values), raw_text, extraction_method)
        self._refresh_update_organization_selector()

    def _fill_update_organization_from_selector(self):
        selected_source = str(self.update_organization_selector.currentData() or "")
        values = next((dict(data) for source, data in self._organization_sources() if source == selected_source), {})
        if not values:
            return
        self._selected_update_organization = {key: value for key, value in values.items()
                                              if key in BusinessAmendmentDocumentService.RECOGNIZED_FIELDS or key.startswith("amendment_")}
        self._set_fields_from_mapping({target: values.get(source, "") for target, source in ORGANIZATION_MAPPING.items()
                                       if source in BusinessAmendmentDocumentService.RECOGNIZED_FIELDS})
        self._refresh_preview()

    def _save_organization_profile(self):
        values = self._organization_result_values()
        if not all(values.get(key, "").strip() for key in BusinessAmendmentDocumentService.RECOGNIZED_FIELDS):
            QMessageBox.warning(self, "Cần kiểm tra dữ liệu", "Cần tên doanh nghiệp và mã số doanh nghiệp/mã số thuế.")
            return
        if values.get("amendment_recognition_confirmed") != "1":
            QMessageBox.warning(self, "Cần đối chiếu PDF", "Kiểm tra, sửa dữ liệu và tích xác nhận đối chiếu trước khi áp dụng.")
            return
        code = values["organization_owner_registration_number"]
        self.organization_profiles = [dict(profile) for profile in self.organization_profiles if profile.get("organization_owner_registration_number") != code]
        self.organization_profiles.append(dict(values))
        self._apply_organization_values_to_current_person(values, self.raw_ocr_text.toPlainText(), "reviewed")
        self._selected_update_organization = dict(values)
        self._set_fields_from_mapping({target: values.get(source, "") for target, source in ORGANIZATION_MAPPING.items()
                                       if source in BusinessAmendmentDocumentService.RECOGNIZED_FIELDS})
        self._refresh_preview()
        QMessageBox.information(self, "Đã lưu dữ liệu tổ chức", "Đã lưu dữ liệu đã đối chiếu vào hồ sơ này và điền thông tin doanh nghiệp hiện tại.")

    def _fill_representative_from_pdf(self):
        values = self._selected_update_organization
        if not values.get("legal_representative_full_name"):
            QMessageBox.warning(self, "Chưa có người đại diện", "Chọn doanh nghiệp có dữ liệu người đại diện hoặc nhập tay/chọn người đã quét.")
            return
        self._set_fields_from_mapping({key: values.get(key, "") for key, _ in REPRESENTATIVE_FIELDS})
        self._representative_company_code = values.get("organization_owner_registration_number", "")
        self._refresh_preview()

    def _fill_section_from_person(self, target, person):
        if target != "legal_representative":
            return super()._fill_section_from_person(target, person)
        data = self._person_data_for_fill(person)
        self._set_fields_from_mapping({key: data.get(key, "") for key, _ in REPRESENTATIVE_FIELDS})
        self._representative_company_code = ""
        self._refresh_preview()

    def _scan_organization_document(self, path):
        if self._scan_in_progress:
            return
        self._scan_in_progress = True
        self._scan_token += 1
        token, person, case_id = self._scan_token, self.ocr_people[self.current_person_index], self.case_id
        start = monotonic()
        self.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = self.organization_document_service.extract_pdf(path, lambda percent, status: self._update_ocr_progress(percent, status, self._format_elapsed(start)) if isValid(self) else None)
        except Exception as exc:
            if isValid(self):
                QMessageBox.critical(self, "Không thể đọc tài liệu", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
            if isValid(self):
                self.setEnabled(True)
            self._scan_in_progress = False
        if not isValid(self):
            return
        if token != self._scan_token or case_id != self.case_id or person is not self.ocr_people[self.current_person_index]:
            return
        if hasattr(self.window(), "current_workspace") and self.window().current_workspace is not self:
            return
        values = dict(result.values)
        values.update({"amendment_recognition_confirmed": "", "amendment_recognition_warnings": "\n".join(result.warnings),
                       "amendment_recognition_sources": json.dumps(result.field_sources, ensure_ascii=False),
                       "amendment_recognition_route": ", ".join(result.processing_route), "amendment_source_pdf": str(path)})
        self._apply_organization_values_to_current_person(values, result.raw_text, result.extraction_method)
        self._update_organization_result_fields(values)
        self.raw_ocr_text.setPlainText(result.raw_text)
        self.organization_document_label.setText(f"Tài liệu: {Path(path).name} — cần đối chiếu dữ liệu nhận diện")
        self.recognition_result_stack.setCurrentIndex(1)
        self._update_ocr_progress(100, "Đã nhận diện — cần đối chiếu PDF", self._format_elapsed(start))

    def _choose_company_document(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn giấy đăng ký doanh nghiệp", "", "Tài liệu PDF (*.pdf)")
        if path:
            self._scan_organization_document(path)

    def _seed_from_case(self, case):
        today = datetime.now()
        values = {"document_day": f"{today.day:02d}", "document_month": f"{today.month:02d}", "document_year": str(today.year)}
        if case:
            values.update({"parent_entity_name": case.company_name, "legal_representative_full_name": case.owner})
            values.update(self._legacy_values)
            if values.get("amendment_schema_version") not in {"3", "4"} and values.get("change_shares_selected", "").lower() in {"1", "x", "true", "yes", "có"}:
                values["change_capital_selected"] = "X"
            for selection in inferred_change_selections(values):
                values[selection] = "X"
        self._ensure_amendment_line_rows(values)
        for key, value in values.items():
            self._set_field(key, value)
        self._refresh_capital_inputs()
        self._refresh_share_inputs()
        self._refresh_amendment_line_numbers()
        if not self._field_value("document_place"):
            self._sync_document_place_from_registration_office()
        self._restore_people(values)
        try:
            restored = json.loads(values.get("amendment_selected_organization", "{}"))
            self._selected_update_organization = dict(restored) if isinstance(restored, dict) else {}
        except (ValueError, TypeError):
            self._selected_update_organization = {}
        self._refresh_update_organization_selector()
        for key, form in self.amendment_change_forms.items():
            form.setVisible(self.fields[key].isChecked())

    def form_values(self, apply_defaults=True):
        values = dict(self._legacy_values)
        values.update({key: self._field_value(key) for key in self.fields})
        for kind, table in self.amendment_line_tables.items():
            prefix = f"amendment_line_{kind}_"
            for key in list(values):
                if key.startswith(prefix):
                    values.pop(key)
            for index, row in enumerate(table.snapshot_rows(), 1):
                for suffix, value in row.items():
                    values[f"{prefix}{index}_{suffix}"] = value
                values[f"{prefix}{index}_name"] = "\n".join(part for part in (row.get("name", ""), row.get("detail", "")) if part)
            values[f"amendment_line_{kind}_row_count"] = str(table.rowCount())
        self._store_people_values(values)
        values.pop("change_shares_selected", None)
        values["amendment_schema_version"] = "4"
        values["company_name"] = values.get("parent_entity_name", "")
        values["signer_full_name"] = values.get("legal_representative_full_name", "")
        values["amendment_representative_company_code"] = self._representative_company_code
        values["amendment_selected_organization"] = json.dumps(self._selected_update_organization, ensure_ascii=False)
        values["document_place_date"] = f"{values.get('document_place', '')}, ngày {values.get('document_day', '')} tháng {values.get('document_month', '')} năm {values.get('document_year', '')}".lstrip(", ")
        return values

    def _refresh_preview(self):
        if getattr(self, "_initializing", True):
            return
        self._sync_amendment_line_tab_height()
        self._refresh_amendment_change_choices()
        values = self.form_values()
        self._set_field("document_place_date", values["document_place_date"])
        self._sync_form_stack_height()

    def _missing_required_fields(self, values: dict[str, str]) -> list[str]:
        issues = BusinessAmendmentTemplateGenerator.validation_issues(values)
        if self._selected_update_organization and self._selected_update_organization.get("amendment_recognition_confirmed") != "1":
            issues.append("Dữ liệu doanh nghiệp từ PDF chưa được xác nhận đối chiếu")
        if self._representative_company_code and self._representative_company_code != values.get("parent_entity_registration_number"):
            issues.append("Người đại diện lấy từ PDF của doanh nghiệp khác; cần chọn lại")
        return issues

    def _document_generator_class(self) -> type:
        return BusinessAmendmentTemplateGenerator

    def _template_and_export_dirs(self) -> tuple[Path, Path]:
        return (
            self.bundle_root / "assets" / "templates" / "word" / BUSINESS_AMENDMENT_TEMPLATE_FOLDER,
            self.selected_export_root or self.default_export_root,
        )

    def _export_case_name(self, values: dict[str, str]) -> str:
        return values.get("parent_entity_name", "").strip() or "Hồ sơ thay đổi ĐKDN"

    def _case_export_folder_name(self, values: dict[str, str]) -> str:
        name = self._safe_export_folder_name(f"Thay đổi ĐKDN_{self._export_case_name(values)}")[:85].rstrip(" .")
        return f"{name}_{self.case_id}"

    def _check_templates(self) -> None:
        template_dir, export_root = self._template_and_export_dirs()
        issues = BusinessAmendmentTemplateGenerator(template_dir, export_root).validate_templates(self.form_values())
        if issues:
            QMessageBox.warning(self, "Mẫu Word cần kiểm tra", self._format_template_issues(issues))
        else:
            QMessageBox.information(self, "Mẫu Word hợp lệ", "Đã kiểm tra phiên bản mẫu và các vị trí được phép điền màu vàng.")

    def build_case_summary(self, *args, **kwargs) -> CaseSummary:
        case = super().build_case_summary(*args, **kwargs)
        return replace(
            case,
            case_type=BUSINESS_AMENDMENT_CASE_TYPE,
            owner=self._field_value("legal_representative_full_name") or "Chưa chọn người ký",
            capital=self._field_value("registered_capital"),
            condition="Thiếu thông tin" if self._missing_required_fields(self.form_values()) else "Đã nhập thông tin",
            warning="Cần đối chiếu Word",
            generated_documents=list(case.generated_documents),
            export_versions=deepcopy(case.export_versions),
        )

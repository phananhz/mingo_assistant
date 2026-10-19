"""Independent amendment form; scan, review, save and fill only yellow inputs."""
from __future__ import annotations

from dataclasses import replace
from copy import deepcopy
import re
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QScrollArea, QTextEdit, QVBoxLayout, QWidget,
    QComboBox, QTabBar, QTabWidget, QDialog,
)

from mingo_assistant.domains.business_amendment import (
    migrate_business_amendment_form_values,
)
from mingo_assistant.models.case import CaseSummary
from mingo_assistant.services.documents.business_amendment_fields import (
    AMENDMENT_FIELD_GROUPS, CHANGE_GROUPS, UNSUPPORTED_GROUPS,
    line_row_count,
)
from mingo_assistant.services.documents.business_amendment_generator import (
    BusinessAmendmentTemplateGenerator,
    change_section_has_data,
)
from mingo_assistant.services.organization_documents.business_amendment_document_service import BusinessAmendmentDocumentService
from mingo_assistant.services.business_lines.legacy_industry_lookup import load_legacy_industry_catalog
from mingo_assistant.services.registration_offices import update_saved_registration_values
from mingo_assistant.ui.views.location_business_update_workspace import LocationBusinessUpdateWorkspace
from mingo_assistant.ui.views.amendment_industry_table import AmendmentIndustryTable
from mingo_assistant.ui.views.business_amendment_capital_section import AmendmentCapitalSection
from mingo_assistant.ui.views.business_amendment_form_state import AmendmentFormState
from mingo_assistant.ui.views.business_amendment_organization_controller import AmendmentOrganizationController
from mingo_assistant.ui.views.business_amendment_tax_section import AmendmentTaxSection


BUSINESS_AMENDMENT_CASE_TYPE = "Doanh nghiệp - Thay đổi nội dung ĐKDN"
BUSINESS_AMENDMENT_TEMPLATE_FOLDER = "business_amendment"


class _NoWheelTabBar(QTabBar):
    """Keep the three industry tables selectable only by clicking their tabs."""

    def wheelEvent(self, event):
        event.ignore()


class BusinessAmendmentWorkspace(LocationBusinessUpdateWorkspace):
    """Reuse scanning and storage mechanics without reusing location field rules."""

    FORM_SCHEMA_VERSION = int(AmendmentFormState.SCHEMA_VERSION)

    def __init__(self, *args, **kwargs):
        legacy_industry_catalog = kwargs.pop("legacy_industry_catalog", None)
        case = kwargs.get("case") or (args[2] if len(args) > 2 else None)
        self._legacy_values = (
            update_saved_registration_values(
                migrate_business_amendment_form_values(
                    case.form_values,
                    from_version=case.form_schema_version,
                )
            )
            if case
            else {}
        )
        self._selected_update_organization = {}
        self._scan_in_progress = False
        self._scan_token = 0
        self._representative_company_code = self._legacy_values.get("amendment_representative_company_code", "")
        self.capital_section = AmendmentCapitalSection(self)
        self.form_state = AmendmentFormState(self)
        self.organization_controller = AmendmentOrganizationController(self)
        self.tax_section = AmendmentTaxSection(self)
        super().__init__(*args, **kwargs)
        self.legacy_industry_catalog = legacy_industry_catalog or load_legacy_industry_catalog(self.bundle_root)
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
        return self.tax_section.build()

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
        self.tax_section.refresh_quick_fill_selector()

    def _apply_tax_person_quick_fill(self, role):
        self.tax_section.apply_person_quick_fill(role)

    def _fill_tax_start_date_today(self):
        self.tax_section.fill_start_date_today()

    def _fill_tax_standard_financial_year(self):
        self.tax_section.fill_standard_financial_year()

    def _refresh_person_fill_selectors(self):
        super()._refresh_person_fill_selectors()
        self._refresh_tax_quick_fill_selector()

    def _capital_money_field(self, key):
        return self.capital_section.money_field(key)

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
        uses_legacy_catalog = kind == "remove"
        self.amendment_industry_dialog.setWindowTitle(
            ("Tra cứu ngành nghề kinh doanh cũ — " if uses_legacy_catalog else "Tra cứu ngành nghề — ")
            + destination
        )
        self.industry_lookup_source.setText(
            (
                '<a href="https://vanban.chinhphu.vn/?docid=194154&pageid=27160">'
                "Nguồn chính thức: Quyết định 27/2018/QĐ-TTg - Cổng Thông tin điện tử Chính phủ</a>"
            )
            if uses_legacy_catalog
            else (
                '<a href="https://vanban.chinhphu.vn/?classid=1&docid=215475&pageid=27160">'
                "Nguồn chính thức: Quyết định 36/2025/QĐ-TTg - Cổng Thông tin điện tử Chính phủ</a>"
            )
        )
        self.industry_search_input.setPlaceholderText(
            "Nhập mã ngành cấp 4 hoặc tên ngành cũ để tìm kiếm..."
            if uses_legacy_catalog
            else "Nhập mã ngành, tên ngành hoặc từ khóa hoạt động"
        )
        self._refresh_industry_results()
        self.amendment_industry_destination.setText("Ngành đã chọn sẽ được thêm vào: " + destination)
        self.amendment_industry_add_button.setText("Thêm vào bảng: " + destination)
        self.amendment_industry_dialog.open()
        self.industry_search_input.setFocus()

    def _industry_lookup_catalog(self):
        """VSIC 2018 is permitted only for the remove-industry amendment table."""
        target = getattr(self, "amendment_industry_target", None)
        if target is not None and target.currentData() == "remove":
            return self.legacy_industry_catalog
        return self.industry_catalog

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
        workspace_scroll = self.findChild(QScrollArea, "BusinessWorkspaceScroll")
        scroll_position = (
            workspace_scroll.verticalScrollBar().value()
            if workspace_scroll is not None
            else None
        )
        focused_widget = QApplication.focusWidget()
        if focused_widget is not None and table.isAncestorOf(focused_widget):
            # The clicked delete button is about to be destroyed.  Leaving it
            # focused makes QScrollArea reveal the next focus target, which is
            # usually near the top of this long form.
            focused_widget.clearFocus()
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
        if workspace_scroll is not None and scroll_position is not None:
            def restore_scroll_position():
                bar = workspace_scroll.verticalScrollBar()
                bar.setValue(min(scroll_position, bar.maximum()))

            # Restore once after the synchronous layout update and once after
            # Qt has processed deleteLater()/focus/layout events from rebuilt
            # row widgets.
            restore_scroll_position()
            QTimer.singleShot(0, restore_scroll_position)

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
        return self.capital_section.build_share_section(title)

    def _refresh_share_inputs(self):
        self.capital_section.refresh_share_inputs()

    def _build_capital_section(self, title):
        return self.capital_section.build(title)

    def _refresh_capital_inputs(self):
        self.capital_section.refresh_capital_inputs()

    def _refresh_amendment_change_choices(self):
        groups = {key: fields for key, _, fields in CHANGE_GROUPS}
        values = {field: self._field_value(field) for field in self.fields}
        for key, card in self.amendment_choice_cards.items():
            checkbox = self.fields.get(key)
            checked = isinstance(checkbox, QCheckBox) and checkbox.isChecked()
            entered = change_section_has_data(values, key) if key in groups else False
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
        return self.organization_controller.result_values()

    def _update_organization_result_fields(self, values):
        self.organization_controller.update_result_fields(values)

    def _apply_organization_values_to_current_person(self, values, raw_text, extraction_method):
        self.organization_controller.apply_values_to_current_person(values, raw_text, extraction_method)

    def _fill_update_organization_from_selector(self):
        self.organization_controller.fill_from_selector()

    def _save_organization_profile(self):
        self.organization_controller.save_profile()

    def _fill_representative_from_pdf(self):
        self.organization_controller.fill_representative_from_pdf()

    def _fill_section_from_person(self, target, person):
        if target != "legal_representative":
            return super()._fill_section_from_person(target, person)
        self.organization_controller.fill_representative_from_person(person)

    def _scan_organization_document(self, path):
        self.organization_controller.scan_document(path)

    def _choose_company_document(self):
        self.organization_controller.choose_document()

    def _seed_from_case(self, case):
        self.form_state.restore(case)

    def form_values(self, apply_defaults=True):
        return self.form_state.serialize()

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

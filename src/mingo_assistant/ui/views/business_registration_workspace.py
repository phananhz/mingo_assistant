from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import monotonic
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QUrl

from mingo_assistant.models.case import CaseSummary
from mingo_assistant.services.documents.docx_generator import DocxTemplateGenerator
from mingo_assistant.services.normalization.address_parser import AddressParser
from mingo_assistant.services.ocr.id_card_parser import IdCardParser
from mingo_assistant.services.ocr.ocr_service import OcrService


FIELD_GROUPS = [
    (
        "Thông tin cơ quan tiếp nhận và thời gian ký",
        [
            ("business_registration_office", "Phòng đăng ký kinh doanh"),
            ("document_place", "Nơi ký"),
            ("document_day", "Ngày ký"),
            ("document_month", "Tháng ký"),
            ("document_year", "Năm ký"),
            ("document_place_date", "Dòng địa điểm/ngày tháng"),
        ],
    ),
    (
        "Thông tin doanh nghiệp",
        [
            ("company_name", "Tên doanh nghiệp"),
            ("company_short_name", "Tên viết tắt"),
            ("company_address", "Địa chỉ trụ sở đầy đủ"),
            ("company_address_detail", "Số nhà/đường/thôn"),
            ("company_ward", "Xã/Phường"),
            ("company_province", "Tỉnh/Thành phố"),
            ("company_phone", "Số điện thoại công ty"),
            ("company_email", "Email công ty"),
        ],
    ),
    ("Ngành nghề kinh doanh", []),
    (
        "Vốn điều lệ và vốn góp",
        [
            ("charter_capital_number", "Vốn điều lệ bằng số"),
            ("charter_capital_text", "Vốn điều lệ bằng chữ"),
            ("charter_capital_full_text", "Vốn điều lệ đầy đủ"),
            ("cash_capital_text", "Vốn bằng tiền mặt"),
            ("asset_capital_text", "Vốn bằng tài sản"),
            ("member_capital_amount", "Vốn góp thành viên"),
            ("member_capital_ratio", "Tỷ lệ góp vốn"),
            ("capital_zero", "Giá trị 0 trong bảng vốn"),
        ],
    ),
    (
        "Thông tin cá nhân/đại diện pháp luật",
        [
            ("legal_representative_full_name", "Họ tên"),
            ("legal_representative_id_number", "Số CCCD"),
            ("legal_representative_date_of_birth", "Ngày sinh"),
            ("legal_representative_gender", "Giới tính"),
            ("legal_representative_nationality", "Quốc tịch"),
            ("legal_representative_permanent_address", "Địa chỉ thường trú đầy đủ"),
            ("legal_representative_address_detail", "Số nhà/đường/thôn"),
            ("legal_representative_ward", "Xã/Phường"),
            ("legal_representative_province", "Tỉnh/Thành phố"),
            ("legal_representative_contact_address", "Địa chỉ liên lạc"),
            ("legal_representative_place_of_origin", "Quê quán"),
            ("legal_representative_issue_date", "Ngày cấp"),
            ("legal_representative_expiry_date", "Ngày hết hạn"),
            ("legal_representative_position", "Chức danh"),
        ],
    ),
    (
        "Thông tin giám đốc/Tổng giám đốc",
        [
            ("director_full_name", "Họ tên giám đốc"),
            ("director_date_of_birth", "Ngày sinh"),
            ("director_gender", "Giới tính"),
            ("director_id_number", "Số CCCD"),
            ("director_phone", "Điện thoại"),
            ("director_position", "Chức danh"),
        ],
    ),
    (
        "Thông tin người đăng ký/nộp hồ sơ",
        [
            ("applicant_full_name", "Họ tên người đăng ký"),
            ("applicant_date_of_birth", "Ngày sinh"),
            ("applicant_gender", "Giới tính"),
            ("applicant_id_number", "Số CCCD"),
            ("applicant_address_detail", "Số nhà/đường/thôn"),
            ("applicant_ward", "Xã/Phường"),
            ("applicant_province", "Tỉnh/Thành phố"),
        ],
    ),
    (
        "Thông tin người được ủy quyền",
        [
            ("authorized_person_full_name", "Họ tên"),
            ("authorized_person_date_of_birth", "Ngày sinh"),
            ("authorized_person_gender", "Giới tính"),
            ("authorized_person_id_number", "Số CCCD"),
            ("authorized_person_contact_address", "Địa chỉ liên lạc"),
            ("authorized_person_phone", "Điện thoại"),
            ("authorized_person_email", "Email"),
        ],
    ),
]

BUSINESS_LINE_FIELD_DEFINITIONS = [
    (f"business_line_{index}_name", f"Ngành {index}") for index in range(1, 11)
] + [
    (f"business_line_{index}_code", f"Mã ngành {index}") for index in range(1, 11)
] + [
    (f"business_line_{index}_is_main", f"Ngành chính {index}") for index in range(1, 11)
]

HIDDEN_FIELD_DEFINITIONS = [
    ("business_lines", "Ghi chú ngành nghề"),
    ("beneficial_owner_full_name", "Họ tên chủ sở hữu hưởng lợi"),
    ("beneficial_owner_date_of_birth", "Ngày sinh chủ sở hữu hưởng lợi"),
    ("beneficial_owner_gender", "Giới tính chủ sở hữu hưởng lợi"),
    ("beneficial_owner_id_number", "Số CCCD chủ sở hữu hưởng lợi"),
    ("beneficial_owner_issue_date", "Ngày cấp chủ sở hữu hưởng lợi"),
    ("beneficial_owner_address", "Địa chỉ chủ sở hữu hưởng lợi"),
]

FIELD_DEFINITIONS = [field for _, fields in FIELD_GROUPS for field in fields] + BUSINESS_LINE_FIELD_DEFINITIONS + HIDDEN_FIELD_DEFINITIONS


MULTILINE_FIELDS = {
    "company_address",
    "business_lines",
    "legal_representative_permanent_address",
    "legal_representative_contact_address",
    "beneficial_owner_address",
    "authorized_person_contact_address",
}


@dataclass
class OcrPerson:
    name: str
    front_path: str = ""
    back_path: str = ""


@dataclass
class BusinessLineRow:
    name_field: QTextEdit
    code_field: QLineEdit
    main_checkbox: QCheckBox
    delete_button: QPushButton


class ClickableImageLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class BusinessRegistrationWorkspace(QWidget):
    def __init__(
        self,
        on_back,
        on_save,
        case: CaseSummary | None = None,
        on_export=None,
        authorized_person_defaults: dict[str, str] | None = None,
    ) -> None:
        super().__init__()
        self.on_back = on_back
        self.on_save = on_save
        self.on_export = on_export
        self.case = case
        self.case_id = case.id if case else str(uuid4())
        self.ocr_service = OcrService()
        self.id_parser = IdCardParser()
        self.address_parser = AddressParser()
        self.fields: dict[str, QLineEdit | QTextEdit] = {}
        self.business_line_rows: list[BusinessLineRow] = []
        self.form_sections: dict[str, QWidget] = {}
        self.authorized_person_defaults = authorized_person_defaults or {}
        self.updating_capital = False
        self.syncing_person_fields = False
        self.syncing_address_fields = False
        self.last_export_dir: Path | None = None
        self.ocr_people: list[OcrPerson] = [OcrPerson("Người 1")]
        self.current_person_index = 0

        self.raw_ocr_text = QTextEdit()
        self.address_input = QTextEdit()
        self.address_result = QTextEdit()
        self.preview_text = QTextEdit()
        self.ocr_engine_input = QComboBox()
        self.front_image_label = QLabel("Chưa chọn ảnh mặt trước")
        self.back_image_label = QLabel("Chưa chọn ảnh mặt sau")
        self.front_image_preview = ClickableImageLabel("Chưa có ảnh mặt trước")
        self.back_image_preview = ClickableImageLabel("Chưa có ảnh mặt sau")
        self.delete_front_image_button = QPushButton("Xóa ảnh mặt trước")
        self.delete_back_image_button = QPushButton("Xóa ảnh mặt sau")
        self.ocr_progress = QProgressBar()
        self.ocr_status_label = QLabel("Sẵn sàng nhận diện")
        self.ocr_eta_label = QLabel("Thời gian còn lại: --")
        self.people_list_layout = QHBoxLayout()
        self.form_nav_layout = QHBoxLayout()
        self.form_stack = QStackedWidget()
        self.form_button_group = QButtonGroup(self)
        self.form_button_group.setExclusive(True)

        self._build_ui()
        self._refresh_selected_person_images()
        self._seed_from_case(case)
        self._refresh_preview()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        layout.addLayout(self._build_header())
        layout.addWidget(self._build_ocr_section())
        layout.addWidget(self._build_address_section())
        layout.addWidget(self._build_form_section())

        scroll.setWidget(page)
        root.addWidget(scroll)

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        back_button = QPushButton("← Quay lại")
        back_button.setObjectName("GhostButton")
        back_button.clicked.connect(self.on_back)

        text = QVBoxLayout()
        title = QLabel("Tạo hồ sơ thành lập công ty")
        title.setObjectName("PageTitle")
        description = QLabel("OCR CCCD, chuẩn hóa địa chỉ, kiểm tra dữ liệu và xuất bộ mẫu Word.")
        description.setObjectName("PageDescription")
        description.setWordWrap(True)
        text.addWidget(title)
        text.addWidget(description)

        save_button = QPushButton("Lưu nháp")
        save_button.setObjectName("GhostButton")
        save_button.clicked.connect(self._save_draft)

        export_button = QPushButton("Xuất Word")
        export_button.setObjectName("PrimaryButton")
        export_button.clicked.connect(self._export_documents)

        header.addWidget(back_button)
        header.addLayout(text, 1)
        header.addWidget(save_button)
        header.addWidget(export_button)
        return header

    def _build_ocr_section(self) -> QWidget:
        group = QGroupBox("Chuyển đổi ảnh CCCD thành văn bản")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        people_header = QHBoxLayout()
        people_label = QLabel("Danh sách người")
        people_label.setObjectName("FilterLabel")
        add_person_button = QPushButton("+ Thêm người")
        add_person_button.setObjectName("GhostButton")
        add_person_button.clicked.connect(self._add_ocr_person)
        people_header.addWidget(people_label)
        people_header.addLayout(self.people_list_layout, 1)
        people_header.addWidget(add_person_button)
        layout.addLayout(people_header)
        self._refresh_people_buttons()

        actions = QHBoxLayout()
        self.ocr_engine_input.addItem("EasyOCR - ưu tiên tiếng Việt", "easyocr")
        self.ocr_engine_input.addItem("PaddleOCR - dự phòng", "paddleocr")
        actions.addWidget(self.ocr_engine_input)

        run_button = QPushButton("Nhận diện ảnh")
        run_button.setObjectName("PrimaryButton")
        run_button.clicked.connect(self._run_ocr)

        actions.addStretch(1)
        actions.addWidget(run_button)
        layout.addLayout(actions)

        image_previews = QHBoxLayout()
        self._setup_image_preview_label(self.front_image_preview, "Bấm để chọn ảnh mặt trước")
        self._setup_image_preview_label(self.back_image_preview, "Bấm để chọn ảnh mặt sau")
        self.front_image_preview.clicked.connect(lambda: self._choose_person_image("front"))
        self.back_image_preview.clicked.connect(lambda: self._choose_person_image("back"))
        self.delete_front_image_button.setObjectName("GhostButton")
        self.delete_back_image_button.setObjectName("GhostButton")
        self.delete_front_image_button.clicked.connect(lambda: self._delete_person_image("front"))
        self.delete_back_image_button.clicked.connect(lambda: self._delete_person_image("back"))

        front_box = QVBoxLayout()
        front_title = QLabel("Mặt trước")
        front_title.setObjectName("FilterLabel")
        front_box.addWidget(front_title)
        front_box.addWidget(self.front_image_preview)
        front_box.addWidget(self.front_image_label)
        front_box.addWidget(self.delete_front_image_button)

        back_box = QVBoxLayout()
        back_title = QLabel("Mặt sau")
        back_title.setObjectName("FilterLabel")
        back_box.addWidget(back_title)
        back_box.addWidget(self.back_image_preview)
        back_box.addWidget(self.back_image_label)
        back_box.addWidget(self.delete_back_image_button)

        image_previews.addLayout(front_box)
        image_previews.addLayout(back_box)
        image_previews.addStretch(1)
        layout.addLayout(image_previews)

        self.ocr_progress.setRange(0, 100)
        self.ocr_progress.setValue(0)
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.ocr_progress, 1)
        progress_layout.addWidget(self.ocr_status_label)
        progress_layout.addWidget(self.ocr_eta_label)
        layout.addLayout(progress_layout)

        self.raw_ocr_text.setPlaceholderText("Kết quả OCR sẽ hiển thị ở đây. Bạn cũng có thể dán văn bản OCR vào rồi bấm xử lý.")
        self.raw_ocr_text.setMinimumHeight(110)
        layout.addWidget(self.raw_ocr_text)

        parse_button = QPushButton("Xử lý văn bản OCR vào form")
        parse_button.setObjectName("GhostButton")
        parse_button.clicked.connect(self._parse_ocr_text)
        layout.addWidget(parse_button, 0, Qt.AlignRight)
        return group

    def _build_address_section(self) -> QWidget:
        group = QGroupBox("Chuyển đổi địa chỉ / nhận diện tên công ty")
        layout = QHBoxLayout(group)
        layout.setSpacing(12)

        input_box = QVBoxLayout()
        label = QLabel("Nhập đoạn địa chỉ hoặc đoạn văn có tên công ty")
        label.setObjectName("FilterLabel")
        self.address_input.setPlaceholderText("Ví dụ: Số nhà 12, thôn A, xã B, huyện C, tỉnh D hoặc Công ty TNHH ABC...")
        self.address_input.setMinimumHeight(110)
        convert_button = QPushButton("Chuyển đổi vào form")
        convert_button.setObjectName("PrimaryButton")
        convert_button.clicked.connect(self._convert_address)
        input_box.addWidget(label)
        input_box.addWidget(self.address_input)
        input_box.addWidget(convert_button, 0, Qt.AlignRight)

        result_box = QVBoxLayout()
        result_label = QLabel("Kết quả phân tích")
        result_label.setObjectName("FilterLabel")
        self.address_result.setReadOnly(True)
        self.address_result.setMinimumHeight(110)
        result_box.addWidget(result_label)
        result_box.addWidget(self.address_result)

        layout.addLayout(input_box, 1)
        layout.addLayout(result_box, 1)
        return group

    def _build_form_section(self) -> QWidget:
        group = QGroupBox("Thông tin dùng để điền vào hồ sơ")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        self.form_nav_layout.setSpacing(8)

        nav_widget = QWidget()
        nav_widget.setLayout(self.form_nav_layout)
        nav_scroll = QScrollArea()
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QFrame.NoFrame)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        nav_scroll.setFixedHeight(54)
        nav_scroll.setWidget(nav_widget)

        layout.addWidget(nav_scroll)
        layout.addWidget(self.form_stack)

        for index, (title, fields) in enumerate(FIELD_GROUPS):
            button = QPushButton(title)
            button.setObjectName("PrimaryButton" if index == 0 else "GhostButton")
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.clicked.connect(lambda checked=False, selected=index: self._select_form_section(selected))
            self.form_button_group.addButton(button, index)
            self.form_nav_layout.addWidget(button)

            if title == "Ngành nghề kinh doanh":
                section = self._build_business_lines_section()
            else:
                section = self._build_regular_form_section(title, fields)
            self.form_sections[title] = section
            self.form_stack.addWidget(section)
        self.form_nav_layout.addStretch(1)
        return group

    def _select_form_section(self, index: int) -> None:
        self.form_stack.setCurrentIndex(index)
        for button in self.form_button_group.buttons():
            button.setObjectName("PrimaryButton" if self.form_button_group.id(button) == index else "GhostButton")
            button.style().unpolish(button)
            button.style().polish(button)

    def _build_regular_form_section(self, title: str, fields: list[tuple[str, str]]) -> QWidget:
        section = QGroupBox(title)
        section_grid = QGridLayout(section)
        section_grid.setHorizontalSpacing(18)
        section_grid.setVerticalSpacing(10)

        for index, (key, label_text) in enumerate(fields):
            row = index // 2
            column = (index % 2) * 2
            label = QLabel(label_text)
            label.setObjectName("FilterLabel")
            field = self._create_field(key)
            section_grid.addWidget(label, row, column)
            section_grid.addWidget(field, row, column + 1)

        if title == "Thông tin người được ủy quyền":
            fill_button = QPushButton("Tự động điền thông tin người ủy quyền")
            fill_button.setObjectName("PrimaryButton")
            fill_button.clicked.connect(self._fill_authorized_person_from_defaults)
            next_row = (len(fields) + 1) // 2
            section_grid.addWidget(fill_button, next_row, 0, 1, 4, Qt.AlignRight)

        return section

    def _create_field(self, key: str) -> QLineEdit | QTextEdit:
        if key in MULTILINE_FIELDS:
            field = QTextEdit()
            field.setFixedHeight(70)
            field.textChanged.connect(self._refresh_preview)
            if key in {"company_address", "legal_representative_permanent_address"}:
                field.textChanged.connect(lambda selected=key: self._sync_address_parts(selected))
            if key.startswith("legal_representative_"):
                field.textChanged.connect(self._sync_director_from_legal_representative)
        else:
            field = QLineEdit()
            field.textChanged.connect(self._refresh_preview)
            if key == "charter_capital_number":
                field.textChanged.connect(self._handle_capital_number_changed)
            if key.startswith("legal_representative_"):
                field.textChanged.connect(self._sync_director_from_legal_representative)
        self.fields[key] = field
        return field

    def _build_business_lines_section(self) -> QWidget:
        section = QGroupBox("Ngành nghề kinh doanh")
        layout = QVBoxLayout(section)
        layout.setSpacing(10)

        table = QFrame()
        table.setObjectName("BusinessLineTable")
        table_layout = QGridLayout(table)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setHorizontalSpacing(0)
        table_layout.setVerticalSpacing(0)

        headers = ["Thông tin ngành nghề", "Mã ngành nghề", "Ngành nghề chính", "Xóa"]
        for column, header_text in enumerate(headers):
            header = QLabel(header_text)
            header.setObjectName("TableHeader")
            header.setAlignment(Qt.AlignCenter)
            header.setMinimumHeight(38)
            table_layout.addWidget(header, 0, column)

        table_layout.setColumnStretch(0, 5)
        table_layout.setColumnStretch(1, 2)
        table_layout.setColumnStretch(2, 1)
        table_layout.setColumnStretch(3, 1)

        for index in range(1, 11):
            self._add_business_line_row(table_layout, index, visible=index == 1)

        layout.addWidget(table)

        add_button = QPushButton("+ Thêm ngành nghề")
        add_button.setObjectName("PrimaryButton")
        add_button.clicked.connect(self._show_next_business_line_row)
        layout.addWidget(add_button, 0, Qt.AlignRight)
        return section

    def _add_business_line_row(self, parent_layout: QGridLayout, index: int, visible: bool) -> None:
        name_field = QTextEdit()
        name_field.setPlaceholderText("Tên ngành nghề\nChi tiết: ...")
        name_field.setFixedHeight(82)
        name_field.textChanged.connect(self._refresh_preview)

        code_field = QLineEdit()
        code_field.setAlignment(Qt.AlignCenter)
        code_field.textChanged.connect(self._refresh_preview)

        main_checkbox = QCheckBox()
        main_checkbox.setText("X")
        main_checkbox.setToolTip("Đánh dấu ngành nghề chính")
        main_checkbox.stateChanged.connect(lambda state, selected=index: self._set_main_business_line(selected, state))

        delete_button = QPushButton("Xóa")
        delete_button.setObjectName("GhostButton")
        delete_button.clicked.connect(lambda checked=False, selected=index: self._delete_business_line_row(selected))

        parent_layout.addWidget(name_field, index, 0)
        parent_layout.addWidget(code_field, index, 1)
        parent_layout.addWidget(main_checkbox, index, 2, Qt.AlignCenter)
        parent_layout.addWidget(delete_button, index, 3)

        self.fields[f"business_line_{index}_name"] = name_field
        self.fields[f"business_line_{index}_code"] = code_field
        self.business_line_rows.append(BusinessLineRow(name_field, code_field, main_checkbox, delete_button))
        self._set_business_line_row_visible(index, visible)

    def _show_next_business_line_row(self) -> None:
        for index, row in enumerate(self.business_line_rows, start=1):
            if not row.name_field.isVisible():
                self._set_business_line_row_visible(index, True)
                return
        QMessageBox.information(self, "Đã đủ ngành nghề", "Hiện form đang hỗ trợ tối đa 10 ngành nghề trong một hồ sơ.")

    def _delete_business_line_row(self, index: int) -> None:
        row = self.business_line_rows[index - 1]
        has_data = bool(row.name_field.toPlainText().strip() or row.code_field.text().strip() or row.main_checkbox.isChecked())
        if has_data:
            answer = QMessageBox.question(
                self,
                "Xóa ngành nghề",
                f"Ngành {index} đang có thông tin. Bạn có muốn xóa ngành này không?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        row.name_field.clear()
        row.code_field.clear()
        row.main_checkbox.setChecked(False)
        if index == 1:
            self._set_business_line_row_visible(index, True)
        else:
            self._set_business_line_row_visible(index, False)
        self._refresh_preview()

    def _set_business_line_row_visible(self, index: int, visible: bool) -> None:
        row = self.business_line_rows[index - 1]
        row.name_field.setVisible(visible)
        row.code_field.setVisible(visible)
        row.main_checkbox.setVisible(visible)
        row.delete_button.setVisible(visible)

    def _set_main_business_line(self, index: int, state: int) -> None:
        if state != Qt.Checked:
            self._refresh_preview()
            return
        for other_index, row in enumerate(self.business_line_rows, start=1):
            if other_index != index and row.main_checkbox.isChecked():
                row.main_checkbox.blockSignals(True)
                row.main_checkbox.setChecked(False)
                row.main_checkbox.blockSignals(False)
        self._refresh_preview()

    def _fill_authorized_person_from_defaults(self) -> None:
        if not self.authorized_person_defaults:
            QMessageBox.information(
                self,
                "Chưa có thông tin người ủy quyền",
                "Bạn cần nhập thông tin người ủy quyền ở màn danh sách hồ sơ trước.",
            )
            return
        for key, value in self.authorized_person_defaults.items():
            if key.startswith("authorized_person_") and value:
                self._set_field(key, value)
        self._refresh_preview()

    def _sync_director_from_legal_representative(self) -> None:
        if self.syncing_person_fields:
            return
        self.syncing_person_fields = True
        try:
            pairs = {
                "director_full_name": "legal_representative_full_name",
                "director_date_of_birth": "legal_representative_date_of_birth",
                "director_gender": "legal_representative_gender",
                "director_id_number": "legal_representative_id_number",
                "beneficial_owner_full_name": "legal_representative_full_name",
                "beneficial_owner_date_of_birth": "legal_representative_date_of_birth",
                "beneficial_owner_gender": "legal_representative_gender",
                "beneficial_owner_id_number": "legal_representative_id_number",
                "beneficial_owner_issue_date": "legal_representative_issue_date",
                "beneficial_owner_address": "legal_representative_permanent_address",
            }
            for target, source in pairs.items():
                source_value = self._field_value(source)
                if source_value:
                    self._set_field(target, source_value)
        finally:
            self.syncing_person_fields = False
        self._refresh_preview()

    def _field_value(self, key: str) -> str:
        field = self.fields.get(key)
        if isinstance(field, QTextEdit):
            return field.toPlainText().strip()
        if isinstance(field, QLineEdit):
            return field.text().strip()
        return ""

    def _sync_address_parts(self, source_key: str) -> None:
        if self.syncing_address_fields:
            return
        address = self._field_value(source_key)
        if not address:
            return
        parsed = self.address_parser.parse(address)
        detail = parsed.street_line or parsed.village
        if not any([detail, parsed.ward, parsed.province]):
            return

        if source_key == "company_address":
            mapping = {
                "company_address_detail": detail,
                "company_ward": parsed.ward,
                "company_province": parsed.province,
            }
        else:
            mapping = {
                "legal_representative_address_detail": detail,
                "legal_representative_ward": parsed.ward,
                "legal_representative_province": parsed.province,
            }

        self.syncing_address_fields = True
        try:
            for key, value in mapping.items():
                if value:
                    self._set_field(key, value)
        finally:
            self.syncing_address_fields = False
        self._refresh_preview()

    def _handle_capital_number_changed(self, text: str) -> None:
        if self.updating_capital:
            return
        digits = self._money_digits(text)
        if not digits:
            return

        formatted = self._format_money(digits)
        self.updating_capital = True
        try:
            field = self.fields.get("charter_capital_number")
            if isinstance(field, QLineEdit) and field.text() != formatted:
                field.setText(formatted)
                field.setCursorPosition(len(formatted))

            capital_text = self._number_to_vietnamese_words(int(digits)).capitalize() + " đồng"
            full_text = f"{formatted} đồng ({capital_text})"
            self._set_field("charter_capital_text", capital_text)
            self._set_field("charter_capital_full_text", full_text)
            self._set_field("cash_capital_text", full_text)
            self._set_field("member_capital_amount", formatted)
            self._set_field("member_capital_ratio", "100%")
        finally:
            self.updating_capital = False
        self._refresh_preview()

    def _money_digits(self, value: str) -> str:
        return re.sub(r"\D", "", value)

    def _format_money(self, digits: str) -> str:
        return f"{int(digits):,}".replace(",", ".")

    def _number_to_vietnamese_words(self, number: int) -> str:
        if number == 0:
            return "không"

        units = ["", "nghìn", "triệu", "tỷ", "nghìn tỷ", "triệu tỷ"]
        groups: list[int] = []
        while number:
            groups.append(number % 1000)
            number //= 1000

        parts: list[str] = []
        for index in range(len(groups) - 1, -1, -1):
            group = groups[index]
            if group == 0:
                continue
            words = self._read_three_digits(group, force_hundreds=index < len(groups) - 1)
            unit = units[index] if index < len(units) else ""
            parts.append(" ".join(part for part in [words, unit] if part))
        return " ".join(parts)

    def _read_three_digits(self, number: int, force_hundreds: bool = False) -> str:
        digits = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
        hundred = number // 100
        ten = (number % 100) // 10
        one = number % 10
        words: list[str] = []

        if hundred:
            words.extend([digits[hundred], "trăm"])
        elif force_hundreds and (ten or one):
            words.extend(["không", "trăm"])

        if ten > 1:
            words.extend([digits[ten], "mươi"])
            if one == 1:
                words.append("mốt")
            elif one == 5:
                words.append("lăm")
            elif one:
                words.append(digits[one])
        elif ten == 1:
            words.append("mười")
            if one == 5:
                words.append("lăm")
            elif one:
                words.append(digits[one])
        elif one:
            if hundred or force_hundreds:
                words.append("lẻ")
            words.append(digits[one])
        return " ".join(words)

    def _build_preview_section(self) -> QWidget:
        group = QGroupBox("Xem trước dữ liệu trước khi xuất Word")
        layout = QVBoxLayout(group)
        self.preview_text.setReadOnly(True)
        self.preview_text.setMinimumHeight(180)
        layout.addWidget(self.preview_text)

        actions = QHBoxLayout()
        refresh_button = QPushButton("Cập nhật xem trước")
        refresh_button.setObjectName("GhostButton")
        refresh_button.clicked.connect(self._refresh_preview)
        open_export_button = QPushButton("Mở thư mục xuất gần nhất")
        open_export_button.setObjectName("GhostButton")
        open_export_button.clicked.connect(self._open_last_export_dir)
        actions.addStretch(1)
        actions.addWidget(refresh_button)
        actions.addWidget(open_export_button)
        layout.addLayout(actions)
        return group

    def _seed_from_case(self, case: CaseSummary | None) -> None:
        defaults = {
            "legal_representative_nationality": "Việt Nam",
            "legal_representative_position": "Giám đốc",
            "director_position": "Giám đốc",
            "authorized_person_gender": "Nữ",
            "member_capital_ratio": "100%",
            "capital_zero": "0",
            "asset_capital_text": "(không có)",
        }
        if case:
            defaults.update(
                {
                    "company_name": case.company_name,
                    "charter_capital_number": case.capital,
                    "legal_representative_full_name": case.owner,
                }
            )
            defaults.update(case.form_values)
        for key, value in defaults.items():
            self._set_field(key, value)
        self._restore_business_lines(case.form_values if case else {})

    def _restore_business_lines(self, values: dict[str, str]) -> None:
        for index, row in enumerate(self.business_line_rows, start=1):
            name = values.get(f"business_line_{index}_name", "")
            code = values.get(f"business_line_{index}_code", "")
            is_main = bool(values.get(f"business_line_{index}_is_main", ""))
            has_data = bool(name or code or is_main)
            if index == 1 or has_data:
                self._set_business_line_row_visible(index, True)
            if name:
                row.name_field.setPlainText(name)
            if code:
                row.code_field.setText(code)
            if is_main:
                row.main_checkbox.setChecked(True)

    def _add_ocr_person(self) -> None:
        self.ocr_people.append(OcrPerson(f"Người {len(self.ocr_people) + 1}"))
        self.current_person_index = len(self.ocr_people) - 1
        self._refresh_people_buttons()
        self._refresh_selected_person_images()

    def _select_ocr_person(self, index: int) -> None:
        self.current_person_index = index
        self._refresh_people_buttons()
        self._refresh_selected_person_images()

    def _refresh_people_buttons(self) -> None:
        while self.people_list_layout.count():
            item = self.people_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for index, person in enumerate(self.ocr_people):
            button = QPushButton(person.name)
            button.setObjectName("PrimaryButton" if index == self.current_person_index else "GhostButton")
            button.clicked.connect(lambda checked=False, selected=index: self._select_ocr_person(selected))
            self.people_list_layout.addWidget(button)

    def _refresh_selected_person_images(self) -> None:
        person = self.ocr_people[self.current_person_index]
        self.front_image_label.setText(person.front_path or "Chưa chọn ảnh mặt trước")
        self.back_image_label.setText(person.back_path or "Chưa chọn ảnh mặt sau")
        self._set_image_preview(self.front_image_preview, person.front_path, "Bấm để chọn ảnh mặt trước")
        self._set_image_preview(self.back_image_preview, person.back_path, "Bấm để chọn ảnh mặt sau")
        self.delete_front_image_button.setVisible(bool(person.front_path))
        self.delete_back_image_button.setVisible(bool(person.back_path))

    def _setup_image_preview_label(self, label: ClickableImageLabel, placeholder: str) -> None:
        label.setMinimumSize(190, 120)
        label.setMaximumSize(280, 176)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        label.setCursor(Qt.PointingHandCursor)
        label.setToolTip(placeholder)
        label.setStyleSheet(
            "background: #fffafc; border: 1px solid #f0c8d6; border-radius: 6px; color: #80606c;"
        )

    def _set_image_preview(self, label: QLabel, image_path: str, empty_text: str) -> None:
        if not image_path:
            label.setPixmap(QPixmap())
            label.setText(empty_text)
            return

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            label.setPixmap(QPixmap())
            label.setText("Không đọc được ảnh")
            return

        label.setText("")
        label.setPixmap(pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _choose_person_image(self, side: str) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn ảnh CCCD",
            "",
            "Ảnh (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;Tất cả file (*.*)",
        )
        if path:
            person = self.ocr_people[self.current_person_index]
            if side == "front":
                person.front_path = path
            else:
                person.back_path = path
            self._refresh_selected_person_images()

    def _delete_person_image(self, side: str) -> None:
        person = self.ocr_people[self.current_person_index]
        current_path = person.front_path if side == "front" else person.back_path
        if not current_path:
            return
        side_label = "mặt trước" if side == "front" else "mặt sau"
        answer = QMessageBox.question(
            self,
            "Xóa ảnh CCCD",
            f"Bạn có muốn xóa ảnh {side_label} đã tải lên không?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        if side == "front":
            person.front_path = ""
        else:
            person.back_path = ""
        self._refresh_selected_person_images()

    def _run_ocr(self) -> None:
        self.ocr_service.set_engine(self.ocr_engine_input.currentData() or "easyocr")
        person = self.ocr_people[self.current_person_index]
        image_jobs = [("mặt trước", person.front_path), ("mặt sau", person.back_path)]
        image_jobs = [(label, image_path) for label, image_path in image_jobs if image_path]
        if not image_jobs:
            QMessageBox.warning(self, "Chưa chọn ảnh", "Bạn cần chọn ít nhất ảnh mặt trước hoặc mặt sau của CCCD.")
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            texts: list[str] = []
            total = len(image_jobs)
            start = monotonic()
            self._update_ocr_progress(0, "Đang chuẩn bị OCR", "--")
            for index, (side_label, image_path) in enumerate(image_jobs, start=1):
                self._update_ocr_progress(
                    int(((index - 1) / total) * 100),
                    f"Đang xử lý {side_label}",
                    self._format_eta(start, index - 1, total),
                )
                QApplication.processEvents()

                extracted_text = self.ocr_service.extract_text(image_path)
                texts.append(f"--- {person.name} - {side_label} ---\n{extracted_text}")

                self._update_ocr_progress(
                    int((index / total) * 100),
                    f"Đã xử lý {side_label}",
                    self._format_eta(start, index, total),
                )
                QApplication.processEvents()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi OCR", f"Không thể nhận diện ảnh:\n{exc}")
            return
        finally:
            QApplication.restoreOverrideCursor()

        self._update_ocr_progress(100, "Hoàn thành OCR", "0 giây")
        self.raw_ocr_text.setPlainText("\n\n".join(texts))
        self._parse_ocr_text()

    def _update_ocr_progress(self, percent: int, status: str, eta: str) -> None:
        self.ocr_progress.setValue(max(0, min(100, percent)))
        self.ocr_status_label.setText(status)
        self.ocr_eta_label.setText(f"Thời gian còn lại: {eta}")

    def _format_eta(self, start: float, completed: int, total: int) -> str:
        if completed <= 0:
            return "--"
        elapsed = monotonic() - start
        remaining = max(0.0, (elapsed / completed) * (total - completed))
        if remaining < 60:
            return f"{int(remaining)} giây"
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        return f"{minutes} phút {seconds} giây"

    def _parse_ocr_text(self) -> None:
        text = self.raw_ocr_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Chưa có văn bản", "Bạn cần OCR ảnh hoặc dán văn bản OCR trước.")
            return

        card = self.id_parser.parse(text)
        card_values = card.to_form_values()
        for key, value in card_values.items():
            if value:
                self._set_field_if_empty(key, value)
        self._parse_registration_office_from_text(text)
        mirror_fields = {
            "director_full_name": "legal_representative_full_name",
            "director_date_of_birth": "legal_representative_date_of_birth",
            "director_gender": "legal_representative_gender",
            "director_id_number": "legal_representative_id_number",
            "beneficial_owner_full_name": "legal_representative_full_name",
            "beneficial_owner_date_of_birth": "legal_representative_date_of_birth",
            "beneficial_owner_gender": "legal_representative_gender",
            "beneficial_owner_id_number": "legal_representative_id_number",
            "beneficial_owner_issue_date": "legal_representative_issue_date",
            "beneficial_owner_address": "legal_representative_permanent_address",
            "applicant_full_name": "legal_representative_full_name",
            "applicant_date_of_birth": "legal_representative_date_of_birth",
            "applicant_gender": "legal_representative_gender",
            "applicant_id_number": "legal_representative_id_number",
        }
        for target, source in mirror_fields.items():
            value = card_values.get(source, "")
            if value:
                self._set_field_if_empty(target, value)
        if card.warnings:
            QMessageBox.warning(self, "Cảnh báo dữ liệu CCCD", "\n".join(card.warnings))
        self._refresh_preview()

    def _parse_registration_office_from_text(self, text: str) -> None:
        office_match = re.search(r"(Phòng\s+Đăng\s+ký\s+kinh\s+doanh[^\n\r,.]*)", text, flags=re.IGNORECASE)
        if office_match:
            self._set_field_if_empty("business_registration_office", office_match.group(1).strip())

        date_match = re.search(
            r"([^\n\r,]+),?\s*ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})",
            text,
            flags=re.IGNORECASE,
        )
        if not date_match:
            return
        place = " ".join(date_match.group(1).split()).strip(" ,.-")
        if place:
            self._set_field_if_empty("document_place", place)
        self._set_field_if_empty("document_day", date_match.group(2).zfill(2))
        self._set_field_if_empty("document_month", date_match.group(3).zfill(2))
        self._set_field_if_empty("document_year", date_match.group(4))

    def _convert_address(self) -> None:
        text = self.address_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Chưa có dữ liệu", "Bạn cần nhập địa chỉ hoặc đoạn văn trước.")
            return

        result = self.address_parser.parse(text)
        self.address_result.setPlainText(result.summary() or "Chưa phân tích được dữ liệu rõ ràng.")
        if result.company_name:
            self._set_field("company_name", result.company_name)
        if result.normalized_address:
            target = "company_address" if result.company_name else "legal_representative_permanent_address"
            self._set_field(target, result.normalized_address)
            self._fill_address_parts_from_result(target, result)
        self._refresh_preview()

    def _fill_address_parts_from_result(self, target: str, result) -> None:
        detail = result.street_line or result.village
        if target == "company_address":
            mapping = {
                "company_address_detail": detail,
                "company_ward": result.ward,
                "company_province": result.province,
            }
        else:
            mapping = {
                "legal_representative_address_detail": detail,
                "legal_representative_ward": result.ward,
                "legal_representative_province": result.province,
            }
        for key, value in mapping.items():
            if value:
                self._set_field(key, value)

    def _save_draft(self) -> None:
        self.on_save(self.build_case_summary())
        QMessageBox.information(self, "Đã lưu", "Hồ sơ nháp đã được lưu vào danh sách.")

    def _export_documents(self) -> None:
        values = self.form_values()
        missing = self._missing_required_fields(values)
        if missing:
            QMessageBox.warning(self, "Thiếu thông tin", "Bạn cần bổ sung:\n- " + "\n- ".join(missing))
            return

        project_root = Path(__file__).resolve().parents[4]
        template_dir = project_root / "assets" / "templates" / "word" / "business_registration"
        export_root = project_root / "exports"
        generator = DocxTemplateGenerator(template_dir=template_dir, export_root=export_root)

        try:
            result = generator.generate(values, values.get("company_name", "ho_so_thanh_lap"))
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi xuất Word", f"Không thể tạo hồ sơ:\n{exc}")
            return

        self.last_export_dir = result.output_dir
        exported_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        generated_documents = [document.output_path.name for document in result.generated]
        saved_case = self.build_case_summary(
            status="Đã tạo hồ sơ",
            condition="Đủ dữ liệu",
            warning=None,
            export_dir=str(result.output_dir),
            exported_at=exported_at,
            generated_documents=generated_documents,
        )
        self.on_save(saved_case)
        message = [f"Đã tạo {len(result.generated)} file DOCX.", f"Thư mục: {result.output_dir}"]
        if result.skipped:
            message.append("\nFile chưa xử lý:")
            message.extend(f"- {item}" for item in result.skipped)
        QMessageBox.information(self, "Xuất hồ sơ thành công", "\n".join(message))
        if self.on_export is not None:
            self.on_export(saved_case)

    def _open_last_export_dir(self) -> None:
        if not self.last_export_dir or not self.last_export_dir.exists():
            QMessageBox.information(self, "Chưa có thư mục", "Bạn chưa xuất hồ sơ trong phiên này.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_export_dir)))

    def _refresh_preview(self) -> None:
        values = self.form_values()
        lines = []
        for key, label in FIELD_DEFINITIONS:
            if key.startswith("beneficial_owner_"):
                continue
            value = values.get(key, "").strip()
            if value:
                lines.append(f"{label}: {value}")
        self.preview_text.setPlainText("\n".join(lines) if lines else "Chưa có dữ liệu để xem trước.")

    def form_values(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for key, field in self.fields.items():
            if isinstance(field, QTextEdit):
                values[key] = field.toPlainText().strip()
            else:
                values[key] = field.text().strip()
        for index, row in enumerate(self.business_line_rows, start=1):
            values[f"business_line_{index}_name"] = row.name_field.toPlainText().strip()
            values[f"business_line_{index}_code"] = row.code_field.text().strip()
            values[f"business_line_{index}_is_main"] = "X" if row.main_checkbox.isChecked() else ""
        self._apply_value_defaults(values)
        return values

    def _apply_value_defaults(self, values: dict[str, str]) -> None:
        document_place = values.get("document_place", "").strip()
        document_day = values.get("document_day", "").strip()
        document_month = values.get("document_month", "").strip()
        document_year = values.get("document_year", "").strip()

        if not values.get("document_place_date") and document_place and document_day and document_month and document_year:
            values["document_place_date"] = f"{document_place}, ngày {document_day} tháng {document_month} năm {document_year}"

        self._fill_composed_address(
            values,
            "company_address",
            ["company_address_detail", "company_ward", "company_province"],
        )
        self._fill_composed_address(
            values,
            "legal_representative_permanent_address",
            ["legal_representative_address_detail", "legal_representative_ward", "legal_representative_province"],
        )
        self._fill_if_missing(values, "legal_representative_contact_address", "legal_representative_permanent_address")
        self._fill_if_missing(values, "company_province", "document_place")

        representative_aliases = {
            "director_full_name": "legal_representative_full_name",
            "director_date_of_birth": "legal_representative_date_of_birth",
            "director_gender": "legal_representative_gender",
            "director_id_number": "legal_representative_id_number",
            "director_phone": "company_phone",
            "beneficial_owner_full_name": "legal_representative_full_name",
            "beneficial_owner_date_of_birth": "legal_representative_date_of_birth",
            "beneficial_owner_gender": "legal_representative_gender",
            "beneficial_owner_id_number": "legal_representative_id_number",
            "beneficial_owner_issue_date": "legal_representative_issue_date",
            "beneficial_owner_address": "legal_representative_permanent_address",
            "applicant_full_name": "legal_representative_full_name",
            "applicant_date_of_birth": "legal_representative_date_of_birth",
            "applicant_gender": "legal_representative_gender",
            "applicant_id_number": "legal_representative_id_number",
            "applicant_address_detail": "legal_representative_address_detail",
            "applicant_ward": "legal_representative_ward",
            "applicant_province": "legal_representative_province",
        }
        for target, source in representative_aliases.items():
            self._fill_if_missing(values, target, source)

        self._fill_if_missing(values, "member_capital_amount", "charter_capital_number")
        self._fill_if_missing(values, "cash_capital_text", "charter_capital_full_text")
        capital_digits = self._money_digits(values.get("charter_capital_number", ""))
        if capital_digits:
            formatted_capital = self._format_money(capital_digits)
            values["charter_capital_number"] = formatted_capital
            if not values.get("member_capital_amount") or self._money_digits(values.get("member_capital_amount", "")) == capital_digits:
                values["member_capital_amount"] = formatted_capital
            if not values.get("charter_capital_text"):
                values["charter_capital_text"] = self._number_to_vietnamese_words(int(capital_digits)).capitalize() + " đồng"
        if not values.get("charter_capital_full_text"):
            capital_number = values.get("charter_capital_number", "")
            capital_text = values.get("charter_capital_text", "")
            if capital_number and capital_text:
                values["charter_capital_full_text"] = f"{capital_number} đồng ({capital_text})"
            elif capital_number:
                values["charter_capital_full_text"] = capital_number
        if not values.get("cash_capital_text"):
            values["cash_capital_text"] = values.get("charter_capital_full_text", "")
        values.setdefault("capital_zero", "0")
        values.setdefault("asset_capital_text", "(không có)")
        if len(self.ocr_people) == 1:
            values["member_capital_ratio"] = "100%"
        values["business_lines"] = self._business_lines_summary(values)

    def _business_lines_summary(self, values: dict[str, str]) -> str:
        lines = []
        for index in range(1, 11):
            name = self._normalize_business_line_text(values.get(f"business_line_{index}_name", ""))
            code = values.get(f"business_line_{index}_code", "").strip()
            if not name and not code:
                continue
            main = " - ngành nghề chính" if values.get(f"business_line_{index}_is_main") else ""
            line = name
            if code:
                line = f"{line} [{code}]" if line else f"[{code}]"
            lines.append(f"{line}{main}")
        return "\n".join(lines)

    def _normalize_business_line_text(self, value: str) -> str:
        text = "\n".join(part.strip() for part in value.replace("\r", "\n").split("\n") if part.strip())
        text = re.sub(r"\s+(Chi\s*tiết\s*:)", r"\n\1", text, flags=re.IGNORECASE)
        return re.sub(r"(?i)chi\s*tiết\s*:", "Chi tiết:", text)

    def _fill_if_missing(self, values: dict[str, str], target: str, source: str) -> None:
        if not values.get(target) and values.get(source):
            values[target] = values[source]

    def _fill_composed_address(self, values: dict[str, str], target: str, parts: list[str]) -> None:
        if values.get(target):
            return
        address = ", ".join(values.get(part, "").strip() for part in parts if values.get(part, "").strip())
        if address:
            values[target] = address

    def build_case_summary(
        self,
        status: str = "Bản nháp",
        condition: str = "Thiếu thông tin",
        warning: str | None = "Cần kiểm tra dữ liệu trước khi xuất",
        export_dir: str | None = None,
        exported_at: str | None = None,
        generated_documents: list[str] | None = None,
    ) -> CaseSummary:
        values = self.form_values()
        existing = self.case
        member_count = len(self.ocr_people)
        return CaseSummary(
            id=self.case_id,
            company_name=values.get("company_name") or "Hồ sơ thành lập doanh nghiệp mới",
            case_type=self._case_type_for_members(member_count),
            owner=values.get("legal_representative_full_name") or "Chưa nhập",
            updated_at=datetime.now().strftime("%d/%m/%Y"),
            status=status,
            condition=condition,
            members=member_count,
            capital=values.get("charter_capital_number") or "Chưa nhập",
            warning=warning,
            export_dir=export_dir if export_dir is not None else (existing.export_dir if existing else ""),
            exported_at=exported_at if exported_at is not None else (existing.exported_at if existing else ""),
            generated_documents=generated_documents if generated_documents is not None else (existing.generated_documents if existing else []),
            form_values=values,
        )

    def _case_type_for_members(self, member_count: int) -> str:
        if member_count <= 1:
            return "TNHH một thành viên"
        return "TNHH hai thành viên trở lên"

    def _missing_required_fields(self, values: dict[str, str]) -> list[str]:
        required = {
            "company_name": "Tên doanh nghiệp",
            "company_address": "Địa chỉ trụ sở",
            "charter_capital_number": "Vốn điều lệ",
            "legal_representative_full_name": "Họ tên cá nhân/đại diện",
            "legal_representative_id_number": "Số CCCD",
            "legal_representative_permanent_address": "Địa chỉ thường trú",
        }
        return [label for key, label in required.items() if not values.get(key, "").strip()]

    def _set_field_if_empty(self, key: str, value: str) -> None:
        field = self.fields.get(key)
        if isinstance(field, QTextEdit):
            current = field.toPlainText().strip()
        elif isinstance(field, QLineEdit):
            current = field.text().strip()
        else:
            current = ""
        if not current:
            self._set_field(key, value)

    def _set_field(self, key: str, value: str) -> None:
        field = self.fields.get(key)
        if field is None:
            return
        if isinstance(field, QTextEdit):
            field.setPlainText(value)
        else:
            field.setText(value)

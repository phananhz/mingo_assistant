from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from time import monotonic
from uuid import uuid4

from PySide6.QtCore import QObject, QThread, QTimer, QUrl, Qt, Signal, Slot, QStringListModel
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QCompleter,
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
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from mingo_assistant.app.paths import get_app_paths, save_settings
from mingo_assistant.models.case import CaseSummary
from mingo_assistant.services.documents.docx_generator import DocxTemplateGenerator
from mingo_assistant.services.business_lines.industry_lookup import IndustryCatalog, IndustryRow
from mingo_assistant.services.normalization.address_parser import AddressParser
from mingo_assistant.services.ocr.id_card_parser import IdCardParser
from mingo_assistant.services.ocr.ocr_service import OcrService
from mingo_assistant.services.registration_offices import RegistrationOfficeCatalog
from mingo_assistant.ui.widgets.combo_box import NoWheelComboBox

PERSON_ROLES = [
    ("legal_representative", "Đại diện pháp luật/Giám đốc"),
    ("member", "Thành viên/chủ sở hữu góp vốn"),
    ("applicant", "Người đăng ký/nộp hồ sơ"),
    ("authorized_person", "Người được ủy quyền"),
]


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
        "Thông tin doanh nghiệp",
        [
            ("company_name", "Tên doanh nghiệp"),
            ("company_english_name", "Tên tiếng Anh"),
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
        "Thông tin người đại diện pháp luật",
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
    role: str = "member"
    front_path: str = ""
    back_path: str = ""
    data: dict[str, str] = field(default_factory=dict)


@dataclass
class BusinessLineRow:
    name_field: QTextEdit
    code_field: QLineEdit
    main_checkbox: QCheckBox
    delete_button: QPushButton
    cells: list[QFrame]


class ClickableImageLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class DocxExportWorker(QObject):
    finished = Signal(object)

    def __init__(self, template_dir: Path, export_root: Path, values: dict[str, str], case_name: str, output_dir: Path) -> None:
        super().__init__()
        self.template_dir = template_dir
        self.export_root = export_root
        self.values = values
        self.case_name = case_name
        self.output_dir = output_dir

    def run(self) -> None:
        try:
            generator = DocxTemplateGenerator(template_dir=self.template_dir, export_root=self.export_root)
            template_issues = generator.validate_templates(self.values)
            if template_issues:
                self.finished.emit({"template_issues": template_issues})
                return
            result = generator.generate(self.values, self.case_name, output_dir=self.output_dir)
            self.finished.emit({"result": result})
        except Exception as exc:
            self.finished.emit({"error": str(exc)})


class BusinessRegistrationWorkspace(QWidget):
    def __init__(
        self,
        on_back,
        on_save,
        case: CaseSummary | None = None,
        on_export=None,
        authorized_person_defaults: dict[str, str] | None = None,
        industry_catalog: IndustryCatalog | None = None,
        bundle_root: Path | None = None,
        default_export_root: Path | None = None,
    ) -> None:
        super().__init__()
        self.on_back = on_back
        self.on_save = on_save
        self.on_export = on_export
        self.case = case
        self.case_id = case.id if case else str(uuid4())
        self.bundle_root = bundle_root or get_app_paths().bundle_root
        self.default_export_root = default_export_root or get_app_paths().documents_root
        self.ocr_service = OcrService()
        self.id_parser = IdCardParser()
        self.address_parser = AddressParser()
        self.industry_catalog = industry_catalog or IndustryCatalog.load_from_project(self.bundle_root)
        self.registration_office_catalog = RegistrationOfficeCatalog.load_from_project(self.bundle_root)
        self.fields: dict[str, QLineEdit | QTextEdit] = {}
        self.ocr_card_fields: dict[str, QLineEdit | QTextEdit] = {}
        self.business_line_rows: list[BusinessLineRow] = []
        self.business_line_table: QFrame | None = None
        self.industry_search_input = QLineEdit()
        self.industry_results_table = QTableWidget()
        self.industry_detail = QTextEdit()
        self.registration_office_completion_model = QStringListModel(self)
        self.form_sections: dict[str, QWidget] = {}
        self.person_fill_selectors: dict[str, QComboBox] = {}
        self.authorized_person_defaults = authorized_person_defaults or {}
        self.updating_capital = False
        self.syncing_person_fields = False
        self.syncing_address_fields = False
        self._pending_address_sync_key = ""
        self._address_sync_timer = QTimer(self)
        self._address_sync_timer.setSingleShot(True)
        self._address_sync_timer.setInterval(550)
        self._address_sync_timer.timeout.connect(self._flush_pending_address_sync)
        self.last_export_dir: Path | None = None
        self.selected_export_root: Path | None = (
            Path(case.export_dir).parent
            if case and case.export_dir
            else self.default_export_root
        )
        self.ocr_people: list[OcrPerson] = [OcrPerson("Người 1", role="legal_representative")]
        self.current_person_index = 0
        self._initializing = True
        self._export_thread: QThread | None = None
        self._export_worker: DocxExportWorker | None = None
        self._export_case_dir: Path | None = None
        self._export_version_name = ""

        self.raw_ocr_text = QTextEdit()
        self.address_input = QTextEdit()
        self.address_result = QTextEdit()
        self.preview_text = QTextEdit()
        self.ocr_engine_input = NoWheelComboBox()
        self.person_role_input = NoWheelComboBox()
        self.front_image_label = QLabel("Chưa chọn ảnh mặt trước")
        self.back_image_label = QLabel("Chưa chọn ảnh mặt sau")
        self.front_image_preview = ClickableImageLabel("Chưa có ảnh mặt trước")
        self.back_image_preview = ClickableImageLabel("Chưa có ảnh mặt sau")
        self.delete_front_image_button = QPushButton("Xóa ảnh mặt trước")
        self.delete_back_image_button = QPushButton("Xóa ảnh mặt sau")
        self.ocr_progress = QProgressBar()
        self.ocr_status_label = QLabel("Sẵn sàng nhận diện")
        self.ocr_eta_label = QLabel("Đã chạy: --")
        self.people_list_layout = QHBoxLayout()
        self.form_nav_layout = QHBoxLayout()
        self.form_stack = QStackedWidget()
        self.form_button_group = QButtonGroup(self)
        self.form_button_group.setExclusive(True)

        self._build_ui()
        self._refresh_selected_person_images()
        self._seed_from_case(case)
        self._initializing = False
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
        description = QLabel("Quét QR CCCD, chuẩn hóa địa chỉ, kiểm tra dữ liệu và xuất bộ mẫu Word.")
        description.setObjectName("PageDescription")
        description.setWordWrap(True)
        text.addWidget(title)
        text.addWidget(description)

        save_button = QPushButton("Lưu nháp")
        save_button.setObjectName("GhostButton")
        save_button.clicked.connect(self._save_draft)

        template_check_button = QPushButton("Kiểm tra mẫu Word")
        template_check_button.setObjectName("GhostButton")
        template_check_button.clicked.connect(self._check_templates)

        storage_button = QPushButton("Chọn nơi lưu")
        storage_button.setObjectName("GhostButton")
        storage_button.clicked.connect(self._choose_export_root)

        export_button = QPushButton("Xuất Word")
        export_button.setObjectName("PrimaryButton")
        export_button.clicked.connect(self._export_documents)

        header.addWidget(back_button)
        header.addLayout(text, 1)
        header.addWidget(template_check_button)
        header.addWidget(storage_button)
        header.addWidget(save_button)
        header.addWidget(export_button)
        return header

    def _build_ocr_section(self) -> QWidget:
        group = QGroupBox("Quét mã QR CCCD")
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

        role_row = QHBoxLayout()
        role_label = QLabel("Vai trò người đang chọn")
        role_label.setObjectName("FilterLabel")
        self.person_role_input.addItems([label for _, label in PERSON_ROLES])
        for index, (role_key, _) in enumerate(PERSON_ROLES):
            self.person_role_input.setItemData(index, role_key)
        self.person_role_input.currentIndexChanged.connect(self._sync_selected_person_role)
        role_row.addWidget(role_label)
        role_row.addWidget(self.person_role_input, 1)
        role_row.addStretch(1)
        layout.addLayout(role_row)

        actions = QHBoxLayout()
        self.ocr_engine_input.addItem("Quét mã QR CCCD", "qr")
        self.ocr_engine_input.setVisible(False)
        actions.addWidget(self.ocr_engine_input)

        run_button = QPushButton("Quét QR")
        run_button.setObjectName("PrimaryButton")
        run_button.clicked.connect(self._run_ocr)

        actions.addStretch(1)
        actions.addWidget(run_button)
        layout.addLayout(actions)

        image_previews = QHBoxLayout()
        self._setup_image_preview_label(self.front_image_preview, "Bấm để chọn ảnh mặt trước")
        self.front_image_preview.clicked.connect(lambda: self._open_or_choose_person_image("front"))
        self.delete_front_image_button.setObjectName("GhostButton")
        self.delete_front_image_button.clicked.connect(lambda: self._delete_person_image("front"))

        front_box = QVBoxLayout()
        front_title = QLabel("Mặt trước")
        front_title.setObjectName("FilterLabel")
        front_box.addWidget(front_title)
        front_box.addWidget(self.front_image_preview)
        front_box.addWidget(self.front_image_label)
        front_box.addWidget(self.delete_front_image_button)

        image_previews.addLayout(front_box)
        image_previews.addStretch(1)
        layout.addLayout(image_previews)

        self.ocr_progress.setRange(0, 100)
        self.ocr_progress.setValue(0)
        self.ocr_progress.setTextVisible(True)
        self.ocr_progress.setFormat("0%")
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.ocr_progress, 1)
        progress_layout.addWidget(self.ocr_status_label)
        progress_layout.addWidget(self.ocr_eta_label)
        layout.addLayout(progress_layout)

        self.raw_ocr_text.setPlaceholderText("Dữ liệu QR CCCD sẽ hiển thị ở đây để kiểm tra khi cần.")
        self.raw_ocr_text.setMinimumHeight(110)

        layout.addWidget(self._build_cccd_result_section())
        return group

    def _build_cccd_result_section(self) -> QWidget:
        group = QGroupBox("Thông tin CCCD nhận diện")
        group.setObjectName("CccdResultCard")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(8)

        fields: list[tuple[str, str, bool]] = [
            ("legal_representative_full_name", "Họ và tên", False),
            ("legal_representative_id_number", "Số CCCD", False),
            ("legal_representative_date_of_birth", "Ngày sinh", False),
            ("legal_representative_gender", "Giới tính", False),
            ("legal_representative_place_of_origin", "Quê quán", True),
            ("legal_representative_permanent_address", "Nơi thường trú", True),
        ]
        for index, (key, label_text, multiline) in enumerate(fields):
            row = index // 2
            column = (index % 2) * 2
            label = QLabel(label_text)
            label.setObjectName("FilterLabel")
            if multiline:
                field: QLineEdit | QTextEdit = QTextEdit()
                field.setFixedHeight(58)
            else:
                field = QLineEdit()
            field.setPlaceholderText(label_text)
            self.ocr_card_fields[key] = field
            layout.addWidget(label, row, column)
            layout.addWidget(field, row, column + 1)

        apply_button = QPushButton("Đưa thông tin CCCD vào form")
        apply_button.setObjectName("PrimaryButton")
        apply_button.clicked.connect(self._apply_cccd_result_to_form)
        layout.addWidget(apply_button, (len(fields) + 1) // 2, 0, 1, 4, Qt.AlignRight)
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

        first_field_row = 0
        person_target = self._person_fill_target_for_section(title)
        if person_target:
            selector = self._build_person_fill_selector(person_target, title)
            section_grid.addWidget(selector, 0, 0, 1, 4)
            first_field_row = 1

        for index, (key, label_text) in enumerate(fields):
            row = first_field_row + index // 2
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
            next_row = first_field_row + (len(fields) + 1) // 2
            section_grid.addWidget(fill_button, next_row, 0, 1, 4, Qt.AlignRight)

        return section

    def _person_fill_target_for_section(self, title: str) -> str:
        targets = {
            "Thông tin người đại diện pháp luật": "legal_representative",
            "Thông tin giám đốc/Tổng giám đốc": "director",
            "Thông tin người đăng ký/nộp hồ sơ": "applicant",
            "Thông tin người được ủy quyền": "authorized_person",
        }
        return targets.get(title, "")

    def _build_person_fill_selector(self, target: str, title: str) -> QWidget:
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        label_text = "Chọn profile" if target == "authorized_person" else "Chọn thành viên"
        label = QLabel(label_text)
        label.setObjectName("FilterLabel")

        selector = NoWheelComboBox()
        selector.currentIndexChanged.connect(lambda _index, selected=target: self._fill_section_from_selector(selected))
        self.person_fill_selectors[target] = selector
        self._refresh_person_fill_selector(target)

        layout.addWidget(label)
        layout.addWidget(selector, 1)
        return wrapper

    def _create_field(self, key: str) -> QLineEdit | QTextEdit:
        if key in MULTILINE_FIELDS:
            field = QTextEdit()
            field.setFixedHeight(70)
            field.textChanged.connect(self._refresh_preview)
            if key in {"company_address", "legal_representative_permanent_address"}:
                field.textChanged.connect(lambda selected=key: self._schedule_address_sync(selected))
            if key.startswith("legal_representative_"):
                field.textChanged.connect(self._sync_director_from_legal_representative)
        else:
            field = QLineEdit()
            field.textChanged.connect(self._refresh_preview)
            if key == "charter_capital_number":
                field.textChanged.connect(self._handle_capital_number_changed)
            if key == "business_registration_office":
                self._setup_registration_office_field(field)
            if key == "company_province":
                field.textChanged.connect(self._fill_registration_office_from_province)
            if key.startswith("legal_representative_"):
                field.textChanged.connect(self._sync_director_from_legal_representative)
        self.fields[key] = field
        return field

    def _setup_registration_office_field(self, field: QLineEdit) -> None:
        field.setPlaceholderText("Nhập tỉnh/thành phố để chọn phòng đăng ký kinh doanh")
        if not self.registration_office_catalog.is_available:
            return
        completer = QCompleter(self.registration_office_completion_model, field)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        completer.setFilterMode(Qt.MatchContains)
        field.setCompleter(completer)
        field.textEdited.connect(lambda text: self._refresh_registration_office_suggestions(field, text))
        completer.activated[str].connect(lambda value: self._set_field("business_registration_office", value))

    def _refresh_registration_office_suggestions(self, field: QLineEdit, text: str) -> None:
        suggestions = self.registration_office_catalog.suggestions(text)
        self.registration_office_completion_model.setStringList(suggestions)
        if suggestions and field.completer():
            field.completer().complete()

    def _fill_registration_office_from_province(self) -> None:
        if self._initializing:
            return
        office_field = self.fields.get("business_registration_office")
        if not isinstance(office_field, QLineEdit) or office_field.text().strip():
            return
        office = self.registration_office_catalog.display_name_for_province(self._field_value("company_province"))
        if office:
            office_field.setText(office)

    def _build_business_lines_section(self) -> QWidget:
        section = QGroupBox("Ngành nghề kinh doanh")
        layout = QVBoxLayout(section)
        layout.setSpacing(10)
        layout.addWidget(self._build_industry_lookup_panel())

        table = QFrame()
        table.setObjectName("BusinessLineTable")
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.business_line_table = table
        table_layout = QGridLayout(table)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setHorizontalSpacing(0)
        table_layout.setVerticalSpacing(0)

        headers = ["Thông tin ngành nghề", "Mã ngành nghề", "Ngành nghề chính", "Xóa"]
        for column, header_text in enumerate(headers):
            header = QLabel(header_text)
            header.setObjectName("TableHeader")
            header.setAlignment(Qt.AlignCenter)
            header.setFixedHeight(42)
            table_layout.addWidget(header, 0, column)

        table_layout.setRowMinimumHeight(0, 42)
        table_layout.setRowStretch(0, 0)
        table_layout.setColumnStretch(0, 5)
        table_layout.setColumnStretch(1, 2)
        table_layout.setColumnStretch(2, 1)
        table_layout.setColumnStretch(3, 1)

        for index in range(1, 11):
            self._add_business_line_row(table_layout, index, visible=index == 1)

        layout.addWidget(table, 0, Qt.AlignTop)

        add_button = QPushButton("+ Thêm ngành nghề")
        add_button.setObjectName("PrimaryButton")
        add_button.clicked.connect(self._show_next_business_line_row)
        layout.addWidget(add_button, 0, Qt.AlignRight)
        return section

    def _build_industry_lookup_panel(self) -> QWidget:
        panel = QGroupBox("Tra cứu ngành nghề")
        panel.setObjectName("IndustryLookupPanel")
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)

        source = QLabel(
            '<a href="https://vanban.chinhphu.vn/?classid=1&docid=215475&pageid=27160">'
            "Nguồn chính thức: Quyết định 36/2025/QĐ-TTg - Cổng Thông tin điện tử Chính phủ</a>"
        )
        source.setObjectName("IndustryLookupSource")
        source.setOpenExternalLinks(False)
        source.linkActivated.connect(lambda url: QDesktopServices.openUrl(QUrl(url)))
        layout.addWidget(source)

        search_row = QHBoxLayout()
        self.industry_search_input.setObjectName("IndustrySearchInput")
        self.industry_search_input.setPlaceholderText("Nhập mã ngành, tên ngành hoặc từ khóa hoạt động")
        self.industry_search_input.textChanged.connect(self._refresh_industry_results)
        add_selected_button = QPushButton("Thêm ngành đã chọn")
        add_selected_button.setObjectName("PrimaryButton")
        add_selected_button.clicked.connect(self._add_selected_industry_row)
        search_row.addWidget(self.industry_search_input, 1)
        search_row.addWidget(add_selected_button)
        layout.addLayout(search_row)

        self.industry_results_table.setObjectName("IndustryTable")
        self.industry_results_table.setColumnCount(3)
        self.industry_results_table.setHorizontalHeaderLabels(["Mã", "Tên ngành", "Chi tiết"])
        self.industry_results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.industry_results_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.industry_results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.industry_results_table.setAlternatingRowColors(True)
        self.industry_results_table.setMinimumHeight(220)
        self.industry_results_table.itemSelectionChanged.connect(self._show_selected_industry_detail)
        header = self.industry_results_table.horizontalHeader()
        header.setStretchLastSection(True)
        self.industry_results_table.setColumnWidth(0, 95)
        self.industry_results_table.setColumnWidth(1, 360)
        layout.addWidget(self.industry_results_table)

        self.industry_detail.setReadOnly(True)
        self.industry_detail.setMinimumHeight(150)
        self.industry_detail.setPlaceholderText(
            "Chọn một ngành để xem nội dung hoạt động và các trường hợp loại trừ."
        )
        layout.addWidget(self.industry_detail)
        self._refresh_industry_results()
        return panel

    def _refresh_industry_results(self) -> None:
        if not self.industry_catalog.is_available:
            self.industry_results_table.setRowCount(0)
            self.industry_detail.setPlainText("Chưa có dữ liệu ngành nghề trong assets/business_lines/vsic_2025.json.")
            return

        query = self.industry_search_input.text().strip()
        rows = self.industry_catalog.filter_rows(query)
        rows = self._rank_industry_rows(rows, query)[:80]
        self.industry_results_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            code = self._industry_row_code(row)
            name_item = QTableWidgetItem(row.name)
            code_item = QTableWidgetItem(code)
            detail_item = QTableWidgetItem(self._compact_text(row.detail, 160))
            for item in (code_item, name_item, detail_item):
                item.setData(Qt.UserRole, row)
            self.industry_results_table.setItem(row_index, 0, code_item)
            self.industry_results_table.setItem(row_index, 1, name_item)
            self.industry_results_table.setItem(row_index, 2, detail_item)
        if rows:
            self.industry_results_table.selectRow(0)
        else:
            self.industry_detail.setPlainText("Không tìm thấy ngành phù hợp.")

    def _rank_industry_rows(self, rows: list[IndustryRow], query: str) -> list[IndustryRow]:
        folded_query = self.industry_catalog._fold(query)
        if not folded_query:
            return rows[:80]

        def score(row: IndustryRow) -> tuple[int, int, str]:
            code = self._industry_row_code(row)
            folded_name = self.industry_catalog._fold(row.name)
            folded_detail = self.industry_catalog._fold(row.detail)
            if code == query:
                rank = 0
            elif code.startswith(query):
                rank = 1
            elif folded_name.startswith(folded_query):
                rank = 2
            elif folded_query in folded_name:
                rank = 3
            elif folded_query in folded_detail:
                rank = 4
            else:
                rank = 5
            return (rank, len(code), row.name)

        return sorted(rows, key=score)

    def _selected_industry_row(self) -> IndustryRow | None:
        selected = self.industry_results_table.selectedItems()
        if not selected:
            return None
        row = selected[0].data(Qt.UserRole)
        return row if hasattr(row, "levels") and hasattr(row, "name") else None

    def _show_selected_industry_detail(self) -> None:
        row = self._selected_industry_row()
        if row is None:
            return
        code = self._industry_row_code(row)
        sections = [f"{code} - {row.name}" if code else row.name]
        if row.included_detail:
            sections.append(f"Nội dung hoạt động:\n{row.included_detail}")
        if row.excluded_detail:
            sections.append(f"Loại trừ:\n{row.excluded_detail}")
        self.industry_detail.setPlainText("\n\n".join(sections))

    def _add_selected_industry_row(self) -> None:
        row = self._selected_industry_row()
        if row is None:
            QMessageBox.information(self, "Chưa chọn ngành", "Bạn cần chọn một ngành nghề trong bảng tra cứu.")
            return
        target_index = self._first_available_business_line_index()
        if target_index is None:
            QMessageBox.information(self, "Đã đủ ngành nghề", "Hiện form đang hỗ trợ tối đa 10 ngành nghề trong một hồ sơ.")
            return
        business_row = self.business_line_rows[target_index - 1]
        code = self._industry_row_code(row)
        business_row.name_field.setPlainText(self._industry_row_form_text(row))
        business_row.code_field.setText(code)
        self._set_business_line_row_visible(target_index, True)
        if not any(item.main_checkbox.isChecked() for item in self.business_line_rows):
            business_row.main_checkbox.setChecked(True)
        self._refresh_preview()

    def _first_available_business_line_index(self) -> int | None:
        for index, row in enumerate(self.business_line_rows, start=1):
            if not row.cells[0].isVisible():
                return index
            if not row.name_field.toPlainText().strip() and not row.code_field.text().strip():
                return index
        return None

    def _industry_row_code(self, row: IndustryRow) -> str:
        for level in reversed(row.levels):
            if level.strip():
                return level.strip()
        return ""

    def _industry_row_form_text(self, row: IndustryRow) -> str:
        text = row.name.strip()
        if row.detail:
            text = f"{text}\nChi tiết: {row.detail.strip()}"
        return text

    def _compact_text(self, value: str, limit: int) -> str:
        text = " ".join((value or "").split())
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    def _add_business_line_row(self, parent_layout: QGridLayout, index: int, visible: bool) -> None:
        name_field = QTextEdit()
        name_field.setPlaceholderText("Tên ngành nghề\nChi tiết: ...")
        name_field.setFixedHeight(82)
        name_field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        name_field.textChanged.connect(self._refresh_preview)

        code_field = QLineEdit()
        code_field.setAlignment(Qt.AlignCenter)
        code_field.setFixedHeight(40)
        code_field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        code_field.textChanged.connect(self._refresh_preview)

        main_checkbox = QCheckBox()
        main_checkbox.setText("X")
        main_checkbox.setToolTip("Đánh dấu ngành nghề chính")
        main_checkbox.stateChanged.connect(lambda state, selected=index: self._set_main_business_line(selected, state))

        delete_button = QPushButton("Xóa")
        delete_button.setObjectName("GhostButton")
        delete_button.setFixedHeight(40)
        delete_button.clicked.connect(lambda checked=False, selected=index: self._delete_business_line_row(selected))

        cells = [
            self._build_table_cell(name_field),
            self._build_table_cell(code_field),
            self._build_table_cell(main_checkbox, Qt.AlignCenter),
            self._build_table_cell(delete_button),
        ]

        for column, cell in enumerate(cells):
            parent_layout.addWidget(cell, index, column)

        self.fields[f"business_line_{index}_name"] = name_field
        self.fields[f"business_line_{index}_code"] = code_field
        self.business_line_rows.append(BusinessLineRow(name_field, code_field, main_checkbox, delete_button, cells))
        self._set_business_line_row_visible(index, visible)

    def _build_table_cell(self, widget: QWidget, alignment=None) -> QFrame:
        cell = QFrame()
        cell.setObjectName("TableCell")
        cell.setFixedHeight(82)
        cell_layout = QHBoxLayout(cell)
        cell_layout.setContentsMargins(0, 0, 0, 0)
        cell_layout.setSpacing(0)
        if alignment:
            cell_layout.addWidget(widget, 1, alignment)
        else:
            cell_layout.addWidget(widget, 1)
        return cell

    def _show_next_business_line_row(self) -> None:
        for index, row in enumerate(self.business_line_rows, start=1):
            if not row.cells[0].isVisible():
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
        for cell in row.cells:
            cell.setVisible(visible)
        self._resize_business_line_table()

    def _resize_business_line_table(self) -> None:
        if self.business_line_table is None:
            return
        visible_rows = sum(1 for row in self.business_line_rows if row.cells[0].isVisible())
        height = 42 + max(1, visible_rows) * 82 + 2
        self.business_line_table.setMinimumHeight(height)
        self.business_line_table.setMaximumHeight(height)

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

    def _refresh_person_fill_selectors(self) -> None:
        for target in list(self.person_fill_selectors):
            self._refresh_person_fill_selector(target)

    def _refresh_person_fill_selector(self, target: str) -> None:
        selector = self.person_fill_selectors.get(target)
        if selector is None:
            return
        current_data = selector.currentData()
        selector.blockSignals(True)
        selector.clear()
        selector.addItem("Chọn để tự động điền", "")
        if target == "authorized_person" and self.authorized_person_defaults:
            profiles = self.authorized_person_defaults.get("__profiles")
            if isinstance(profiles, list) and profiles:
                for index, profile in enumerate(profiles):
                    if isinstance(profile, dict):
                        name = profile.get("authorized_person_full_name") or f"Profile người ủy quyền {index + 1}"
                        selector.addItem(str(name), f"authorized_profile:{index}")
            else:
                name = self.authorized_person_defaults.get("authorized_person_full_name") or "Profile người ủy quyền đã lưu"
                selector.addItem(name, "authorized_defaults")
        for index, person in enumerate(self.ocr_people):
            selector.addItem(self._person_display_name(index, person), f"person:{index}")
        if current_data:
            match_index = selector.findData(current_data)
            if match_index >= 0:
                selector.setCurrentIndex(match_index)
        selector.blockSignals(False)

    def _person_display_name(self, index: int, person: OcrPerson) -> str:
        role_label = dict(PERSON_ROLES).get(person.role, "Thành viên")
        return f"{index + 1}. {person.name} - {role_label}"

    def _fill_section_from_selector(self, target: str) -> None:
        selector = self.person_fill_selectors.get(target)
        if selector is None:
            return
        selected = str(selector.currentData() or "")
        if not selected:
            return
        if selected == "authorized_defaults":
            self._fill_authorized_person_from_defaults()
            return
        if selected.startswith("authorized_profile:"):
            self._fill_authorized_person_from_profile(selected)
            return
        if not selected.startswith("person:"):
            return
        try:
            person_index = int(selected.split(":", 1)[1])
        except ValueError:
            return
        if person_index < 0 or person_index >= len(self.ocr_people):
            return
        self._fill_section_from_person(target, self.ocr_people[person_index])

    def _fill_authorized_person_from_profile(self, selected: str) -> None:
        try:
            profile_index = int(selected.split(":", 1)[1])
        except ValueError:
            return
        profiles = self.authorized_person_defaults.get("__profiles")
        if not isinstance(profiles, list) or profile_index < 0 or profile_index >= len(profiles):
            return
        profile = profiles[profile_index]
        if not isinstance(profile, dict):
            return
        for key, value in profile.items():
            if str(key).startswith("authorized_person_") and value:
                self._set_field(str(key), str(value))
        self._refresh_preview()

    def _fill_section_from_person(self, target: str, person: OcrPerson) -> None:
        data = self._person_data_for_fill(person)
        full_name = data.get("legal_representative_full_name", "")
        id_number = data.get("legal_representative_id_number", "")
        date_of_birth = data.get("legal_representative_date_of_birth", "")
        gender = data.get("legal_representative_gender", "")
        permanent_address = data.get("legal_representative_permanent_address", "")

        if target == "legal_representative":
            mapping = {
                "legal_representative_full_name": full_name,
                "legal_representative_id_number": id_number,
                "legal_representative_date_of_birth": date_of_birth,
                "legal_representative_gender": gender,
                "legal_representative_nationality": data.get("legal_representative_nationality", ""),
                "legal_representative_permanent_address": permanent_address,
                "legal_representative_place_of_origin": data.get("legal_representative_place_of_origin", ""),
                "legal_representative_issue_date": data.get("legal_representative_issue_date", ""),
                "legal_representative_expiry_date": data.get("legal_representative_expiry_date", ""),
            }
            self._set_fields_from_mapping(mapping)
            self._sync_address_parts("legal_representative_permanent_address")
            self._sync_director_from_legal_representative()
        elif target == "director":
            self._set_fields_from_mapping(
                {
                    "director_full_name": full_name,
                    "director_date_of_birth": date_of_birth,
                    "director_gender": gender,
                    "director_id_number": id_number,
                }
            )
        elif target == "applicant":
            parsed = self.address_parser.parse(permanent_address)
            self._set_fields_from_mapping(
                {
                    "applicant_full_name": full_name,
                    "applicant_date_of_birth": date_of_birth,
                    "applicant_gender": gender,
                    "applicant_id_number": id_number,
                    "applicant_address_detail": parsed.street_line or parsed.village,
                    "applicant_ward": parsed.ward,
                    "applicant_province": parsed.province,
                }
            )
        elif target == "authorized_person":
            self._set_fields_from_mapping(
                {
                    "authorized_person_full_name": full_name,
                    "authorized_person_date_of_birth": date_of_birth,
                    "authorized_person_gender": gender,
                    "authorized_person_id_number": id_number,
                    "authorized_person_contact_address": permanent_address,
                }
            )
        self._refresh_preview()

    def _person_data_for_fill(self, person: OcrPerson) -> dict[str, str]:
        if person.data:
            return person.data
        values = self.form_values()
        if person.role == "legal_representative":
            return {
                "legal_representative_full_name": values.get("legal_representative_full_name", ""),
                "legal_representative_id_number": values.get("legal_representative_id_number", ""),
                "legal_representative_date_of_birth": values.get("legal_representative_date_of_birth", ""),
                "legal_representative_gender": values.get("legal_representative_gender", ""),
                "legal_representative_nationality": values.get("legal_representative_nationality", ""),
                "legal_representative_permanent_address": values.get("legal_representative_permanent_address", ""),
                "legal_representative_place_of_origin": values.get("legal_representative_place_of_origin", ""),
                "legal_representative_issue_date": values.get("legal_representative_issue_date", ""),
                "legal_representative_expiry_date": values.get("legal_representative_expiry_date", ""),
            }
        return {}

    def _set_fields_from_mapping(self, mapping: dict[str, str]) -> None:
        for key, value in mapping.items():
            if value:
                self._set_field(key, value)

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

    def _schedule_address_sync(self, source_key: str) -> None:
        """Delay expensive administrative-place matching until the user pauses typing."""
        if self._initializing or self.syncing_address_fields:
            return
        self._pending_address_sync_key = source_key
        self._address_sync_timer.start()

    def _flush_pending_address_sync(self) -> None:
        source_key = self._pending_address_sync_key
        self._pending_address_sync_key = ""
        if source_key:
            self._sync_address_parts(source_key)
    def _sync_address_parts(self, source_key: str) -> None:
        if self.syncing_address_fields:
            return
        address = self._field_value(source_key)
        if not address:
            return
        parsed = self.address_parser.parse(address)
        detail = self._address_detail_from_result(parsed)
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
        today = datetime.now()
        defaults = {
            "document_day": f"{today.day:02d}",
            "document_month": f"{today.month:02d}",
            "document_year": str(today.year),
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
        self._restore_people(case.form_values if case else {})

    def _restore_people(self, values: dict[str, str]) -> None:
        try:
            count = int(values.get("people_count", "0") or 0)
        except ValueError:
            count = 0
        if count <= 0:
            return
        people: list[OcrPerson] = []
        for index in range(1, count + 1):
            person = OcrPerson(
                name=values.get(f"person_{index}_name") or f"Người {index}",
                role=values.get(f"person_{index}_role") or ("legal_representative" if index == 1 else "member"),
                front_path=values.get(f"person_{index}_front_path", ""),
                back_path=values.get(f"person_{index}_back_path", ""),
            )
            person.data = {
                key: values.get(f"person_{index}_{key}", "")
                for key in [
                    "legal_representative_full_name",
                    "legal_representative_id_number",
                    "legal_representative_date_of_birth",
                    "legal_representative_gender",
                    "legal_representative_nationality",
                    "legal_representative_permanent_address",
                    "legal_representative_place_of_origin",
                    "legal_representative_issue_date",
                    "legal_representative_expiry_date",
                ]
                if values.get(f"person_{index}_{key}", "")
            }
            people.append(person)
        self.ocr_people = people or self.ocr_people
        self.current_person_index = 0
        self._refresh_people_buttons()
        self._refresh_selected_person_images()

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
        self.ocr_people.append(OcrPerson(f"Người {len(self.ocr_people) + 1}", role="member"))
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
        self._refresh_person_fill_selectors()

    def _refresh_selected_person_images(self) -> None:
        person = self.ocr_people[self.current_person_index]
        self.front_image_label.setText(person.front_path or "Chưa chọn ảnh mặt trước")
        self.back_image_label.setText(person.back_path or "Chưa chọn ảnh mặt sau")
        self._set_image_preview(self.front_image_preview, person.front_path, "Bấm để chọn ảnh mặt trước")
        self._set_image_preview(self.back_image_preview, person.back_path, "Bấm để chọn ảnh mặt sau")
        self.delete_front_image_button.setVisible(bool(person.front_path))
        self.delete_back_image_button.setVisible(bool(person.back_path))
        role_index = self._role_index(person.role)
        self.person_role_input.blockSignals(True)
        self.person_role_input.setCurrentIndex(role_index)
        self.person_role_input.blockSignals(False)
        self._update_cccd_result_fields(person.data)

    def _role_index(self, role: str) -> int:
        for index, (role_key, _) in enumerate(PERSON_ROLES):
            if role_key == role:
                return index
        return 0

    def _sync_selected_person_role(self) -> None:
        if not self.ocr_people:
            return
        role = self.person_role_input.currentData() or "member"
        person = self.ocr_people[self.current_person_index]
        person.role = str(role)
        if person.data:
            self._apply_person_data_to_role(person.data, person.role, self.current_person_index + 1)
        self._refresh_people_buttons()
        self._refresh_preview()

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
            label.setToolTip(empty_text)
            return

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            label.setPixmap(QPixmap())
            label.setText("Không đọc được ảnh")
            label.setToolTip(image_path)
            return

        label.setText("")
        label.setToolTip(f"Bấm để xem ảnh đã tải lên\n{image_path}")
        label.setPixmap(pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _open_or_choose_person_image(self, side: str) -> None:
        person = self.ocr_people[self.current_person_index]
        image_path = person.front_path if side == "front" else person.back_path
        if image_path and Path(image_path).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(image_path))))
            return
        self._choose_person_image(side)

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
        person = self.ocr_people[self.current_person_index]
        if not person.front_path:
            QMessageBox.warning(self, "Chưa chọn ảnh mặt trước", "Bạn cần chọn ảnh mặt trước của CCCD để quét mã QR.")
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        start = monotonic()
        try:
            self._update_ocr_progress(0, "Đang chuẩn bị quét QR", "0 giây")
            QApplication.processEvents()
            qr_text = self.ocr_service.scan_qr(
                person.front_path,
                progress_callback=lambda percent, status: self._update_ocr_progress(percent, status, self._format_elapsed(start)),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi quét QR", f"Không thể quét mã QR từ ảnh CCCD:\n{exc}")
            return
        finally:
            QApplication.restoreOverrideCursor()

        self._update_ocr_progress(100, "Hoàn thành quét QR", self._format_elapsed(start))
        self.raw_ocr_text.setPlainText(qr_text)
        self._parse_ocr_text()

    def _update_ocr_progress(self, percent: int, status: str, eta: str) -> None:
        value = max(0, min(100, percent))
        self.ocr_progress.setValue(value)
        self.ocr_progress.setFormat(f"{value}%")
        self.ocr_status_label.setText(status)
        self.ocr_eta_label.setText(f"Đã chạy: {eta}")
        QApplication.processEvents()

    def _format_elapsed(self, start: float) -> str:
        elapsed = max(0.0, monotonic() - start)
        if elapsed < 60:
            return f"{int(elapsed)} giây"
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        return f"{minutes} phút {seconds} giây"

    def _update_cccd_result_fields(self, values: dict[str, str]) -> None:
        for key, field in self.ocr_card_fields.items():
            value = values.get(key, "")
            field.blockSignals(True)
            if isinstance(field, QTextEdit):
                field.setPlainText(value)
            else:
                field.setText(value)
            field.blockSignals(False)

    def _cccd_result_values(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for key, field in self.ocr_card_fields.items():
            if isinstance(field, QTextEdit):
                values[key] = field.toPlainText().strip()
            else:
                values[key] = field.text().strip()
        return values

    def _apply_cccd_result_to_form(self) -> None:
        values = self._cccd_result_values()
        if not any(values.values()):
            QMessageBox.warning(self, "Chưa có dữ liệu CCCD", "Bạn cần quét QR hoặc nhập thông tin CCCD trước.")
            return
        self._apply_cccd_values_to_current_person(values)

    def _apply_cccd_values_to_current_person(self, card_values: dict[str, str]) -> None:
        person = self.ocr_people[self.current_person_index]
        person.data = {key: value for key, value in card_values.items() if value}
        full_name = card_values.get("legal_representative_full_name", "")
        if full_name:
            person.name = f"Người {self.current_person_index + 1} - {full_name}"
            self._refresh_people_buttons()
        self._apply_person_data_to_role(card_values, person.role, self.current_person_index + 1, overwrite=True)
        self._refresh_preview()

    def _parse_ocr_text(self) -> None:
        text = self.raw_ocr_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Chưa có dữ liệu QR", "Bạn cần quét QR CCCD trước.")
            return

        card = self.id_parser.parse_qr(text)
        card_values = card.to_form_values()
        self._update_cccd_result_fields(card_values)
        self._apply_cccd_values_to_current_person(card_values)
        self._parse_registration_office_from_text(text)
        if card.warnings:
            QMessageBox.warning(self, "Cảnh báo dữ liệu CCCD", "\n".join(card.warnings))
        self._refresh_preview()

    def _apply_person_data_to_role(self, card_values: dict[str, str], role: str, person_number: int, overwrite: bool = False) -> None:
        role_prefix_map = {
            "legal_representative": "legal_representative",
            "applicant": "applicant",
            "authorized_person": "authorized_person",
            "member": f"member_{person_number}",
        }
        prefix = role_prefix_map.get(role, "legal_representative")
        source_map = {
            "full_name": "legal_representative_full_name",
            "id_number": "legal_representative_id_number",
            "date_of_birth": "legal_representative_date_of_birth",
            "gender": "legal_representative_gender",
            "permanent_address": "legal_representative_permanent_address",
            "place_of_origin": "legal_representative_place_of_origin",
        }
        target_suffixes = {
            "full_name": "full_name",
            "id_number": "id_number",
            "date_of_birth": "date_of_birth",
            "gender": "gender",
            "permanent_address": "permanent_address",
            "place_of_origin": "place_of_origin",
        }
        for suffix, source_key in source_map.items():
            value = card_values.get(source_key, "")
            if not value:
                continue
            if role == "applicant" and suffix == "permanent_address":
                parsed = self.address_parser.parse(value)
                if overwrite:
                    self._set_field("applicant_address_detail", self._address_detail_from_result(parsed))
                    self._set_field("applicant_ward", parsed.ward)
                    self._set_field("applicant_province", parsed.province)
                else:
                    self._set_field_if_empty("applicant_address_detail", self._address_detail_from_result(parsed))
                    self._set_field_if_empty("applicant_ward", parsed.ward)
                    self._set_field_if_empty("applicant_province", parsed.province)
                continue
            target_key = f"{prefix}_{target_suffixes[suffix]}"
            if overwrite:
                self._set_field(target_key, value)
            else:
                self._set_field_if_empty(target_key, value)

        if role == "legal_representative":
            if card_values.get("legal_representative_permanent_address"):
                self._sync_address_parts("legal_representative_permanent_address")
            self._sync_director_from_legal_representative()
        elif role == "authorized_person":
            address = card_values.get("legal_representative_permanent_address", "")
            if address:
                if overwrite:
                    self._set_field("authorized_person_contact_address", address)
                else:
                    self._set_field_if_empty("authorized_person_contact_address", address)

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
        detail = self._address_detail_from_result(result)
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
        if target == "company_address" and result.province:
            office = self.registration_office_catalog.display_name_for_province(result.province)
            if office:
                self._set_field_if_empty("business_registration_office", office)

    def _address_detail_from_result(self, result) -> str:
        parts = [result.street_line, result.village]
        return ", ".join(part for part in parts if part)

    def _save_draft(self) -> None:
        saved_case = self.build_case_summary()
        self.on_save(saved_case)
        self.case = saved_case
        QMessageBox.information(self, "Đã lưu", "Hồ sơ nháp đã được lưu vào danh sách.")

    def _export_documents(self) -> None:
        if self._export_thread is not None and self._export_thread.isRunning():
            return
        values = self.form_values()
        issues = self._validation_issues(values)
        if issues:
            QMessageBox.warning(self, "Cần kiểm tra dữ liệu", "Bạn cần xử lý trước khi xuất Word:\n- " + "\n- ".join(issues))
            return

        template_dir, export_root = self._template_and_export_dirs()
        case_export_dir = self._case_export_dir(export_root, values)
        version_number = self._next_export_version_number(case_export_dir)
        version_name = f"bản {version_number}"
        version_dir = case_export_dir / version_name

        self._set_export_busy(True)
        self._export_case_dir = case_export_dir
        self._export_version_name = version_name
        self._export_thread = QThread(self)
        self._export_worker = DocxExportWorker(
            template_dir,
            export_root,
            values,
            values.get("company_name", "ho_so_thanh_lap"),
            version_dir,
        )
        self._export_worker.moveToThread(self._export_thread)
        self._export_thread.started.connect(self._export_worker.run)
        self._export_worker.finished.connect(self._handle_export_finished)
        self._export_worker.finished.connect(self._export_thread.quit)
        self._export_thread.finished.connect(self._export_worker.deleteLater)
        self._export_thread.finished.connect(self._export_thread.deleteLater)
        self._export_thread.finished.connect(lambda: self._clear_export_worker())
        self._export_thread.start()

    def _set_export_busy(self, busy: bool) -> None:
        self.setEnabled(not busy)
        if busy:
            self.ocr_status_label.setText("Đang kiểm tra và tạo bộ file Word...")

    def _clear_export_worker(self) -> None:
        self._export_worker = None
        self._export_thread = None
        self._set_export_busy(False)

    @Slot(object)
    def _handle_export_finished(self, payload: object) -> None:
        if self._export_case_dir is None:
            return
        self._finish_export(payload, self._export_case_dir, self._export_version_name)

    def _finish_export(self, payload: object, case_export_dir: Path, version_name: str) -> None:
        data = payload if isinstance(payload, dict) else {}
        if data.get("error"):
            QMessageBox.critical(self, "Lỗi xuất Word", f"Không thể tạo hồ sơ:\n{data['error']}")
            return
        template_issues = data.get("template_issues")
        if template_issues:
            QMessageBox.warning(self, "Mẫu Word còn placeholder chưa hiểu", self._format_template_issues(template_issues))
            return
        result = data.get("result")
        if result is None:
            QMessageBox.critical(self, "Lỗi xuất Word", "Không nhận được kết quả tạo hồ sơ.")
            return

        self.last_export_dir = result.output_dir
        exported_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        generated_documents = [document.output_path.name for document in result.generated]
        export_versions = self._next_export_versions(
            str(case_export_dir),
            str(result.output_dir),
            exported_at,
            generated_documents,
            version_name,
        )
        saved_case = self.build_case_summary(
            status="Đã tạo hồ sơ",
            condition="Đủ dữ liệu",
            warning="Còn placeholder chưa điền trong file Word" if result.unresolved else None,
            export_dir=str(case_export_dir),
            exported_at=exported_at,
            generated_documents=generated_documents,
            export_versions=export_versions,
        )
        self.on_save(saved_case)
        self.case = saved_case
        message = [
            f"Đã tạo {len(result.generated)} file DOCX.",
            f"Thư mục hồ sơ: {case_export_dir}",
            f"Phiên bản: {version_name}",
        ]
        if result.skipped:
            message.append("\nFile chưa xử lý:")
            message.extend(f"- {item}" for item in result.skipped)
        if result.unresolved:
            message.append("\nCòn placeholder chưa điền:")
            message.append(self._format_template_issues(result.unresolved))
        QMessageBox.information(self, "Xuất hồ sơ thành công", "\n".join(message))
        if self.on_export is not None:
            self.on_export(saved_case)

    def _check_templates(self) -> None:
        values = self.form_values()
        template_dir, export_root = self._template_and_export_dirs()
        generator = DocxTemplateGenerator(template_dir=template_dir, export_root=export_root)
        try:
            template_issues = generator.validate_templates(values)
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi kiểm tra mẫu Word", f"Không thể kiểm tra mẫu Word:\n{exc}")
            return
        if not template_issues:
            QMessageBox.information(self, "Mẫu Word hợp lệ", "Tool đã hiểu toàn bộ placeholder trong 5 file mẫu.")
            return
        QMessageBox.warning(self, "Mẫu Word cần kiểm tra", self._format_template_issues(template_issues))

    def _template_and_export_dirs(self) -> tuple[Path, Path]:
        return (
            self.bundle_root / "assets" / "templates" / "word" / "business_registration",
            self.selected_export_root or self.default_export_root,
        )

    def _format_template_issues(self, issues: dict[str, list[str]]) -> str:
        lines: list[str] = []
        for file_name, placeholders in issues.items():
            lines.append(file_name)
            lines.extend(f"  - [{placeholder}]" for placeholder in placeholders[:20])
            if len(placeholders) > 20:
                lines.append(f"  - ... và {len(placeholders) - 20} placeholder khác")
        return "\n".join(lines)

    def _case_export_dir(self, export_root: Path, values: dict[str, str]) -> Path:
        folder_name = self._case_export_folder_name(values)
        return export_root / folder_name

    def _case_export_folder_name(self, values: dict[str, str]) -> str:
        day = values.get("document_day", "").strip().zfill(2)
        month = values.get("document_month", "").strip().zfill(2)
        year = values.get("document_year", "").strip()
        if not (day.strip("0") and month.strip("0") and year):
            now = datetime.now()
            day = f"{now.day:02d}"
            month = f"{now.month:02d}"
            year = str(now.year)
        company_name = (values.get("company_name", "") or "HO SO THANH LAP").strip().upper()
        return self._safe_export_folder_name(f"{day}.{month}.{year}.{company_name}")

    def _safe_export_folder_name(self, value: str) -> str:
        text = re.sub(r'[<>:"/\\|?*]', " ", value)
        text = re.sub(r"\s+", " ", text).strip(" .")
        return text[:160] or "ho_so_thanh_lap"

    def _next_export_version_number(self, case_export_dir: Path) -> int:
        existing_versions = list(self.case.export_versions) if self.case else []
        numbers = [len(existing_versions)]
        if not existing_versions and self.case and self.case.export_dir:
            numbers.append(1)
        if case_export_dir.exists():
            for child in case_export_dir.iterdir():
                if not child.is_dir():
                    continue
                match = re.fullmatch(r"bản\s+(\d+)", child.name.strip(), flags=re.IGNORECASE)
                if match:
                    numbers.append(int(match.group(1)))
        return max(numbers) + 1

    def _next_export_versions(
        self,
        case_export_dir: str,
        version_export_dir: str,
        exported_at: str,
        documents: list[str],
        version_name: str,
    ) -> list[dict[str, object]]:
        existing_versions = list(self.case.export_versions) if self.case else []
        if not existing_versions and self.case and self.case.export_dir:
            existing_versions.append(
                {
                    "name": "bản 1",
                    "export_dir": self.case.export_dir,
                    "exported_at": self.case.exported_at,
                    "documents": self.case.generated_documents,
                }
            )
        existing_versions.append(
            {
                "name": version_name,
                "case_export_dir": case_export_dir,
                "export_dir": version_export_dir,
                "exported_at": exported_at,
                "documents": documents,
            }
        )
        return existing_versions

    def _choose_export_root(self) -> None:
        _, default_export_root = self._template_and_export_dirs()
        selected = QFileDialog.getExistingDirectory(
            self,
            "Chọn nơi lưu hồ sơ Word",
            str(default_export_root),
        )
        if selected:
            self.selected_export_root = Path(selected)
            paths = get_app_paths()
            paths.documents_root = self.selected_export_root
            save_settings(paths, {"export_root": str(self.selected_export_root)})
            QMessageBox.information(self, "Đã chọn nơi lưu", f"Hồ sơ sẽ được lưu tại:\n{self.selected_export_root}")

    def _open_last_export_dir(self) -> None:
        if not self.last_export_dir or not self.last_export_dir.exists():
            QMessageBox.information(self, "Chưa có thư mục", "Bạn chưa xuất hồ sơ trong phiên này.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_export_dir)))

    def _refresh_preview(self) -> None:
        if self._initializing:
            return
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
        self._store_people_values(values)
        self._apply_value_defaults(values)
        return values

    def _store_people_values(self, values: dict[str, str]) -> None:
        values["people_count"] = str(len(self.ocr_people))
        member_index = 0
        for index, person in enumerate(self.ocr_people, start=1):
            values[f"person_{index}_name"] = person.name
            values[f"person_{index}_role"] = person.role
            values[f"person_{index}_front_path"] = person.front_path
            values[f"person_{index}_back_path"] = person.back_path
            for key, value in person.data.items():
                values[f"person_{index}_{key}"] = value
            if person.role in {"legal_representative", "member"}:
                member_index += 1
                self._copy_person_to_member_values(values, member_index, person)
        if member_index == 0 and values.get("legal_representative_full_name"):
            values["member_1_full_name"] = values.get("legal_representative_full_name", "")
            values["member_1_id_number"] = values.get("legal_representative_id_number", "")
            values["member_1_date_of_birth"] = values.get("legal_representative_date_of_birth", "")
            values["member_1_gender"] = values.get("legal_representative_gender", "")
            values["member_1_permanent_address"] = values.get("legal_representative_permanent_address", "")

    def _copy_person_to_member_values(self, values: dict[str, str], member_index: int, person: OcrPerson) -> None:
        data = person.data
        if person.role == "legal_representative":
            data = {
                "legal_representative_full_name": data.get("legal_representative_full_name") or values.get("legal_representative_full_name", ""),
                "legal_representative_id_number": data.get("legal_representative_id_number") or values.get("legal_representative_id_number", ""),
                "legal_representative_date_of_birth": data.get("legal_representative_date_of_birth") or values.get("legal_representative_date_of_birth", ""),
                "legal_representative_gender": data.get("legal_representative_gender") or values.get("legal_representative_gender", ""),
                "legal_representative_permanent_address": data.get("legal_representative_permanent_address") or values.get("legal_representative_permanent_address", ""),
            }
        mapping = {
            "full_name": "legal_representative_full_name",
            "id_number": "legal_representative_id_number",
            "date_of_birth": "legal_representative_date_of_birth",
            "gender": "legal_representative_gender",
            "permanent_address": "legal_representative_permanent_address",
        }
        for suffix, source_key in mapping.items():
            values[f"member_{member_index}_{suffix}"] = data.get(source_key, "")

    def _apply_value_defaults(self, values: dict[str, str]) -> None:
        document_day = values.get("document_day", "").strip()
        document_month = values.get("document_month", "").strip()
        document_year = values.get("document_year", "").strip()

        if not values.get("document_place_date") and document_day and document_month and document_year:
            values["document_place_date"] = f"ngày {document_day} tháng {document_month} năm {document_year}"

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
        }
        if self._company_member_count() <= 1:
            representative_aliases.update(
                {
                    "applicant_full_name": "legal_representative_full_name",
                    "applicant_date_of_birth": "legal_representative_date_of_birth",
                    "applicant_gender": "legal_representative_gender",
                    "applicant_id_number": "legal_representative_id_number",
                    "applicant_address_detail": "legal_representative_address_detail",
                    "applicant_ward": "legal_representative_ward",
                    "applicant_province": "legal_representative_province",
                }
            )
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
        member_count = self._company_member_count()
        values["company_member_count"] = str(member_count)
        values["company_type_label"] = self._case_type_for_members(member_count)
        if member_count == 1:
            values["member_capital_ratio"] = "100%"
        elif capital_digits:
            equal_amount = int(capital_digits) // member_count
            equal_ratio = round(100 / member_count, 2)
            values["member_capital_ratio"] = values.get("member_capital_ratio") or f"{equal_ratio:g}%"
            if self._money_digits(values.get("member_capital_amount", "")) == capital_digits:
                values["member_capital_amount"] = self._format_money(str(equal_amount))
        for index in range(1, member_count + 1):
            default_amount = values.get("charter_capital_number", "")
            default_ratio = "100%" if member_count == 1 else values.get("member_capital_ratio", "")
            if member_count > 1 and capital_digits:
                default_amount = values.get("member_capital_amount", default_amount)
            values.setdefault(f"member_{index}_capital_amount", default_amount)
            values.setdefault(
                f"member_{index}_capital_ratio",
                default_ratio,
            )
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
        export_versions: list[dict[str, object]] | None = None,
    ) -> CaseSummary:
        values = self.form_values()
        existing = self.case
        member_count = self._company_member_count()
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
            export_versions=export_versions if export_versions is not None else (existing.export_versions if existing else []),
            form_values=values,
        )

    def _company_member_count(self) -> int:
        counted_roles = {"legal_representative", "member"}
        count = sum(1 for person in self.ocr_people if person.role in counted_roles)
        return max(1, count)

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

    def _validation_issues(self, values: dict[str, str]) -> list[str]:
        issues = self._missing_required_fields(values)
        if not any(values.get(f"business_line_{index}_name", "").strip() for index in range(1, 11)):
            issues.append("Ít nhất 1 ngành nghề kinh doanh")
        if not any(values.get(f"business_line_{index}_is_main", "").strip() for index in range(1, 11)):
            issues.append("Chọn 1 ngành nghề chính")
        for index in range(1, 11):
            name = values.get(f"business_line_{index}_name", "").strip()
            code = values.get(f"business_line_{index}_code", "").strip()
            if name and not code:
                issues.append(f"Mã ngành nghề của ngành {index}")
        if self._company_member_count() > 1:
            if not values.get("applicant_full_name", "").strip():
                issues.append("Người đăng ký/nộp hồ sơ phải tách riêng với đại diện pháp luật trong hồ sơ nhiều thành viên")
            if values.get("applicant_full_name") and values.get("applicant_full_name") == values.get("legal_representative_full_name"):
                issues.append("Người đăng ký/nộp hồ sơ đang trùng đại diện pháp luật; hãy kiểm tra lại vai trò")
        return issues

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


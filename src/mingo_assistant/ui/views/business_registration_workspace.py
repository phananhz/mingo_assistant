from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from time import monotonic
from uuid import uuid4

from PySide6.QtCore import QObject, QRegularExpression, QSignalBlocker, QThread, QTimer, QUrl, Qt, Signal, Slot, QStringListModel
from PySide6.QtGui import QDesktopServices, QPixmap, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QCompleter,
    QFileDialog,
    QFrame,
    QFormLayout,
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


AUTO_FILL_PROMPT = "\u0043h\u1ecdn \u0111\u1ec3 t\u1ef1 \u0111\u1ed9ng \u0111i\u1ec1n"


def _normalize_organization_issue_place(value: object) -> str:
    """Keep the issuing authority, without a subordinate department suffix."""
    return str(value or "").split(" - ", 1)[0].strip(" ,;-")


def _is_organization_owner(value: object) -> bool:
    text = str(value or "").strip().lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(character for character in text if unicodedata.category(character) != "Mn")
    return text == "to chuc"
from mingo_assistant.services.organization_documents import OrganizationDocumentService
from mingo_assistant.services.personal_profiles import PersonalProfileRepository
from mingo_assistant.services.registration_offices import RegistrationOfficeCatalog
from mingo_assistant.ui.widgets.combo_box import NoWheelComboBox

PERSON_ROLES = [
    ("beneficial_owner", "Chủ sở hữu"),
    ("legal_representative", "Đại diện pháp luật/Giám đốc"),
    ("member", "Thành viên/chủ sở hữu góp vốn"),
    ("applicant", "Người đăng ký/nộp hồ sơ"),
    ("authorized_person", "Người được ủy quyền"),
]


FIELD_GROUPS = [
    ("Thông tin cơ quan tiếp nhận và thời gian ký", [("business_registration_office", "Phòng đăng ký kinh doanh"), ("document_place", "Nơi ký"), ("document_day", "Ngày ký"), ("document_month", "Tháng ký"), ("document_year", "Năm ký"), ("document_place_date", "Dòng địa điểm/ngày tháng")]),
    ("Thông tin người đăng ký/nộp hồ sơ", [("applicant_full_name", "Họ tên người đăng ký"), ("applicant_date_of_birth", "Ngày sinh"), ("applicant_gender", "Giới tính"), ("applicant_id_number", "Số CCCD"), ("applicant_address_detail", "Số nhà/đường/thôn"), ("applicant_ward", "Xã/Phường"), ("applicant_province", "Tỉnh/Thành phố"), ("applicant_phone", "Điện thoại"), ("applicant_email", "Thư điện tử (nếu có)")]),
    ("Thông tin doanh nghiệp", [("company_name", "Tên doanh nghiệp"), ("company_english_name", "Tên tiếng Anh (nếu có)"), ("company_short_name", "Tên viết tắt (nếu có)"), ("company_address", "Địa chỉ trụ sở đầy đủ"), ("company_address_detail", "Số nhà/đường/thôn"), ("company_ward", "Xã/Phường"), ("company_province", "Tỉnh/Thành phố"), ("company_phone", "Số điện thoại công ty"), ("company_email", "Email công ty (nếu có)"), ("company_fax", "Số fax (nếu có)"), ("company_website", "Website (nếu có)"), ("company_land_use_certificate", "Có giấy chứng nhận quyền sử dụng đất thuộc khu vực quốc phòng, an ninh")]),
    ("Ngành nghề kinh doanh", []),
    ("Thông tin chủ sở hữu", [
        ("beneficial_owner_full_name", "Họ tên chủ sở hữu"),
        ("beneficial_owner_date_of_birth", "Ngày sinh"),
        ("beneficial_owner_gender", "Giới tính"),
        ("beneficial_owner_ethnicity", "Dân tộc"),
        ("beneficial_owner_id_number", "Số CCCD"),
        ("beneficial_owner_issue_date", "Ngày cấp CCCD"),
        ("beneficial_owner_address", "Địa chỉ liên lạc"),
        ("organization_owner_name", "Tên tổ chức (ghi bằng chữ in hoa)"),
        ("organization_owner_registration_number", "Mã số doanh nghiệp/Số quyết định thành lập"),
        ("organization_owner_issue_date", "Ngày cấp"),
        ("organization_owner_issue_place", "Nơi cấp"),
        ("organization_owner_address_detail", "Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn"),
        ("organization_owner_ward", "Xã/Phường/Đặc khu"),
        ("organization_owner_province", "Tỉnh/Thành phố trực thuộc trung ương"),
        ("organization_owner_country", "Quốc gia"),
        ("organization_owner_phone", "Điện thoại (nếu có)"),
        ("organization_owner_fax", "Số fax (nếu có)"),
        ("organization_owner_email", "Thư điện tử (nếu có)"),
        ("organization_owner_website", "Website (nếu có)"),
    ]),
    ("Vốn điều lệ và vốn góp", [("charter_capital_number", "Vốn điều lệ bằng số"), ("charter_capital_text", "Vốn điều lệ bằng chữ"), ("charter_capital_full_text", "Vốn điều lệ đầy đủ"), ("cash_capital_text", "Vốn bằng tiền mặt"), ("asset_capital_text", "Vốn bằng tài sản"), ("member_capital_amount", "Vốn góp thành viên"), ("member_capital_ratio", "Tỷ lệ góp vốn"), ("capital_zero", "Giá trị 0 trong bảng vốn")]),
    ("Thông tin người đại diện pháp luật", [("legal_representative_full_name", "Họ tên"), ("legal_representative_id_number", "Số CCCD"), ("legal_representative_date_of_birth", "Ngày sinh"), ("legal_representative_gender", "Giới tính"), ("legal_representative_nationality", "Quốc tịch"), ("legal_representative_ethnicity", "Dân tộc"), ("legal_representative_permanent_address", "Địa chỉ thường trú đầy đủ"), ("legal_representative_address_detail", "Số nhà/đường/thôn"), ("legal_representative_ward", "Xã/Phường"), ("legal_representative_province", "Tỉnh/Thành phố"), ("legal_representative_contact_address", "Địa chỉ liên lạc"), ("legal_representative_issue_date", "Ngày cấp"), ("legal_representative_expiry_date", "Ngày hết hạn"), ("legal_representative_position", "Chức danh"), ("legal_representative_phone", "Điện thoại"), ("legal_representative_email", "Thư điện tử (nếu có)"), ("legal_representative_issue_place", "Nơi cấp CCCD")]),
    ("Thông tin giám đốc/Tổng giám đốc", [("director_full_name", "Họ tên giám đốc"), ("director_date_of_birth", "Ngày sinh"), ("director_gender", "Giới tính"), ("director_id_number", "Số CCCD"), ("director_phone", "Điện thoại"), ("director_position", "Chức danh")]),
    ("Thông tin đăng ký thuế và bảo hiểm xã hội", [("tax_accounting_method", "Hình thức hạch toán"), ("tax_consolidated_financial_statement", "Có báo cáo tài chính hợp nhất"), ("tax_fiscal_year_start", "Năm tài chính bắt đầu (ngày/tháng)"), ("tax_fiscal_year_end", "Năm tài chính kết thúc (ngày/tháng)"), ("tax_labor_count", "Tổng số lao động dự kiến"), ("tax_bot_project", "Hoạt động theo dự án BOT/BTO/BT/BOO, BLT, BTL, O&M"), ("tax_vat_method", "Phương pháp tính thuế GTGT"), ("tax_declaration_period", "Phương thức đóng bảo hiểm xã hội")]),
    ("Danh s\u00e1ch ch\u1ee7 s\u1edf h\u1eefu h\u01b0\u1edfng l\u1ee3i", [("beneficial_owner_list_capital_direct", "9. V\u1ed1n \u0111i\u1ec1u l\u1ec7 tr\u1ef1c ti\u1ebfp"), ("beneficial_owner_list_capital_indirect", "10. V\u1ed1n \u0111i\u1ec1u l\u1ec7 gi\u00e1n ti\u1ebfp"), ("beneficial_owner_list_capital_total", "11. T\u1ed5ng v\u1ed1n \u0111i\u1ec1u l\u1ec7"), ("beneficial_owner_list_voting_direct", "12. Bi\u1ec3u quy\u1ebft tr\u1ef1c ti\u1ebfp"), ("beneficial_owner_list_voting_indirect", "13. Bi\u1ec3u quy\u1ebft gi\u00e1n ti\u1ebfp"), ("beneficial_owner_list_voting_total", "14. T\u1ed5ng bi\u1ec3u quy\u1ebft"), ("beneficial_owner_list_general_partner", "15. Th\u00e0nh vi\u00ean h\u1ee3p danh"), ("beneficial_owner_list_related_group", "16. Nh\u00f3m c\u00e1 nh\u00e2n li\u00ean quan"), ("beneficial_owner_list_control", "17. Ki\u1ec3m so\u00e1t doanh nghi\u1ec7p"), ("beneficial_owner_list_manager", "18. Ng\u01b0\u1eddi qu\u1ea3n l\u00fd doanh nghi\u1ec7p")]),
    ("Thông tin người được ủy quyền", [("authorized_person_full_name", "Họ tên"), ("authorized_person_date_of_birth", "Ngày sinh"), ("authorized_person_gender", "Giới tính"), ("authorized_person_id_number", "Số CCCD"), ("authorized_person_issue_date", "Ngày cấp CCCD"), ("authorized_person_issue_place", "Nơi cấp CCCD"), ("authorized_person_contact_address", "Địa chỉ liên lạc"), ("authorized_person_phone", "Điện thoại"), ("authorized_person_email", "Email (nếu có)")]),
]

BUSINESS_LINE_FIELD_DEFINITIONS = [
    (f"business_line_{index}_name", f"Ngành {index}") for index in range(1, 11)
] + [
    (f"business_line_{index}_code", f"Mã ngành {index}") for index in range(1, 11)
] + [
    (f"business_line_{index}_is_main", f"Ngành chính {index}") for index in range(1, 11)
] + [
    (f"business_line_{index}_detail", f"Mô tả chi tiết ngành {index}") for index in range(1, 11)
]

HIDDEN_FIELD_DEFINITIONS = [
    ("business_lines", "Ghi chú ngành nghề"),
    ("signature_initial_note", "Ghi chú ký"),
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

INDIVIDUAL_OWNER_FIELD_KEYS = (
    "beneficial_owner_full_name",
    "beneficial_owner_date_of_birth",
    "beneficial_owner_gender",
    "beneficial_owner_id_number",
    "beneficial_owner_issue_date",
    "beneficial_owner_address",
)

ORGANIZATION_OWNER_FIELD_KEYS = (
    "organization_owner_name",
    "organization_owner_registration_number",
    "organization_owner_issue_date",
    "organization_owner_issue_place",
    "organization_owner_address_detail",
    "organization_owner_ward",
    "organization_owner_province",
    "organization_owner_country",
    "organization_owner_phone",
    "organization_owner_fax",
    "organization_owner_email",
    "organization_owner_website",
)

ORGANIZATION_OWNER_REPRESENTATIVE_FIELD_KEYS = (
    "organization_owner_representative_number",
    "organization_owner_representative_full_name",
    "organization_owner_representative_date_of_birth",
    "organization_owner_representative_gender",
    "organization_owner_representative_identity",
    "organization_owner_representative_nationality",
    "organization_owner_representative_ethnicity",
    "organization_owner_representative_contact_address",
    "organization_owner_representative_authorized_capital_value",
    "organization_owner_representative_authorized_capital_ratio",
    "organization_owner_representative_authorized_capital_date",
    "organization_owner_representative_signature",
    "organization_owner_representative_notes",
)

@dataclass
class OcrPerson:
    name: str
    role: str = "member"
    front_path: str = ""
    back_path: str = ""
    data: dict[str, str] = field(default_factory=dict)
    recognition_type: str = ""
    raw_text: str = ""
    organization_data: dict[str, str] = field(default_factory=dict)
    organization_extraction_method: str = ""


@dataclass
class BusinessLineRow:
    name_field: QLineEdit
    detail_field: QTextEdit
    code_field: QLineEdit
    main_checkbox: QCheckBox
    delete_button: QPushButton
    cells: list[QFrame]


CAPITAL_SOURCE_LABELS = (
    "Vốn ngân sách nhà nước",
    "Vốn tư nhân",
    "Vốn nước ngoài",
    "Vốn khác",
)
ASSET_CONTRIBUTION_LABELS = (
    "Đồng Việt Nam",
    "Ngoại tệ tự do chuyển đổi",
    "Vàng",
    "Quyền sử dụng đất",
    "Quyền sở hữu trí tuệ",
    "Các tài sản khác",
)
POSITION_OPTIONS = ("Giám đốc", "Tổng giám đốc")


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
        self.organization_document_service = OrganizationDocumentService()
        self.profile_repository = PersonalProfileRepository()
        self.address_parser = AddressParser()
        self.industry_catalog = industry_catalog or IndustryCatalog.load_from_project(self.bundle_root)
        self.registration_office_catalog = RegistrationOfficeCatalog.load_from_project(self.bundle_root)
        self.fields: dict[str, QLineEdit | QTextEdit | QCheckBox | QComboBox] = {}
        self.beneficial_owner_list_auto_fields: dict[str, QLineEdit | QTextEdit] = {}
        self.beneficial_owner_list_selector: QComboBox | None = None
        self.ocr_card_fields: dict[str, QLineEdit | QTextEdit | QComboBox] = {}
        self.cccd_address_status_label: QLabel | None = None
        self._cccd_address_status = ""
        self._cccd_address_message = ""
        self._cccd_address_requires_confirmation = False
        self.organization_card_fields: dict[str, QLineEdit | QTextEdit] = {}
        self.business_line_rows: list[BusinessLineRow] = []
        self.business_line_table: QFrame | None = None
        self.industry_search_input = QLineEdit()
        self.industry_results_table = QTableWidget()
        self.industry_detail = QTextEdit()
        self.registration_office_completion_model = QStringListModel(self)
        self.form_sections: dict[str, QWidget] = {}
        self.form_nav_buttons: dict[str, QPushButton] = {}
        self.form_nav_widget: QWidget | None = None
        self.person_fill_selectors: dict[str, QComboBox] = {}
        self.authorized_person_defaults = authorized_person_defaults or {}
        # Quick-fill profiles are scoped to this open case only.
        self.personal_profiles: list[dict[str, str]] = []
        self.organization_profiles: list[dict[str, str]] = []
        self.organization_owner_profile_selector: QComboBox | None = None
        self.organization_representative_selector: QComboBox | None = None
        self.updating_capital = False
        self.syncing_person_fields = False
        self.syncing_address_fields = False
        self._pending_address_sync_key = ""
        self._address_sync_timer = QTimer(self)
        self._address_sync_timer.setSingleShot(True)
        self._address_sync_timer.setInterval(1800)
        self._address_sync_timer.timeout.connect(self._flush_pending_address_sync)
        self._preview_refresh_timer = QTimer(self)
        self._preview_refresh_timer.setSingleShot(True)
        self._preview_refresh_timer.setInterval(250)
        self._preview_refresh_timer.timeout.connect(self._refresh_preview_now)
        self._director_sync_timer = QTimer(self)
        self._director_sync_timer.setSingleShot(True)
        self._director_sync_timer.setInterval(180)
        self._director_sync_timer.timeout.connect(self._sync_director_from_legal_representative)
        self._refreshing_preview = False
        self._preview_refresh_pending = False
        self.last_export_dir: Path | None = None
        self.selected_export_root: Path | None = (
            Path(case.export_dir).parent
            if case and case.export_dir
            else self.default_export_root
        )
        self.ocr_people: list[OcrPerson] = [OcrPerson("Chưa có tên", role="")]
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
        self.front_image_label = QLabel("Chưa chọn tài liệu")
        self.back_image_label = QLabel("Chưa chọn ảnh mặt sau")
        self.front_image_preview = ClickableImageLabel("Chưa có tài liệu")
        self.back_image_preview = ClickableImageLabel("Chưa có ảnh mặt sau")
        self.delete_front_image_button = QPushButton("Xóa ảnh mặt trước")
        self.delete_back_image_button = QPushButton("Xóa ảnh mặt sau")
        self.ocr_progress = QProgressBar()
        self.ocr_status_label = QLabel("Sẵn sàng nhận diện")
        self.ocr_eta_label = QLabel("Đã chạy: --")
        self.people_list_layout = QHBoxLayout()
        self.people_list_layout.setContentsMargins(0, 0, 0, 0)
        self.people_list_layout.setSpacing(8)
        self.people_list_widget = QWidget()
        self.people_list_widget.setLayout(self.people_list_layout)
        self.people_list_scroll = QScrollArea()
        self.add_person_button = QPushButton("+ Thêm người")
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
        group = QGroupBox("Quét tài liệu")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        people_header = QHBoxLayout()
        people_header.setSpacing(10)
        people_label = QLabel("Danh sách người trong hồ sơ")
        people_label.setObjectName("FilterLabel")
        people_label.setMinimumWidth(176)
        self.people_list_scroll.setWidget(self.people_list_widget)
        self.people_list_scroll.setWidgetResizable(True)
        self.people_list_scroll.setFrameShape(QFrame.NoFrame)
        self.people_list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.people_list_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.people_list_scroll.setFixedHeight(68)
        self.people_list_scroll.setMinimumWidth(240)
        self.add_person_button.setObjectName("GhostButton")
        self.add_person_button.setFixedHeight(40)
        self.add_person_button.clicked.connect(self._add_ocr_person)
        people_header.addWidget(people_label)
        people_header.addWidget(self.people_list_scroll, 1)
        people_header.addWidget(self.add_person_button)
        layout.addLayout(people_header)
        self._refresh_people_buttons()

        self.person_role_input.clear()
        self.person_role_input.addItems([label for _, label in PERSON_ROLES])
        for index, (role_key, _) in enumerate(PERSON_ROLES):
            self.person_role_input.setItemData(index, role_key)
        self.person_role_input.currentIndexChanged.connect(self._sync_selected_person_role)
        self.person_role_input.setVisible(False)

        actions = QHBoxLayout()
        self.ocr_engine_input.addItem("Quét mã QR CCCD", "qr")
        self.ocr_engine_input.setVisible(False)
        actions.addWidget(self.ocr_engine_input)

        run_button = QPushButton("Quét tài liệu")
        run_button.setObjectName("PrimaryButton")
        run_button.clicked.connect(self._run_document_scan)
        actions.addStretch(1)
        actions.addWidget(run_button)

        layout.addLayout(actions)

        image_previews = QHBoxLayout()
        self._setup_image_preview_label(self.front_image_preview, "Bấm để tải lên tài liệu")
        self.front_image_preview.clicked.connect(lambda: self._open_or_choose_person_image("front"))
        self.delete_front_image_button.setObjectName("GhostButton")
        self.delete_front_image_button.clicked.connect(lambda: self._delete_person_image("front"))

        front_box = QVBoxLayout()
        front_title = QLabel("Tải lên tài liệu ở đây")
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

        self.raw_ocr_text.setPlaceholderText("Dữ liệu nhận diện sẽ hiển thị ở đây để kiểm tra khi cần.")
        self.raw_ocr_text.setMinimumHeight(110)

        layout.addWidget(self._build_recognition_result_sections())
        return group

    def _build_recognition_result_sections(self) -> QWidget:
        self.recognition_result_stack = QStackedWidget()
        self.recognition_result_stack.addWidget(self._build_cccd_result_section())
        self.recognition_result_stack.addWidget(self._build_organization_result_section())
        return self.recognition_result_stack

    def _build_organization_result_section(self) -> QWidget:
        group = QGroupBox("Thông tin tổ chức nhận diện")
        group.setObjectName("CccdResultCard")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(8)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        self.organization_document_label = QLabel("Chưa tải tài liệu hồ sơ doanh nghiệp")
        self.organization_document_label.setObjectName("FilterLabel")
        self.organization_document_label.setWordWrap(True)
        layout.addWidget(self.organization_document_label, 0, 0, 1, 4)

        fields: list[tuple[str, str, str]] = [
            ("organization_owner_name", "Tên tổ chức", "text"),
            ("organization_owner_registration_number", "Mã số doanh nghiệp/Số quyết định", "text"),
            ("organization_owner_issue_date", "Ngày cấp", "text"),
            ("organization_owner_issue_place", "Nơi cấp", "text"),
            ("organization_owner_address_detail", "Địa chỉ trụ sở chính", "multiline"),
            ("organization_owner_ward", "Xã/Phường/Đặc khu", "text"),
            ("organization_owner_province", "Tỉnh/Thành phố", "text"),
            ("organization_owner_country", "Quốc gia", "text"),
            ("organization_owner_phone", "Điện thoại (nếu có)", "text"),
            ("organization_owner_fax", "Số fax (nếu có)", "text"),
            ("organization_owner_email", "Thư điện tử (nếu có)", "text"),
            ("organization_owner_website", "Website (nếu có)", "text"),
        ]

        def add_full_row(row: int, item: tuple[str, str, str]) -> None:
            key, label_text, field_type = item
            label = QLabel(label_text)
            label.setObjectName("FilterLabel")
            label.setWordWrap(True)
            field: QLineEdit | QTextEdit
            if field_type == "multiline":
                field = QTextEdit()
                field.setFixedHeight(58)
            else:
                field = QLineEdit()
            field.setPlaceholderText(label_text)
            self.organization_card_fields[key] = field
            layout.addWidget(label, row, 0)
            layout.addWidget(field, row, 1, 1, 3)

        def add_pair(row: int, left: tuple[str, str, str], right: tuple[str, str, str]) -> None:
            for column, item in ((0, left), (2, right)):
                key, label_text, _field_type = item
                label = QLabel(label_text)
                label.setObjectName("FilterLabel")
                label.setWordWrap(True)
                field = QLineEdit()
                field.setPlaceholderText(label_text)
                self.organization_card_fields[key] = field
                layout.addWidget(label, row, column)
                layout.addWidget(field, row, column + 1)

        add_pair(1, fields[0], fields[1])
        add_pair(2, fields[2], fields[3])
        add_full_row(3, fields[4])
        add_full_row(4, fields[5])
        add_full_row(5, fields[6])
        add_full_row(6, fields[7])
        add_pair(7, fields[8], fields[9])
        add_pair(8, fields[10], fields[11])

        save_button = QPushButton("Lưu dữ liệu tổ chức")
        save_button.setObjectName("PrimaryButton")
        save_button.clicked.connect(self._save_organization_profile)
        layout.addWidget(save_button, 9, 0, 1, 4, Qt.AlignRight)
        return group
    def _build_cccd_result_section(self) -> QWidget:
        group = QGroupBox("\u0054h\u00f4ng tin CCCD nh\u1eadn di\u1ec7n")
        group.setObjectName("CccdResultCard")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(8)

        fields: list[tuple[str, str, str]] = [
            ("legal_representative_full_name", "\u0048\u1ecd v\u00e0 t\u00ean", "text"),
            ("legal_representative_id_number", "S\u1ed1 CCCD", "text"),
            ("legal_representative_date_of_birth", "Ng\u00e0y sinh", "text"),
            ("legal_representative_gender", "Gi\u1edbi t\u00ednh", "text"),
            ("legal_representative_issue_date", "Ng\u00e0y c\u1ea5p", "text"),
            ("legal_representative_issue_place", "N\u01a1i c\u1ea5p", "issue_place"),
        ]
        for index, (key, label_text, field_type) in enumerate(fields):
            row = index // 2
            column = (index % 2) * 2
            label = QLabel(label_text)
            label.setObjectName("FilterLabel")
            if field_type == "issue_place":
                field: QLineEdit | QTextEdit | QComboBox = NoWheelComboBox()
                field.setPlaceholderText("Ch\u1ecdn n\u01a1i c\u1ea5p")
                field.addItems((
                    "C\u1ee5c C\u1ea3nh s\u00e1t Qu\u1ea3n l\u00fd H\u00e0nh ch\u00ednh v\u1ec1 Tr\u1eadt t\u1ef1 X\u00e3 h\u1ed9i",
                    "B\u1ed9 C\u00f4ng an",
                ))
                field.setCurrentIndex(-1)
            else:
                field = QLineEdit()
            field.setPlaceholderText(label_text)
            self.ocr_card_fields[key] = field
            layout.addWidget(label, row, column)
            layout.addWidget(field, row, column + 1)

        raw_label = QLabel("\u0110\u1ecba ch\u1ec9 g\u1ed1c tr\u00ean CCCD/QR")
        raw_label.setObjectName("FilterLabel")
        raw_address = QTextEdit()
        raw_address.setReadOnly(True)
        raw_address.setFixedHeight(58)
        raw_address.setPlaceholderText("\u0110\u1ecba ch\u1ec9 nguy\u00ean v\u0103n do QR CCCD tr\u1ea3 v\u1ec1")
        self.ocr_card_fields["legal_representative_raw_permanent_address"] = raw_address
        layout.addWidget(raw_label, 3, 0)
        layout.addWidget(raw_address, 3, 1, 1, 3)

        normalized_label = QLabel("\u0110\u1ecba ch\u1ec9 d\u00f9ng \u0111i\u1ec1n h\u1ed3 s\u01a1")
        normalized_label.setObjectName("FilterLabel")
        normalized_address = QTextEdit()
        normalized_address.setFixedHeight(58)
        normalized_address.setPlaceholderText("\u0110\u1ecba ch\u1ec9 sau khi chuy\u1ec3n \u0111\u1ed5i ho\u1eb7c do ng\u01b0\u1eddi d\u00f9ng x\u00e1c nh\u1eadn")
        normalized_address.textChanged.connect(self._mark_cccd_address_edited)
        self.ocr_card_fields["legal_representative_permanent_address"] = normalized_address
        layout.addWidget(normalized_label, 4, 0)
        layout.addWidget(normalized_address, 4, 1, 1, 3)

        status_label = QLabel("Tr\u1ea1ng th\u00e1i \u0111\u1ecba ch\u1ec9")
        status_label.setObjectName("FilterLabel")
        self.cccd_address_status_label = QLabel()
        self.cccd_address_status_label.setWordWrap(True)
        self.cccd_address_status_label.setObjectName("FilterLabel")
        layout.addWidget(status_label, 5, 0)
        layout.addWidget(self.cccd_address_status_label, 5, 1, 1, 3)
        self._set_cccd_address_status("", "")

        actions = QHBoxLayout()
        actions.addStretch(1)
        confirm_button = QPushButton("X\u00e1c nh\u1eadn \u0111\u1ecba ch\u1ec9")
        confirm_button.setObjectName("GhostButton")
        confirm_button.clicked.connect(self._confirm_cccd_address)
        actions.addWidget(confirm_button)
        apply_button = QPushButton("L\u01b0u d\u1eef li\u1ec7u c\u00e1 nh\u00e2n")
        apply_button.setObjectName("PrimaryButton")
        apply_button.clicked.connect(self._save_cccd_personal_profile)
        actions.addWidget(apply_button)
        layout.addLayout(actions, 6, 0, 1, 4)
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
        self.form_nav_widget = nav_widget
        nav_scroll = QScrollArea()
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QFrame.NoFrame)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        nav_scroll.setFixedHeight(54)
        nav_scroll.setWidget(nav_widget)

        layout.addWidget(nav_scroll)
        self.form_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout.addWidget(self.form_stack, 0, Qt.AlignTop)

        ordered_field_groups = list(FIELD_GROUPS)
        owner_index = next(index for index, (title, _) in enumerate(ordered_field_groups) if title == "Thông tin chủ sở hữu")
        legal_index = next(index for index, (title, _) in enumerate(ordered_field_groups) if title == "Thông tin người đại diện pháp luật")
        legal_group = ordered_field_groups.pop(legal_index)
        if legal_index < owner_index:
            owner_index -= 1
        ordered_field_groups.insert(owner_index, legal_group)

        for index, (title, fields) in enumerate(ordered_field_groups):
            button = QPushButton(title)
            button.setObjectName("PrimaryButton" if index == 0 else "GhostButton")
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.clicked.connect(lambda checked=False, selected=index: self._select_form_section(selected))
            self.form_button_group.addButton(button, index)
            self.form_nav_buttons[title] = button
            self.form_nav_layout.addWidget(button)

            if title == "Ngành nghề kinh doanh":
                section = self._build_business_lines_section()
            elif title == "Vốn điều lệ và vốn góp":
                section = self._build_capital_section()
            elif title == "Danh s\u00e1ch ch\u1ee7 s\u1edf h\u1eefu h\u01b0\u1edfng l\u1ee3i":
                section = self._build_beneficial_owner_list_section(fields)
            elif title == "Th\u00f4ng tin doanh nghi\u1ec7p":
                section = self._build_company_section(fields)
            elif title == "Thông tin chủ sở hữu":
                section = self._build_owner_section(fields)
            else:
                section = self._build_regular_form_section(title, fields)
            self.form_sections[title] = section
            self.form_stack.addWidget(section)
        self.form_nav_layout.addStretch(1)
        self._select_form_section(0)
        return group

    def _select_form_section(self, index: int) -> None:
        self.form_stack.setCurrentIndex(index)
        self._sync_form_stack_height()
        for button in self.form_button_group.buttons():
            button.setObjectName("PrimaryButton" if self.form_button_group.id(button) == index else "GhostButton")
            button.style().unpolish(button)
            button.style().polish(button)

    def _show_beneficial_owner_list_section(self) -> None:
        for index, (title, _fields) in enumerate(FIELD_GROUPS):
            if title == "Danh s\u00e1ch ch\u1ee7 s\u1edf h\u1eefu h\u01b0\u1edfng l\u1ee3i":
                self._select_form_section(index)
                return

    def _sync_form_stack_height(self) -> None:
        current = self.form_stack.currentWidget()
        if current is not None:
            self.form_stack.setFixedHeight(max(250, current.sizeHint().height() + 10))
    def _build_beneficial_owner_list_section(self, fields: list[tuple[str, str]]) -> QWidget:
        section = QGroupBox("Danh sách chủ sở hữu hưởng lợi")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        owner_group = QGroupBox("Thông tin chủ sở hữu")
        owner_layout = QVBoxLayout(owner_group)
        selector_row = QHBoxLayout()
        selector_label = QLabel("Chọn profile cá nhân")
        selector_label.setObjectName("FilterLabel")
        self.beneficial_owner_list_selector = NoWheelComboBox()
        self.beneficial_owner_list_selector.currentIndexChanged.connect(self._fill_beneficial_owner_list_from_selector)
        selector_row.addWidget(selector_label)
        selector_row.addWidget(self.beneficial_owner_list_selector, 1)
        owner_layout.addLayout(selector_row)

        owner_grid = QGridLayout()
        owner_grid.setHorizontalSpacing(14)
        owner_grid.setVerticalSpacing(9)
        owner_grid.setColumnStretch(1, 1)
        owner_grid.setColumnStretch(3, 1)
        owner_fields = [
            ("beneficial_owner_list_number", "STT"),
            ("beneficial_owner_list_full_name", "Họ và tên"),
            ("beneficial_owner_list_date_of_birth", "Ngày sinh"),
            ("beneficial_owner_list_gender", "Giới tính"),
            ("beneficial_owner_list_identity", "Giấy tờ pháp lý"),
            ("beneficial_owner_list_nationality", "Quốc tịch"),
            ("beneficial_owner_list_ethnicity", "Dân tộc"),
            ("beneficial_owner_list_address", "Địa chỉ liên lạc"),
        ]
        for index, (key, label_text) in enumerate(owner_fields):
            row, column = divmod(index, 2)
            label = QLabel(label_text)
            label.setObjectName("FilterLabel")
            field: QLineEdit | QTextEdit
            if key in {"beneficial_owner_list_identity", "beneficial_owner_list_address"}:
                field = QTextEdit()
                field.setFixedHeight(54)
                field.textChanged.connect(self._refresh_preview)
            else:
                field = QLineEdit()
                field.textChanged.connect(self._refresh_preview)
            self.beneficial_owner_list_auto_fields[key] = field
            self.fields[key] = field
            owner_grid.addWidget(label, row, column * 2)
            owner_grid.addWidget(field, row, column * 2 + 1)
        owner_layout.addLayout(owner_grid)
        layout.addWidget(owner_group)

        benefit_group = QGroupBox("Thông tin hưởng lợi của doanh nghiệp")
        benefit_grid = QGridLayout(benefit_group)
        benefit_grid.setHorizontalSpacing(14)
        benefit_grid.setVerticalSpacing(9)
        benefit_grid.setColumnStretch(1, 1)
        benefit_grid.setColumnStretch(3, 1)
        for index, (key, label_text) in enumerate(fields):
            row, column = divmod(index, 2)
            label = QLabel(label_text)
            label.setObjectName("FilterLabel")
            field = QLineEdit()
            field.textChanged.connect(self._refresh_preview)
            self.fields[key] = field
            benefit_grid.addWidget(label, row, column * 2)
            benefit_grid.addWidget(field, row, column * 2 + 1)
        layout.addWidget(benefit_group)
        self._refresh_beneficial_owner_list_selector()
        return section
    def _build_company_section(self, fields: list[tuple[str, str]]) -> QWidget:
        section = QGroupBox("Th\u00f4ng tin doanh nghi\u1ec7p")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)
        selector = self._build_person_fill_selector("company_address", "Th\u00f4ng tin doanh nghi\u1ec7p")
        layout.addWidget(selector)

        labels = dict(fields)
        columns = QHBoxLayout()
        columns.setSpacing(28)
        left_form = QFormLayout()
        right_form = QFormLayout()
        for form in (left_form, right_form):
            form.setHorizontalSpacing(14)
            form.setVerticalSpacing(10)
            form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        left_keys = ["company_name", "company_short_name", "company_address_detail", "company_province", "company_email", "company_website"]
        right_keys = ["company_english_name", "company_address", "company_ward", "company_phone", "company_fax", "company_land_use_certificate"]
        for form, keys in ((left_form, left_keys), (right_form, right_keys)):
            for key in keys:
                label = QLabel(labels[key])
                label.setObjectName("FilterLabel")
                label.setWordWrap(True)
                field = self._create_field(key)
                self.fields[key] = field
                form.addRow(label, field)
        left_wrapper = QWidget()
        left_wrapper.setLayout(left_form)
        right_wrapper = QWidget()
        right_wrapper.setLayout(right_form)
        columns.addWidget(left_wrapper, 1)
        columns.addWidget(right_wrapper, 1)
        layout.addLayout(columns)
        return section

    def _refresh_beneficial_owner_list_selector(self) -> None:
        selector = self.beneficial_owner_list_selector
        if selector is None:
            return
        current_data = selector.currentData()
        selector.blockSignals(True)
        selector.clear()
        selector.addItem(AUTO_FILL_PROMPT, "")
        for index, profile in enumerate(self.personal_profiles):
            name = profile.get("legal_representative_full_name") or f"Profile cá nhân {index + 1}"
            selector.addItem(name, f"personal_profile:{index}")
        for display_index, (person_index, person) in enumerate(self._unique_saved_people(), start=1):
            selector.addItem(self._person_display_name(display_index, person), f"person:{person_index}")
        if current_data:
            match_index = selector.findData(current_data)
            if match_index >= 0:
                selector.setCurrentIndex(match_index)
        selector.blockSignals(False)

    def _fill_beneficial_owner_list_from_selector(self) -> None:
        selector = self.beneficial_owner_list_selector
        if selector is None:
            return
        selected = str(selector.currentData() or "")
        if not selected:
            for key in self.beneficial_owner_list_auto_fields:
                self._set_field(key, "")
            self._refresh_preview()
            return
        data: dict[str, str] = {}
        if selected.startswith("personal_profile:"):
            try:
                profile_index = int(selected.split(":", 1)[1])
            except ValueError:
                return
            if 0 <= profile_index < len(self.personal_profiles):
                data = self.personal_profiles[profile_index]
        elif selected.startswith("person:"):
            try:
                person_index = int(selected.split(":", 1)[1])
            except ValueError:
                return
            if 0 <= person_index < len(self.ocr_people):
                data = self._person_data_for_fill(self.ocr_people[person_index])
        if not data:
            return
        data = self._normalize_person_fill_data(data)
        contact_address = data.get("legal_representative_contact_address") or data.get("legal_representative_permanent_address", "")
        values = {
            "beneficial_owner_list_number": "1",
            "beneficial_owner_list_full_name": data.get("legal_representative_full_name", ""),
            "beneficial_owner_list_date_of_birth": data.get("legal_representative_date_of_birth", ""),
            "beneficial_owner_list_gender": data.get("legal_representative_gender", ""),
            "beneficial_owner_list_identity": self._representative_identity_text(data),
            "beneficial_owner_list_nationality": data.get("legal_representative_nationality", "") or "Việt Nam",
            "beneficial_owner_list_ethnicity": data.get("legal_representative_ethnicity", ""),
            "beneficial_owner_list_address": contact_address,
        }
        for key, value in values.items():
            self._set_field(key, value)
        self._refresh_preview()
    def _build_owner_section(self, fields: list[tuple[str, str]]) -> QWidget:
        section = QGroupBox("Thông tin chủ sở hữu")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        type_row = QHBoxLayout()
        type_label = QLabel("Loại chủ sở hữu")
        type_label.setObjectName("FilterLabel")
        self.owner_type_selector = NoWheelComboBox()
        self.owner_type_selector.addItems(("Cá nhân", "Tổ chức"))
        self.owner_type_selector.currentTextChanged.connect(self._change_owner_type)
        self.fields["owner_type"] = self.owner_type_selector
        type_row.addWidget(type_label)
        type_row.addWidget(self.owner_type_selector, 1)
        layout.addLayout(type_row)

        labels = dict(fields)
        individual_fields = [(key, labels[key]) for key in INDIVIDUAL_OWNER_FIELD_KEYS]
        self.owner_form_stack = QStackedWidget()
        self.owner_form_stack.addWidget(self._build_regular_form_section("Thông tin chủ sở hữu", individual_fields))
        self.owner_form_stack.addWidget(self._build_organization_owner_form(labels))
        layout.addWidget(self.owner_form_stack)
        self._active_owner_type = "Cá nhân"
        return section

    def _build_organization_owner_form(self, labels: dict[str, str]) -> QWidget:
        form_widget = QWidget()
        layout = QVBoxLayout(form_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        profile_row = QHBoxLayout()
        profile_label = QLabel("Thông tin tổ chức đã lưu")
        profile_label.setObjectName("FilterLabel")
        self.organization_owner_profile_selector = NoWheelComboBox()
        self.organization_owner_profile_selector.currentIndexChanged.connect(self._fill_organization_owner_from_selector)
        profile_row.addWidget(profile_label)
        profile_row.addWidget(self.organization_owner_profile_selector, 1)
        layout.addLayout(profile_row)
        self._refresh_organization_owner_selector()
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        def add_row(row: int, key: str, *, column: int = 0, span: int = 1) -> None:
            label = QLabel(labels[key])
            label.setObjectName("FilterLabel")
            label.setWordWrap(True)
            field = self._create_field(key)
            grid.addWidget(label, row, column)
            grid.addWidget(field, row, column + 1, 1, span)

        add_row(0, "organization_owner_name", span=3)
        add_row(1, "organization_owner_registration_number", span=3)
        add_row(2, "organization_owner_issue_date")
        add_row(2, "organization_owner_issue_place", column=2)
        add_row(3, "organization_owner_address_detail", span=3)
        add_row(4, "organization_owner_ward", span=3)
        add_row(5, "organization_owner_province", span=3)
        add_row(6, "organization_owner_country", span=3)
        add_row(7, "organization_owner_phone")
        add_row(7, "organization_owner_fax", column=2)
        add_row(8, "organization_owner_email")
        add_row(8, "organization_owner_website", column=2)
        layout.addLayout(grid)

        representative_fill_row = QHBoxLayout()
        representative_fill_label = QLabel("Tự điền cột 1-8")
        representative_fill_label.setObjectName("FilterLabel")
        self.organization_representative_selector = NoWheelComboBox()
        self.organization_representative_selector.currentIndexChanged.connect(self._fill_organization_representative_from_selector)
        representative_fill_row.addWidget(representative_fill_label)
        representative_fill_row.addWidget(self.organization_representative_selector, 1)
        layout.addLayout(representative_fill_row)
        representative_title = QLabel(
            "Th\u00f4ng tin v\u1ec1 ng\u01b0\u1eddi \u0111\u1ea1i di\u1ec7n theo ph\u00e1p lu\u1eadt/ng\u01b0\u1eddi \u0111\u1ea1i di\u1ec7n theo \u1ee7y quy\u1ec1n c\u1ee7a ch\u1ee7 s\u1edf h\u1eefu"
        )
        representative_title.setObjectName("FilterLabel")
        representative_title.setWordWrap(True)
        layout.addWidget(representative_title)

        table = QTableWidget(4, len(ORGANIZATION_OWNER_REPRESENTATIVE_FIELD_KEYS))
        table.setObjectName("OrganizationRepresentativeTable")
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        table.setHorizontalHeaderLabels([])
        table.horizontalHeader().setVisible(False)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.setWordWrap(True)
        table.setTextElideMode(Qt.ElideNone)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setFixedHeight(292)
        table.setRowHeight(0, 82)
        table.setRowHeight(1, 66)
        table.setRowHeight(2, 34)
        table.setRowHeight(3, 78)

        column_widths = (48, 180, 92, 78, 156, 82, 82, 196, 226, 86, 112, 194, 80)
        for column, width in enumerate(column_widths):
            table.setColumnWidth(column, width)

        def add_header(row: int, column: int, text: str) -> None:
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            item.setFlags(Qt.ItemIsEnabled)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            table.setItem(row, column, item)

        header_labels = (
            "STT",
            "T\u00ean ng\u01b0\u1eddi \u0111\u1ea1i di\u1ec7n theo ph\u00e1p lu\u1eadt/ng\u01b0\u1eddi \u0111\u1ea1i di\u1ec7n theo \u1ee7y quy\u1ec1n",
            "Ng\u00e0y, th\u00e1ng, n\u0103m sinh",
            "Gi\u1edbi t\u00ednh",
            "S\u1ed1, ng\u00e0y c\u1ea5p, c\u01a1 quan c\u1ea5p Gi\u1ea5y t\u1edd ph\u00e1p l\u00fd c\u1ee7a c\u00e1 nh\u00e2n",
            "Qu\u1ed1c t\u1ecbch",
            "D\u00e2n t\u1ed9c",
            "\u0110\u1ecba ch\u1ec9 li\u00ean l\u1ea1c",
        )
        for column, label_text in enumerate(header_labels):
            add_header(0, column, label_text)
            table.setSpan(0, column, 2, 1)
        add_header(0, 8, "V\u1ed1n \u0111\u1ecb\u01b0\u1ee3c \u1ee7y quy\u1ec1n")
        table.setSpan(0, 8, 1, 3)
        add_header(1, 8, "T\u1ed5ng gi\u00e1 tr\u1ecb v\u1ed1n \u0111\u1ecb\u01b0\u1ee3c \u0111\u1ea1i di\u1ec7n (b\u1eb1ng s\u1ed1; VN\u0110 v\u00e0 gi\u00e1 tr\u1ecb t\u01b0\u01a1ng \u0111\u01b0\u01a1ng theo \u0111\u01a1n v\u1ecb ti\u1ec1n n\u01b0\u1edbc ngo\u00e0i, n\u1ebfu c\u00f3)")
        add_header(1, 9, "T\u1ef7 l\u1ec7 (%)")
        add_header(1, 10, "Th\u1eddi \u0111i\u1ec3m \u0111\u1ea1i di\u1ec7n ph\u1ea7n v\u1ed1n")
        add_header(0, 11, "Ch\u1eef k\u00fd c\u1ee7a ng\u01b0\u1eddi \u0111\u1ea1i di\u1ec7n theo ph\u00e1p lu\u1eadt/ng\u01b0\u1eddi \u0111\u1ea1i di\u1ec7n theo \u1ee7y quy\u1ec1n")
        table.setSpan(0, 11, 2, 1)
        add_header(0, 12, "Ghi ch\u00fa (n\u1ebfu c\u00f3)")
        table.setSpan(0, 12, 2, 1)

        for column in range(len(ORGANIZATION_OWNER_REPRESENTATIVE_FIELD_KEYS)):
            add_header(2, column, str(column + 1))

        for column, key in enumerate(ORGANIZATION_OWNER_REPRESENTATIVE_FIELD_KEYS):
            field = QLineEdit()
            field.setReadOnly(column < 8)
            field.setAlignment(Qt.AlignCenter if column in {0, 2, 3, 5, 6, 9, 10} else Qt.AlignLeft | Qt.AlignVCenter)
            field.textChanged.connect(self._refresh_preview)
            self.fields[key] = field
            table.setCellWidget(3, column, field)

        self._refresh_organization_representative_selector()
        layout.addWidget(table)
        return form_widget

    def _refresh_organization_owner_selector(self) -> None:
        selector = self.organization_owner_profile_selector
        if selector is None:
            return
        current_data = selector.currentData()
        selector.blockSignals(True)
        selector.clear()
        selector.addItem("Chọn tổ chức đã lưu", "")
        for index, profile in enumerate(self.organization_profiles):
            name = profile.get("organization_owner_name") or f"Tổ chức {index + 1}"
            registration_number = profile.get("organization_owner_registration_number", "")
            label = f"{name} - {registration_number}" if registration_number else name
            selector.addItem(label, f"organization:{index}")
        if current_data:
            match_index = selector.findData(current_data)
            if match_index >= 0:
                selector.setCurrentIndex(match_index)
        selector.blockSignals(False)

    def _fill_organization_owner_from_selector(self) -> None:
        selector = self.organization_owner_profile_selector
        if selector is None:
            return
        selected = str(selector.currentData() or "")
        if not selected:
            for key in ORGANIZATION_OWNER_FIELD_KEYS:
                self._set_field(key, "")
            self._refresh_preview()
            return
        if not selected.startswith("organization:"):
            return
        try:
            profile_index = int(selected.split(":", 1)[1])
        except ValueError:
            return
        if profile_index < 0 or profile_index >= len(self.organization_profiles):
            return
        profile = self.organization_profiles[profile_index]
        if self.owner_type_selector.currentText() != "Tổ chức":
            with QSignalBlocker(self.owner_type_selector):
                self.owner_type_selector.setCurrentText("Tổ chức")
            self._set_active_owner_type("Tổ chức")
        for key in ORGANIZATION_OWNER_FIELD_KEYS:
            value = profile.get(key, "")
            if key == "organization_owner_issue_place":
                value = _normalize_organization_issue_place(value)
            self._set_field(key, value)
        self._refresh_preview()

    def _refresh_organization_representative_selector(self) -> None:
        selector = self.organization_representative_selector
        if selector is None:
            return
        current_data = selector.currentData()
        selector.blockSignals(True)
        selector.clear()
        selector.addItem(AUTO_FILL_PROMPT, "")
        if self._field_value("legal_representative_full_name") or self._field_value("legal_representative_id_number"):
            name = self._field_value("legal_representative_full_name") or "Người đại diện pháp luật"
            selector.addItem(f"Đại diện pháp luật - {name}", "legal_representative")
        for index, profile in enumerate(self.personal_profiles):
            name = profile.get("legal_representative_full_name") or f"Profile cá nhân {index + 1}"
            selector.addItem(name, f"personal_profile:{index}")
        for display_index, (person_index, person) in enumerate(self._unique_saved_people(), start=1):
            selector.addItem(self._person_display_name(display_index, person), f"person:{person_index}")
        if current_data:
            match_index = selector.findData(current_data)
            if match_index >= 0:
                selector.setCurrentIndex(match_index)
        selector.blockSignals(False)

    def _fill_organization_representative_from_selector(self) -> None:
        selector = self.organization_representative_selector
        if selector is None:
            return
        selected = str(selector.currentData() or "")
        if not selected:
            for key in ORGANIZATION_OWNER_REPRESENTATIVE_FIELD_KEYS[:8]:
                self._set_field(key, "")
            self._refresh_preview()
            return
        data: dict[str, str] = {}
        if selected == "legal_representative":
            data = self._person_data_for_fill(OcrPerson("", role="legal_representative"))
        elif selected.startswith("personal_profile:"):
            try:
                profile_index = int(selected.split(":", 1)[1])
            except ValueError:
                return
            if 0 <= profile_index < len(self.personal_profiles):
                data = self.personal_profiles[profile_index]
        elif selected.startswith("person:"):
            try:
                person_index = int(selected.split(":", 1)[1])
            except ValueError:
                return
            if 0 <= person_index < len(self.ocr_people):
                data = self._person_data_for_fill(self.ocr_people[person_index])
        if not data:
            return
        data = self._normalize_person_fill_data(data)
        contact_address = data.get("legal_representative_contact_address") or data.get("legal_representative_permanent_address", "")
        representative_values = {
            "organization_owner_representative_number": "1",
            "organization_owner_representative_full_name": data.get("legal_representative_full_name", ""),
            "organization_owner_representative_date_of_birth": data.get("legal_representative_date_of_birth", ""),
            "organization_owner_representative_gender": data.get("legal_representative_gender", ""),
            "organization_owner_representative_identity": self._representative_identity_text(data),
            "organization_owner_representative_nationality": data.get("legal_representative_nationality", ""),
            "organization_owner_representative_ethnicity": data.get("legal_representative_ethnicity", ""),
            "organization_owner_representative_contact_address": contact_address,
        }
        for key, value in representative_values.items():
            self._set_field(key, value)
        self._refresh_preview()

    def _representative_identity_text(self, data: dict[str, str]) -> str:
        parts = []
        id_number = data.get("legal_representative_id_number", "").strip()
        issue_date = data.get("legal_representative_issue_date", "").strip()
        issue_place = data.get("legal_representative_issue_place", "").strip()
        if id_number:
            parts.append(f"CCCD số {id_number}")
        if issue_date:
            parts.append(f"cấp ngày {issue_date}")
        if issue_place:
            parts.append(f"nơi cấp {issue_place}")
        return ", ".join(parts)
    def _change_owner_type(self, selected_type: str) -> None:
        current_type = getattr(self, "_active_owner_type", "Cá nhân")
        if selected_type == current_type:
            return
        if self._initializing:
            self._set_active_owner_type(selected_type)
            return

        dialog = QMessageBox(self)
        dialog.setWindowTitle("Chuyển loại chủ sở hữu")
        dialog.setIcon(QMessageBox.Warning)
        dialog.setText("Bạn có muốn chuyển sang chủ sở hữu khác không? Nếu có thì dữ liệu đã điền hiện tại sẽ bị mất.")
        continue_button = dialog.addButton("Tiếp tục", QMessageBox.AcceptRole)
        dialog.addButton("Tạm dừng", QMessageBox.RejectRole)
        dialog.exec()
        if dialog.clickedButton() != continue_button:
            with QSignalBlocker(self.owner_type_selector):
                self.owner_type_selector.setCurrentText(current_type)
            return

        keys_to_clear = (
            INDIVIDUAL_OWNER_FIELD_KEYS
            if current_type == "Cá nhân"
            else ORGANIZATION_OWNER_FIELD_KEYS + ORGANIZATION_OWNER_REPRESENTATIVE_FIELD_KEYS
        )
        for key in keys_to_clear:
            self._set_field(key, "")
        self._set_active_owner_type(selected_type)
        self._refresh_preview()

    def _set_active_owner_type(self, owner_type: str) -> None:
        self._active_owner_type = owner_type
        self.owner_form_stack.setCurrentIndex(0 if owner_type == "Cá nhân" else 1)
        self._sync_form_stack_height()

    def _build_regular_form_section(self, title: str, fields: list[tuple[str, str]]) -> QWidget:
        section = QGroupBox(title)
        section_grid = QGridLayout(section)
        section_grid.setHorizontalSpacing(18)
        section_grid.setVerticalSpacing(10)
        section_grid.setAlignment(Qt.AlignTop)
        section_grid.setColumnStretch(1, 1)
        section_grid.setColumnStretch(3, 1)

        first_field_row = 0
        person_target = self._person_fill_target_for_section(title)
        if person_target:
            selector = self._build_person_fill_selector(person_target, title)
            section_grid.addWidget(selector, 0, 0, 1, 4)
            first_field_row = 1
        elif title == "Thông tin giám đốc/Tổng giám đốc":
            hint = QLabel("Tự động đồng bộ từ Người đại diện pháp luật")
            hint.setObjectName("FilterLabel")
            section_grid.addWidget(hint, 0, 0, 1, 4)
            first_field_row = 1

        for index, (key, label_text) in enumerate(fields):
            row = first_field_row + index // 2
            column = (index % 2) * 2
            label = QLabel(label_text)
            label.setObjectName("FilterLabel")
            field = self._create_field(key)
            if title == "Thông tin giám đốc/Tổng giám đốc" and isinstance(field, QLineEdit):
                field.setReadOnly(True)
            section_grid.addWidget(label, row, column)
            section_grid.addWidget(field, row, column + 1)

        if title == "Thông tin người được ủy quyền":
            fill_button = QPushButton("Tự động điền thông tin người ủy quyền")
            fill_button.setObjectName("PrimaryButton")
            fill_button.clicked.connect(self._fill_authorized_person_from_defaults)
            next_row = first_field_row + (len(fields) + 1) // 2
            section_grid.addWidget(fill_button, next_row, 0, 1, 4, Qt.AlignRight)

        if title == "Th\u00f4ng tin ch\u1ee7 s\u1edf h\u1eefu":
            owner_list_button = QPushButton("M\u1edf danh s\u00e1ch ch\u1ee7 s\u1edf h\u1eefu h\u01b0\u1edfng l\u1ee3i")
            owner_list_button.setObjectName("PrimaryButton")
            owner_list_button.clicked.connect(self._show_beneficial_owner_list_section)
            next_row = first_field_row + (len(fields) + 1) // 2
            section_grid.addWidget(owner_list_button, next_row, 0, 1, 4, Qt.AlignRight)

        return section

    def _person_fill_target_for_section(self, title: str) -> str:
        targets = {
            "Thông tin chủ sở hữu": "beneficial_owner",
            "Thông tin người đại diện pháp luật": "legal_representative",
            "Thông tin người đăng ký/nộp hồ sơ": "applicant",
            "Thông tin người được ủy quyền": "authorized_person",
            "Thông tin doanh nghiệp": "company_address",
        }
        return targets.get(title, "")

    def _build_person_fill_selector(self, target: str, title: str) -> QWidget:
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        label_text = "Chọn profile cá nhân"
        label = QLabel(label_text)
        label.setObjectName("FilterLabel")

        selector = NoWheelComboBox()
        selector.currentIndexChanged.connect(lambda _index, selected=target: self._fill_section_from_selector(selected))
        self.person_fill_selectors[target] = selector
        self._refresh_person_fill_selector(target)

        layout.addWidget(label)
        layout.addWidget(selector, 1)
        return wrapper

    def _create_field(self, key: str) -> QLineEdit | QTextEdit | QCheckBox | QComboBox:
        if key == "company_land_use_certificate":
            field = QCheckBox("Tích X vào ô Có")
            field.setToolTip("Đánh dấu khi doanh nghiệp có giấy chứng nhận quyền sử dụng đất thuộc khu vực nêu trong mẫu")
            field.stateChanged.connect(self._refresh_preview)
        elif key == "legal_representative_position":
            field = NoWheelComboBox()
            field.addItems(POSITION_OPTIONS)
            field.currentTextChanged.connect(self._refresh_preview)
            field.currentTextChanged.connect(self._schedule_director_sync)
        elif key in {"tax_consolidated_financial_statement", "tax_bot_project"}:
            field = QCheckBox("Tích chọn")
            field.setToolTip("Tích để xuất dấu X vào ô vuông tương ứng trong mẫu Word")
            field.stateChanged.connect(self._refresh_preview)
        elif key == "tax_accounting_method":
            field = NoWheelComboBox()
            field.addItems(("Hạch toán độc lập", "Hạch toán phụ thuộc"))
            field.currentTextChanged.connect(self._refresh_preview)
        elif key == "tax_vat_method":
            field = NoWheelComboBox()
            field.addItems(("Khấu trừ", "Trực tiếp trên GTGT", "Trực tiếp trên doanh số", "Không phải nộp thuế GTGT"))
            field.currentTextChanged.connect(self._refresh_preview)
        elif key == "tax_declaration_period":
            field = NoWheelComboBox()
            field.addItems(("Hàng tháng", "03 tháng một lần", "06 tháng một lần"))
            field.currentTextChanged.connect(self._refresh_preview)
        elif key in MULTILINE_FIELDS:
            field = QTextEdit()
            field.setFixedHeight(70)
            field.textChanged.connect(self._refresh_preview)
            if key in {"company_address", "legal_representative_permanent_address"}:
                field.textChanged.connect(lambda selected=key: self._schedule_address_sync(selected))
            if key in {"legal_representative_full_name", "legal_representative_date_of_birth", "legal_representative_gender", "legal_representative_id_number", "legal_representative_phone", "legal_representative_position"}:
                field.textChanged.connect(self._schedule_director_sync)
        else:
            field = QLineEdit()
            field.textChanged.connect(self._refresh_preview)
            if key == "charter_capital_number":
                field.textChanged.connect(self._handle_capital_number_changed)
            if key == "business_registration_office":
                self._setup_registration_office_field(field)
                field.textChanged.connect(self._sync_document_place_from_registration_office)
            if key in {"document_day", "document_month", "document_year"}:
                field.textChanged.connect(self._sync_document_place_date)
            if key in {"document_place", "document_place_date"}:
                field.setReadOnly(True)
            if key == "company_email":
                field.setPlaceholderText("Để trống sẽ xuất ..................")
            if key == "company_province":
                field.textChanged.connect(self._fill_registration_office_from_province)
            if key == "company_phone":
                field.textChanged.connect(self._sync_company_phone_to_tax_registration)
            if key in {"legal_representative_full_name", "legal_representative_date_of_birth", "legal_representative_gender", "legal_representative_id_number", "legal_representative_phone", "legal_representative_position"}:
                field.textChanged.connect(self._schedule_director_sync)
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

    def _signing_place_for_office(self, office_name: str) -> str:
        place = self.registration_office_catalog.province_for_office(office_name).strip()
        if place.casefold() == "thành phố hồ chí minh":
            return place
        return re.sub(r"^(?:Th\u00e0nh ph\u1ed1|T\u1ec9nh)\s+", "", place, flags=re.IGNORECASE).strip()

    def _sync_document_place_from_registration_office(self) -> None:
        place = self._signing_place_for_office(self._field_value("business_registration_office"))
        if place:
            self._set_field("document_place", place)
        self._sync_document_place_date()

    def _sync_document_place_date(self) -> None:
        day = self._field_value("document_day")
        month = self._field_value("document_month")
        year = self._field_value("document_year")
        if not (day and month and year):
            return
        place = self._field_value("document_place")
        date_text = f"ngày {day} tháng {month} năm {year}"
        self._set_field("document_place_date", f"{place}, {date_text}" if place else date_text)
    def _fill_registration_office_from_province(self) -> None:
        if self._initializing:
            return
        office_field = self.fields.get("business_registration_office")
        if not isinstance(office_field, QLineEdit) or office_field.text().strip():
            return
        office = self.registration_office_catalog.display_name_for_province(self._field_value("company_province"))
        if office:
            office_field.setText(office)

    def _build_capital_section(self) -> QWidget:
        section = QGroupBox("Vốn điều lệ và vốn góp")
        layout = QVBoxLayout(section)
        layout.setSpacing(12)

        summary = QGridLayout()
        summary.setHorizontalSpacing(18)
        summary.setVerticalSpacing(10)
        for index, (key, label_text) in enumerate((
            ("charter_capital_number", "Vốn điều lệ (VNĐ)"),
            ("charter_capital_text", "Vốn điều lệ bằng chữ"),
            ("cash_capital_text", "Vốn bằng tiền mặt"),
            ("asset_capital_text", "Vốn bằng tài sản"),
        )):
            label = QLabel(label_text)
            label.setObjectName("FilterLabel")
            field = self._create_field(key)
            if key != "charter_capital_number":
                field.setReadOnly(True)
            summary.addWidget(label, index // 2, (index % 2) * 2)
            summary.addWidget(field, index // 2, (index % 2) * 2 + 1)
        layout.addLayout(summary)
        layout.addWidget(self._build_capital_breakdown_table("Nguồn vốn điều lệ", CAPITAL_SOURCE_LABELS, "capital_source"))
        layout.addWidget(self._build_capital_breakdown_table("Tài sản góp vốn", ASSET_CONTRIBUTION_LABELS, "asset_contribution"))
        return section

    def _build_capital_breakdown_table(self, title: str, labels: tuple[str, ...], prefix: str) -> QWidget:
        group = QGroupBox(title)
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        for column, heading in enumerate(("STT", "Nội dung", "Giá trị (VNĐ)", "Tỷ lệ (%)")):
            label = QLabel(heading)
            label.setObjectName("TableHeader")
            label.setAlignment(Qt.AlignCenter)
            grid.addWidget(label, 0, column)
        for index, label_text in enumerate(labels, start=1):
            index_label = QLabel(str(index))
            index_label.setAlignment(Qt.AlignCenter)
            name_label = QLabel(label_text)
            name_label.setWordWrap(True)
            amount = self._create_field(f"{prefix}_{index}_amount")
            ratio = self._create_field(f"{prefix}_{index}_ratio")
            if isinstance(ratio, QLineEdit):
                ratio.setReadOnly(True)
                ratio.setAlignment(Qt.AlignCenter)
            if isinstance(amount, QLineEdit):
                amount.setAlignment(Qt.AlignRight)
                amount.textChanged.connect(self._recalculate_capital_breakdowns)
            grid.addWidget(index_label, index, 0)
            grid.addWidget(name_label, index, 1)
            grid.addWidget(amount, index, 2)
            grid.addWidget(ratio, index, 3)
        total_row = len(labels) + 1
        total_label = QLabel("Tổng số")
        total_label.setObjectName("TableHeader")
        total_amount = self._create_field(f"{prefix}_total_amount")
        total_ratio = self._create_field(f"{prefix}_total_ratio")
        for field in (total_amount, total_ratio):
            if isinstance(field, QLineEdit):
                field.setReadOnly(True)
                field.setAlignment(Qt.AlignCenter)
        grid.addWidget(total_label, total_row, 0, 1, 2)
        grid.addWidget(total_amount, total_row, 2)
        grid.addWidget(total_ratio, total_row, 3)
        grid.setColumnStretch(1, 4)
        grid.setColumnStretch(2, 2)
        return group

    def _recalculate_capital_breakdowns(self) -> None:
        if self.updating_capital:
            return
        self.updating_capital = True
        try:
            asset_total = self._refresh_capital_breakdown("asset_contribution", len(ASSET_CONTRIBUTION_LABELS))
            self._refresh_capital_breakdown("capital_source", len(CAPITAL_SOURCE_LABELS))
            if asset_total:
                formatted = self._format_money(str(asset_total))
                charter = self.fields.get("charter_capital_number")
                if isinstance(charter, QLineEdit) and charter.text() != formatted:
                    charter.setText(formatted)
                self._set_field("charter_capital_text", self._number_to_vietnamese_words(asset_total).capitalize() + " đồng")
                self._set_field("charter_capital_full_text", f"{formatted} đồng ({self._number_to_vietnamese_words(asset_total).capitalize()} đồng)")
                self._set_field("cash_capital_text", f"{formatted} đồng ({self._number_to_vietnamese_words(asset_total).capitalize()} đồng)")
        finally:
            self.updating_capital = False
        self._refresh_preview()

    def _refresh_capital_breakdown(self, prefix: str, count: int) -> int:
        amounts = [self._money_digits(self._field_value(f"{prefix}_{index}_amount")) for index in range(1, count + 1)]
        total = sum(int(amount or "0") for amount in amounts)
        for index, amount in enumerate(amounts, start=1):
            ratio = (int(amount or "0") * 100 / total) if total else 0
            self._set_field(f"{prefix}_{index}_ratio", f"{ratio:.2f}".rstrip("0").rstrip("."))
        self._set_field(f"{prefix}_total_amount", self._format_money(str(total)) if total else "0")
        self._set_field(f"{prefix}_total_ratio", "100" if total else "0")
        return total
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
        rows = self._rank_industry_rows(rows, query)
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
            return rows

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
        code = self._industry_row_code(row)
        if self._has_duplicate_business_line_code(code):
            QMessageBox.warning(self, "Mã ngành nghề đã tồn tại", f"Đã có mã ngành nghề này trong danh sách: {code}.")
            return
        target_index = self._first_available_business_line_index()
        if target_index is None:
            QMessageBox.information(self, "Đã đủ ngành nghề", "Hiện form đang hỗ trợ tối đa 10 ngành nghề trong một hồ sơ.")
            return
        business_row = self.business_line_rows[target_index - 1]
        business_row.name_field.setText(self._industry_row_form_text(row))
        business_row.detail_field.clear()
        business_row.code_field.setText(code)
        self._set_business_line_row_visible(target_index, True)
        if not any(item.main_checkbox.isChecked() for item in self.business_line_rows):
            business_row.main_checkbox.setChecked(True)
        self._refresh_preview()

    def _has_duplicate_business_line_code(self, code: str, excluded_index: int | None = None) -> bool:
        normalized_code = re.sub(r"\D", "", code or "")
        if not normalized_code:
            return False
        return any(
            index != excluded_index and re.sub(r"\D", "", row.code_field.text()) == normalized_code
            for index, row in enumerate(self.business_line_rows, start=1)
        )

    def _warn_duplicate_business_line_code(self, index: int) -> None:
        code = self.business_line_rows[index - 1].code_field.text()
        if self._has_duplicate_business_line_code(code, excluded_index=index):
            QMessageBox.warning(self, "Mã ngành nghề đã tồn tại", f"Đã có mã ngành nghề này trong danh sách: {code.strip()}.")
    def _first_available_business_line_index(self) -> int | None:
        for index, row in enumerate(self.business_line_rows, start=1):
            if row.cells[0].isHidden():
                return index
            if not row.name_field.text().strip() and not row.detail_field.toPlainText().strip() and not row.code_field.text().strip():
                return index
        return None

    def _industry_row_code(self, row: IndustryRow) -> str:
        # Ho so dang ky doanh nghiep chi su dung ma nganh cap 4.
        for level in reversed(row.levels):
            code = re.sub(r"\D", "", level or "")
            if len(code) == 4:
                return code
        for level in row.levels:
            code = re.sub(r"\D", "", level or "")
            if len(code) >= 4:
                return code[:4]
        return ""

    def _industry_row_form_text(self, row: IndustryRow) -> str:
        return row.name.strip()

    def _compact_text(self, value: str, limit: int) -> str:
        text = " ".join((value or "").split())
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    def _add_business_line_row(self, parent_layout: QGridLayout, index: int, visible: bool) -> None:
        name_field = QLineEdit()
        name_field.setPlaceholderText("Ten nganh nghe")
        name_field.textChanged.connect(self._refresh_preview)

        detail_field = QTextEdit()
        detail_field.setPlaceholderText("Mo ta chi tiet hoac ngoai le (neu co)")
        detail_field.setFixedHeight(58)
        detail_field.textChanged.connect(self._refresh_preview)

        code_field = QLineEdit()
        code_field.setAlignment(Qt.AlignCenter)
        code_field.setPlaceholderText("4 chu so")
        code_field.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d{0,4}"), code_field))
        code_field.setFixedHeight(40)
        code_field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        code_field.textChanged.connect(self._refresh_preview)
        code_field.editingFinished.connect(lambda selected=index: self._warn_duplicate_business_line_code(selected))

        main_checkbox = QCheckBox()
        main_checkbox.setToolTip("Danh dau nganh nghe chinh")
        main_checkbox.stateChanged.connect(lambda state, selected=index: self._set_main_business_line(selected, state))

        delete_button = QPushButton("Xoa")
        delete_button.setObjectName("GhostButton")
        delete_button.setFixedHeight(40)
        delete_button.clicked.connect(lambda checked=False, selected=index: self._delete_business_line_row(selected))

        cells = [
            self._build_business_line_info_cell(name_field, detail_field),
            self._build_table_cell(code_field, Qt.AlignCenter),
            self._build_table_cell(main_checkbox, Qt.AlignCenter),
            self._build_table_cell(delete_button, Qt.AlignCenter),
        ]
        for column, cell in enumerate(cells):
            parent_layout.addWidget(cell, index, column)

        self.fields[f"business_line_{index}_name"] = name_field
        self.fields[f"business_line_{index}_detail"] = detail_field
        self.fields[f"business_line_{index}_code"] = code_field
        self.business_line_rows.append(BusinessLineRow(name_field, detail_field, code_field, main_checkbox, delete_button, cells))
        self._set_business_line_row_visible(index, visible)

    def _build_business_line_info_cell(self, name_field: QLineEdit, detail_field: QTextEdit) -> QFrame:
        cell = QFrame()
        cell.setObjectName("TableCell")
        cell.setFixedHeight(124)
        layout = QVBoxLayout(cell)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(5)
        layout.addWidget(name_field)
        layout.addWidget(detail_field)
        return cell

    def _build_table_cell(self, widget: QWidget, alignment=None) -> QFrame:
        cell = QFrame()
        cell.setObjectName("TableCell")
        cell.setFixedHeight(124)
        cell_layout = QHBoxLayout(cell)
        cell_layout.setContentsMargins(8, 6, 8, 6)
        cell_layout.setSpacing(0)
        if alignment:
            cell_layout.addWidget(widget, 1, alignment)
        else:
            cell_layout.addWidget(widget, 1)
        return cell

    def _show_next_business_line_row(self) -> None:
        for index, row in enumerate(self.business_line_rows, start=1):
            if row.cells[0].isHidden():
                self._set_business_line_row_visible(index, True)
                return
        QMessageBox.information(self, "Đã đủ ngành nghề", "Hiện form đang hỗ trợ tối đa 10 ngành nghề trong một hồ sơ.")

    def _delete_business_line_row(self, index: int) -> None:
        row = self.business_line_rows[index - 1]
        has_data = bool(row.name_field.text().strip() or row.detail_field.toPlainText().strip() or row.code_field.text().strip() or row.main_checkbox.isChecked())
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
        row.detail_field.clear()
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
        visible_rows = sum(1 for row in self.business_line_rows if not row.cells[0].isHidden())
        height = 42 + max(1, visible_rows) * 124 + 2
        self.business_line_table.setMinimumHeight(height)
        self.business_line_table.setMaximumHeight(height)
        QTimer.singleShot(0, self._sync_form_stack_height)

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
        selector.addItem(AUTO_FILL_PROMPT, "")
        if target == "authorized_person":
            self._add_authorized_person_default_options(selector)
        else:
            for index, profile in enumerate(self.personal_profiles):
                name = profile.get("legal_representative_full_name") or f"Profile cá nhân {index + 1}"
                selector.addItem(name, f"personal_profile:{index}")
            for display_index, (person_index, person) in enumerate(self._unique_saved_people(), start=1):
                selector.addItem(self._person_display_name(display_index, person), f"person:{person_index}")
        if current_data:
            match_index = selector.findData(current_data)
            if match_index >= 0:
                selector.setCurrentIndex(match_index)
        selector.blockSignals(False)

    def _person_has_saved_data(self, person: OcrPerson) -> bool:
        return bool(person.data)

    def _person_identity(self, data: dict[str, str]) -> str:
        id_number = str(data.get("legal_representative_id_number", "") or "").strip()
        if id_number:
            return f"id:{id_number}"
        name = str(data.get("legal_representative_full_name", "") or "").strip()
        return f"name:{name.casefold()}" if name else ""

    def _unique_saved_people(self) -> list[tuple[int, OcrPerson]]:
        identities = {self._person_identity(self._normalize_person_fill_data(profile)) for profile in self.personal_profiles}
        identities.discard("")
        people: list[tuple[int, OcrPerson]] = []
        for index, person in enumerate(self.ocr_people):
            if not self._person_has_saved_data(person):
                continue
            identity = self._person_identity(self._person_data_for_fill(person))
            if identity and identity in identities:
                continue
            identities.add(identity)
            people.append((index, person))
        return people

    def _add_authorized_person_default_options(self, selector: QComboBox) -> None:
        profiles = self.authorized_person_defaults.get("__profiles")
        if isinstance(profiles, list) and profiles:
            for index, profile in enumerate(profiles):
                if not isinstance(profile, dict):
                    continue
                name = profile.get("authorized_person_full_name") or f"Người được ủy quyền {index + 1}"
                selector.addItem(str(name), f"authorized_profile:{index}")
            return
        if self.authorized_person_defaults:
            name = self.authorized_person_defaults.get("authorized_person_full_name") or "Profile người ủy quyền đã lưu"
            selector.addItem(name, "authorized_defaults")

    def _person_display_name(self, display_index: int, person: OcrPerson) -> str:
        return f"{display_index}. {self._person_list_name(person)}"

    def _fill_section_from_selector(self, target: str) -> None:
        selector = self.person_fill_selectors.get(target)
        if selector is None:
            return
        selected = str(selector.currentData() or "")
        if not selected:
            self._clear_person_fill_target(target)
            self._refresh_preview()
            return
        if selected == "authorized_defaults":
            self._fill_authorized_person_from_defaults()
            return
        if selected.startswith("authorized_profile:"):
            self._fill_authorized_person_from_profile(selected)
            return
        if selected.startswith("personal_profile:"):
            try:
                profile_index = int(selected.split(":", 1)[1])
            except ValueError:
                return
            if 0 <= profile_index < len(self.personal_profiles):
                profile = self.personal_profiles[profile_index]
                self._fill_section_from_person(target, OcrPerson(profile.get("legal_representative_full_name", ""), data=profile))
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

    def _clear_person_fill_target(self, target: str) -> None:
        fields_by_target = {
            "legal_representative": (
                "legal_representative_full_name", "legal_representative_id_number", "legal_representative_date_of_birth",
                "legal_representative_gender", "legal_representative_nationality", "legal_representative_ethnicity",
                "legal_representative_permanent_address", "legal_representative_address_detail", "legal_representative_ward",
                "legal_representative_province", "legal_representative_contact_address", "legal_representative_issue_date",
                "legal_representative_expiry_date", "legal_representative_issue_place", "legal_representative_phone", "legal_representative_email",
            ),
            "beneficial_owner": INDIVIDUAL_OWNER_FIELD_KEYS,
            "applicant": (
                "applicant_full_name", "applicant_date_of_birth", "applicant_gender", "applicant_id_number",
                "applicant_address_detail", "applicant_ward", "applicant_province", "applicant_phone", "applicant_email",
            ),
            "authorized_person": (
                "authorized_person_full_name", "authorized_person_date_of_birth", "authorized_person_gender",
                "authorized_person_id_number", "authorized_person_issue_date", "authorized_person_issue_place",
                "authorized_person_contact_address", "authorized_person_phone", "authorized_person_email",
            ),
            "company_address": ("company_address", "company_address_detail", "company_ward", "company_province"),
        }
        for key in fields_by_target.get(target, ()):
            self._set_field(key, "")
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

    def _assign_core_role(self, target: str, person: OcrPerson) -> bool:
        role_by_target = {
            "beneficial_owner": "beneficial_owner",
            "legal_representative": "legal_representative",
        }
        selected_role = role_by_target.get(target)
        if not selected_role:
            return True
        for other in self.ocr_people:
            if other is not person and other.role == selected_role:
                other.role = ""
        person.role = selected_role
        self._refresh_people_buttons()
        self._refresh_person_fill_selectors()
        return True

    def _fill_section_from_person(self, target: str, person: OcrPerson) -> None:
        if not self._assign_core_role(target, person):
            return
        data = self._person_data_for_fill(person)
        full_name = data.get("legal_representative_full_name", "")
        id_number = data.get("legal_representative_id_number", "")
        date_of_birth = data.get("legal_representative_date_of_birth", "")
        gender = data.get("legal_representative_gender", "")
        permanent_address = data.get("legal_representative_permanent_address", "")

        if target == "legal_representative":
            self._set_fields_from_mapping(
                {
                    "legal_representative_full_name": full_name,
                    "legal_representative_id_number": id_number,
                    "legal_representative_date_of_birth": date_of_birth,
                    "legal_representative_gender": gender,
                    "legal_representative_nationality": data.get("legal_representative_nationality", ""),
                    "legal_representative_ethnicity": data.get("legal_representative_ethnicity", ""),
                    "legal_representative_permanent_address": permanent_address,
                    "legal_representative_issue_date": data.get("legal_representative_issue_date", ""),
                    "legal_representative_expiry_date": data.get("legal_representative_expiry_date", ""),
                    "legal_representative_issue_place": data.get("legal_representative_issue_place", ""),
                    "legal_representative_phone": data.get("personal_phone", ""),
                    "legal_representative_email": data.get("personal_email", ""),
                }
            )
            self._sync_address_parts("legal_representative_permanent_address")
            self._sync_director_from_legal_representative()
        elif target == "beneficial_owner":
            self._set_fields_from_mapping(
                {
                    "beneficial_owner_full_name": full_name,
                    "beneficial_owner_date_of_birth": date_of_birth,
                    "beneficial_owner_gender": gender,
                    "beneficial_owner_ethnicity": data.get("legal_representative_ethnicity", ""),
                    "beneficial_owner_id_number": id_number,
                    "beneficial_owner_issue_date": data.get("legal_representative_issue_date", ""),
                    "beneficial_owner_address": permanent_address,
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
                    "applicant_phone": data.get("personal_phone", ""),
                    "applicant_email": data.get("personal_email", ""),
                }
            )
        elif target == "authorized_person":
            self._set_fields_from_mapping(
                {
                    "authorized_person_full_name": full_name,
                    "authorized_person_date_of_birth": date_of_birth,
                    "authorized_person_gender": gender,
                    "authorized_person_id_number": id_number,
                    "authorized_person_issue_date": data.get("legal_representative_issue_date", ""),
                    "authorized_person_issue_place": data.get("legal_representative_issue_place", ""),
                    "authorized_person_contact_address": self._authorization_contact_address(data),
                    "authorized_person_phone": data.get("personal_phone", ""),
                    "authorized_person_email": data.get("personal_email", ""),
                }
            )
        elif target == "company_address":
            self._set_field("company_address", permanent_address)
            self._sync_address_parts("company_address")
        self._refresh_preview()

    def _person_data_for_fill(self, person: OcrPerson) -> dict[str, str]:
        if person.data:
            data = self._normalize_person_fill_data(person.data)
            identity = self._person_identity(data)
            # A saved profile is authoritative after edited CCCD data is
            # stored. The OcrPerson saved in a case can retain an old address.
            if identity:
                for profile in reversed(self.personal_profiles):
                    saved_data = self._normalize_person_fill_data(profile)
                    if self._person_identity(saved_data) == identity:
                        return saved_data
            return data
        values = self.form_values()
        if person.role == "legal_representative":
            return self._normalize_person_fill_data({
                "legal_representative_full_name": values.get("legal_representative_full_name", ""),
                "legal_representative_id_number": values.get("legal_representative_id_number", ""),
                "legal_representative_date_of_birth": values.get("legal_representative_date_of_birth", ""),
                "legal_representative_gender": values.get("legal_representative_gender", ""),
                "legal_representative_nationality": values.get("legal_representative_nationality", ""),
                "legal_representative_permanent_address": values.get("legal_representative_permanent_address", ""),
                "legal_representative_contact_address": values.get("legal_representative_contact_address", ""),
                "legal_representative_issue_date": values.get("legal_representative_issue_date", ""),
                "legal_representative_expiry_date": values.get("legal_representative_expiry_date", ""),
                "legal_representative_issue_place": values.get("legal_representative_issue_place", ""),
                "personal_phone": values.get("legal_representative_phone", ""),
                "personal_email": values.get("legal_representative_email", ""),
            })
        return {}

    def _normalize_person_fill_data(self, data: dict[str, str]) -> dict[str, str]:
        normalized = dict(data)
        aliases = {
            "legal_representative_full_name": ("personal_full_name", "full_name"),
            "legal_representative_id_number": ("personal_id_number", "id_number"),
            "legal_representative_date_of_birth": ("personal_date_of_birth", "date_of_birth"),
            "legal_representative_gender": ("personal_gender", "gender"),
            "legal_representative_nationality": ("personal_nationality", "nationality"),
            "legal_representative_ethnicity": ("personal_ethnicity", "ethnicity"),
            "legal_representative_permanent_address": ("personal_permanent_address", "permanent_address"),
            "legal_representative_contact_address": ("personal_contact_address", "contact_address"),
            "legal_representative_issue_date": ("personal_issue_date", "issue_date"),
            "legal_representative_issue_place": ("personal_issue_place", "issue_place"),
        }
        for target, sources in aliases.items():
            if normalized.get(target):
                continue
            normalized[target] = next((str(data.get(source, "") or "") for source in sources if data.get(source)), "")
        return normalized

    @staticmethod
    def _authorization_contact_address(data: dict[str, str]) -> str:
        """Use one explicit fallback order for the authorization UI and DOCX."""
        for key in (
            "legal_representative_contact_address",
            "personal_contact_address",
            "legal_representative_permanent_address",
            "personal_permanent_address",
        ):
            value = str(data.get(key, "") or "").strip()
            if value:
                return value
        return ""

    def _set_fields_from_mapping(self, mapping: dict[str, str]) -> None:
        for key, value in mapping.items():
            if value:
                self._set_field(key, value)

    def _sync_company_phone_to_tax_registration(self) -> None:
        self._refresh_preview()

    def _schedule_director_sync(self, *_args) -> None:
        if not self._initializing:
            self._director_sync_timer.start()

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
                "director_position": "legal_representative_position",
                "director_phone": "legal_representative_phone",
            }
            for target, source in pairs.items():
                self._set_field(target, self._field_value(source))
        finally:
            self.syncing_person_fields = False
        self._refresh_preview()

    def _field_value(self, key: str) -> str:
        field = self.fields.get(key)
        if isinstance(field, QTextEdit):
            return field.toPlainText().strip()
        if isinstance(field, QLineEdit):
            return field.text().strip()
        if isinstance(field, QComboBox):
            return field.currentText().strip()
        if isinstance(field, QCheckBox):
            return "X" if field.isChecked() else ""
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
        # Confirmation only gates automatic use of an ambiguous CCCD scan. A
        # user-entered or saved address can still be split when labels are clear.
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
                # A new profile selection must replace every stored address
                # component. Otherwise an absent component leaves an old
                # ward, province, or detail in the case.
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
        self._sync_capital_breakdowns_from_charter(formatted)
        self._refresh_preview()

    def _sync_capital_breakdowns_from_charter(self, formatted: str) -> None:
        if "asset_contribution_1_amount" not in self.fields:
            return
        source_other = any(self._money_digits(self._field_value(f"capital_source_{index}_amount")) for index in (1, 3, 4))
        asset_other = any(self._money_digits(self._field_value(f"asset_contribution_{index}_amount")) for index in range(2, 7))
        self.updating_capital = True
        try:
            if not source_other:
                self._set_field("capital_source_2_amount", formatted)
            if not asset_other:
                self._set_field("asset_contribution_1_amount", formatted)
            self._refresh_capital_breakdown("capital_source", len(CAPITAL_SOURCE_LABELS))
            self._refresh_capital_breakdown("asset_contribution", len(ASSET_CONTRIBUTION_LABELS))
        finally:
            self.updating_capital = False

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
            "tax_accounting_method": "Hạch toán độc lập",
            "tax_fiscal_year_start": "01/01",
            "tax_fiscal_year_end": "31/12",
            "tax_labor_count": "1",
            "tax_vat_method": "Khấu trừ",
            "tax_declaration_period": "Hàng tháng",
            "signature_initial_note": "KHÔNG KÝ NHÁY",
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
                role=values.get(f"person_{index}_role", ""),
                front_path=values.get(f"person_{index}_front_path", ""),
                back_path=values.get(f"person_{index}_back_path", ""),
                recognition_type=values.get(f"person_{index}_recognition_type", ""),
                raw_text=values.get(f"person_{index}_raw_text", ""),
                organization_extraction_method=values.get(f"person_{index}_organization_extraction_method", ""),
            )
            person.data = {
                key: values.get(f"person_{index}_{key}", "")
                for key in [
                    "legal_representative_full_name", "legal_representative_id_number",
                    "legal_representative_date_of_birth", "legal_representative_gender",
                    "legal_representative_nationality", "legal_representative_ethnicity", "legal_representative_permanent_address",
                    "legal_representative_issue_date", "legal_representative_expiry_date",
                    "legal_representative_issue_place",
                ]
                if values.get(f"person_{index}_{key}", "")
            }
            person.organization_data = {
                key: values.get(f"person_{index}_organization_{key}", "")
                for key in ORGANIZATION_OWNER_FIELD_KEYS
                if values.get(f"person_{index}_organization_{key}", "")
            }
            if not person.recognition_type:
                person.recognition_type = "organization" if person.organization_data else "individual" if person.data else ""
            people.append(person)
        self.ocr_people = people or self.ocr_people
        self.current_person_index = 0
        self._refresh_people_buttons()
        self._refresh_selected_person_images()

    def _restore_business_lines(self, values: dict[str, str]) -> None:
        for index, row in enumerate(self.business_line_rows, start=1):
            name = values.get(f"business_line_{index}_name", "")
            detail = values.get(f"business_line_{index}_detail", "")
            code = re.sub(r"\D", "", values.get(f"business_line_{index}_code", ""))[:4]
            # Ho so cu gop Chi tiet vao ten nganh; tach ra khi mo de chinh sua.
            if not detail and re.search(r"(?i)\n?chi\s*tiết\s*:", name):
                name, detail = re.split(r"(?i)\n?chi\s*tiết\s*:", name, maxsplit=1)
            is_main = bool(values.get(f"business_line_{index}_is_main", ""))
            has_data = bool(name or detail or code or is_main)
            if index == 1 or has_data:
                self._set_business_line_row_visible(index, True)
            if name:
                row.name_field.setText(name.strip())
            if detail:
                row.detail_field.setPlainText(detail.strip())
            if code:
                row.code_field.setText(code)
            if is_main:
                row.main_checkbox.setChecked(True)
        self._resize_business_line_table()

    def _add_ocr_person(self) -> None:
        if len(self.ocr_people) >= 5:
            QMessageBox.information(self, "Đã đủ người", "Hồ sơ chỉ hỗ trợ tối đa 5 người.")
            return
        self._persist_current_person_recognition()
        self.ocr_people.append(OcrPerson("Chưa có tên", role=""))
        self.current_person_index = len(self.ocr_people) - 1
        self._refresh_people_buttons()
        self._refresh_selected_person_images()

    def _select_ocr_person(self, index: int) -> None:
        if index == self.current_person_index:
            return
        self._persist_current_person_recognition()
        self.current_person_index = index
        self._refresh_people_buttons()
        self._refresh_selected_person_images()

    def _person_list_name(self, person: OcrPerson) -> str:
        name = re.sub(r"^Người\s+\d+\s*-\s*", "", person.name or "", flags=re.IGNORECASE).strip()
        return name or "Chưa có tên"

    def _refresh_people_buttons(self) -> None:
        while self.people_list_layout.count():
            item = self.people_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for index, person in enumerate(self.ocr_people):
            full_name = self._person_list_name(person)
            profile_type = "Tổ chức" if person.recognition_type == "organization" else "Cá nhân"
            button = QPushButton(self._compact_text(f"{profile_type}: {full_name}", 24))
            button.setObjectName("PrimaryButton" if index == self.current_person_index else "GhostButton")
            button.setFixedSize(180, 40)
            button.setToolTip(f"{profile_type}: {full_name}")
            button.clicked.connect(lambda checked=False, selected=index: self._select_ocr_person(selected))
            self.people_list_layout.addWidget(button)

        content_width = max(180, len(self.ocr_people) * 188 - 8)
        self.people_list_widget.setMinimumSize(content_width, 40)
        self.people_list_widget.adjustSize()
        self.add_person_button.setEnabled(len(self.ocr_people) < 5)
        self.add_person_button.setToolTip("Hồ sơ chỉ hỗ trợ tối đa 5 người" if len(self.ocr_people) >= 5 else "Thêm người vào hồ sơ")
        self._refresh_person_fill_selectors()

    def _refresh_selected_person_images(self) -> None:
        person = self.ocr_people[self.current_person_index]
        self.front_image_label.setText(person.front_path or "Chưa chọn tài liệu")
        self.back_image_label.setText(person.back_path or "Chưa chọn ảnh mặt sau")
        self._set_image_preview(self.front_image_preview, person.front_path, "Bấm để tải lên tài liệu")
        self._set_image_preview(self.back_image_preview, person.back_path, "Bấm để chọn ảnh mặt sau")
        is_front_document = Path(person.front_path).suffix.lower() == ".pdf"
        self.delete_front_image_button.setText("Xóa tài liệu" if is_front_document else "Xóa ảnh mặt trước")
        self.delete_front_image_button.setVisible(bool(person.front_path))
        self.delete_back_image_button.setVisible(bool(person.back_path))
        role_index = self._role_index(person.role)
        self.person_role_input.blockSignals(True)
        self.person_role_input.setCurrentIndex(role_index)
        self.person_role_input.blockSignals(False)
        self._restore_selected_person_recognition(person)

    def _persist_current_person_recognition(self) -> None:
        if not self.ocr_people or not (0 <= self.current_person_index < len(self.ocr_people)):
            return
        person = self.ocr_people[self.current_person_index]
        if person.recognition_type == "organization":
            person.organization_data = self._organization_result_values()
        elif person.recognition_type == "individual":
            person.data = self._cccd_result_values()
        if person.recognition_type:
            person.raw_text = self.raw_ocr_text.toPlainText()

    def _restore_selected_person_recognition(self, person: OcrPerson) -> None:
        self.raw_ocr_text.setPlainText(person.raw_text)
        if person.recognition_type == "organization":
            self._update_organization_result_fields(person.organization_data)
            method = "OCR" if person.organization_extraction_method == "ocr" else "văn bản PDF"
            document_name = Path(person.front_path).name if person.front_path else "Tài liệu tổ chức"
            self.organization_document_label.setText(f"Tài liệu: {document_name} - Nhận diện bằng {method}")
            self.recognition_result_stack.setCurrentIndex(1)
            self._update_ocr_progress(100, "Đã nhận diện thông tin tổ chức", "")
            return

        self._update_cccd_result_fields(person.data)
        self.recognition_result_stack.setCurrentIndex(0)
        if person.recognition_type == "individual" and person.data:
            self._update_ocr_progress(100, "Đã nhận diện thông tin CCCD", "")
        else:
            self._update_ocr_progress(0, "Sẵn sàng nhận diện", "--")

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

        if Path(image_path).suffix.lower() == ".pdf":
            label.setPixmap(QPixmap())
            label.setText("Tài liệu PDF đã tải lên\nBấm để mở tài liệu")
            label.setToolTip(f"Bấm để mở tài liệu đã tải lên\n{image_path}")
            return

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            label.setPixmap(QPixmap())
            label.setText("Không đọc được tài liệu")
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
            "Tải lên tài liệu",
            "",
            "Tài liệu hỗ trợ (*.pdf *.png *.jpg *.jpeg *.bmp *.tif *.tiff);;PDF (*.pdf);;Ảnh (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;Tất cả file (*.*)",
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
        is_document = side == "front" and Path(current_path).suffix.lower() == ".pdf"
        if is_document:
            title = "Xóa tài liệu"
            message = "Bạn có muốn xóa tài liệu đã tải lên không?"
        else:
            side_label = "mặt trước" if side == "front" else "mặt sau"
            title = "Xóa ảnh CCCD"
            message = f"Bạn có muốn xóa ảnh {side_label} đã tải lên không?"
        answer = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        if side == "front":
            person.front_path = ""
            person.data.clear()
            person.organization_data.clear()
            person.recognition_type = ""
            person.raw_text = ""
            person.organization_extraction_method = ""
        else:
            person.back_path = ""
        self._refresh_selected_person_images()

    def _run_document_scan(self) -> None:
        """Choose the recognition engine from the uploaded file type."""
        person = self.ocr_people[self.current_person_index]
        if not person.front_path:
            QMessageBox.warning(
                self,
                "Chưa chọn tài liệu",
                "Bạn cần tải lên tài liệu trước khi chọn Quét tài liệu.",
            )
            return

        suffix = Path(person.front_path).suffix.lower()
        if suffix == ".pdf":
            self._scan_organization_document(person.front_path)
            return
        if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
            self._run_qr_scan(person.front_path)
            return

        QMessageBox.warning(
            self,
            "Định dạng chưa hỗ trợ",
            "Vui lòng tải lên file PDF hoặc ảnh CCCD hợp lệ.",
        )

    def _run_ocr(self) -> None:
        # Keep the old entry point for existing callers and saved UI state.
        self._run_document_scan()

    def _run_qr_scan(self, image_path: str) -> None:
        self.recognition_result_stack.setCurrentIndex(0)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        start = monotonic()
        try:
            self._update_ocr_progress(0, "Đang chuẩn bị quét QR", "0 giây")
            QApplication.processEvents()
            qr_text = self.ocr_service.scan_qr(
                image_path,
                progress_callback=lambda percent, status: self._update_ocr_progress(
                    percent, status, self._format_elapsed(start)
                ),
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Lỗi quét QR",
                f"Không thể quét mã QR từ ảnh CCCD:\n{exc}",
            )
            return
        finally:
            QApplication.restoreOverrideCursor()

        self._update_ocr_progress(100, "Hoàn thành quét QR", self._format_elapsed(start))
        self.raw_ocr_text.setPlainText(qr_text)
        self._parse_ocr_text()

    def _scan_organization_document(self, path: str) -> None:
        QApplication.setOverrideCursor(Qt.WaitCursor)
        start = monotonic()
        try:
            self._update_ocr_progress(0, "Đang đọc tài liệu doanh nghiệp", "0 giây")
            result = self.organization_document_service.extract_pdf(
                path,
                progress_callback=lambda percent, status: self._update_ocr_progress(
                    percent, status, self._format_elapsed(start)
                ),
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Không thể đọc tài liệu",
                f"Không thể nhận diện thông tin tổ chức:\n{exc}",
            )
            return
        finally:
            QApplication.restoreOverrideCursor()

        if not self._activate_organization_owner_for_document():
            return
        self._apply_organization_values_to_current_person(result.values, result.raw_text, result.extraction_method)
        self._update_organization_result_fields(result.values)
        self.organization_document_label.setText(
            f"Tài liệu: {Path(path).name} - Nhận diện bằng "
            f"{'OCR' if result.extraction_method == 'ocr' else 'văn bản PDF'}"
        )
        self.raw_ocr_text.setPlainText(result.raw_text)
        self.recognition_result_stack.setCurrentIndex(1)
        self._update_ocr_progress(100, "Đã nhận diện thông tin tổ chức", self._format_elapsed(start))
        if result.warnings:
            QMessageBox.warning(
                self,
                "Cần kiểm tra dữ liệu tổ chức",
                "\n".join(result.warnings),
            )
    def _choose_company_document(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Tải tài liệu hồ sơ doanh nghiệp",
            "",
            "Tài liệu PDF (*.pdf);;Tất cả file (*.*)",
        )
        if not path:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        start = monotonic()
        try:
            self._update_ocr_progress(0, "Đang đọc tài liệu doanh nghiệp", "0 giây")
            result = self.organization_document_service.extract_pdf(
                path,
                progress_callback=lambda percent, status: self._update_ocr_progress(
                    percent, status, self._format_elapsed(start)
                ),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Không thể đọc tài liệu", f"Không thể nhận diện thông tin tổ chức:\n{exc}")
            return
        finally:
            QApplication.restoreOverrideCursor()

        if not self._activate_organization_owner_for_document():
            return
        self._apply_organization_values_to_current_person(result.values, result.raw_text, result.extraction_method)
        self._update_organization_result_fields(result.values)
        self.organization_document_label.setText(
            f"Tài liệu: {Path(path).name} - Nhận diện bằng "
            f"{'OCR' if result.extraction_method == 'ocr' else 'văn bản PDF'}"
        )
        self.raw_ocr_text.setPlainText(result.raw_text)
        self.recognition_result_stack.setCurrentIndex(1)
        self._update_ocr_progress(100, "Đã nhận diện thông tin tổ chức", self._format_elapsed(start))
        if result.warnings:
            QMessageBox.warning(self, "Cần kiểm tra dữ liệu tổ chức", "\n".join(result.warnings))

    def _activate_organization_owner_for_document(self) -> bool:
        if self.owner_type_selector.currentText() == "Tổ chức":
            return True

        has_individual_data = any(self._field_value(key) for key in INDIVIDUAL_OWNER_FIELD_KEYS)
        if has_individual_data:
            answer = QMessageBox.question(
                self,
                "Chuyển sang chủ sở hữu tổ chức",
                "Tài liệu doanh nghiệp chỉ dùng cho chủ sở hữu tổ chức. Dữ liệu chủ sở hữu cá nhân hiện tại sẽ bị xóa. Bạn có muốn tiếp tục?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return False

        for key in INDIVIDUAL_OWNER_FIELD_KEYS:
            self._set_field(key, "")
        with QSignalBlocker(self.owner_type_selector):
            self.owner_type_selector.setCurrentText("Tổ chức")
        self._set_active_owner_type("Tổ chức")
        self.owner_type_selector.setVisible(True)
        self.owner_type_selector.setEnabled(True)
        return True

    def _update_organization_result_fields(self, values: dict[str, str]) -> None:
        for key, field in self.organization_card_fields.items():
            value = values.get(key, "")
            field.blockSignals(True)
            if isinstance(field, QTextEdit):
                field.setPlainText(value)
            else:
                field.setText(value)
                field.setCursorPosition(0)
            field.setToolTip(value)
            field.blockSignals(False)

    def _apply_organization_values_to_current_person(
        self, values: dict[str, str], raw_text: str, extraction_method: str
    ) -> None:
        person = self.ocr_people[self.current_person_index]
        person.organization_data = {key: value for key, value in values.items() if value}
        person.recognition_type = "organization"
        person.raw_text = raw_text
        person.organization_extraction_method = extraction_method
        person.data.clear()
        name = values.get("organization_owner_name", "")
        if name:
            person.name = name
            self._refresh_people_buttons()
    def _organization_result_values(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for key, field in self.organization_card_fields.items():
            values[key] = field.toPlainText().strip() if isinstance(field, QTextEdit) else field.text().strip()
        return values

    def _save_organization_profile(self) -> None:
        if self.owner_type_selector.currentText() != "Tổ chức":
            QMessageBox.warning(
                self,
                "Không thể lưu dữ liệu tổ chức",
                "Dữ liệu tổ chức chỉ được phép điền khi loại chủ sở hữu là Tổ chức.",
            )
            return

        values = self._organization_result_values()
        required = {
            "organization_owner_name": "Tên tổ chức",
            "organization_owner_registration_number": "Mã số doanh nghiệp/Số quyết định thành lập",
            "organization_owner_address_detail": "Địa chỉ trụ sở chính",
        }
        missing = [label for key, label in required.items() if not values.get(key, "")]
        if missing:
            QMessageBox.warning(self, "Cần kiểm tra dữ liệu tổ chức", "Chưa có:\n- " + "\n- ".join(missing))
            return

        saved = {key: str(values.get(key, "") or "").strip() for key in ORGANIZATION_OWNER_FIELD_KEYS}
        saved["organization_owner_issue_place"] = _normalize_organization_issue_place(
            saved.get("organization_owner_issue_place", "")
        )
        self._set_field("organization_owner_issue_place", saved["organization_owner_issue_place"])
        registration_number = saved.get("organization_owner_registration_number", "")
        existing = next(
            (
                profile
                for profile in self.organization_profiles
                if profile.get("organization_owner_registration_number") == registration_number
            ),
            None,
        )
        if existing is None:
            self.organization_profiles.append(saved)
        else:
            existing.update(saved)
            saved = existing
        self._refresh_organization_owner_selector()
        self._refresh_preview()
        QMessageBox.information(self, "Đã lưu dữ liệu tổ chức", "Đã lưu và điền thông tin vào phần Chủ sở hữu tổ chức.")
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

    def _set_cccd_address_status(self, status: str, message: str = "") -> None:
        self._cccd_address_status = status or ""
        self._cccd_address_message = message or ""
        self._cccd_address_requires_confirmation = status == "needs_confirmation"
        status_text = {
            "current": "\u0110\u1ecba ch\u1ec9 CCCD \u0111\u00e3 theo ch\u00ednh quy\u1ec1n hai c\u1ea5p.",
            "converted": "\u0110\u00e3 chuy\u1ec3n \u0111\u1ed5i \u0111\u1ecba ch\u1ec9 t\u1eeb h\u1ec7 th\u1ed1ng h\u00e0nh ch\u00ednh c\u0169.",
            "confirmed": "\u0110\u1ecba ch\u1ec9 \u0111\u00e3 \u0111\u01b0\u1ee3c ng\u01b0\u1eddi d\u00f9ng x\u00e1c nh\u1eadn.",
            "needs_confirmation": "C\u1ea7n ki\u1ec3m tra \u0111\u1ecba ch\u1ec9 g\u1ed1c v\u00e0 x\u00e1c nh\u1eadn tr\u01b0\u1edbc khi d\u00f9ng cho h\u1ed3 s\u01a1.",
            "": "Ch\u01b0a c\u00f3 \u0111\u1ecba ch\u1ec9 CCCD \u0111\u1ec3 \u0111\u1ed1i chi\u1ebfu.",
        }.get(status or "", "C\u1ea7n ki\u1ec3m tra \u0111\u1ecba ch\u1ec9 CCCD.")
        text = message or status_text
        if self.cccd_address_status_label is not None:
            color = "#a5531c" if status == "needs_confirmation" else "#2f6d4f"
            if not status:
                color = "#6b6470"
            self.cccd_address_status_label.setText(text)
            self.cccd_address_status_label.setToolTip(text)
            self.cccd_address_status_label.setStyleSheet(f"color: {color};")

    def _mark_cccd_address_edited(self) -> None:
        raw_field = self.ocr_card_fields.get("legal_representative_raw_permanent_address")
        normalized_field = self.ocr_card_fields.get("legal_representative_permanent_address")
        if not isinstance(raw_field, QTextEdit) or not isinstance(normalized_field, QTextEdit):
            return
        if raw_field.toPlainText().strip() and normalized_field.toPlainText().strip():
            self._set_cccd_address_status(
                "needs_confirmation",
                "\u0110\u1ecba ch\u1ec9 \u0111\u00e3 \u0111\u01b0\u1ee3c ch\u1ec9nh s\u1eeda. Ch\u1ecdn X\u00e1c nh\u1eadn \u0111\u1ecba ch\u1ec9 tr\u01b0\u1edbc khi d\u00f9ng.",
            )
            self._apply_cccd_values_to_current_person(
                self._cccd_result_values(),
                apply_to_form=False,
            )

    def _confirm_cccd_address(self) -> None:
        if not self._require_cccd_issue_place():
            return
        values = self._cccd_result_values()
        if not values.get("legal_representative_raw_permanent_address") or not values.get(
            "legal_representative_permanent_address"
        ):
            QMessageBox.warning(
                self,
                "Ch\u01b0a th\u1ec3 x\u00e1c nh\u1eadn \u0111\u1ecba ch\u1ec9",
                "C\u1ea7n c\u00f3 c\u1ea3 \u0111\u1ecba ch\u1ec9 g\u1ed1c v\u00e0 \u0111\u1ecba ch\u1ec9 d\u00f9ng \u0111i\u1ec1n h\u1ed3 s\u01a1.",
            )
            return
        self._set_cccd_address_status(
            "confirmed",
            "\u0110\u1ecba ch\u1ec9 \u0111\u00e3 \u0111\u01b0\u1ee3c ng\u01b0\u1eddi d\u00f9ng x\u00e1c nh\u1eadn.",
        )
        self._apply_cccd_values_to_current_person(self._cccd_result_values())

    def _update_cccd_result_fields(self, values: dict[str, str]) -> None:
        for key, field in self.ocr_card_fields.items():
            value = values.get(key, "")
            field.blockSignals(True)
            if isinstance(field, QTextEdit):
                field.setPlainText(value)
            elif isinstance(field, QComboBox):
                field.setCurrentIndex(field.findText(value) if value else -1)
            else:
                field.setText(value)
                field.setCursorPosition(0)
            field.setToolTip(value)
            field.blockSignals(False)
        self._set_cccd_address_status(
            values.get("legal_representative_address_status", ""),
            values.get("legal_representative_address_message", ""),
        )

    def _cccd_result_values(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for key, field in self.ocr_card_fields.items():
            if isinstance(field, QTextEdit):
                values[key] = field.toPlainText().strip()
            elif isinstance(field, QComboBox):
                values[key] = field.currentText().strip()
            else:
                values[key] = field.text().strip()
        values["legal_representative_address_status"] = self._cccd_address_status
        values["legal_representative_address_message"] = self._cccd_address_message
        return values

    def _require_cccd_issue_place(self) -> bool:
        field = self.ocr_card_fields.get("legal_representative_issue_place")
        issue_place = field.currentText().strip() if isinstance(field, QComboBox) else ""
        if issue_place:
            return True
        QMessageBox.warning(
            self,
            "Cần chọn nơi cấp CCCD",
            "Chọn nơi cấp CCCD trước khi áp dụng hoặc lưu dữ liệu nhận diện. "
            "Hồ sơ sẽ không thể xuất khi thiếu nơi cấp.",
        )
        return False

    def _require_confirmed_cccd_address(self) -> bool:
        if not self._cccd_address_requires_confirmation:
            return True
        QMessageBox.warning(
            self,
            "C\u1ea7n x\u00e1c nh\u1eadn \u0111\u1ecba ch\u1ec9 CCCD",
            "Ki\u1ec3m tra \u0111\u1ecba ch\u1ec9 g\u1ed1c, ch\u1ec9nh \u0111\u1ecba ch\u1ec9 d\u00f9ng \u0111i\u1ec1n h\u1ed3 s\u01a1 n\u1ebfu c\u1ea7n, r\u1ed3i ch\u1ecdn X\u00e1c nh\u1eadn \u0111\u1ecba ch\u1ec9.",
        )
        return False

    def _apply_cccd_result_to_form(self) -> None:
        values = self._cccd_result_values()
        if not any(values.values()):
            QMessageBox.warning(self, "Ch\u01b0a c\u00f3 d\u1eef li\u1ec7u CCCD", "B\u1ea1n c\u1ea7n qu\u00e9t QR ho\u1eb7c nh\u1eadp th\u00f4ng tin CCCD tr\u01b0\u1edbc.")
            return
        if not self._require_confirmed_cccd_address() or not self._require_cccd_issue_place():
            return
        self._apply_cccd_values_to_current_person(values)

    def _save_cccd_personal_profile(self) -> None:
        values = self._cccd_result_values()
        if not any(values.values()):
            QMessageBox.warning(self, "Ch\u01b0a c\u00f3 d\u1eef li\u1ec7u CCCD", "B\u1ea1n c\u1ea7n qu\u00e9t QR ho\u1eb7c nh\u1eadp th\u00f4ng tin CCCD tr\u01b0\u1edbc.")
            return
        if not self._require_confirmed_cccd_address() or not self._require_cccd_issue_place():
            return
        current_person_data = self._person_data_for_fill(self.ocr_people[self.current_person_index])
        previous_id_number = current_person_data.get("legal_representative_id_number", "").strip()
        full_name = values.get("legal_representative_full_name", "").strip()
        id_number = values.get("legal_representative_id_number", "").strip()
        if not full_name or not id_number:
            QMessageBox.warning(self, "Kh\u00f4ng th\u1ec3 l\u01b0u d\u1eef li\u1ec7u", "C\u1ea7n c\u00f3 h\u1ecd t\u00ean v\u00e0 s\u1ed1 CCCD \u0111\u1ec3 l\u01b0u profile trong h\u1ed3 s\u01a1 n\u00e0y.")
            return
        values["legal_representative_ethnicity"] = self._field_value("legal_representative_ethnicity")
        values["personal_phone"] = self._field_value("legal_representative_phone") or self._field_value("applicant_phone")
        values["personal_email"] = self._field_value("legal_representative_email") or self._field_value("applicant_email")
        saved = dict(values)
        known_id_numbers = {number for number in (id_number, previous_id_number) if number}
        existing = next(
            (
                profile
                for profile in self.personal_profiles
                if profile.get("legal_representative_id_number", "").strip() in known_id_numbers
            ),
            None,
        )
        if existing is None:
            self.personal_profiles.append(saved)
        else:
            existing.update(saved)
            saved = existing
        self._refresh_person_fill_selectors()
        self._refresh_beneficial_owner_list_selector()
        self._refresh_organization_representative_selector()
        self._apply_cccd_values_to_current_person(saved)
        self._sync_personal_data_to_case(saved, previous_id_number)
        QMessageBox.information(self, "\u0110\u00e3 l\u01b0u d\u1eef li\u1ec7u c\u00e1 nh\u00e2n", f"\u0110\u00e3 l\u01b0u profile {full_name} cho h\u1ed3 s\u01a1 hi\u1ec7n t\u1ea1i.")

    @staticmethod
    def _same_person_identity(value: object, id_numbers: set[str]) -> bool:
        digits = re.sub(r"\D", "", str(value or ""))
        return bool(digits and digits in id_numbers)

    def _sync_personal_data_to_case(self, card_values: dict[str, str], previous_id_number: str) -> None:
        """Refresh every in-case reference that belongs to the CCCD being edited."""
        id_numbers = {
            re.sub(r"\D", "", number)
            for number in (
                previous_id_number,
                card_values.get("legal_representative_id_number", ""),
            )
            if re.sub(r"\D", "", number)
        }
        if not id_numbers:
            return

        for person in self.ocr_people:
            person_id = person.data.get("legal_representative_id_number", "")
            if not self._same_person_identity(person_id, id_numbers):
                continue
            updated_data = dict(person.data)
            updated_data.update(card_values)
            person.data = {key: value for key, value in updated_data.items() if value}
            person.recognition_type = "individual"

        role_id_fields = {
            "legal_representative": "legal_representative_id_number",
            "applicant": "applicant_id_number",
            "authorized_person": "authorized_person_id_number",
            "beneficial_owner": "beneficial_owner_id_number",
        }
        for role, id_field in role_id_fields.items():
            if self._same_person_identity(self._field_value(id_field), id_numbers):
                self._apply_person_data_to_role(card_values, role, self.current_person_index + 1, overwrite=True)

        if self._same_person_identity(self._field_value("legal_representative_id_number"), id_numbers):
            contact_address = (
                card_values.get("legal_representative_contact_address", "")
                or card_values.get("legal_representative_permanent_address", "")
            )
            if contact_address:
                self._set_field("legal_representative_contact_address", contact_address)

        if self._same_person_identity(self._field_value("beneficial_owner_list_identity"), id_numbers):
            self._set_fields_from_mapping(
                {
                    "beneficial_owner_list_full_name": card_values.get("legal_representative_full_name", ""),
                    "beneficial_owner_list_date_of_birth": card_values.get("legal_representative_date_of_birth", ""),
                    "beneficial_owner_list_gender": card_values.get("legal_representative_gender", ""),
                    "beneficial_owner_list_identity": self._representative_identity_text(card_values),
                    "beneficial_owner_list_ethnicity": card_values.get("legal_representative_ethnicity", ""),
                    "beneficial_owner_list_address": (
                        card_values.get("legal_representative_contact_address", "")
                        or card_values.get("legal_representative_permanent_address", "")
                    ),
                }
            )

        self._refresh_people_buttons()
        self._refresh_person_fill_selectors()
        self._refresh_beneficial_owner_list_selector()
        self._refresh_preview()


    def _apply_cccd_values_to_current_person(
        self,
        card_values: dict[str, str],
        apply_to_form: bool = True,
    ) -> None:
        person = self.ocr_people[self.current_person_index]
        person.data = {key: value for key, value in card_values.items() if value}
        person.recognition_type = "individual"
        person.organization_data.clear()
        person.organization_extraction_method = ""
        full_name = card_values.get("legal_representative_full_name", "")
        if full_name:
            person.name = full_name
            self._refresh_people_buttons()
        self._refresh_organization_representative_selector()
        if apply_to_form and person.role in {"legal_representative", "member", "applicant", "authorized_person", "beneficial_owner"}:
            self._apply_person_data_to_role(card_values, person.role, self.current_person_index + 1, overwrite=True)
        self._refresh_preview()

    def _parse_ocr_text(self) -> None:
        text = self.raw_ocr_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Ch\u01b0a c\u00f3 d\u1eef li\u1ec7u QR", "B\u1ea1n c\u1ea7n qu\u00e9t QR CCCD tr\u01b0\u1edbc.")
            return

        card = self.id_parser.parse_qr(text)
        card_values = card.to_form_values()
        self._update_cccd_result_fields(card_values)
        self._apply_cccd_values_to_current_person(
            self._cccd_result_values(),
            apply_to_form=(
                not self._cccd_address_requires_confirmation
                and bool(self._cccd_result_values().get("legal_representative_issue_place", ""))
            ),
        )
        self.ocr_people[self.current_person_index].raw_text = text
        self._parse_registration_office_from_text(text)
        if card.warnings:
            QMessageBox.warning(self, "C\u1ea3nh b\u00e1o d\u1eef li\u1ec7u CCCD", "\\n".join(card.warnings))
        self._refresh_preview()

    def _apply_person_data_to_role(self, card_values: dict[str, str], role: str, person_number: int, overwrite: bool = False) -> None:
        role_prefix_map = {
            "legal_representative": "legal_representative",
            "applicant": "applicant",
            "authorized_person": "authorized_person",
            "member": f"member_{person_number}",
            "beneficial_owner": "beneficial_owner",
        }
        prefix = role_prefix_map.get(role, "legal_representative")
        source_map = {
            "full_name": "legal_representative_full_name",
            "id_number": "legal_representative_id_number",
            "date_of_birth": "legal_representative_date_of_birth",
            "gender": "legal_representative_gender",
            "permanent_address": "legal_representative_permanent_address",
            "nationality": "legal_representative_nationality",
            "issue_date": "legal_representative_issue_date",
            "expiry_date": "legal_representative_expiry_date",
            "issue_place": "legal_representative_issue_place",
        }
        target_suffixes = {
            "full_name": "full_name",
            "id_number": "id_number",
            "date_of_birth": "date_of_birth",
            "gender": "gender",
            "permanent_address": "permanent_address",
            "nationality": "nationality",
            "issue_date": "issue_date",
            "expiry_date": "expiry_date",
            "issue_place": "issue_place",
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
            if role == "beneficial_owner" and suffix == "permanent_address":
                target_key = "beneficial_owner_address"
            if overwrite:
                self._set_field(target_key, value)
            else:
                self._set_field_if_empty(target_key, value)

        if role == "legal_representative":
            if card_values.get("legal_representative_permanent_address"):
                self._sync_address_parts("legal_representative_permanent_address")
            self._sync_director_from_legal_representative()
        elif role == "authorized_person":
            address = self._authorization_contact_address(card_values)
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
        company_folder = self._safe_export_folder_name(values.get("company_name", "") or "HO SO THANH LAP")
        version_dir = case_export_dir / version_name / company_folder

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
        company_name = (values.get("company_name", "") or "HO SO THANH LAP").strip()
        return self._safe_export_folder_name(company_name)
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
        """Coalesce UI updates so typing never blocks the event loop."""
        if self._initializing:
            return
        self._preview_refresh_pending = True
        if self._refreshing_preview or self._preview_refresh_timer.isActive():
            return
        self._preview_refresh_timer.start()

    def _refresh_preview_now(self) -> None:
        if self._initializing or self._refreshing_preview or not self._preview_refresh_pending:
            return
        self._preview_refresh_pending = False
        self._refreshing_preview = True
        try:
            values = self.form_values(apply_defaults=False)
            lines = []
            for key, label in FIELD_DEFINITIONS:
                if key.startswith("beneficial_owner_"):
                    continue
                value = values.get(key, "").strip()
                if value:
                    lines.append(f"{label}: {value}")
            preview = "\n".join(lines) if lines else "Chưa có dữ liệu để xem trước."
            if self.preview_text.toPlainText() != preview:
                self.preview_text.setPlainText(preview)
            self._refresh_form_completion(values)
        finally:
            self._refreshing_preview = False
        if self._preview_refresh_pending:
            self._preview_refresh_timer.start()

    def _refresh_form_completion(self, values: dict[str, str]) -> None:
        requirements = {
            "Thông tin cơ quan tiếp nhận và thời gian ký": ("business_registration_office", "document_day", "document_month", "document_year"),
            "Thông tin người đăng ký/nộp hồ sơ": ("applicant_full_name", "applicant_id_number", "applicant_phone"),
            "Thông tin doanh nghiệp": ("company_name", "company_address", "company_phone"),
            "Thông tin chủ sở hữu": ("beneficial_owner_full_name", "beneficial_owner_id_number", "beneficial_owner_address"),
            "Vốn điều lệ và vốn góp": ("charter_capital_number",),
            "Thông tin người đại diện pháp luật": ("legal_representative_full_name", "legal_representative_id_number", "legal_representative_permanent_address", "legal_representative_position"),
            "Thông tin giám đốc/Tổng giám đốc": ("director_full_name", "director_id_number", "director_position"),
            "Thông tin đăng ký thuế và bảo hiểm xã hội": ("tax_labor_count", "tax_vat_method", "tax_declaration_period"),
            "Thông tin người được ủy quyền": ("authorized_person_full_name", "authorized_person_id_number"),
        }
        if values.get("owner_type", "Cá nhân") == "Tổ chức":
            requirements["Thông tin chủ sở hữu"] = (
                "organization_owner_name",
                "organization_owner_registration_number",
                "organization_owner_address_detail",
            )
        completed_prefix = chr(0x2713) + " "
        for title, button in self.form_nav_buttons.items():
            if title == "Ngành nghề kinh doanh":
                complete = any(values.get(f"business_line_{index}_name", "").strip() and values.get(f"business_line_{index}_code", "").strip() for index in range(1, 11))
            else:
                fields = requirements.get(title, ())
                complete = bool(fields) and all(values.get(field, "").strip() for field in fields)
            button_text = completed_prefix + title if complete else title
            if button.text() != button_text:
                button.setText(button_text)
            tooltip = "Đã nhập đủ thông tin chính" if complete else "Chưa nhập đủ thông tin chính"
            if button.toolTip() != tooltip:
                button.setToolTip(tooltip)


    def form_values(self, apply_defaults: bool = True) -> dict[str, str]:
        values: dict[str, str] = {}
        for key in self.fields:
            values[key] = self._field_value(key)
        for index, row in enumerate(self.business_line_rows, start=1):
            values[f"business_line_{index}_name"] = row.name_field.text().strip()
            values[f"business_line_{index}_detail"] = row.detail_field.toPlainText().strip()
            values[f"business_line_{index}_code"] = row.code_field.text().strip()
            values[f"business_line_{index}_is_main"] = "X" if row.main_checkbox.isChecked() else ""
        self._store_people_values(values)
        owner_type = values.get("owner_type", "Cá nhân")
        inactive_owner_fields = (
            ORGANIZATION_OWNER_FIELD_KEYS + ORGANIZATION_OWNER_REPRESENTATIVE_FIELD_KEYS
            if owner_type == "Cá nhân"
            else INDIVIDUAL_OWNER_FIELD_KEYS
        )
        for key in inactive_owner_fields:
            values[key] = ""
        if apply_defaults:
            self._apply_value_defaults(values)
        return values

    def _store_people_values(self, values: dict[str, str]) -> None:
        self._persist_current_person_recognition()
        values["people_count"] = str(len(self.ocr_people))
        for index, person in enumerate(self.ocr_people, start=1):
            values[f"person_{index}_name"] = person.name
            values[f"person_{index}_role"] = person.role
            values[f"person_{index}_front_path"] = person.front_path
            values[f"person_{index}_back_path"] = person.back_path
            values[f"person_{index}_recognition_type"] = person.recognition_type
            values[f"person_{index}_raw_text"] = person.raw_text
            values[f"person_{index}_organization_extraction_method"] = person.organization_extraction_method
            for key, value in person.organization_data.items():
                values[f"person_{index}_organization_{key}"] = value
            for key, value in person.data.items():
                values[f"person_{index}_{key}"] = value

        owner_prefix = "beneficial_owner" if values.get("beneficial_owner_full_name", "").strip() else "legal_representative"
        values["member_1_full_name"] = values.get(f"{owner_prefix}_full_name", "")
        values["member_1_id_number"] = values.get(f"{owner_prefix}_id_number", "")
        values["member_1_date_of_birth"] = values.get(f"{owner_prefix}_date_of_birth", "")
        values["member_1_gender"] = values.get(f"{owner_prefix}_gender", "")
        address_key = "beneficial_owner_address" if owner_prefix == "beneficial_owner" else "legal_representative_permanent_address"
        values["member_1_permanent_address"] = values.get(address_key, "")

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

        signing_place = self._signing_place_for_office(values.get("business_registration_office", ""))
        if signing_place:
            values["document_place"] = signing_place
        if document_day and document_month and document_year:
            date_text = f"ngày {document_day} tháng {document_month} năm {document_year}"
            values["document_place_date"] = f"{values.get('document_place', '').strip()}, {date_text}".strip(", ")

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
        owner_address = values.get("beneficial_owner_address", "").strip()
        if owner_address:
            parsed_owner_address = self.address_parser.parse(owner_address)
            values.setdefault("beneficial_owner_address_detail", parsed_owner_address.street_line or parsed_owner_address.village)
            values.setdefault("beneficial_owner_ward", parsed_owner_address.ward)
            values.setdefault("beneficial_owner_province", parsed_owner_address.province)
        if _is_organization_owner(values.get("owner_type", "")):
            representative_defaults = {
                "beneficial_owner_list_number": "organization_owner_representative_number",
                "beneficial_owner_list_full_name": "organization_owner_representative_full_name",
                "beneficial_owner_list_date_of_birth": "organization_owner_representative_date_of_birth",
                "beneficial_owner_list_gender": "organization_owner_representative_gender",
                "beneficial_owner_list_identity": "organization_owner_representative_identity",
                "beneficial_owner_list_ethnicity": "organization_owner_representative_ethnicity",
                "beneficial_owner_list_address": "organization_owner_representative_contact_address",
            }
            for target, source in representative_defaults.items():
                self._fill_if_missing(values, target, source)
            values.setdefault("beneficial_owner_list_number", "1")

        representative_aliases = {
            "director_full_name": "legal_representative_full_name",
            "director_date_of_birth": "legal_representative_date_of_birth",
            "director_gender": "legal_representative_gender",
            "director_id_number": "legal_representative_id_number",
            "director_position": "legal_representative_position",
            "director_phone": "legal_representative_phone",
        }
        applicant_prefix = "authorized_person" if values.get("authorized_person_full_name", "").strip() else "legal_representative"
        representative_aliases.update(
            {
                "applicant_full_name": f"{applicant_prefix}_full_name",
                "applicant_date_of_birth": f"{applicant_prefix}_date_of_birth",
                "applicant_gender": f"{applicant_prefix}_gender",
                "applicant_id_number": f"{applicant_prefix}_id_number",
                "applicant_address_detail": f"{applicant_prefix}_address_detail",
                "applicant_ward": f"{applicant_prefix}_ward",
                "applicant_province": f"{applicant_prefix}_province",
                "applicant_phone": f"{applicant_prefix}_phone",
                "applicant_email": f"{applicant_prefix}_email",
            }
        )
        for target, source in representative_aliases.items():
            self._fill_if_missing(values, target, source)

        for target, source in {
            "director_full_name": "legal_representative_full_name",
            "director_date_of_birth": "legal_representative_date_of_birth",
            "director_gender": "legal_representative_gender",
            "director_id_number": "legal_representative_id_number",
            "director_position": "legal_representative_position",
            "director_phone": "legal_representative_phone",
        }.items():
            values[target] = values.get(source, "").strip()

        # Giám đốc/Tổng giám đốc luôn là chính người đại diện pháp luật.
        values["director_phone"] = values.get("legal_representative_phone", "").strip()

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
        self._normalize_capital_breakdown_values(values)
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
        values.setdefault("tax_labor_count", "1")
        values["business_lines"] = self._business_lines_summary(values)

    def _normalize_capital_breakdown_values(self, values: dict[str, str]) -> None:
        """Word templates require every source and contributed-asset amount to be explicit."""
        for prefix, count in (("capital_source", len(CAPITAL_SOURCE_LABELS)), ("asset_contribution", len(ASSET_CONTRIBUTION_LABELS))):
            total = 0
            amounts: list[int] = []
            for index in range(1, count + 1):
                digits = self._money_digits(values.get(f"{prefix}_{index}_amount", ""))
                amount = int(digits or "0")
                amounts.append(amount)
                total += amount
                values[f"{prefix}_{index}_amount"] = self._format_money(str(amount)) if amount else "0"
            for index, amount in enumerate(amounts, start=1):
                ratio = amount * 100 / total if total else 0
                values[f"{prefix}_{index}_ratio"] = f"{ratio:.2f}".rstrip("0").rstrip(".")
            values[f"{prefix}_total_amount"] = self._format_money(str(total)) if total else "0"
            values[f"{prefix}_total_ratio"] = "100" if total else "0"

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
            owner=values.get("authorized_person_full_name") or (existing.owner if existing else "Chưa chọn người ủy quyền"),
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
        return 1

    def _case_type_for_members(self, member_count: int) -> str:
        if member_count <= 1:
            return "TNHH một thành viên"
        return "TNHH hai thành viên trở lên"

    def _missing_required_fields(self, values: dict[str, str]) -> list[str]:
        required = {
            "beneficial_owner_full_name": "Họ tên chủ sở hữu",
            "beneficial_owner_id_number": "Số CCCD chủ sở hữu",
            "beneficial_owner_address": "Địa chỉ liên lạc của chủ sở hữu",
            "company_name": "Tên doanh nghiệp",
            "company_address": "Địa chỉ trụ sở",
            "company_phone": "Số điện thoại công ty (dùng cho thông tin đăng ký thuế)",
            "charter_capital_number": "Vốn điều lệ",
            "legal_representative_full_name": "Họ tên cá nhân/đại diện",
            "legal_representative_id_number": "Số CCCD",
            "legal_representative_permanent_address": "Địa chỉ thường trú",
        }
        if values.get("owner_type", "Cá nhân") == "Tổ chức":
            for key in ("beneficial_owner_full_name", "beneficial_owner_id_number", "beneficial_owner_address"):
                required.pop(key, None)
            required.update(
                {
                    "organization_owner_name": "Tên tổ chức chủ sở hữu",
                    "organization_owner_registration_number": "Mã số doanh nghiệp/Số quyết định thành lập của chủ sở hữu",
                    "organization_owner_address_detail": "Địa chỉ chi tiết của chủ sở hữu tổ chức",
                    "organization_owner_representative_full_name": "Họ tên người đại diện vốn của tổ chức",
                    "organization_owner_representative_identity": "Giấy tờ pháp lý của người đại diện vốn",
                }
            )
        required["legal_representative_issue_place"] = "Nơi cấp CCCD của người đại diện pháp luật"
        if values.get("authorized_person_full_name", "").strip() or values.get("authorized_person_id_number", "").strip():
            required["authorized_person_issue_place"] = "Nơi cấp CCCD của người được ủy quyền"
            required["authorized_person_contact_address"] = "Địa chỉ liên lạc của người được ủy quyền"
        missing = [label for key, label in required.items() if not values.get(key, "").strip()]
        if any(
            person.recognition_type == "individual"
            and person.data.get("legal_representative_address_status") == "needs_confirmation"
            for person in self.ocr_people
        ):
            missing.append("Xác nhận địa chỉ CCCD trước khi xuất hồ sơ")
        return missing

    def _validation_issues(self, values: dict[str, str]) -> list[str]:
        issues = self._missing_required_fields(values)
        if not any(values.get(f"business_line_{index}_name", "").strip() for index in range(1, 11)):
            issues.append("Ít nhất 1 ngành nghề kinh doanh")
        if not any(values.get(f"business_line_{index}_is_main", "").strip() for index in range(1, 11)):
            issues.append("Chọn 1 ngành nghề chính")
        for index in range(1, 11):
            name = values.get(f"business_line_{index}_name", "").strip()
            code = values.get(f"business_line_{index}_code", "").strip()
            if name and len(re.sub(r"\D", "", code)) != 4:
                issues.append(f"Mã ngành nghề cấp 4 của ngành {index}")
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
        text_value = str(value or "")
        if isinstance(field, QTextEdit):
            if field.toPlainText() != text_value:
                field.setPlainText(text_value)
        elif isinstance(field, QComboBox):
            if field.currentText() != text_value:
                field.setCurrentText(text_value)
        elif isinstance(field, QCheckBox):
            checked = text_value.strip().lower() in {"x", "1", "true", "có", "co", "yes"}
            if field.isChecked() != checked:
                field.setChecked(checked)
        elif field.text() != text_value:
            field.setText(text_value)

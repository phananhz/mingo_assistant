from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QDesktopServices, QFontMetrics

from mingo_assistant import __version__
from mingo_assistant.app.paths import AppPaths, get_app_paths, load_settings, save_settings
from mingo_assistant.models.case import CaseSummary
from mingo_assistant.repositories.case_repository import CaseRepository
from mingo_assistant.services.business_lines.industry_lookup import IndustryCatalog, IndustryRow
from mingo_assistant.ui.dialogs.settings_dialog import SettingsDialog
from mingo_assistant.ui.styles import stylesheet_for_theme
from mingo_assistant.ui.views.business_registration_documents import BusinessRegistrationDocumentsView
from mingo_assistant.ui.views.business_registration_workspace import BusinessRegistrationWorkspace
from mingo_assistant.ui.widgets.combo_box import NoWheelComboBox


NAV_ITEMS = [
    ("business_registration", "Hồ sơ thành lập doanh nghiệp"),
    ("industry_lookup", "Tra cứu ngành nghề kinh doanh"),
    ("trash", "Thùng rác"),
    ("capital_change", "Hồ sơ thay đổi vốn điều lệ"),
    ("legal_representative_change", "Hồ sơ thay đổi đại diện pháp luật"),
    ("address_change", "Hồ sơ thay đổi địa chỉ trụ sở"),
    ("business_lines_change", "Hồ sơ bổ sung ngành nghề"),
    ("dissolution", "Hồ sơ giải thể doanh nghiệp"),
    ("templates", "Quản lý mẫu Word"),
    ("people", "Kho cá nhân/tổ chức"),
]


BUILT_IN_AUTHORIZED_PERSON_PROFILES: tuple[dict[str, str], ...] = (
    {
        "id": "builtin-duong-hong-ngoc",
        "authorized_person_full_name": "D\u01b0\u01a1ng H\u1ed3ng Ng\u1ecdc",
        "authorized_person_gender": "N\u1eef",
        "authorized_person_id_number": "068303008330",
        "authorized_person_issue_date": "12/06/2021",
        "authorized_person_issue_place": "C\u1ee5c C\u1ea3nh s\u00e1t Qu\u1ea3n l\u00fd H\u00e0nh ch\u00ednh v\u1ec1 Tr\u1eadt t\u1ef1 X\u00e3 h\u1ed9i",
        "authorized_person_contact_address": "S\u1ed1 43-45 \u0110\u01b0\u1eddng s\u1ed1 7, Khu Ph\u1ed1 1, Ph\u01b0\u1eddng Hi\u1ec7p B\u00ecnh, Th\u00e0nh ph\u1ed1 H\u1ed3 Ch\u00ed Minh",
        "authorized_person_phone": "0986602511",
        "authorized_person_email": "ngocduonghong21@gmail.com",
    },
    {
        "id": "builtin-mai-xuan-luong",
        "authorized_person_full_name": "Mai Xu\u00e2n L\u01b0\u01a1ng",
        "authorized_person_gender": "Nam",
        "authorized_person_id_number": "040095033863",
        "authorized_person_issue_date": "25/09/2022",
        "authorized_person_issue_place": "C\u1ee5c C\u1ea3nh s\u00e1t Qu\u1ea3n l\u00fd H\u00e0nh ch\u00ednh v\u1ec1 Tr\u1eadt t\u1ef1 X\u00e3 h\u1ed9i",
        "authorized_person_contact_address": "S\u1ed1 43-45 \u0110\u01b0\u1eddng s\u1ed1 7, Khu Ph\u1ed1 1, Ph\u01b0\u1eddng Hi\u1ec7p B\u00ecnh, Th\u00e0nh ph\u1ed1 H\u1ed3 Ch\u00ed Minh",
        "authorized_person_phone": "0973584275",
        "authorized_person_email": "luongmx1710@gmail.com",
    },
    {
        "id": "builtin-nguyen-thi-minh-ngoc",
        "authorized_person_full_name": "Nguy\u1ec5n Th\u1ecb Minh Ng\u1ecdc",
        "authorized_person_gender": "N\u1eef",
        "authorized_person_id_number": "031199001726",
        "authorized_person_issue_date": "09/12/2024",
        "authorized_person_issue_place": "B\u1ed9 C\u00f4ng an",
        "authorized_person_contact_address": "S\u1ed1 43-45 \u0110\u01b0\u1eddng s\u1ed1 7, Khu Ph\u1ed1 1, Ph\u01b0\u1eddng Hi\u1ec7p B\u00ecnh, Th\u00e0nh ph\u1ed1 H\u1ed3 Ch\u00ed Minh",
        "authorized_person_phone": "0879247679",
        "authorized_person_email": "minhhngoc0304.huynh@gmail.com",
    },
)


class MainWindow(QMainWindow):
    SIDEBAR_WIDTH = 220
    PAGE_HORIZONTAL_MARGIN = 48
    CARD_WIDTH = 220
    CARD_GAP = 18

    def __init__(self, app_paths: AppPaths | None = None) -> None:
        super().__init__()
        self.app_paths = app_paths or get_app_paths()
        self.setWindowTitle(f"Mingo Assistant v{__version__}")
        self.resize(1280, 760)
        self.setMinimumSize(760, 520)

        self.case_repository = CaseRepository(self.app_paths.cases_file)
        self.cases: list[CaseSummary] = self.case_repository.list_cases()
        self.nav_buttons: dict[str, QPushButton] = {}
        self.stack = QStackedWidget()
        self.current_workspace: BusinessRegistrationWorkspace | None = None
        self.current_documents_view: BusinessRegistrationDocumentsView | None = None
        self.authorized_person_path = self.app_paths.authorized_person_file
        self.authorized_person_profiles: list[dict[str, str]] = []
        self.authorized_person_selected_id = ""
        self.authorized_person_fields: dict[str, QLineEdit | QTextEdit] = {}
        self.authorized_person_cards_layout: QGridLayout | None = None
        self.authorized_person_save_button: QPushButton | None = None
        self._last_applied_theme: tuple[str, int, str, bool] | None = None

        self.search_input = QLineEdit()
        self.case_type_filter = NoWheelComboBox()
        self.condition_filter = NoWheelComboBox()
        self.status_filter = NoWheelComboBox()
        self.result_text = QLabel()
        self.filters_wrapper = QWidget()
        self.filters_layout = QGridLayout(self.filters_wrapper)
        self.filter_specs: list[tuple[str, QWidget]] = []
        self.current_filter_columns = 0
        self.cards_scroll: QScrollArea | None = None
        self.cards_container = QWidget()
        self.cards_layout = QGridLayout(self.cards_container)
        self.current_card_columns = 0
        self.trash_container = QWidget()
        self.trash_layout = QVBoxLayout(self.trash_container)
        self.industry_catalog = IndustryCatalog.load_from_project(self.app_paths.bundle_root)
        self.industry_search_input = QLineEdit()
        self.industry_table = QTableWidget()
        self.industry_status_label = QLabel()
        self.industry_detail = QTextEdit()

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._build_sidebar())
        root_layout.addWidget(self._build_content_stack(), 1)

        self.setCentralWidget(root)
        self._select_nav("business_registration")
        self._refresh_cases()

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(self.SIDEBAR_WIDTH)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 12, 12, 16)
        layout.setSpacing(7)

        eyebrow = QLabel("MINGO ASSISTANT")
        eyebrow.setObjectName("AppEyebrow")
        title = QLabel("Quản lý hồ sơ")
        title.setObjectName("AppTitle")

        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addSpacing(18)

        for key, label in NAV_ITEMS:
            button = QPushButton(label)
            button.setObjectName("NavButton")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, item_key=key: self._select_nav(item_key))
            self.nav_buttons[key] = button
            layout.addWidget(button)

        layout.addStretch(1)

        footer = QLabel("Dữ liệu lưu cục bộ trên máy")
        footer.setObjectName("SidebarFooter")
        footer.setStyleSheet("font-size: 12px;")
        layout.addWidget(footer)

        return sidebar

    def _build_content_stack(self) -> QWidget:
        content = QFrame()
        content.setObjectName("Content")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        self.business_page = self._build_business_registration_page()
        self.authorized_person_page = self._build_authorized_person_page()
        self.industry_lookup_page = self._build_industry_lookup_page()
        self.trash_page = self._build_trash_page()
        self.coming_soon_page = self._build_coming_soon_page()

        self.stack.addWidget(self.business_page)
        self.stack.addWidget(self.authorized_person_page)
        self.stack.addWidget(self.industry_lookup_page)
        self.stack.addWidget(self.trash_page)
        self.stack.addWidget(self.coming_soon_page)
        layout.addWidget(self.stack)

        return content

    def _select_nav(self, key: str) -> None:
        for item_key, button in self.nav_buttons.items():
            button.setProperty("active", item_key == key)
            button.style().unpolish(button)
            button.style().polish(button)

        if key == "business_registration":
            self.stack.setCurrentWidget(self.business_page)
        elif key == "industry_lookup":
            self._refresh_industry_lookup()
            self.stack.setCurrentWidget(self.industry_lookup_page)
        elif key == "trash":
            self._refresh_trash()
            self.stack.setCurrentWidget(self.trash_page)
        else:
            self.stack.setCurrentWidget(self.coming_soon_page)

    def _build_business_registration_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("BusinessCasesPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(18)

        header = QHBoxLayout()
        header_text = QVBoxLayout()
        title = QLabel("Hồ sơ thành lập doanh nghiệp")
        title.setObjectName("PageTitle")
        description = QLabel(
            "Quản lý hồ sơ, kiểm tra dữ liệu QR CCCD và tạo bộ Word cho hồ sơ thành lập doanh nghiệp."
        )
        description.setObjectName("PageDescription")
        description.setWordWrap(True)
        header_text.addWidget(title)
        header_text.addWidget(description)

        create_button = QPushButton("+ Tạo hồ sơ mới")
        create_button.setObjectName("PrimaryButton")
        create_button.setCursor(Qt.PointingHandCursor)
        create_button.clicked.connect(self._open_new_business_case)

        authorized_person_button = QPushButton("Thông tin người ủy quyền")
        authorized_person_button.setObjectName("GhostButton")
        authorized_person_button.setCursor(Qt.PointingHandCursor)
        authorized_person_button.clicked.connect(self._open_authorized_person_manager)

        settings_button = QPushButton("⚙")
        settings_button.setObjectName("SettingsButton")
        settings_button.setToolTip("Cài đặt ứng dụng")
        settings_button.setAccessibleName("Cài đặt ứng dụng")
        settings_button.setCursor(Qt.PointingHandCursor)
        settings_button.clicked.connect(self._open_settings)

        header.addLayout(header_text, 1)
        header.addWidget(settings_button, 0, Qt.AlignTop)
        header.addWidget(authorized_person_button, 0, Qt.AlignTop)
        header.addWidget(create_button, 0, Qt.AlignTop)
        layout.addLayout(header)

        layout.addWidget(self._build_filters())

        self.result_text.setObjectName("ResultText")
        layout.addWidget(self.result_text)

        self.cards_scroll = QScrollArea()
        self.cards_scroll.setObjectName("CaseCardsScroll")
        self.cards_container.setObjectName("CaseCardsContainer")
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setFrameShape(QFrame.NoFrame)
        self.cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setHorizontalSpacing(18)
        self.cards_layout.setVerticalSpacing(18)

        self.cards_scroll.setWidget(self.cards_container)
        layout.addWidget(self.cards_scroll, 1)

        return page

    def _apply_theme_preview(self, theme_id: str, strength: int = 100, appearance_mode: str = "light") -> None:
        app = QApplication.instance()
        if app is None:
            return
        system_is_dark = self._system_prefers_dark(app)
        key = (theme_id, int(strength), appearance_mode, system_is_dark)
        if key == self._last_applied_theme:
            return
        self._last_applied_theme = key
        app.setStyleSheet(stylesheet_for_theme(*key))

    @staticmethod
    def _system_prefers_dark(app: QApplication) -> bool:
        try:
            return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
        except AttributeError:
            return False

    def _open_settings(self) -> None:
        current_settings = load_settings(self.app_paths)
        current_theme = current_settings.get("theme", "rose")
        try:
            current_strength = int(current_settings.get("theme_strength", "100"))
        except ValueError:
            current_strength = 100
        current_mode = current_settings.get("appearance_mode", "light")
        dialog = SettingsDialog(
            current_theme,
            current_strength,
            current_mode,
            export_root=self.app_paths.documents_root,
        )
        dialog.theme_preview_changed.connect(self._apply_theme_preview)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self._apply_theme_preview(current_theme, current_strength, current_mode)
            return
        selected_theme = dialog.selected_theme()
        selected_strength = dialog.selected_strength()
        selected_mode = dialog.selected_appearance_mode()
        selected_export_root = dialog.selected_export_root()
        selected_export_root.mkdir(parents=True, exist_ok=True)
        self.app_paths.documents_root = selected_export_root
        save_settings(
            self.app_paths,
            {
                "theme": selected_theme,
                "theme_strength": str(selected_strength),
                "appearance_mode": selected_mode,
                "export_root": str(selected_export_root),
            },
        )

    def _build_trash_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(18)

        header = QHBoxLayout()
        text = QVBoxLayout()
        title = QLabel("Thùng rác")
        title.setObjectName("PageTitle")
        description = QLabel("Quản lý hồ sơ đã xóa. Bạn có thể khôi phục hoặc xóa vĩnh viễn.")
        description.setObjectName("PageDescription")
        description.setWordWrap(True)
        text.addWidget(title)
        text.addWidget(description)

        empty_button = QPushButton("Xóa toàn bộ")
        empty_button.setObjectName("GhostButton")
        empty_button.clicked.connect(self._empty_trash)

        header.addLayout(text, 1)
        header.addWidget(empty_button, 0, Qt.AlignTop)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.trash_layout.setContentsMargins(0, 0, 0, 0)
        self.trash_layout.setSpacing(12)
        scroll.setWidget(self.trash_container)
        layout.addWidget(scroll, 1)
        return page

    def _build_industry_lookup_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("IndustryLookupPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(18)

        header = QVBoxLayout()
        title = QLabel("Tra cứu ngành nghề kinh doanh")
        title.setObjectName("IndustryLookupTitle")
        description = QLabel("Tra cứu mã ngành, tên ngành và nội dung ngành theo Hệ thống ngành kinh tế Việt Nam 2025.")
        description.setObjectName("IndustryLookupDescription")
        description.setWordWrap(True)
        header.addWidget(title)
        header.addWidget(description)
        layout.addLayout(header)

        panel = QFrame()
        panel.setObjectName("IndustryLookupPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(18, 16, 18, 18)
        panel_layout.setSpacing(12)

        source = QLabel(
            '<a href="https://vanban.chinhphu.vn/?classid=1&docid=215475&pageid=27160">'
            "Nguồn chính thức: Quyết định 36/2025/QĐ-TTg - Cổng Thông tin điện tử Chính phủ</a>"
        )
        source.setObjectName("IndustryLookupSource")
        source.setAlignment(Qt.AlignCenter)
        source.setOpenExternalLinks(False)
        source.linkActivated.connect(lambda url: QDesktopServices.openUrl(QUrl(url)))
        panel_layout.addWidget(source)

        sub_source = QLabel("Bảng chuyển đổi Hệ thống ngành nghề kinh tế Việt Nam VSIC 2018 - VSIC 2025")
        sub_source.setObjectName("IndustryLookupSubSource")
        sub_source.setAlignment(Qt.AlignCenter)
        sub_source.setWordWrap(True)
        panel_layout.addWidget(sub_source)

        search_row = QHBoxLayout()
        self.industry_search_input.setObjectName("IndustrySearchInput")
        self.industry_search_input.setPlaceholderText("Nhập mã ngành, tên ngành để tìm kiếm...")
        self.industry_search_input.textChanged.connect(self._refresh_industry_lookup)
        search_row.addWidget(self.industry_search_input, 1)
        panel_layout.addLayout(search_row)

        self.industry_table.setObjectName("IndustryTable")
        self.industry_table.setColumnCount(6)
        self.industry_table.setHorizontalHeaderLabels(["Cấp 1", "Cấp 2", "Cấp 3", "Cấp 4", "Cấp 5", "Tên ngành"])
        self.industry_table.setAlternatingRowColors(True)
        self.industry_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.industry_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.industry_table.verticalHeader().setVisible(False)
        self.industry_table.verticalHeader().setDefaultSectionSize(42)
        self.industry_table.setMinimumHeight(460)
        self.industry_table.setColumnWidth(0, 48)
        self.industry_table.setColumnWidth(1, 48)
        self.industry_table.setColumnWidth(2, 58)
        self.industry_table.setColumnWidth(3, 58)
        self.industry_table.setColumnWidth(4, 68)
        self.industry_table.horizontalHeader().setStretchLastSection(True)
        self.industry_table.itemSelectionChanged.connect(self._show_selected_industry_detail)
        panel_layout.addWidget(self.industry_table, 1)

        detail_group = QGroupBox("Chi tiết ngành nghề")
        detail_layout = QVBoxLayout(detail_group)
        detail_layout.setContentsMargins(10, 10, 10, 10)
        self.industry_detail.setReadOnly(True)
        self.industry_detail.setMinimumHeight(150)
        self.industry_detail.setPlaceholderText(
            "Chọn một ngành trong bảng để xem nội dung hoạt động và các trường hợp loại trừ."
        )
        detail_layout.addWidget(self.industry_detail)
        panel_layout.addWidget(detail_group)

        self.industry_status_label.setObjectName("IndustryLookupStatus")
        self.industry_status_label.setWordWrap(True)
        panel_layout.addWidget(self.industry_status_label)

        layout.addWidget(panel, 1)
        self._refresh_industry_lookup()
        return page

    def _refresh_industry_lookup(self) -> None:
        self.industry_table.clearContents()
        self.industry_table.setRowCount(0)
        if not self.industry_catalog.is_available:
            self.industry_table.setRowCount(1)
            item = QTableWidgetItem(
                "Chưa có dữ liệu ngành nghề chuẩn để tra cứu. "
                "Cần bổ sung file assets/business_lines/vsic_2025.json từ nguồn chính thức trước khi dùng."
            )
            self.industry_table.setItem(0, 0, item)
            self.industry_table.setSpan(0, 0, 1, 6)
            self.industry_status_label.setText(
                "Repo hiện chưa có dataset VSIC 2025 đầy đủ. Không tự điền dữ liệu để tránh sai mã ngành hoặc nội dung ngành."
            )
            self.industry_detail.clear()
            return

        rows = self.industry_catalog.filter_rows(self.industry_search_input.text())
        self.industry_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column, value in enumerate([*row.levels, row.name]):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, row)
                if column < 5:
                    item.setTextAlignment(Qt.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                if row.detail:
                    item.setToolTip(row.detail)
                self.industry_table.setItem(row_index, column, item)
        if rows:
            self.industry_table.selectRow(0)
        else:
            self.industry_detail.setPlainText("Không tìm thấy ngành phù hợp.")
        code_count = self._industry_row_code_count(rows)
        self.industry_status_label.setText(
            f"Đang dùng dữ liệu từ: {self.industry_catalog.source_path}. "
            f"Hiển thị {len(rows)} dòng bảng từ {code_count} mã ngành phù hợp."
        )

    def _industry_row_code_count(self, rows: list[IndustryRow]) -> int:
        return sum(1 for row in rows for code in row.levels if code)

    def _show_selected_industry_detail(self) -> None:
        selected = self.industry_table.selectedItems()
        if not selected:
            return
        row = selected[0].data(Qt.UserRole)
        if not isinstance(row, IndustryRow):
            return
        code = next((level for level in reversed(row.levels) if level), "")
        title = f"{code} - {row.name}" if code else row.name
        sections = [title]
        if row.included_detail:
            sections.append(f"Nội dung hoạt động:\n{row.included_detail}")
        if row.excluded_detail:
            sections.append(f"Loại trừ:\n{row.excluded_detail}")
        self.industry_detail.setPlainText("\n\n".join(sections))

    def _build_filters(self) -> QWidget:
        layout = self.filters_layout
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(6)

        self.search_input.setPlaceholderText("Tìm theo tên công ty, người ủy quyền...")
        self.case_type_filter.addItems(
            ["Tất cả loại hình", "TNHH hai thành viên trở lên", "TNHH một thành viên", "Công ty cổ phần"]
        )
        self.condition_filter.addItems(["Tất cả", "Đủ dữ liệu", "Thiếu thông tin", "Cần kiểm tra"])
        self.status_filter.addItems(["Tất cả", "Bản nháp", "Thiếu thông tin", "Sẵn sàng tạo", "Đã tạo hồ sơ", "Đã hoàn thành"])

        self.search_input.textChanged.connect(self._refresh_cases)
        self.case_type_filter.currentTextChanged.connect(self._refresh_cases)
        self.condition_filter.currentTextChanged.connect(self._refresh_cases)
        self.status_filter.currentTextChanged.connect(self._refresh_cases)

        self.filter_specs = [
            ("TÌM KIẾM", self.search_input),
            ("LOẠI HÌNH", self.case_type_filter),
            ("TÌNH TRẠNG HỒ SƠ", self.condition_filter),
            ("TRẠNG THÁI", self.status_filter),
        ]

        self._relayout_filters()
        return self.filters_wrapper

    def _relayout_filters(self) -> None:
        if not self.filter_specs:
            return
        width = self._content_width()
        columns = 1 if width < 560 else 2 if width < 980 else 4
        if columns == self.current_filter_columns and self.filters_layout.count():
            return
        self.current_filter_columns = columns
        while self.filters_layout.count():
            item = self.filters_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        for index, (label_text, field) in enumerate(self.filter_specs):
            row = (index // columns) * 2
            column = index % columns
            label = QLabel(label_text)
            label.setObjectName("FilterLabel")
            self.filters_layout.addWidget(label, row, column)
            self.filters_layout.addWidget(field, row + 1, column)

        for column in range(4):
            self.filters_layout.setColumnStretch(column, 1 if column < columns else 0)

    def _refresh_cases(self) -> None:
        filtered_cases = self._filtered_cases()
        self.result_text.setText(f"{len(filtered_cases)} hồ sơ được tìm thấy")
        self._clear_cards()

        columns = self._card_column_count()
        self.current_card_columns = columns
        for index, case in enumerate(filtered_cases):
            row = index // columns
            column = index % columns
            self.cards_layout.addWidget(self._build_case_card(case), row, column)

        create_index = len(filtered_cases)
        create_row = create_index // columns
        create_column = create_index % columns
        self.cards_layout.addWidget(self._build_create_card(), create_row, create_column)

        for column in range(columns):
            self.cards_layout.setColumnStretch(column, 1)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "business_page") and hasattr(self, "cards_layout") and self.stack.currentWidget() == self.business_page:
            self._relayout_filters()
            columns = self._card_column_count()
            if columns != self.current_card_columns:
                self._refresh_cases()

    def _card_column_count(self) -> int:
        available_width = max(1, self._content_width())
        return max(1, min(4, (available_width + self.CARD_GAP) // (self.CARD_WIDTH + self.CARD_GAP)))

    def _content_width(self) -> int:
        return max(1, self.width() - self.SIDEBAR_WIDTH - self.PAGE_HORIZONTAL_MARGIN)

    def _authorized_person_name(self, case: CaseSummary) -> str:
        name = str(case.form_values.get("authorized_person_full_name", "") or "").strip()
        return name or case.owner or "Chưa chọn"

    def _display_company_name(self, company_name: str) -> str:
        text = " ".join(str(company_name or "").split())
        if not text:
            return ""
        legal_form_patterns = [
            r"\bcông\s+ty\b",
            r"\bcong\s+ty\b",
            r"\bcty\b",
            r"\btnhh\b",
            r"\btrách\s+nhiệm\s+hữu\s+hạn\b",
            r"\btrach\s+nhiem\s+huu\s+han\b",
            r"\bmột\s+thành\s+viên\b",
            r"\bmot\s+thanh\s+vien\b",
            r"\bhai\s+thành\s+viên\s+trở\s+lên\b",
            r"\bhai\s+thanh\s+vien\s+tro\s+len\b",
            r"\bmtv\b",
            r"\bctcp\b",
            r"\btmcp\b",
            r"\bcp\b",
            r"\bcổ\s+phần\b",
            r"\bco\s+phan\b",
            r"\bdntn\b",
            r"\bdoanh\s+nghiệp\s+tư\s+nhân\b",
            r"\bdoanh\s+nghiep\s+tu\s+nhan\b",
        ]
        for pattern in legal_form_patterns:
            text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text).strip(" -,")
        return text or company_name

    def _card_title_text(self, title: str, metrics: QFontMetrics, width: int, max_lines: int = 3) -> str:
        words = title.split()
        if not words:
            return ""
        lines: list[str] = []
        index = 0
        while index < len(words) and len(lines) < max_lines:
            line = words[index]
            index += 1
            while index < len(words) and metrics.horizontalAdvance(f"{line} {words[index]}") <= width:
                line = f"{line} {words[index]}"
                index += 1
            lines.append(line)
        if index < len(words):
            remaining = f"{lines[-1]} {' '.join(words[index:])}".rstrip()
            suffix = "..."
            while remaining and metrics.horizontalAdvance(f"{remaining}{suffix}") > width:
                remaining = remaining[:-1].rstrip()
            lines[-1] = f"{remaining}{suffix}"
        return "\n".join(lines)

    def _filtered_cases(self) -> list[CaseSummary]:
        search_text = self.search_input.text().strip().lower()
        case_type = self.case_type_filter.currentText()
        condition = self.condition_filter.currentText()
        status = self.status_filter.currentText()

        result = []
        for case in self.cases:
            haystack = f"{case.company_name} {self._authorized_person_name(case)} {case.case_type} {case.status}".lower()
            if search_text and search_text not in haystack:
                continue
            if case_type != "Tất cả loại hình" and case.case_type != case_type:
                continue
            if condition != "Tất cả" and case.condition != condition:
                continue
            if status != "Tất cả" and case.status != status:
                continue
            result.append(case)
        return result

    def _clear_cards(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _delete_case(self, case: CaseSummary) -> None:
        answer = QMessageBox.question(
            self,
            "Xóa hồ sơ",
            f"Bạn có muốn chuyển hồ sơ \"{case.company_name}\" vào thùng rác không?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.case_repository.soft_delete_case(case.id)
        self.cases = self.case_repository.list_cases()
        self._refresh_cases()

    def _refresh_trash(self) -> None:
        while self.trash_layout.count():
            item = self.trash_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        deleted_cases = self.case_repository.list_deleted_cases()
        if not deleted_cases:
            empty = QLabel("Thùng rác đang trống.")
            empty.setObjectName("EmptyDescription")
            self.trash_layout.addWidget(empty)
            self.trash_layout.addStretch(1)
            return

        for case in deleted_cases:
            self.trash_layout.addWidget(self._build_trash_row(case))
        self.trash_layout.addStretch(1)

    def _build_trash_row(self, case: CaseSummary) -> QWidget:
        row = QFrame()
        row.setObjectName("Card")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        info = QVBoxLayout()
        title = QLabel(case.company_name)
        title.setObjectName("CardTitle")
        title.setWordWrap(True)
        meta = QLabel(f"{case.case_type} | Người ủy quyền: {self._authorized_person_name(case)} | Đã xóa: {case.deleted_at or 'Không rõ'}")
        meta.setObjectName("MetaText")
        meta.setWordWrap(True)
        info.addWidget(title)
        info.addWidget(meta)

        restore_button = QPushButton("Khôi phục")
        restore_button.setObjectName("PrimaryButton")
        restore_button.clicked.connect(lambda checked=False, selected=case: self._restore_case(selected))

        delete_button = QPushButton("Xóa vĩnh viễn")
        delete_button.setObjectName("GhostButton")
        delete_button.clicked.connect(lambda checked=False, selected=case: self._delete_case_permanently(selected))

        layout.addLayout(info, 1)
        layout.addWidget(restore_button)
        layout.addWidget(delete_button)
        return row

    def _restore_case(self, case: CaseSummary) -> None:
        self.case_repository.restore_case(case.id)
        self.cases = self.case_repository.list_cases()
        self._refresh_trash()

    def _delete_case_permanently(self, case: CaseSummary) -> None:
        answer = QMessageBox.question(
            self,
            "Xóa vĩnh viễn",
            f"Hồ sơ \"{case.company_name}\" sẽ bị xóa vĩnh viễn. Bạn có chắc không?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.case_repository.delete_case_permanently(case.id)
        self.cases = self.case_repository.list_cases()
        self._refresh_trash()

    def _empty_trash(self) -> None:
        deleted_cases = self.case_repository.list_deleted_cases()
        if not deleted_cases:
            QMessageBox.information(self, "Thùng rác", "Thùng rác đang trống.")
            return
        answer = QMessageBox.question(
            self,
            "Xóa toàn bộ thùng rác",
            f"Bạn có muốn xóa vĩnh viễn toàn bộ {len(deleted_cases)} hồ sơ trong thùng rác không?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.case_repository.empty_trash()
        self.cases = self.case_repository.list_cases()
        self._refresh_trash()

    def _build_case_card(self, case: CaseSummary) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        card.setFixedSize(220, 344)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 14)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("CardHeader")
        header.setFixedHeight(112)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(14, 12, 14, 12)

        top_row = QHBoxLayout()
        badge = QLabel(case.warning or case.status)
        badge.setObjectName("WarningBadge" if case.warning else "StatusBadge")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedHeight(24)
        delete_button = QPushButton("Xóa")
        delete_button.setObjectName("HeaderDeleteButton")
        delete_button.clicked.connect(lambda checked=False, selected=case: self._delete_case(selected))
        top_row.addWidget(badge, 0, Qt.AlignLeft | Qt.AlignTop)
        top_row.addStretch(1)
        top_row.addWidget(delete_button, 0, Qt.AlignRight | Qt.AlignTop)
        header_layout.addLayout(top_row)
        header_layout.addStretch(1)

        icon = QLabel("DOC")
        icon.setStyleSheet("font-size: 28px; font-weight: 800; color: rgba(255,255,255,0.78);")
        icon.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(icon)
        header_layout.addStretch(1)

        layout.addWidget(header)

        body = QVBoxLayout()
        body.setContentsMargins(14, 14, 14, 0)
        body.setSpacing(8)

        display_name = self._display_company_name(case.name)
        title = QLabel()
        title.setObjectName("CardTitle")
        title.setToolTip(case.name)
        title.setText(self._card_title_text(display_name, title.fontMetrics(), self.CARD_WIDTH - 28))
        title.setWordWrap(False)
        title.setMinimumHeight(title.fontMetrics().lineSpacing() * 3)
        body.addWidget(title)

        subtitle = QLabel(case.case_type.upper())
        subtitle.setObjectName("CardSubtitle")
        subtitle.setWordWrap(True)
        body.addWidget(subtitle)

        body.addSpacing(4)
        body.addWidget(self._meta_row("Người ủy quyền", self._authorized_person_name(case)))
        body.addWidget(self._meta_row("Thành viên", str(case.members)))
        body.addWidget(self._meta_row("Vốn điều lệ", case.capital))
        body.addWidget(self._meta_row("Cập nhật", case.updated_at))
        body.addStretch(1)

        actions = QHBoxLayout()
        open_button = QPushButton("Mở")
        open_button.setObjectName("GhostButton")
        open_button.clicked.connect(lambda checked=False, selected=case: self._open_case_documents(selected))
        edit_button = QPushButton("Sửa")
        edit_button.setObjectName("GhostButton")
        edit_button.clicked.connect(lambda checked=False, selected=case: self._open_case_workspace(selected))
        actions.addWidget(open_button)
        actions.addWidget(edit_button)
        body.addLayout(actions)

        layout.addLayout(body, 1)
        return card

    def _meta_row(self, label: str, value: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label_widget = QLabel(label)
        label_widget.setObjectName("MetaText")
        value_widget = QLabel(value)
        value_widget.setObjectName("MetaText")
        value_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value_widget.setWordWrap(True)

        layout.addWidget(label_widget)
        layout.addWidget(value_widget, 1)
        return row

    def _build_create_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("CreateCard")
        card.setFixedSize(220, 344)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)
        layout.addItem(QSpacerItem(1, 34, QSizePolicy.Minimum, QSizePolicy.Expanding))

        icon = QLabel("+")
        icon.setObjectName("CreateIcon")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        title = QLabel("Tạo hồ sơ mới")
        title.setObjectName("CreateTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        description = QLabel("Tạo form hồ sơ thành lập doanh nghiệp và lưu dữ liệu vào máy.")
        description.setObjectName("CreateDescription")
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignCenter)
        layout.addWidget(description)

        button = QPushButton("Tạo hồ sơ")
        button.setObjectName("PrimaryButton")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(self._open_new_business_case)
        layout.addWidget(button)
        layout.addItem(QSpacerItem(1, 34, QSizePolicy.Minimum, QSizePolicy.Expanding))

        return card

    def _open_create_case_dialog(self) -> None:
        self._open_new_business_case()
        return
        dialog = CreateCaseDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            case = dialog.build_case()
            self.case_repository.save_case(case)
            self.cases = self.case_repository.list_cases()
            self._refresh_cases()

    def _show_case_info(self, case: CaseSummary) -> None:
        QMessageBox.information(
            self,
            "Thông tin hồ sơ",
            (
                f"Tên doanh nghiệp: {case.company_name}\n"
                f"Loại hình: {case.case_type}\n"
                f"Người ủy quyền: {self._authorized_person_name(case)}\n"
                f"Số thành viên: {case.members}\n"
                f"Vốn điều lệ: {case.capital}\n"
                f"Trạng thái: {case.status}"
            ),
        )

    def _build_coming_soon_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 28, 36, 28)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Ch\u1ee9c n\u0103ng n\u00e0y \u0111ang \u0111\u01b0\u1ee3c ph\u00e1t tri\u1ec3n")
        title.setObjectName("ComingSoonTitle")
        title.setAlignment(Qt.AlignCenter)

        description = QLabel(
            "T\u00ednh n\u0103ng n\u00e0y s\u1ebd \u0111\u01b0\u1ee3c b\u1ed5 sung trong c\u00e1c phi\u00ean b\u1ea3n s\u1eafp t\u1edbi."
        )
        description.setObjectName("EmptyDescription")
        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)
        description.setMaximumWidth(520)
        layout.addWidget(title)
        layout.addWidget(description)
        return page

    def _open_new_business_case(self) -> None:
        self._open_case_workspace(None)

    def _build_authorized_person_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        header = QHBoxLayout()
        back_button = QPushButton("Quay l\u1ea1i h\u1ed3 s\u01a1")
        back_button.setObjectName("GhostButton")
        back_button.setCursor(Qt.PointingHandCursor)
        back_button.clicked.connect(self._return_to_business_list)
        heading = QVBoxLayout()
        title = QLabel("Qu\u1ea3n l\u00fd th\u00f4ng tin ng\u01b0\u1eddi \u1ee7y quy\u1ec1n")
        title.setObjectName("PageTitle")
        description = QLabel("Ch\u1ecdn nhanh ng\u01b0\u1eddi \u1ee7y quy\u1ec1n khi t\u1ea1o h\u1ed3 s\u01a1. Profile m\u1eb7c \u0111\u1ecbnh lu\u00f4n \u0111\u01b0\u1ee3c gi\u1eef nguy\u00ean.")
        description.setObjectName("PageDescription")
        description.setWordWrap(True)
        heading.addWidget(title)
        heading.addWidget(description)
        new_button = QPushButton("+ T\u1ea1o profile m\u1edbi")
        new_button.setObjectName("PrimaryButton")
        new_button.setCursor(Qt.PointingHandCursor)
        new_button.clicked.connect(self._new_authorized_person_profile)
        header.addWidget(back_button, 0, Qt.AlignTop)
        header.addLayout(heading, 1)
        header.addWidget(new_button, 0, Qt.AlignTop)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(16)

        cards_frame = QFrame()
        cards_frame.setObjectName("Card")
        cards_layout = QGridLayout(cards_frame)
        cards_layout.setContentsMargins(16, 14, 16, 14)
        cards_layout.setHorizontalSpacing(14)
        cards_layout.setVerticalSpacing(14)
        self.authorized_person_cards_layout = cards_layout
        container_layout.addWidget(cards_frame)

        form_frame = QFrame()
        form_frame.setObjectName("Card")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(16, 14, 16, 14)
        form_layout.setSpacing(12)
        form_title = QLabel("Th\u00f4ng tin profile \u0111ang ch\u1ec9nh s\u1eeda")
        form_title.setObjectName("SectionTitle")
        form_layout.addWidget(form_title)

        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)
        definitions = [
            ("authorized_person_full_name", "H\u1ecd t\u00ean"),
            ("authorized_person_date_of_birth", "Ng\u00e0y sinh"),
            ("authorized_person_gender", "Gi\u1edbi t\u00ednh"),
            ("authorized_person_id_number", "S\u1ed1 CCCD"),
            ("authorized_person_issue_date", "Ng\u00e0y c\u1ea5p"),
            ("authorized_person_issue_place", "N\u01a1i c\u1ea5p"),
            ("authorized_person_contact_address", "\u0110\u1ecba ch\u1ec9 li\u00ean l\u1ea1c"),
            ("authorized_person_phone", "\u0110i\u1ec7n tho\u1ea1i"),
            ("authorized_person_email", "Email"),
        ]
        for key, label_text in definitions:
            if key == "authorized_person_contact_address":
                field: QLineEdit | QTextEdit = QTextEdit()
                field.setFixedHeight(84)
            else:
                field = QLineEdit()
            self.authorized_person_fields[key] = field
            form.addRow(label_text, field)
        form_layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        reset_button = QPushButton("H\u1ee7y thay \u0111\u1ed5i")
        reset_button.setObjectName("GhostButton")
        reset_button.clicked.connect(self._reload_authorized_person_manager)
        save_button = QPushButton("L\u01b0u profile")
        save_button.setObjectName("PrimaryButton")
        save_button.clicked.connect(self._save_authorized_person_manager)
        self.authorized_person_save_button = save_button
        buttons.addWidget(reset_button)
        buttons.addWidget(save_button)
        form_layout.addLayout(buttons)
        container_layout.addWidget(form_frame)
        container_layout.addStretch(1)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        return page

    def _open_authorized_person_manager(self) -> None:
        self._reload_authorized_person_manager()
        self.stack.setCurrentWidget(self.authorized_person_page)

    def _reload_authorized_person_manager(self) -> None:
        payload = self._load_authorized_person_profiles()
        self.authorized_person_profiles = [dict(profile) for profile in payload["profiles"]]
        self.authorized_person_selected_id = str(payload.get("selected_profile_id", ""))
        profile = self._authorized_profile_by_id(
            self.authorized_person_profiles, self.authorized_person_selected_id
        )
        self._write_authorized_person_form(profile or {})
        self._refresh_authorized_person_cards()

    def _write_authorized_person_form(self, profile: dict[str, str]) -> None:
        for key, field in self.authorized_person_fields.items():
            value = str(profile.get(key, ""))
            if isinstance(field, QTextEdit):
                field.setPlainText(value)
            else:
                field.setText(value)
            field.setReadOnly(False)
        if self.authorized_person_save_button is not None:
            self.authorized_person_save_button.setEnabled(True)

    def _read_authorized_person_form(self) -> dict[str, str]:
        profile = {"id": self.authorized_person_selected_id or str(uuid4())}
        for key, field in self.authorized_person_fields.items():
            profile[key] = field.toPlainText().strip() if isinstance(field, QTextEdit) else field.text().strip()
        return profile

    def _new_authorized_person_profile(self) -> None:
        self.authorized_person_selected_id = str(uuid4())
        self._write_authorized_person_form({"authorized_person_gender": "N\u1eef"})
        self._refresh_authorized_person_cards()

    def _edit_authorized_person_profile(self, profile_id: str) -> None:
        profile = self._authorized_profile_by_id(self.authorized_person_profiles, profile_id)
        if profile is None:
            return
        self.authorized_person_selected_id = profile_id
        self._write_authorized_person_form(profile)
        self._refresh_authorized_person_cards()

    def _delete_authorized_person_profile(self, profile_id: str) -> None:
        if self._is_builtin_authorized_person_profile(profile_id):
            return
        profile = self._authorized_profile_by_id(self.authorized_person_profiles, profile_id)
        if profile is None:
            return
        name = profile.get("authorized_person_full_name", "profile n\u00e0y")
        answer = QMessageBox.question(
            self,
            "X\u00f3a profile",
            f"B\u1ea1n c\u00f3 mu\u1ed1n x\u00f3a {name} kh\u1ecfi danh s\u00e1ch ng\u01b0\u1eddi \u1ee7y quy\u1ec1n kh\u00f4ng?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.authorized_person_profiles = [
            item for item in self.authorized_person_profiles if str(item.get("id", "")) != profile_id
        ]
        if self.authorized_person_selected_id == profile_id:
            self.authorized_person_selected_id = ""
        self._save_authorized_person_profiles(
            {"selected_profile_id": self.authorized_person_selected_id, "profiles": self.authorized_person_profiles}
        )
        self._reload_authorized_person_manager()

    def _save_authorized_person_manager(self) -> None:
        profile = self._read_authorized_person_form()
        self.authorized_person_profiles = [
            item for item in self.authorized_person_profiles if str(item.get("id", "")) != profile["id"]
        ]
        self.authorized_person_profiles.append(profile)
        self.authorized_person_selected_id = profile["id"]
        self._save_authorized_person_profiles(
            {"selected_profile_id": profile["id"], "profiles": self.authorized_person_profiles}
        )
        self._reload_authorized_person_manager()
        QMessageBox.information(self, "\u0110\u00e3 l\u01b0u", "Profile ng\u01b0\u1eddi \u1ee7y quy\u1ec1n \u0111\u00e3 \u0111\u01b0\u1ee3c l\u01b0u tr\u00ean m\u00e1y.")

    def _refresh_authorized_person_cards(self) -> None:
        if self.authorized_person_cards_layout is None:
            return
        while self.authorized_person_cards_layout.count():
            item = self.authorized_person_cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for index, profile in enumerate(self.authorized_person_profiles):
            self.authorized_person_cards_layout.addWidget(
                self._build_authorized_profile_card(
                    profile,
                    str(profile.get("id", "")) == self.authorized_person_selected_id,
                    self._edit_authorized_person_profile,
                    self._delete_authorized_person_profile,
                ),
                index // 3,
                index % 3,
            )

    def _build_authorized_profile_card(self, profile: dict[str, str], active: bool, on_edit, on_delete) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        card.setCursor(Qt.PointingHandCursor)
        card.setFixedSize(260, 178)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        top = QHBoxLayout()
        profile_id = str(profile.get("id", ""))
        is_builtin = self._is_builtin_authorized_person_profile(profile_id)
        badge = QLabel("M\u1eb7c \u0111\u1ecbnh" if is_builtin else ("\u0110ang ch\u1ecdn" if active else "Profile"))
        badge.setObjectName("StatusBadge")
        delete_button = QPushButton("X\u00f3a")
        delete_button.setObjectName("HeaderDeleteButton")
        delete_button.setEnabled(not is_builtin)
        delete_button.clicked.connect(lambda checked=False, selected=profile_id: on_delete(selected))
        top.addWidget(badge)
        top.addStretch(1)
        top.addWidget(delete_button)
        layout.addLayout(top)

        name = QLabel(profile.get("authorized_person_full_name", "Chưa nhập tên"))
        name.setObjectName("CardTitle")
        name.setWordWrap(True)
        layout.addWidget(name)
        layout.addWidget(self._meta_row("CCCD", profile.get("authorized_person_id_number", "Chưa nhập")))
        layout.addWidget(self._meta_row("Điện thoại", profile.get("authorized_person_phone", "Chưa nhập")))
        layout.addStretch(1)

        edit_button = QPushButton("Ch\u1ecdn / s\u1eeda")
        edit_button.setObjectName("GhostButton")
        edit_button.clicked.connect(lambda checked=False, selected=profile_id: on_edit(selected))
        layout.addWidget(edit_button)

        def select_profile(event, selected=profile_id) -> None:
            if event.button() == Qt.LeftButton:
                on_edit(selected)
                event.accept()

        card.mousePressEvent = select_profile
        return card

    def _load_authorized_person(self) -> dict[str, str]:
        payload = self._load_authorized_person_profiles()
        selected = self._authorized_profile_by_id(payload["profiles"], str(payload.get("selected_profile_id", "")))
        selected = selected or (payload["profiles"][0] if payload["profiles"] else {})
        result = dict(selected)
        result["__profiles"] = payload["profiles"]
        return result

    @staticmethod
    def _builtin_authorized_person_profiles() -> list[dict[str, str]]:
        return [dict(profile) for profile in BUILT_IN_AUTHORIZED_PERSON_PROFILES]

    @staticmethod
    def _is_builtin_authorized_person_profile(profile_id: str) -> bool:
        return any(profile_id == profile["id"] for profile in BUILT_IN_AUTHORIZED_PERSON_PROFILES)

    def _merge_authorized_person_profiles(
        self, selected_profile_id: str, profiles: list[dict[str, str]]
    ) -> dict[str, object]:
        built_in_profiles = self._builtin_authorized_person_profiles()
        saved_profiles = {str(profile.get("id", "")): profile for profile in profiles}
        for profile in built_in_profiles:
            saved_profiles.pop(profile["id"], None)
        merged_profiles = built_in_profiles + list(saved_profiles.values())
        if not self._authorized_profile_by_id(merged_profiles, selected_profile_id):
            selected_profile_id = built_in_profiles[0]["id"]
        return {"selected_profile_id": selected_profile_id, "profiles": merged_profiles}

    def _load_authorized_person_profiles(self) -> dict[str, object]:
        selected_profile_id = ""
        profiles: list[dict[str, str]] = []
        if self.authorized_person_path.exists():
            try:
                raw = json.loads(self.authorized_person_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raw = {}
            if isinstance(raw, dict) and isinstance(raw.get("profiles"), list):
                selected_profile_id = str(raw.get("selected_profile_id", ""))
                profiles = [item for item in raw["profiles"] if isinstance(item, dict)]
            elif isinstance(raw, dict) and any(str(key).startswith("authorized_person_") for key in raw):
                profile = {str(key): str(value) for key, value in raw.items()}
                profile.setdefault("id", str(uuid4()))
                selected_profile_id = profile["id"]
                profiles = [profile]
        return self._merge_authorized_person_profiles(selected_profile_id, profiles)

    def _authorized_profile_by_id(self, profiles: list[dict[str, str]], profile_id: str) -> dict[str, str] | None:
        for profile in profiles:
            if str(profile.get("id", "")) == profile_id:
                return profile
        return None

    def _save_authorized_person_profiles(self, payload: dict[str, object]) -> None:
        selected_profile_id = str(payload.get("selected_profile_id", ""))
        profiles = [profile for profile in payload.get("profiles", []) if isinstance(profile, dict)]
        self.authorized_person_path.parent.mkdir(parents=True, exist_ok=True)
        self.authorized_person_path.write_text(
            json.dumps(
                {"selected_profile_id": selected_profile_id, "profiles": profiles},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _save_authorized_person(self, values: dict[str, str]) -> None:
        values.setdefault("id", str(uuid4()))
        self._save_authorized_person_profiles({"selected_profile_id": values["id"], "profiles": [values]})

    def _open_case_workspace(self, case: CaseSummary | None) -> None:
        if case is not None:
            case = self.case_repository.get_case(case.id) or case
        if self.current_workspace is not None:
            self.stack.removeWidget(self.current_workspace)
            self.current_workspace.deleteLater()
            self.current_workspace = None
        if self.current_documents_view is not None:
            self.stack.removeWidget(self.current_documents_view)
            self.current_documents_view.deleteLater()
            self.current_documents_view = None

        self.current_workspace = BusinessRegistrationWorkspace(
            on_back=self._return_to_business_list,
            on_save=self._save_case_from_workspace,
            case=case,
            on_export=self._open_case_documents,
            authorized_person_defaults=self._load_authorized_person(),
            industry_catalog=self.industry_catalog,
            bundle_root=self.app_paths.bundle_root,
            default_export_root=self.app_paths.documents_root,
        )
        self.stack.addWidget(self.current_workspace)
        self.stack.setCurrentWidget(self.current_workspace)

    def _open_case_documents(self, case: CaseSummary) -> None:
        case = self.case_repository.get_case(case.id) or case
        if self.current_workspace is not None:
            self.stack.removeWidget(self.current_workspace)
            self.current_workspace.deleteLater()
            self.current_workspace = None
        if self.current_documents_view is not None:
            self.stack.removeWidget(self.current_documents_view)
            self.current_documents_view.deleteLater()
            self.current_documents_view = None

        self.current_documents_view = BusinessRegistrationDocumentsView(
            case=case,
            on_back=self._return_to_business_list,
            on_edit=lambda selected_id=case.id: self._open_case_workspace(self.case_repository.get_case(selected_id) or case),
        )
        self.stack.addWidget(self.current_documents_view)
        self.stack.setCurrentWidget(self.current_documents_view)

    def _return_to_business_list(self) -> None:
        self.cases = self.case_repository.list_cases()
        self._refresh_cases()
        self.stack.setCurrentWidget(self.business_page)

    def _save_case_from_workspace(self, case: CaseSummary) -> None:
        self.case_repository.save_case(case)
        self.cases = self.case_repository.list_cases()

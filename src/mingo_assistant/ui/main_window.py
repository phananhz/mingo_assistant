from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mingo_assistant.models.case import CaseSummary
from mingo_assistant.repositories.case_repository import CaseRepository
from mingo_assistant.ui.views.business_registration_documents import BusinessRegistrationDocumentsView
from mingo_assistant.ui.views.business_registration_workspace import BusinessRegistrationWorkspace


NAV_ITEMS = [
    ("business_registration", "Hồ sơ thành lập doanh nghiệp"),
    ("trash", "Thùng rác"),
    ("capital_change", "Hồ sơ thay đổi vốn điều lệ"),
    ("legal_representative_change", "Hồ sơ thay đổi đại diện pháp luật"),
    ("address_change", "Hồ sơ thay đổi địa chỉ trụ sở"),
    ("business_lines_change", "Hồ sơ bổ sung ngành nghề"),
    ("dissolution", "Hồ sơ giải thể doanh nghiệp"),
    ("templates", "Quản lý mẫu Word"),
    ("people", "Kho cá nhân/tổ chức"),
]


class MainWindow(QMainWindow):
    SIDEBAR_WIDTH = 220
    PAGE_HORIZONTAL_MARGIN = 48
    CARD_WIDTH = 220
    CARD_GAP = 18

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Mingo Assistant")
        self.resize(1280, 760)
        self.setMinimumSize(760, 520)

        self.case_repository = CaseRepository()
        self.cases: list[CaseSummary] = self.case_repository.list_cases()
        self.nav_buttons: dict[str, QPushButton] = {}
        self.stack = QStackedWidget()
        self.current_workspace: BusinessRegistrationWorkspace | None = None
        self.current_documents_view: BusinessRegistrationDocumentsView | None = None
        self.authorized_person_path = Path("data/app/authorized_person.json")

        self.search_input = QLineEdit()
        self.case_type_filter = QComboBox()
        self.condition_filter = QComboBox()
        self.status_filter = QComboBox()
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
        footer.setStyleSheet("color: #ffe3ec; font-size: 12px;")
        layout.addWidget(footer)

        return sidebar

    def _build_content_stack(self) -> QWidget:
        content = QFrame()
        content.setObjectName("Content")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        self.business_page = self._build_business_registration_page()
        self.trash_page = self._build_trash_page()
        self.coming_soon_page = self._build_coming_soon_page()

        self.stack.addWidget(self.business_page)
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
        elif key == "trash":
            self._refresh_trash()
            self.stack.setCurrentWidget(self.trash_page)
        else:
            self.stack.setCurrentWidget(self.coming_soon_page)

    def _build_business_registration_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(18)

        header = QHBoxLayout()
        header_text = QVBoxLayout()
        title = QLabel("Hồ sơ thành lập doanh nghiệp")
        title.setObjectName("PageTitle")
        description = QLabel(
            "Quản lý hồ sơ, kiểm tra dữ liệu OCR và tạo bộ Word cho hồ sơ thành lập doanh nghiệp."
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
        authorized_person_button.clicked.connect(self._open_authorized_person_dialog)

        header.addLayout(header_text, 1)
        header.addWidget(authorized_person_button, 0, Qt.AlignTop)
        header.addWidget(create_button, 0, Qt.AlignTop)
        layout.addLayout(header)

        layout.addWidget(self._build_filters())

        self.result_text.setObjectName("ResultText")
        layout.addWidget(self.result_text)

        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setFrameShape(QFrame.NoFrame)
        self.cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setHorizontalSpacing(18)
        self.cards_layout.setVerticalSpacing(18)

        self.cards_scroll.setWidget(self.cards_container)
        layout.addWidget(self.cards_scroll, 1)

        return page

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

    def _build_filters(self) -> QWidget:
        layout = self.filters_layout
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(6)

        self.search_input.setPlaceholderText("Tìm theo tên công ty, người phụ trách...")
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

    def _filtered_cases(self) -> list[CaseSummary]:
        search_text = self.search_input.text().strip().lower()
        case_type = self.case_type_filter.currentText()
        condition = self.condition_filter.currentText()
        status = self.status_filter.currentText()

        result = []
        for case in self.cases:
            haystack = f"{case.company_name} {case.owner} {case.case_type} {case.status}".lower()
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
        meta = QLabel(f"{case.case_type} | Người phụ trách: {case.owner} | Đã xóa: {case.deleted_at or 'Không rõ'}")
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

        title = QLabel(case.name)
        title.setObjectName("CardTitle")
        title.setWordWrap(True)
        body.addWidget(title)

        subtitle = QLabel(case.case_type.upper())
        subtitle.setObjectName("CardSubtitle")
        subtitle.setWordWrap(True)
        body.addWidget(subtitle)

        body.addSpacing(4)
        body.addWidget(self._meta_row("Người phụ trách", case.owner))
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
        if dialog.exec() == QDialog.Accepted:
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
                f"Người phụ trách: {case.owner}\n"
                f"Số thành viên: {case.members}\n"
                f"Vốn điều lệ: {case.capital}\n"
                f"Trạng thái: {case.status}"
            ),
        )

    def _build_coming_soon_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 28, 36, 28)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Đang được phát triển")
        title.setObjectName("ComingSoonTitle")
        title.setAlignment(Qt.AlignCenter)

        description = QLabel("Chức năng này sẽ được bổ sung sau. Hiện MVP ưu tiên hồ sơ thành lập doanh nghiệp.")
        description.setObjectName("EmptyDescription")
        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)
        description.setMaximumWidth(520)

        layout.addWidget(title)
        layout.addWidget(description)

        return page

    def _open_new_business_case(self) -> None:
        self._open_case_workspace(None)

    def _open_authorized_person_dialog(self) -> None:
        values = self._load_authorized_person()
        dialog = QDialog(self)
        dialog.setWindowTitle("Thông tin người ủy quyền")
        dialog.setMinimumWidth(620)

        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)

        fields: dict[str, QLineEdit | QTextEdit] = {}
        definitions = [
            ("authorized_person_full_name", "Họ tên"),
            ("authorized_person_date_of_birth", "Ngày sinh"),
            ("authorized_person_gender", "Giới tính"),
            ("authorized_person_id_number", "Số CCCD"),
            ("authorized_person_contact_address", "Địa chỉ liên lạc"),
            ("authorized_person_phone", "Điện thoại"),
            ("authorized_person_email", "Email"),
        ]
        for key, label_text in definitions:
            if key == "authorized_person_contact_address":
                field = QTextEdit()
                field.setFixedHeight(84)
                field.setPlainText(values.get(key, ""))
            else:
                field = QLineEdit(values.get(key, ""))
            fields[key] = field
            form.addRow(label_text, field)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        layout.addLayout(form)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.Accepted:
            return

        saved: dict[str, str] = {}
        for key, field in fields.items():
            if isinstance(field, QTextEdit):
                saved[key] = field.toPlainText().strip()
            else:
                saved[key] = field.text().strip()
        self._save_authorized_person(saved)
        QMessageBox.information(self, "Đã lưu", "Thông tin người ủy quyền đã được lưu trên máy.")

    def _load_authorized_person(self) -> dict[str, str]:
        if not self.authorized_person_path.exists():
            return {}
        try:
            return json.loads(self.authorized_person_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_authorized_person(self, values: dict[str, str]) -> None:
        self.authorized_person_path.parent.mkdir(parents=True, exist_ok=True)
        self.authorized_person_path.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")

    def _open_case_workspace(self, case: CaseSummary | None) -> None:
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
        )
        self.stack.addWidget(self.current_workspace)
        self.stack.setCurrentWidget(self.current_workspace)

    def _open_case_documents(self, case: CaseSummary) -> None:
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
            on_edit=lambda selected=case: self._open_case_workspace(selected),
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

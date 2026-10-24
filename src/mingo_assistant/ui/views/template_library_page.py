"""Form previews, DKDN downloads and tax dossier entry points."""
import re
import unicodedata
from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices

from PySide6.QtCore import QRect, QSignalBlocker, QSize, Qt
from PySide6.QtWidgets import (
    QBoxLayout, QButtonGroup, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
    QFileDialog, QMessageBox, QTabWidget,
)

from mingo_assistant.ui.views.template_library_catalog import TEMPLATE_GROUPS, TemplateDisplayItem
from mingo_assistant.services.documents.template_library import TemplateLibraryFiles
from mingo_assistant.ui.views.tax_dossier_list import TaxDossierList


def _search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    folded = "".join(character for character in normalized if not unicodedata.combining(character))
    return re.sub(r"\bms\s*(\d+)", r"ms\1", folded)


class TemplateFileList(QListWidget):
    def fit_rows(self) -> None:
        width = max(120, self.viewport().width() - 32)
        for index in range(self.count()):
            item = self.item(index)
            height = self.fontMetrics().boundingRect(QRect(0, 0, width, 10000), Qt.TextWordWrap, item.text()).height()
            item.setSizeHint(QSize(0, max(60, height + 20)))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.fit_rows()


class TemplateLibraryPage(QWidget):
    tax_template_requested = Signal(str)
    tax_case_requested = Signal(str)
    tax_case_edit_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None, *, bundle_root: Path | None = None) -> None:
        super().__init__(parent)
        self.files = TemplateLibraryFiles(
            bundle_root or Path(__file__).resolve().parents[4],
            {item.id: item.filename for item in TEMPLATE_GROUPS[0].items},
        )
        self.tax_files = TemplateLibraryFiles(
            bundle_root or Path(__file__).resolve().parents[4],
            {item.id: item.filename for item in TEMPLATE_GROUPS[1].items}, "tax",
        )
        self.setObjectName("TemplatesPage")
        self.current_group_id = TEMPLATE_GROUPS[0].id
        self.visible_templates: tuple[TemplateDisplayItem, ...] = ()
        self.group_buttons: dict[str, QPushButton] = {}
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)
        title = QLabel("Biểu mẫu")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        description = QLabel("Chọn nhóm và tìm biểu mẫu. Xem trước, tải biểu mẫu ĐKDN hoặc soạn hồ sơ từ biểu mẫu thuế.")
        description.setObjectName("PageDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        self.tabs = QTabWidget()
        catalog = QWidget()
        self.tabs.addTab(catalog, "Danh mục biểu mẫu")
        self.dossiers = TaxDossierList()
        self.tabs.addTab(self.dossiers, "Hồ sơ thuế đã soạn (0)")
        self.dossiers.open_requested.connect(self.tax_case_requested.emit)
        self.dossiers.edit_requested.connect(self.tax_case_edit_requested.emit)
        self.dossiers.create_requested.connect(self.show_tax_catalog)
        layout.addWidget(self.tabs, 1)
        layout = QVBoxLayout(catalog)

        groups_row = QHBoxLayout()
        groups_row.setSpacing(8)
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        for group in TEMPLATE_GROUPS:
            button = QPushButton(f"{group.title} ({len(group.items)})")
            button.setToolTip(group.description)
            button.setCheckable(True)
            button.setFixedHeight(40)
            button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            button.setCursor(Qt.PointingHandCursor)
            button.setAccessibleName(group.title)
            button.clicked.connect(lambda checked=False, key=group.id: self.select_group(key))
            self.button_group.addButton(button)
            self.group_buttons[group.id] = button
            groups_row.addWidget(button)
        groups_row.addStretch(1)
        layout.addLayout(groups_row)

        self.body_layout = QBoxLayout(QBoxLayout.LeftToRight)
        self.body_layout.setSpacing(14)
        self.list_panel = QGroupBox("Danh sách biểu mẫu")
        list_layout = QVBoxLayout(self.list_panel)
        list_layout.setContentsMargins(16, 20, 16, 16)
        list_layout.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("TemplateSearchInput")
        self.search_input.setFixedHeight(40)
        self.search_input.setPlaceholderText("Tìm theo tên biểu mẫu, tên file hoặc mã mẫu…")
        self.search_input.setAccessibleName("Tìm biểu mẫu trong nhóm đang chọn")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._refresh_list)
        list_layout.addWidget(self.search_input)
        self.count_label = QLabel()
        self.count_label.setObjectName("PageDescription")
        list_layout.addWidget(self.count_label)
        self.template_list = TemplateFileList()
        self.template_list.setObjectName("TemplateFileList")
        self.template_list.setWordWrap(True)
        self.template_list.setSpacing(4)
        self.template_list.setMinimumHeight(330)
        self.template_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.template_list.setAccessibleName("Danh sách file biểu mẫu")
        self.template_list.currentItemChanged.connect(self._show_selected_template)
        list_layout.addWidget(self.template_list, 1)
        self.empty_state = QLabel("Không có biểu mẫu phù hợp. Thử từ khóa khác hoặc xóa nội dung tìm kiếm.")
        self.empty_state.setWordWrap(True)
        self.empty_state.setAlignment(Qt.AlignCenter)
        self.empty_state.setMinimumHeight(110)
        list_layout.addWidget(self.empty_state)
        self.body_layout.addWidget(self.list_panel, 1)

        self.detail_panel = QGroupBox("Thông tin biểu mẫu")
        details = QVBoxLayout(self.detail_panel)
        details.setContentsMargins(18, 20, 18, 18)
        details.setSpacing(12)
        self.format_label = QLabel()
        self.format_label.setObjectName("SectionTitle")
        self.detail_title = QLabel()
        self.detail_title.setObjectName("CardTitle")
        self.detail_filename = QLabel()
        self.detail_folder = QLabel()
        for label in (self.detail_title, self.detail_filename, self.detail_folder):
            label.setTextFormat(Qt.PlainText)
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        for widget in (self.format_label, self.detail_title, QLabel("Tên file gốc"), self.detail_filename,
                       QLabel("Nhóm / thư mục"), self.detail_folder):
            details.addWidget(widget)
        details.addStretch(1)
        notice = QLabel()
        self.action_notice = notice
        notice.setWordWrap(True)
        notice.setObjectName("PageDescription")
        details.addWidget(notice)
        self.preview_button = QPushButton("Xem trước")
        self.preview_button.clicked.connect(self._preview_template)
        details.addWidget(self.preview_button)
        self.download_button = QPushButton("Tải biểu mẫu")
        self.download_button.setObjectName("PrimaryButton")
        self.download_button.clicked.connect(self._download_template)
        details.addWidget(self.download_button)
        self.use_template_button = QPushButton("Sử dụng biểu mẫu")
        self.use_template_button.setObjectName("PrimaryButton")
        self.use_template_button.setEnabled(False)
        self.use_template_button.setToolTip("Chưa bật xử lý biểu mẫu trong phiên bản giao diện này.")
        self.use_template_button.clicked.connect(self._use_tax_template)
        details.addWidget(self.use_template_button)
        self.body_layout.addWidget(self.detail_panel)
        layout.addLayout(self.body_layout, 1)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        self.select_group(self.current_group_id)

    def set_cases(self, cases) -> None:
        self.dossiers.set_cases(cases)
        self.tabs.setTabText(1, f"Hồ sơ thuế đã soạn ({len(self.dossiers.cases)})")

    def show_tax_catalog(self) -> None:
        self.select_group("tax")
        self.tabs.setCurrentIndex(0)

    @property
    def selected_template(self) -> TemplateDisplayItem | None:
        item = self.template_list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def select_group(self, key: str) -> None:
        if not any(group.id == key for group in TEMPLATE_GROUPS):
            return
        self.current_group_id = key
        for item_key, button in self.group_buttons.items():
            button.setChecked(item_key == key)
            button.setObjectName("CompactPrimaryButton" if item_key == key else "CompactGhostButton")
            button.style().unpolish(button)
            button.style().polish(button)
        with QSignalBlocker(self.search_input):
            self.search_input.clear()
        self._refresh_list()

    def _refresh_list(self) -> None:
        group = next(group for group in TEMPLATE_GROUPS if group.id == self.current_group_id)
        query = _search_text(self.search_input.text().strip())
        previous = self.selected_template
        self.visible_templates = tuple(item for item in group.items
                                       if query in _search_text(f"{item.title} {item.filename}"))
        with QSignalBlocker(self.template_list):
            self.template_list.clear()
            selected_row = 0
            for index, template in enumerate(self.visible_templates):
                item = QListWidgetItem(f"{template.title}\n{template.filename}")
                item.setData(Qt.UserRole, template)
                item.setToolTip(template.filename)
                self.template_list.addItem(item)
                if previous and previous.id == template.id:
                    selected_row = index
            if self.visible_templates:
                self.template_list.setCurrentRow(selected_row)
        self.count_label.setText(f"{len(self.visible_templates)} / {len(group.items)} biểu mẫu · {group.title}")
        self.empty_state.setVisible(not self.visible_templates)
        self.template_list.setVisible(bool(self.visible_templates))
        self.template_list.fit_rows()
        self._show_selected_template()

    def _show_selected_template(self, *_args) -> None:
        template = self.selected_template
        dkdn = self.current_group_id == "dkdn"
        for button in (self.preview_button, self.download_button):
            button.setVisible(dkdn or button is self.preview_button)
            button.setEnabled(template is not None)
        self.preview_button.setText("Xem trước" if dkdn else "Xem trước biểu mẫu")
        self.use_template_button.setVisible(not dkdn)
        self.use_template_button.setEnabled(not dkdn and template is not None)
        self.use_template_button.setToolTip("Mở hồ sơ, quét ERC, điền thông tin và xuất Word.")
        self.action_notice.setText(
            "Xem trước bằng ứng dụng đọc Word trên máy. Tải xuống để lưu bản sao biểu mẫu."
            if dkdn else "Xem trước hoặc sử dụng biểu mẫu để quét ERC, soạn hồ sơ và xuất Word."
        )
        self.format_label.setText(f"WORD · {template.format_label}" if template else "CHƯA CHỌN BIỂU MẪU")
        self.detail_title.setText(template.title if template else "Chọn một biểu mẫu trong danh sách")
        self.detail_filename.setText(template.filename if template else "—")
        self.detail_folder.setText(template.folder if template else "—")

    def _preview_template(self) -> None:
        template = self.selected_template
        if template is None:
            return
        try:
            files = self.files if self.current_group_id == "dkdn" else self.tax_files
            path = files.preview_copy(template.id)
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
                raise OSError("Không mở được trình xem. Vui lòng cài ứng dụng đọc Word hoặc tải biểu mẫu xuống.")
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Không thể xem trước", str(exc))

    def _use_tax_template(self) -> None:
        template = self.selected_template
        if self.current_group_id == "tax" and template is not None:
            self.tax_template_requested.emit(template.id)

    def _download_template(self) -> None:
        template = self.selected_template
        if self.current_group_id != "dkdn" or template is None:
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Lưu biểu mẫu", template.filename, "Word (*.docx)")
        if not filename:
            return
        destination = Path(filename)
        if not destination.suffix:
            destination = destination.with_suffix(".docx")
        try:
            self.files.download(template.id, destination)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Không thể tải biểu mẫu", str(exc))
            return
        QMessageBox.information(self, "Đã tải biểu mẫu", f"Đã lưu biểu mẫu tại:\n{destination}")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        wide = self.width() >= 900
        self.body_layout.setDirection(QBoxLayout.LeftToRight if wide else QBoxLayout.TopToBottom)
        self.detail_panel.setMaximumWidth(340 if wide else 16777215)

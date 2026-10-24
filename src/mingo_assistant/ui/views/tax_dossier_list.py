"""A case-scoped list of saved tax dossiers; no storage writes."""
import unicodedata

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QGridLayout, QSizePolicy,
)
from mingo_assistant.ui.widgets.combo_box import NoWheelComboBox
from mingo_assistant.ui.views.template_library_catalog import TEMPLATE_GROUPS
from mingo_assistant.ui.widgets.case_card import build_case_card, format_card_title, CASE_CARD_WIDTH, CASE_CARD_GAP


def searchable(text):
    text = unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
    return "".join(c for c in text if not unicodedata.combining(c))


class TaxDossierList(QWidget):
    open_requested = Signal(str)
    edit_requested = Signal(str)
    create_requested = Signal()
    delete_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.cases = []
        self.visible_cases = []
        self.cards = []
        self.columns = 0
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        self.count_label = QLabel("Hồ sơ thuế đã soạn")
        header.addWidget(self.count_label, 1)
        create = QPushButton("+ Soạn hồ sơ mới")
        create.clicked.connect(self.create_requested.emit)
        header.addWidget(create)
        layout.addLayout(header)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Tìm theo tên hồ sơ, biểu mẫu hoặc mã hồ sơ…")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(40)
        self.search.textChanged.connect(self.refresh)
        self.template_filter = NoWheelComboBox()
        self.template_filter.setAccessibleName("Lọc hồ sơ theo loại biểu mẫu thuế")
        self.template_filter.setToolTip("Lọc hồ sơ theo loại biểu mẫu thuế")
        self.template_filter.setFixedHeight(40)
        self.template_filter.setMinimumContentsLength(18)
        self.template_filter.setSizeAdjustPolicy(NoWheelComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.search.setMinimumWidth(0)
        self.template_filter.setMinimumWidth(0)
        self.search.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.template_filter.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.template_filter.addItem("Tất cả biểu mẫu", "")
        for template in TEMPLATE_GROUPS[1].items:
            self.template_filter.addItem(template.title, template.id)
        self.template_filter.currentIndexChanged.connect(self.refresh)
        filters = QHBoxLayout()
        filters.addWidget(self.search, 1)
        filters.addWidget(self.template_filter, 1)
        layout.addLayout(filters)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.grid.setSpacing(CASE_CARD_GAP)
        self.scroll.setWidget(self.grid_widget)
        layout.addWidget(self.scroll, 1)
        self.empty = QLabel("Chưa có hồ sơ thuế. Chọn biểu mẫu thuế để bắt đầu soạn hồ sơ mới.")
        self.empty.setWordWrap(True)
        layout.addWidget(self.empty)

    def set_cases(self, cases):
        from mingo_assistant.ui.views.tax_template_workspace import TAX_TEMPLATE_CASE_TYPE
        self.cases = [case for case in cases if case.case_type == TAX_TEMPLATE_CASE_TYPE and not case.is_deleted]
        self.refresh()

    def refresh(self, *_args):
        self.visible_cases = []
        query = searchable(self.search.text().strip())
        template_id = self.template_filter.currentData()
        for case in reversed(self.cases):
            if template_id and case.form_values.get("tax_template_id") != template_id:
                continue
            title = case.form_values.get("tax_dossier_name") or case.company_name
            template = case.form_values.get("tax_template_title", "Biểu mẫu thuế")
            if query not in searchable(f"{title} {template} {case.id}"):
                continue
            self.visible_cases.append(case)
        self.count_label.setText(f"{len(self.visible_cases)} hồ sơ được tìm thấy / {len(self.cases)} hồ sơ thuế")
        self.empty.setVisible(not self.visible_cases)
        self.empty.setText("Không tìm thấy hồ sơ phù hợp. Thử từ khóa khác hoặc chọn Tất cả biểu mẫu." if self.cases else "Chưa có hồ sơ thuế. Chọn biểu mẫu thuế để bắt đầu soạn hồ sơ mới.")
        self._build_cards()

    def _build_cards(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self.cards = []
        for case in self.visible_cases:
            title = case.form_values.get("tax_dossier_name") or case.company_name
            template = case.form_values.get("tax_template_title", "Biểu mẫu thuế")
            card = build_case_card(
                case, display_name=title, format_title=format_card_title,
                subtitle=format_card_title(template, self.fontMetrics(), CASE_CARD_WIDTH - 28, 2),
                metadata=[("Loại hồ sơ", "Biểu mẫu thuế"), ("Cập nhật", case.updated_at.split(" ")[0])],
                on_open=lambda selected: self.open_requested.emit(selected.id),
                on_edit=lambda selected: self.edit_requested.emit(selected.id),
                on_delete=lambda selected: self.delete_requested.emit(selected.id),
            )
            card.setToolTip(f"{title}\n{template}\nMã hồ sơ: {case.id}\nCập nhật: {case.updated_at}")
            self.cards.append(card)
        self._relayout_cards()

    def _relayout_cards(self):
        self.columns = max(1, (self.scroll.viewport().width() - 18 + CASE_CARD_GAP) // (CASE_CARD_WIDTH + CASE_CARD_GAP))
        for index, card in enumerate(self.cards):
            self.grid.addWidget(card, index // self.columns, index % self.columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout_cards()

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class DependentProcedureOption:
    id: str
    unit_type_id: str
    action_id: str
    title: str
    description: str
    badge: str
    icon: str
    is_ready: bool = False


UNIT_TYPE_SPECS = [
    {
        "id": "chi_nhanh",
        "title": "Chi nhánh",
        "subtitle": "Có con dấu & hạch toán",
        "icon": "🏢",
        "procedures": [
            DependentProcedureOption(
                id="cn_create",
                unit_type_id="chi_nhanh",
                action_id="create",
                title="Thành lập chi nhánh mới",
                description="Tạo thông báo lập chi nhánh, quyết định thành lập và văn bản bổ nhiệm người đứng đầu.",
                badge="Đang phát triển",
                icon="➕",
                is_ready=False,
            ),
            DependentProcedureOption(
                id="cn_update",
                unit_type_id="chi_nhanh",
                action_id="update",
                title="Thay đổi thông tin chi nhánh",
                description="Thay đổi địa chỉ, tên, ngành nghề hoạt động hoặc người đứng đầu chi nhánh.",
                badge="Đang phát triển",
                icon="✏️",
                is_ready=False,
            ),
            DependentProcedureOption(
                id="cn_terminate",
                unit_type_id="chi_nhanh",
                action_id="terminate",
                title="Chấm dứt hoạt động chi nhánh",
                description="Thông báo chấm dứt hoạt động chi nhánh, quyết định đóng chi nhánh và hoàn tất thuế.",
                badge="Đang phát triển",
                icon="❌",
                is_ready=False,
            ),
        ],
    },
    {
        "id": "vpdd",
        "title": "Văn phòng đại diện",
        "subtitle": "Đại diện theo ủy quyền",
        "icon": "🏛️",
        "procedures": [
            DependentProcedureOption(
                id="vpdd_create",
                unit_type_id="vpdd",
                action_id="create",
                title="Thành lập văn phòng đại diện mới",
                description="Tạo thông báo lập VPĐD, quyết định thành lập và bổ nhiệm người đứng đầu VPĐD.",
                badge="Đang phát triển",
                icon="➕",
                is_ready=False,
            ),
            DependentProcedureOption(
                id="vpdd_update",
                unit_type_id="vpdd",
                action_id="update",
                title="Thay đổi thông tin văn phòng đại diện",
                description="Thay đổi địa chỉ, tên hoặc người đứng đầu văn phòng đại diện.",
                badge="Đang phát triển",
                icon="✏️",
                is_ready=False,
            ),
            DependentProcedureOption(
                id="vpdd_terminate",
                unit_type_id="vpdd",
                action_id="terminate",
                title="Chấm dứt hoạt động văn phòng đại diện",
                description="Thông báo chấm dứt hoạt động VPĐD, quyết định đóng VPĐD và hoàn tất thủ tục.",
                badge="Đang phát triển",
                icon="❌",
                is_ready=False,
            ),
        ],
    },
    {
        "id": "ddkd",
        "title": "Địa điểm kinh doanh",
        "subtitle": "Kinh doanh cụ thể",
        "icon": "📍",
        "procedures": [
            DependentProcedureOption(
                id="ddkd_create",
                unit_type_id="ddkd",
                action_id="create",
                title="Lập địa điểm kinh doanh mới",
                description="Thông báo lập địa điểm kinh doanh trực thuộc doanh nghiệp hoặc chi nhánh.",
                badge="Đang phát triển",
                icon="➕",
                is_ready=False,
            ),
            DependentProcedureOption(
                id="ddkd_update",
                unit_type_id="ddkd",
                action_id="update",
                title="Thay đổi thông tin địa điểm kinh doanh",
                description="Thay đổi tên, địa chỉ hoặc ngành nghề kinh doanh tại địa điểm kinh doanh.",
                badge="Đang phát triển",
                icon="✏️",
                is_ready=False,
            ),
            DependentProcedureOption(
                id="ddkd_terminate",
                unit_type_id="ddkd",
                action_id="terminate",
                title="Chấm dứt hoạt động địa điểm kinh doanh",
                description="Thông báo chấm dứt hoạt động địa điểm kinh doanh theo quy định.",
                badge="Đang phát triển",
                icon="❌",
                is_ready=False,
            ),
        ],
    },
]


class UnitTypeCard(QFrame):
    """Card on top representing one of the 3 dependent unit types."""

    clicked = Signal(str)

    def __init__(self, type_id: str, title: str, subtitle: str, icon: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.type_id = type_id
        self.is_active = False
        self.setObjectName("CompanyTypeCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(126)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        self.icon_badge = QLabel(icon)
        self.icon_badge.setObjectName("CompanyTypeIcon")
        self.icon_badge.setAlignment(Qt.AlignCenter)
        self.icon_badge.setFixedSize(38, 38)
        top_row.addWidget(self.icon_badge)

        top_row.addStretch(1)

        self.check_badge = QLabel("✓")
        self.check_badge.setObjectName("CompanyTypeCheck")
        self.check_badge.setAlignment(Qt.AlignCenter)
        self.check_badge.setFixedSize(22, 22)
        top_row.addWidget(self.check_badge)

        layout.addLayout(top_row)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("CompanyTypeTitle")

        self.sub_label = QLabel(subtitle)
        self.sub_label.setObjectName("CompanyTypeSubtitle")

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.sub_label)
        layout.addLayout(text_layout)

    def set_active(self, active: bool) -> None:
        self.is_active = active
        self.setProperty("active", "true" if active else "false")
        self.check_badge.setVisible(active)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if event is None or event.button() == Qt.LeftButton:
            self.clicked.emit(self.type_id)
        if event is not None:
            super().mousePressEvent(event)


class DependentProcedureItem(QFrame):
    """List item for a procedure under the chosen unit type."""

    selected = Signal(str)
    activated = Signal(str)

    def __init__(self, option: DependentProcedureOption, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.option = option
        self.is_selected = False
        self.setObjectName("DossierListItem")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        self.icon_label = QLabel(option.icon)
        self.icon_label.setObjectName("DossierItemIcon")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(42, 42)
        layout.addWidget(self.icon_label)

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        self.title_label = QLabel(option.title)
        self.title_label.setObjectName("DossierItemTitle")
        header_row.addWidget(self.title_label)

        self.badge_label = QLabel(option.badge)
        self.badge_label.setObjectName("DossierItemBadgeReady" if option.is_ready else "DossierItemBadgeDev")
        header_row.addWidget(self.badge_label)
        header_row.addStretch(1)

        info_layout.addLayout(header_row)

        self.desc_label = QLabel(option.description)
        self.desc_label.setObjectName("DossierItemDesc")
        self.desc_label.setWordWrap(True)
        info_layout.addWidget(self.desc_label)

        layout.addLayout(info_layout, 1)

        self.indicator = QLabel("✓")
        self.indicator.setObjectName("DossierItemIndicator")
        self.indicator.setAlignment(Qt.AlignCenter)
        self.indicator.setFixedSize(22, 22)
        layout.addWidget(self.indicator)

    def set_selected(self, is_selected: bool) -> None:
        self.is_selected = is_selected
        self.setProperty("selected", "true" if is_selected else "false")
        self.indicator.setVisible(is_selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if event is None or event.button() == Qt.LeftButton:
            self.selected.emit(self.option.id)
        if event is not None:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event is None or event.button() == Qt.LeftButton:
            self.activated.emit(self.option.id)
        if event is not None:
            super().mouseDoubleClickEvent(event)


class DependentUnitModal(QDialog):
    """
    Modal for selecting a dependent unit procedure (Chi nhánh, VPĐD, Địa điểm KD).
    """

    procedure_chosen = Signal(str, str, str, bool)  # unit_type_id, action_id, title, is_ready

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("DependentUnitModal")
        self.setModal(True)

        self.current_unit_id = "chi_nhanh"
        self.unit_cards: dict[str, UnitTypeCard] = {}
        self.procedure_items: list[DependentProcedureItem] = []
        self.selected_procedure: DependentProcedureOption | None = None

        if parent is not None:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.resize(parent.size())
            self.move(parent.mapToGlobal(QPoint(0, 0)))
        else:
            self.setWindowTitle("Thủ tục đơn vị phụ thuộc DN")
            self.resize(1020, 700)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.overlay_container = QFrame(self)
        self.overlay_container.setObjectName("ModalOverlayContainer")
        container_layout = QVBoxLayout(self.overlay_container)
        container_layout.setContentsMargins(24, 24, 24, 24)
        container_layout.setAlignment(Qt.AlignCenter)

        # Popup Box
        self.modal_box = QFrame(self.overlay_container)
        self.modal_box.setObjectName("BusinessCreationModalBox")
        self.modal_box.setFixedWidth(980)
        self.modal_box.setMaximumHeight(680)

        shadow = QGraphicsDropShadowEffect(self.modal_box)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(15, 23, 42, 65))
        shadow.setOffset(0, 14)
        self.modal_box.setGraphicsEffect(shadow)

        box_layout = QVBoxLayout(self.modal_box)
        box_layout.setContentsMargins(36, 26, 36, 26)
        box_layout.setSpacing(18)

        # Top Bar
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.addSpacing(36)

        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        header_layout.setAlignment(Qt.AlignCenter)

        self.title_label = QLabel("Bạn muốn thực hiện thủ tục đơn vị phụ thuộc nào?")
        self.title_label.setObjectName("ModalTitle")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.subtitle_label = QLabel("Chọn loại hình đơn vị phụ thuộc và thủ tục tương ứng để bắt đầu.")
        self.subtitle_label.setObjectName("ModalSubtitle")
        self.subtitle_label.setAlignment(Qt.AlignCenter)

        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.subtitle_label)
        top_bar.addLayout(header_layout, 1)

        self.close_button = QPushButton("✕")
        self.close_button.setObjectName("ModalCloseButton")
        self.close_button.setFixedSize(36, 36)
        self.close_button.setCursor(Qt.PointingHandCursor)
        self.close_button.setToolTip("Đóng (ESC)")
        self.close_button.clicked.connect(self.reject)
        top_bar.addWidget(self.close_button, 0, Qt.AlignTop)

        box_layout.addLayout(top_bar)

        # 3 Unit Cards
        cards_row = QHBoxLayout()
        cards_row.setContentsMargins(0, 4, 0, 4)
        cards_row.setSpacing(14)

        for spec in UNIT_TYPE_SPECS:
            card = UnitTypeCard(
                type_id=spec["id"],
                title=spec["title"],
                subtitle=spec["subtitle"],
                icon=spec["icon"],
            )
            card.clicked.connect(self._on_unit_card_clicked)
            self.unit_cards[spec["id"]] = card
            cards_row.addWidget(card, 1)

        box_layout.addLayout(cards_row)

        # Section Header
        sec_header = QHBoxLayout()
        sec_header.setContentsMargins(0, 4, 0, 0)
        sec_title = QLabel("Danh sách thủ tục")
        sec_title.setObjectName("DossierSectionTitle")
        sec_header.addWidget(sec_title, 1)

        self.count_badge = QLabel("3 thủ tục khả dụng")
        self.count_badge.setObjectName("ItemCountBadge")
        sec_header.addWidget(self.count_badge, 0, Qt.AlignVCenter)
        box_layout.addLayout(sec_header)

        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("DossierScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.viewport().setAutoFillBackground(False)
        self.scroll_area.setMaximumHeight(260)

        self.list_container = QWidget()
        self.list_container.setObjectName("DossierListContainer")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 4, 4, 4)
        self.list_layout.setSpacing(10)
        self.scroll_area.setWidget(self.list_container)
        box_layout.addWidget(self.scroll_area, 1)

        # Footer
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 8, 0, 0)

        self.status_icon = QLabel("●")
        self.status_icon.setObjectName("ModalStatusDot")
        footer_layout.addWidget(self.status_icon)

        self.selected_summary_label = QLabel("Hồ sơ đang chọn: Chưa chọn")
        self.selected_summary_label.setObjectName("ModalSelectedSummary")
        footer_layout.addWidget(self.selected_summary_label, 1)

        self.dismiss_button = QPushButton("Đóng")
        self.dismiss_button.setObjectName("ModalDismissButton")
        self.dismiss_button.setCursor(Qt.PointingHandCursor)
        self.dismiss_button.setFixedHeight(42)
        self.dismiss_button.clicked.connect(self.reject)
        footer_layout.addWidget(self.dismiss_button)

        self.create_button = QPushButton("Tạo hồ sơ →")
        self.create_button.setObjectName("ModalCreateButton")
        self.create_button.setCursor(Qt.PointingHandCursor)
        self.create_button.setFixedHeight(42)
        self.create_button.setMinimumWidth(150)
        self.create_button.clicked.connect(self._on_create_clicked)
        footer_layout.addWidget(self.create_button)

        box_layout.addLayout(footer_layout)
        container_layout.addWidget(self.modal_box)
        root_layout.addWidget(self.overlay_container)

        self._select_unit_type("chi_nhanh")

    def _select_unit_type(self, unit_id: str) -> None:
        self.current_unit_id = unit_id
        for uid, card in self.unit_cards.items():
            card.set_active(uid == unit_id)

        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        self.procedure_items.clear()

        spec = next((s for s in UNIT_TYPE_SPECS if s["id"] == unit_id), UNIT_TYPE_SPECS[0])
        procedures = spec["procedures"]
        self.count_badge.setText(f"{len(procedures)} thủ tục khả dụng")

        self.selected_procedure = procedures[0] if procedures else None
        self._update_selected_summary()

        for opt in procedures:
            item_widget = DependentProcedureItem(opt)
            item_widget.set_selected(self.selected_procedure == opt)
            item_widget.selected.connect(self._on_procedure_selected)
            item_widget.activated.connect(self._on_procedure_activated)
            self.procedure_items.append(item_widget)
            self.list_layout.addWidget(item_widget)

        self.list_layout.addStretch(1)

    def _on_unit_card_clicked(self, unit_id: str) -> None:
        if unit_id != self.current_unit_id:
            self._select_unit_type(unit_id)

    def _on_procedure_selected(self, option_id: str) -> None:
        for item in self.procedure_items:
            is_match = item.option.id == option_id
            item.set_selected(is_match)
            if is_match:
                self.selected_procedure = item.option
        self._update_selected_summary()

    def _on_procedure_activated(self, option_id: str) -> None:
        self._on_procedure_selected(option_id)
        self._on_create_clicked()

    def _update_selected_summary(self) -> None:
        if self.selected_procedure:
            self.selected_summary_label.setText(f"Hồ sơ đang chọn: <b>{self.selected_procedure.title}</b>")
            self.create_button.setEnabled(True)
        else:
            self.selected_summary_label.setText("Vui lòng chọn một thủ tục")
            self.create_button.setEnabled(False)

    def _on_create_clicked(self) -> None:
        if self.selected_procedure is None:
            return
        self.procedure_chosen.emit(
            self.selected_procedure.unit_type_id,
            self.selected_procedure.action_id,
            self.selected_procedure.title,
            self.selected_procedure.is_ready,
        )
        self.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        if self.parent() is not None:
            pos_in_box = self.modal_box.mapFromParent(event.pos())
            if not self.modal_box.rect().contains(pos_in_box):
                self.reject()
                return
        super().mousePressEvent(event)

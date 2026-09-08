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
class TaxStatusOption:
    id: str
    title: str
    description: str
    badge: str
    icon: str
    is_ready: bool = False


DISSOLUTION_COMPANY_TYPES = [
    {
        "id": "tnhh_1tv",
        "title": "Công ty TNHH một thành viên",
        "subtitle": "1 chủ sở hữu",
        "icon": "🏢",
        "name": "Công ty TNHH một thành viên",
    },
    {
        "id": "tnhh_2tv",
        "title": "Công ty TNHH 2TV trở lên",
        "subtitle": "Từ 2 đến 50 thành viên",
        "icon": "👥",
        "name": "Công ty TNHH hai thành viên trở lên",
    },
    {
        "id": "co_phan",
        "title": "Công ty cổ phần",
        "subtitle": "Từ 3 cổ đông trở lên",
        "icon": "🏛️",
        "name": "Công ty cổ phần",
    },
]

TAX_STATUS_OPTIONS = [
    TaxStatusOption(
        id="locked_mst",
        title="Trường hợp bị khóa Mã số thuế",
        description="Doanh nghiệp bị cơ quan thuế đóng/khóa MST do vi phạm hoặc không hoạt động tại địa chỉ đăng ký; cần thực hiện thủ tục xử lý thuế trước khi đóng mã số thuế.",
        badge="Đang phát triển",
        icon="⚠️",
        is_ready=False,
    ),
    TaxStatusOption(
        id="active_mst",
        title="Trường hợp không bị khóa Mã số thuế",
        description="Mã số thuế đang hoạt động bình thường; tiến hành thủ tục đóng mã số thuế tại cơ quan thuế và nộp hồ sơ giải thể tại Sở KH&ĐT.",
        badge="Đang phát triển",
        icon="✅",
        is_ready=False,
    ),
]


class DissolutionCompanyCard(QFrame):
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
        self.title_label.setWordWrap(True)

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


class TaxStatusItem(QFrame):
    selected = Signal(str)
    activated = Signal(str)

    def __init__(self, option: TaxStatusOption, parent: QWidget | None = None) -> None:
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


class DissolutionModal(QDialog):
    """
    Modal for selecting business dissolution by company type and tax status.
    """

    dissolution_chosen = Signal(str, str, str, bool)  # company_type_id, tax_status_id, full_title, is_ready

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("DissolutionModal")
        self.setModal(True)

        self.current_type_id = "tnhh_1tv"
        self.selected_tax_status: TaxStatusOption | None = None
        self.company_cards: dict[str, DissolutionCompanyCard] = {}
        self.tax_status_items: list[TaxStatusItem] = []

        if parent is not None:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.resize(parent.size())
            self.move(parent.mapToGlobal(QPoint(0, 0)))
        else:
            self.setWindowTitle("Hồ sơ giải thể doanh nghiệp")
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

        self.title_label = QLabel("Bạn muốn tạo hồ sơ giải thể nào?")
        self.title_label.setObjectName("ModalTitle")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.subtitle_label = QLabel("Chọn loại hình doanh nghiệp và tình trạng mã số thuế hiện tại.")
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

        # 3 Company Cards
        cards_row = QHBoxLayout()
        cards_row.setContentsMargins(0, 4, 0, 4)
        cards_row.setSpacing(14)

        for spec in DISSOLUTION_COMPANY_TYPES:
            card = DissolutionCompanyCard(
                type_id=spec["id"],
                title=spec["title"],
                subtitle=spec["subtitle"],
                icon=spec["icon"],
            )
            card.clicked.connect(self._on_type_card_clicked)
            self.company_cards[spec["id"]] = card
            cards_row.addWidget(card, 1)

        box_layout.addLayout(cards_row)

        # Section Header
        sec_header = QHBoxLayout()
        sec_header.setContentsMargins(0, 4, 0, 0)
        sec_title = QLabel("Tình trạng Mã số thuế (MST)")
        sec_title.setObjectName("DossierSectionTitle")
        sec_header.addWidget(sec_title, 1)

        self.count_badge = QLabel("2 trường hợp xử lý")
        self.count_badge.setObjectName("ItemCountBadge")
        sec_header.addWidget(self.count_badge, 0, Qt.AlignVCenter)
        box_layout.addLayout(sec_header)

        # Scroll Area for Tax Status
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

        for opt in TAX_STATUS_OPTIONS:
            item_widget = TaxStatusItem(opt)
            item_widget.selected.connect(self._on_tax_status_selected)
            item_widget.activated.connect(self._on_tax_status_activated)
            self.tax_status_items.append(item_widget)
            self.list_layout.addWidget(item_widget)

        self.list_layout.addStretch(1)
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

        self._select_company_type("tnhh_1tv")
        if self.tax_status_items:
            self._on_tax_status_selected(self.tax_status_items[0].option.id)

    def _select_company_type(self, type_id: str) -> None:
        self.current_type_id = type_id
        for tid, card in self.company_cards.items():
            card.set_active(tid == type_id)
        self._update_selected_summary()

    def _on_type_card_clicked(self, type_id: str) -> None:
        if type_id != self.current_type_id:
            self._select_company_type(type_id)

    def _on_tax_status_selected(self, status_id: str) -> None:
        for item in self.tax_status_items:
            is_match = item.option.id == status_id
            item.set_selected(is_match)
            if is_match:
                self.selected_tax_status = item.option
        self._update_selected_summary()

    def _on_tax_status_activated(self, status_id: str) -> None:
        self._on_tax_status_selected(status_id)
        self._on_create_clicked()

    def _current_company_name(self) -> str:
        spec = next((s for s in DISSOLUTION_COMPANY_TYPES if s["id"] == self.current_type_id), DISSOLUTION_COMPANY_TYPES[0])
        return spec["name"]

    def _update_selected_summary(self) -> None:
        if self.selected_tax_status:
            comp_name = self._current_company_name()
            self.selected_summary_label.setText(
                f"Hồ sơ đang chọn: <b>Giải thể {comp_name} - {self.selected_tax_status.title}</b>"
            )
            self.create_button.setEnabled(True)
        else:
            self.selected_summary_label.setText("Vui lòng chọn tình trạng thuế")
            self.create_button.setEnabled(False)

    def _on_create_clicked(self) -> None:
        if self.selected_tax_status is None:
            return
        comp_name = self._current_company_name()
        full_title = f"Giải thể {comp_name} ({self.selected_tax_status.title})"
        self.dissolution_chosen.emit(
            self.current_type_id,
            self.selected_tax_status.id,
            full_title,
            self.selected_tax_status.is_ready,
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

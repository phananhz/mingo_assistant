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
class AmendmentOption:
    id: str
    title: str
    description: str
    badge: str
    procedure_name: str
    icon: str
    is_ready: bool = False


AMENDMENT_PROCEDURES: list[AmendmentOption] = [
    AmendmentOption(
        id="amend_address",
        title="Thay đổi địa chỉ trụ sở chính",
        description="Chuyển trụ sở cùng quận/huyện, khác quận/huyện, hoặc khác tỉnh/thành phố trực thuộc Trung ương.",
        badge="Đang phát triển",
        procedure_name="Thay đổi địa chỉ trụ sở chính",
        icon="📍",
        is_ready=False,
    ),
    AmendmentOption(
        id="amend_capital",
        title="Thay đổi vốn điều lệ",
        description="Tăng vốn điều lệ, giảm vốn điều lệ, thay đổi tỷ lệ phần vốn góp giữa các thành viên.",
        badge="Đang phát triển",
        procedure_name="Thay đổi vốn điều lệ",
        icon="💰",
        is_ready=False,
    ),
    AmendmentOption(
        id="amend_legal_rep",
        title="Thay đổi người đại diện theo pháp luật",
        description="Thay đổi người đại diện theo pháp luật, bổ sung hoặc thay đổi chức danh người đại diện.",
        badge="Đang phát triển",
        procedure_name="Thay đổi người đại diện theo pháp luật",
        icon="👤",
        is_ready=False,
    ),
    AmendmentOption(
        id="amend_business_lines",
        title="Bổ sung, thay đổi ngành nghề kinh doanh",
        description="Bổ sung ngành nghề mới, rút bớt ngành nghề, cập nhật mã ngành theo hệ thống VSIC chuẩn.",
        badge="Đang phát triển",
        procedure_name="Bổ sung, thay đổi ngành nghề kinh doanh",
        icon="📋",
        is_ready=False,
    ),
    AmendmentOption(
        id="amend_members",
        title="Thay đổi thành viên góp vốn / Cổ đông",
        description="Chuyển nhượng phần vốn góp, tiếp nhận thành viên mới hoặc cập nhật thông tin thành viên.",
        badge="Đang phát triển",
        procedure_name="Thay đổi thành viên góp vốn",
        icon="👥",
        is_ready=False,
    ),
]


class AmendmentItemWidget(QFrame):
    """Horizontal card in the amendment procedure list."""

    selected = Signal(str)
    activated = Signal(str)

    def __init__(self, option: AmendmentOption, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.option = option
        self.is_selected = False
        self.setObjectName("DossierListItem")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        # Left icon badge
        self.icon_label = QLabel(option.icon)
        self.icon_label.setObjectName("DossierItemIcon")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(42, 42)
        layout.addWidget(self.icon_label)

        # Middle text
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

        # Right indicator
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


class BusinessAmendmentModal(QDialog):
    """
    Modal for selecting a business registration amendment procedure.
    """

    procedure_chosen = Signal(str, str, bool)  # procedure_id, procedure_name, is_ready

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("BusinessAmendmentModal")
        self.setModal(True)

        self.selected_option: AmendmentOption | None = None
        self.procedure_widgets: list[AmendmentItemWidget] = []

        if parent is not None:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.resize(parent.size())
            self.move(parent.mapToGlobal(QPoint(0, 0)))
        else:
            self.setWindowTitle("Đăng ký thay đổi ĐKDN")
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

        self.title_label = QLabel("Bạn muốn thực hiện thủ tục thay đổi nào?")
        self.title_label.setObjectName("ModalTitle")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.subtitle_label = QLabel("Chọn thủ tục thay đổi nội dung đăng ký doanh nghiệp để bắt đầu.")
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

        # Section Header
        sec_header = QHBoxLayout()
        sec_header.setContentsMargins(0, 4, 0, 0)
        sec_title = QLabel("Danh sách thủ tục thay đổi")
        sec_title.setObjectName("DossierSectionTitle")
        sec_header.addWidget(sec_title, 1)

        self.count_badge = QLabel(f"{len(AMENDMENT_PROCEDURES)} thủ tục khả dụng")
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
        self.scroll_area.setMaximumHeight(350)

        self.list_container = QWidget()
        self.list_container.setObjectName("DossierListContainer")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 4, 4, 4)
        self.list_layout.setSpacing(10)

        for option in AMENDMENT_PROCEDURES:
            widget = AmendmentItemWidget(option)
            widget.selected.connect(self._on_procedure_selected)
            widget.activated.connect(self._on_procedure_activated)
            self.procedure_widgets.append(widget)
            self.list_layout.addWidget(widget)

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

        # Default selection: first procedure
        if self.procedure_widgets:
            self._on_procedure_selected(self.procedure_widgets[0].option.id)

    def _on_procedure_selected(self, option_id: str) -> None:
        for w in self.procedure_widgets:
            is_match = w.option.id == option_id
            w.set_selected(is_match)
            if is_match:
                self.selected_option = w.option
        if self.selected_option:
            self.selected_summary_label.setText(f"Hồ sơ đang chọn: <b>{self.selected_option.title}</b>")
            self.create_button.setEnabled(True)
        else:
            self.selected_summary_label.setText("Vui lòng chọn một thủ tục")
            self.create_button.setEnabled(False)

    def _on_procedure_activated(self, option_id: str) -> None:
        self._on_procedure_selected(option_id)
        self._on_create_clicked()

    def _on_create_clicked(self) -> None:
        if self.selected_option is None:
            return
        self.procedure_chosen.emit(
            self.selected_option.id,
            self.selected_option.procedure_name,
            self.selected_option.is_ready,
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

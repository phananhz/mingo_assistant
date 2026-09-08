from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from mingo_assistant.app.paths import get_app_paths, load_settings, save_settings


class LiquidGlassModalBox(QFrame):
    """
    Frosted glass container frame for modal dialogs that renders a 3D Liquid Glass
    wallpaper background with smooth aspect-ratio scaling, anti-aliased rounded
    clipping, and adjustable live opacity.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        initial_opacity: float = 0.75,
        is_liquid_glass: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("BusinessCreationModalBox")
        self._is_liquid_glass = is_liquid_glass
        self.setAttribute(Qt.WA_StyledBackground, not is_liquid_glass)
        self._bg_opacity = max(0.0, min(1.0, float(initial_opacity))) if is_liquid_glass else 0.0
        self._pixmap: QPixmap | None = None
        if is_liquid_glass:
            self._load_wallpaper()

    def _load_wallpaper(self) -> None:
        candidate_paths: list[Path] = [
            Path("assets/branding/liquid_glass_modal_bg.jpg"),
            Path("1788854948446_6680548491042055114_6680548491042055114_b3c20f94c82698a0b47b22ff7a8214b4.jpg"),
        ]
        try:
            bundle = get_app_paths().bundle_root
            candidate_paths.insert(0, bundle / "assets" / "branding" / "liquid_glass_modal_bg.jpg")
            candidate_paths.insert(1, bundle / "1788854948446_6680548491042055114_6680548491042055114_b3c20f94c82698a0b47b22ff7a8214b4.jpg")
        except Exception:
            pass

        for p in candidate_paths:
            if p.exists():
                pix = QPixmap(str(p))
                if not pix.isNull():
                    self._pixmap = pix
                    break

    @property
    def bg_opacity(self) -> float:
        return self._bg_opacity

    def set_bg_opacity(self, opacity: float) -> None:
        new_val = max(0.0, min(1.0, float(opacity)))
        if abs(new_val - self._bg_opacity) > 1e-4:
            self._bg_opacity = new_val
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        rect = QRectF(self.rect())
        radius = 20.0
        clip_path = QPainterPath()
        clip_path.addRoundedRect(rect, radius, radius)
        painter.setClipPath(clip_path)

        # 1. Base solid clean background
        painter.fillRect(rect, QColor(255, 255, 255, 255))

        # 2. Draw 3D Liquid Glass Wallpaper (ONLY in liquid_glass mode)
        if self._is_liquid_glass and self._pixmap is not None and not self._pixmap.isNull() and self._bg_opacity > 0.001:
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.setOpacity(self._bg_opacity)
            painter.drawPixmap(x, y, scaled)

        # 3. Soft luminous outer/inner border stroke
        painter.setOpacity(1.0)
        border_col = QColor(255, 255, 255, 220) if self._is_liquid_glass else QColor(226, 232, 240, 255)
        border_pen = QPen(border_col, 1.5)
        painter.strokePath(clip_path, border_pen)
        painter.end()

        super().paintEvent(event)


@dataclass(frozen=True)
class DossierOption:
    id: str
    title: str
    description: str
    badge: str
    case_type: str
    is_ready: bool
    icon: str


COMPANY_TYPE_SPECS = [
    {
        "id": "tnhh_1tv",
        "title": "Công ty TNHH\nmột thành viên",
        "subtitle": "1 chủ sở hữu",
        "icon": "🏢",
        "dossiers": [
            DossierOption(
                id="dossier_tnhh_1tv",
                title="Thành lập công ty TNHH một thành viên",
                description="Tạo trọn bộ hồ sơ: Giấy đề nghị đăng ký, Điều lệ công ty, Danh sách chủ sở hữu hưởng lợi và Giấy ủy quyền.",
                badge="Sẵn sàng sử dụng",
                case_type="TNHH một thành viên",
                is_ready=True,
                icon="📄",
            )
        ],
    },
    {
        "id": "tnhh_2tv",
        "title": "Công ty TNHH\nhai thành viên trở lên",
        "subtitle": "Từ 2 đến 50 thành viên",
        "icon": "👥",
        "dossiers": [
            DossierOption(
                id="dossier_tnhh_2tv_personal",
                title="Thành lập công ty TNHH hai thành viên trở lên (Thành viên là Cá nhân)",
                description="Tạo trọn bộ hồ sơ thành lập công ty TNHH 2TV với các thành viên góp vốn là cá nhân.",
                badge="Đang phát triển",
                case_type="TNHH hai thành viên (Cá nhân)",
                is_ready=False,
                icon="👥",
            ),
            DossierOption(
                id="dossier_tnhh_2tv_org",
                title="Thành lập công ty TNHH hai thành viên trở lên (Thành viên là Tổ chức)",
                description="Tạo trọn bộ hồ sơ thành lập công ty TNHH 2TV với các thành viên góp vốn là tổ chức/doanh nghiệp.",
                badge="Đang phát triển",
                case_type="TNHH hai thành viên (Tổ chức)",
                is_ready=False,
                icon="🏢",
            ),
        ],
    },
    {
        "id": "co_phan",
        "title": "Công ty cổ phần",
        "subtitle": "Từ 3 cổ đông trở lên",
        "icon": "🏛️",
        "dossiers": [
            DossierOption(
                id="dossier_co_phan",
                title="Thành lập công ty cổ phần",
                description="Tạo trọn bộ hồ sơ: Giấy đề nghị đăng ký, Điều lệ công ty, Danh sách cổ đông sáng lập và Giấy ủy quyền.",
                badge="Đang phát triển",
                case_type="Công ty cổ phần",
                is_ready=False,
                icon="🏛️",
            )
        ],
    },
]


class CompanyTypeCard(QFrame):
    """Card on the top row representing one of the 3 company types."""

    clicked = Signal(str)

    def __init__(self, type_id: str, title: str, subtitle: str, icon: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.type_id = type_id
        self.setObjectName("CompanyTypeCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(126)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # Top row: icon on left, active check badge on right
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

        # Bottom: Title & Subtitle
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
        self.is_active = False
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


class DossierListItem(QFrame):
    """Horizontal card in the dossier list with selection effect."""

    selected = Signal(str)
    activated = Signal(str)

    def __init__(self, option: DossierOption, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.option = option
        self.is_selected = False
        self.setObjectName("DossierListItem")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        # Left: Icon badge
        self.icon_label = QLabel(option.icon)
        self.icon_label.setObjectName("DossierItemIcon")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(42, 42)
        layout.addWidget(self.icon_label)

        # Middle: Title + Badge, and description
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

        # Right: Selection Indicator
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


class BusinessCreationModal(QDialog):
    """
    Modal dialog allowing the user to:
    1. Select a business type among 3 cards.
    2. View and select an associated dossier.
    3. Click 'Tạo hồ sơ' to initiate creation or view coming-soon notice.
    """

    dossier_chosen = Signal(str, bool)  # case_type, is_ready

    def __init__(self, parent: QWidget | None = None, layout_mode: str | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("BusinessCreationModal")
        self.setModal(True)

        self.current_type_id = "tnhh_1tv"
        self.selected_dossier: DossierOption | None = None
        self.company_cards: dict[str, CompanyTypeCard] = {}
        self.dossier_items: list[DossierListItem] = []

        # If parent provided, size to cover parent window for dark overlay effect
        if parent is not None:
            self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.resize(parent.size())
            self.move(parent.mapToGlobal(QPoint(0, 0)))
        else:
            self.setWindowTitle("Bạn muốn tạo hồ sơ thành lập nào?")
            self.resize(1020, 700)

        # Root overlay layout
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.overlay_container = QFrame(self)
        self.overlay_container.setObjectName("ModalOverlayContainer")
        container_layout = QVBoxLayout(self.overlay_container)
        container_layout.setContentsMargins(24, 24, 24, 24)
        container_layout.setAlignment(Qt.AlignCenter)

        # Determine layout mode: only 'liquid_glass' shows 3D wallpaper and opacity slider
        self._paths = get_app_paths()
        saved_settings = load_settings(self._paths)
        if layout_mode is None:
            if parent is not None and hasattr(parent, "current_layout"):
                layout_mode = getattr(parent, "current_layout")
            elif parent is not None and hasattr(parent, "_layout_mode"):
                layout_mode = getattr(parent, "_layout_mode")
            else:
                layout_mode = saved_settings.get("layout", "classic")
        self._layout_mode = layout_mode
        self._is_liquid_glass = (self._layout_mode == "liquid_glass")

        # Load user opacity preference (default 75% matching Image 3)
        initial_opacity_pct = 75
        try:
            initial_opacity_pct = int(saved_settings.get("modal_bg_opacity", "75"))
            initial_opacity_pct = max(0, min(100, initial_opacity_pct))
        except (ValueError, TypeError):
            initial_opacity_pct = 75

        # Timer for debounced setting persistence
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(300)
        self._save_timer.timeout.connect(self._persist_opacity_setting)

        # White / Frosted Glass Popup Box (width 980px)
        self.modal_box = LiquidGlassModalBox(
            self.overlay_container,
            initial_opacity=initial_opacity_pct / 100.0,
            is_liquid_glass=self._is_liquid_glass,
        )
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

        # Top Bar: Header centered, [X] button at top right
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.addSpacing(36)  # Balance close button width on the left

        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        header_layout.setAlignment(Qt.AlignCenter)

        self.title_label = QLabel("Bạn muốn tạo hồ sơ thành lập nào?")
        self.title_label.setObjectName("ModalTitle")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.subtitle_label = QLabel("Chọn loại hình doanh nghiệp để xem các hồ sơ phù hợp.")
        self.subtitle_label.setObjectName("ModalSubtitle")
        self.subtitle_label.setAlignment(Qt.AlignCenter)

        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.subtitle_label)
        top_bar.addLayout(header_layout, 1)

        # [X] Close button
        self.close_button = QPushButton("✕")
        self.close_button.setObjectName("ModalCloseButton")
        self.close_button.setFixedSize(36, 36)
        self.close_button.setCursor(Qt.PointingHandCursor)
        self.close_button.setToolTip("Đóng (ESC)")
        self.close_button.clicked.connect(self.reject)
        top_bar.addWidget(self.close_button, 0, Qt.AlignTop)

        box_layout.addLayout(top_bar)

        # Selection row: Exactly 3 cards
        cards_row = QHBoxLayout()
        cards_row.setContentsMargins(0, 4, 0, 4)
        cards_row.setSpacing(14)

        for spec in COMPANY_TYPE_SPECS:
            card = CompanyTypeCard(
                type_id=spec["id"],
                title=spec["title"],
                subtitle=spec["subtitle"],
                icon=spec["icon"],
            )
            card.clicked.connect(self._on_type_card_clicked)
            self.company_cards[spec["id"]] = card
            cards_row.addWidget(card, 1)

        box_layout.addLayout(cards_row)

        # Dossier Section Title
        section_header = QHBoxLayout()
        section_header.setContentsMargins(0, 6, 0, 0)
        section_header_text = QVBoxLayout()
        section_header_text.setSpacing(2)

        dossier_sec_title = QLabel("Chọn hồ sơ")
        dossier_sec_title.setObjectName("DossierSectionTitle")
        dossier_sec_sub = QLabel("Nhấp vào một hồ sơ để chọn, sau đó bấm nút \"Tạo hồ sơ\" bên dưới.")
        dossier_sec_sub.setObjectName("DossierSectionSubtitle")

        section_header_text.addWidget(dossier_sec_title)
        section_header_text.addWidget(dossier_sec_sub)
        section_header.addLayout(section_header_text, 1)

        self.item_count_label = QLabel("1 hồ sơ khả dụng")
        self.item_count_label.setObjectName("ItemCountBadge")
        section_header.addWidget(self.item_count_label, 0, Qt.AlignVCenter)
        box_layout.addLayout(section_header)

        # Scroll area for dossier list
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("DossierScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.viewport().setAutoFillBackground(False)
        self.scroll_area.setMaximumHeight(250)

        self.list_container = QWidget()
        self.list_container.setObjectName("DossierListContainer")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 4, 4, 4)
        self.list_layout.setSpacing(10)
        self.scroll_area.setWidget(self.list_container)

        box_layout.addWidget(self.scroll_area, 1)

        # Footer Bar: Left status label, middle opacity slider, right "Đóng" and "Tạo hồ sơ"
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 8, 0, 0)
        footer_layout.setSpacing(10)

        self.status_icon = QLabel("●")
        self.status_icon.setObjectName("ModalStatusDot")
        footer_layout.addWidget(self.status_icon)

        self.selected_summary_label = QLabel("Hồ sơ đang chọn: Chưa chọn")
        self.selected_summary_label.setObjectName("ModalSelectedSummary")
        footer_layout.addWidget(self.selected_summary_label, 1)

        # Opacity slider capsule ("Thanh điều chỉnh độ mờ")
        self.opacity_box = QFrame()
        self.opacity_box.setObjectName("ModalOpacityBox")
        opacity_layout = QHBoxLayout(self.opacity_box)
        opacity_layout.setContentsMargins(10, 4, 10, 4)
        opacity_layout.setSpacing(8)

        opacity_icon = QLabel("🎨")
        opacity_icon.setObjectName("ModalOpacityIcon")

        opacity_title = QLabel("Độ mờ:")
        opacity_title.setObjectName("ModalOpacityLabel")

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setObjectName("ModalOpacitySlider")
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(initial_opacity_pct)
        self.opacity_slider.setFixedWidth(110)
        self.opacity_slider.setCursor(Qt.PointingHandCursor)
        self.opacity_slider.setToolTip("Điều chỉnh độ mờ hình nền 3D (0% - 100%)")
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.opacity_slider.sliderReleased.connect(self._persist_opacity_setting)

        self.opacity_val_label = QLabel(f"{initial_opacity_pct}%")
        self.opacity_val_label.setObjectName("ModalOpacityValue")

        opacity_layout.addWidget(opacity_icon)
        opacity_layout.addWidget(opacity_title)
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_val_label)

        footer_layout.addWidget(self.opacity_box)
        self.opacity_box.setVisible(self._is_liquid_glass)

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

        # Default active type: TNHH 1TV
        self._select_company_type("tnhh_1tv")

    def _select_company_type(self, type_id: str) -> None:
        self.current_type_id = type_id

        # Update card visuals
        for cid, card in self.company_cards.items():
            card.set_active(cid == type_id)

        # Clear existing items
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        self.dossier_items.clear()

        # Find spec
        spec = next((s for s in COMPANY_TYPE_SPECS if s["id"] == type_id), COMPANY_TYPE_SPECS[0])
        dossiers = spec["dossiers"]
        self.item_count_label.setText(f"{len(dossiers)} hồ sơ khả dụng")

        # Auto-select first dossier in this group
        self.selected_dossier = dossiers[0] if dossiers else None
        self._update_selected_summary()

        # Populate list items
        for option in dossiers:
            item_widget = DossierListItem(option)
            item_widget.set_selected(self.selected_dossier == option)
            item_widget.selected.connect(self._on_dossier_selected)
            item_widget.activated.connect(self._on_dossier_activated)
            self.dossier_items.append(item_widget)
            self.list_layout.addWidget(item_widget)

        self.list_layout.addStretch(1)

    def _on_type_card_clicked(self, type_id: str) -> None:
        if type_id != self.current_type_id:
            self._select_company_type(type_id)

    def _on_dossier_selected(self, dossier_id: str) -> None:
        for item in self.dossier_items:
            is_match = item.option.id == dossier_id
            item.set_selected(is_match)
            if is_match:
                self.selected_dossier = item.option
        self._update_selected_summary()

    def _on_dossier_activated(self, dossier_id: str) -> None:
        self._on_dossier_selected(dossier_id)
        self._on_create_clicked()

    def _update_selected_summary(self) -> None:
        if self.selected_dossier:
            self.selected_summary_label.setText(f"Hồ sơ đang chọn: <b>{self.selected_dossier.title}</b>")
            self.create_button.setEnabled(True)
        else:
            self.selected_summary_label.setText("Vui lòng chọn một hồ sơ")
            self.create_button.setEnabled(False)

    def _on_create_clicked(self) -> None:
        if self.selected_dossier is None:
            return
        self.dossier_chosen.emit(self.selected_dossier.case_type, self.selected_dossier.is_ready)
        self.accept()

    def _on_opacity_changed(self, value: int) -> None:
        self.opacity_val_label.setText(f"{value}%")
        self.modal_box.set_bg_opacity(value / 100.0)
        self._save_timer.start()

    def _persist_opacity_setting(self) -> None:
        try:
            val = self.opacity_slider.value()
            save_settings(self._paths, {"modal_bg_opacity": str(val)})
        except Exception:
            pass

    def accept(self) -> None:
        self._persist_opacity_setting()
        super().accept()

    def reject(self) -> None:
        self._persist_opacity_setting()
        super().reject()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        # If user clicks outside the modal_box (on the dark overlay), dismiss modal
        if self.parent() is not None:
            pos_in_box = self.modal_box.mapFromParent(event.pos())
            if not self.modal_box.rect().contains(pos_in_box):
                self.reject()
                return
        super().mousePressEvent(event)

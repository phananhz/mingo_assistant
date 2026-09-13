from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QRectF, Qt, QUrl
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHeaderView,
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
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QFontMetrics,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

from mingo_assistant import __version__
from mingo_assistant.app.paths import AppPaths, get_app_paths, load_settings, save_settings
from mingo_assistant.application.business_registration import BusinessRegistrationServices
from mingo_assistant.application.cases import CaseUseCases
from mingo_assistant.application.profiles import AuthorizedPersonUseCases
from mingo_assistant.models.case import CaseSummary
from mingo_assistant.repositories.authorized_person_repository import AuthorizedPersonProfileRepository
from mingo_assistant.repositories.case_repository import CaseRepository
from mingo_assistant.services.business_lines.industry_lookup import IndustryCatalog, IndustryRow
from mingo_assistant.ui.dialogs.settings_dialog import SettingsDialog, SettingsView
from mingo_assistant.ui.styles import (
    EFFECT_SHADOW_OPTIONS,
    LAYOUT_OPTIONS,
    THEME_OPTIONS,
    apply_app_palette,
    resolved_appearance_mode,
    stylesheet_for_theme,
)
from mingo_assistant.ui.views.business_registration_documents import BusinessRegistrationDocumentsView
from mingo_assistant.ui.views.business_registration_workspace import BusinessRegistrationWorkspace
from mingo_assistant.ui.views.location_business_workspace import LOCATION_CASE_TYPE, LocationBusinessWorkspace
from mingo_assistant.ui.widgets.combo_box import NoWheelComboBox


NAV_ITEMS = [
    ("business_registration", "1. Thủ tục thành lập doanh nghiệp"),
    ("business_amendment", "2. Thủ tục thay đổi ĐKDN"),
    ("dissolution", "3. Thủ tục giải thể DN"),
    ("dependent_units", "4. Thủ tục của đơn vị phụ thuộc"),
    ("industry_lookup", "Tra cứu ngành nghề kinh doanh"),
    ("templates", "Quản lý mẫu Word"),
    ("people", "Kho cá nhân/tổ chức"),
    ("trash", "Thùng rác"),
]


class TechImageSidebar(QFrame):
    """
    Sidebar frame that renders custom wallpaper
    (assets/branding/sidebar_liquid_glass_bg.jpg or sidebar_tech_bg.jpg)
    with rounded clipping, smooth transformation, and delicate luminous border.
    In 'liquid_glass' layout mode, it uses the purple abstract wallpaper
    (image/1788859280719_...jpg).
    """

    def __init__(self, parent: QWidget | None = None, layout_mode: str = "liquid_glass") -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self._layout_mode = layout_mode
        self._liquid_glass_pixmap: QPixmap | None = None
        self._cyber_tech_pixmap: QPixmap | None = None
        self._pixmap: QPixmap | None = None
        self._load_backgrounds()
        self._update_styled_bg()

    def set_layout_mode(self, layout: str) -> None:
        self._layout_mode = layout
        self._update_styled_bg()
        self.update()

    def _update_styled_bg(self) -> None:
        self.setAttribute(Qt.WA_StyledBackground, self._layout_mode != "liquid_glass")

    def _load_backgrounds(self) -> None:
        bundle = None
        try:
            bundle = get_app_paths().bundle_root
        except Exception:
            pass

        # 1. Liquid Glass abstract wallpaper (blue sphere glass wallpaper)
        lg_candidates: list[Path] = [
            Path("assets/branding/sidebar_liquid_glass_bg.jpg"),
            Path("image/1788861355930_6680548491042055114_6680548491042055114_58dde08bd7452e42ebcb60615f75606d.jpg"),
            Path("image/1788859280719_6680548491042055114_6680548491042055114_e28013c5b36f3e0aebc9136086b0a038.jpg"),
        ]
        if bundle:
            lg_candidates.insert(0, bundle / "assets" / "branding" / "sidebar_liquid_glass_bg.jpg")
            lg_candidates.insert(1, bundle / "image" / "1788861355930_6680548491042055114_6680548491042055114_58dde08bd7452e42ebcb60615f75606d.jpg")
            lg_candidates.insert(2, bundle / "image" / "1788859280719_6680548491042055114_6680548491042055114_e28013c5b36f3e0aebc9136086b0a038.jpg")

        for p in lg_candidates:
            if p.exists():
                pix = QPixmap(str(p))
                if not pix.isNull():
                    self._liquid_glass_pixmap = pix
                    break

        # 2. Cyber tech circuit wallpaper
        tech_candidates: list[Path] = [
            Path("assets/branding/sidebar_tech_bg.jpg"),
            Path("1788856436915_6680548491042055114_6680548491042055114_90b07d86dc6f853f7a7fb6c9dae168b0.jpg"),
        ]
        if bundle:
            tech_candidates.insert(0, bundle / "assets" / "branding" / "sidebar_tech_bg.jpg")
            tech_candidates.insert(1, bundle / "1788856436915_6680548491042055114_6680548491042055114_90b07d86dc6f853f7a7fb6c9dae168b0.jpg")

        for p in tech_candidates:
            if p.exists():
                pix = QPixmap(str(p))
                if not pix.isNull():
                    self._cyber_tech_pixmap = pix
                    break

        # Primary default pixmap reference (ensures self._pixmap is never null)
        self._pixmap = self._liquid_glass_pixmap or self._cyber_tech_pixmap or QPixmap()

    def paintEvent(self, event) -> None:
        if self._layout_mode != "liquid_glass":
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        rect = QRectF(self.rect())
        radius = 20.0
        clip_path = QPainterPath()
        clip_path.addRoundedRect(rect, radius, radius)
        painter.setClipPath(clip_path)

        if self._layout_mode == "liquid_glass":
            pix = self._liquid_glass_pixmap or self._pixmap
            base_col = QColor(36, 30, 85)
            border_pen = QPen(QColor(255, 255, 255, 75), 1.2)
        else:
            pix = self._cyber_tech_pixmap or self._pixmap
            base_col = QColor(26, 20, 52)
            border_pen = QPen(QColor(255, 255, 255, 55), 1.0)

        # 1. Base color fill
        painter.fillRect(rect, base_col)

        # 2. Draw scaled background image
        if pix is not None and not pix.isNull():
            if self._layout_mode == "liquid_glass":
                # Position the crystal sphere elegantly in the lower-middle region (near Thung rac)
                # while preserving a clean, deep twilight gradient for the top navigation items.
                scaled_h = int(self.height() * 0.88)
                scaled = pix.scaledToHeight(scaled_h, Qt.SmoothTransformation)
                x = (self.width() - scaled.width()) // 2 - int(scaled.width() * 0.08)
                y = int(self.height() * 0.32)
            else:
                scaled = pix.scaled(
                    self.size(),
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation,
                )
                x = (self.width() - scaled.width()) // 2
                y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)

        # 3. Soft luminous outer edge border
        painter.strokePath(clip_path, border_pen)
        painter.end()

        super().paintEvent(event)


class MainWindow(QMainWindow):
    SIDEBAR_WIDTH = 220
    PAGE_HORIZONTAL_MARGIN = 48
    CARD_WIDTH = 220
    CARD_GAP = 18

    def __init__(
        self,
        app_paths: AppPaths | None = None,
        case_repository: CaseRepository | None = None,
        case_use_cases: CaseUseCases | None = None,
        authorized_person_repository: AuthorizedPersonProfileRepository | None = None,
        authorized_person_use_cases: AuthorizedPersonUseCases | None = None,
        registration_services: BusinessRegistrationServices | None = None,
        industry_catalog: IndustryCatalog | None = None,
    ) -> None:
        super().__init__()
        self.app_paths = app_paths or get_app_paths()
        self.setWindowTitle(f"Min Assistant v{__version__}")
        self._app_icon_path = self.app_paths.bundle_root / "assets" / "branding" / "min-assistant.ico"
        self._brand_mark_path = self.app_paths.bundle_root / "assets" / "branding" / "min-assistant-mark.png"
        if self._app_icon_path.is_file():
            self.setWindowIcon(QIcon(str(self._app_icon_path)))
        self.resize(1280, 760)
        self.setMinimumSize(760, 520)

        self.case_repository = case_repository or CaseRepository(self.app_paths.cases_file)
        self.case_use_cases = case_use_cases or CaseUseCases(self.case_repository)
        self.authorized_person_repository = authorized_person_repository or AuthorizedPersonProfileRepository(
            self.app_paths.authorized_person_file,
            self.app_paths.authorized_person_defaults_file,
        )
        self.authorized_person_use_cases = authorized_person_use_cases or AuthorizedPersonUseCases(
            self.authorized_person_repository
        )
        self.registration_services = registration_services or BusinessRegistrationServices.from_project(
            self.app_paths.bundle_root
        )
        self.industry_catalog = industry_catalog or self.registration_services.industry_catalog
        self.cases: list[CaseSummary] = self.case_use_cases.list_active()
        self.nav_buttons: dict[str, QPushButton] = {}
        self.top_nav_buttons: dict[str, QPushButton] = {}
        self.slim_nav_buttons: dict[str, QPushButton] = {}
        self._selected_case_for_detail: CaseSummary | None = None
        self._current_nav_key = "business_registration"
        self.stack = QStackedWidget()
        self.current_workspace: BusinessRegistrationWorkspace | None = None
        self.current_documents_view: BusinessRegistrationDocumentsView | None = None
        self.authorized_person_profiles: list[dict[str, str]] = []
        self.authorized_person_selected_id = ""
        self.authorized_person_fields: dict[str, QLineEdit | QTextEdit] = {}
        self.authorized_person_cards_layout: QGridLayout | None = None
        self.authorized_person_save_button: QPushButton | None = None
        self._authorized_recovery_warned = False
        self._last_applied_theme: tuple | None = None
        self.macos_traffic_lights: QFrame | None = None
        self.settings_page: QWidget | None = None
        self.settings_view: SettingsView | None = None
        self._previous_widget_before_settings: QWidget | None = None
        self._settings_snapshot: dict | None = None

        init_settings = load_settings(self.app_paths)
        self.current_layout: str = init_settings.get("layout", "default")

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
        self.dependent_cases_scroll: QScrollArea | None = None
        self.dependent_cases_container: QWidget | None = None
        self.dependent_cases_layout: QGridLayout | None = None
        self.current_dependent_card_columns = 0
        self.dependent_cases_count_label: QLabel | None = None
        self.trash_container = QWidget()
        self.trash_layout = QVBoxLayout(self.trash_container)
        self.industry_search_input = QLineEdit()
        self.industry_table = QTableWidget()
        self.industry_status_label = QLabel()
        self.industry_detail = QTextEdit()

        self.sidebar = self._build_sidebar()
        self.slim_sidebar = self._build_slim_sidebar()
        self.global_topbar = self._build_global_topbar()
        self.top_nav_bar = self._build_top_nav_bar()
        self.content_stack_wrapper = self._build_content_stack()
        # Keep sidebar state tied to the page actually shown, not to whichever
        # workflow happened to hide it most recently.
        self.stack.currentChanged.connect(self._sync_navigation_visibility)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self.global_topbar)
        root_layout.addWidget(self.top_nav_bar)

        self.body_container = QWidget()
        self.body_layout = QHBoxLayout(self.body_container)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)
        self.body_layout.addWidget(self.sidebar)
        self.body_layout.addWidget(self.slim_sidebar)
        self.body_layout.addWidget(self.content_stack_wrapper, 1)

        root_layout.addWidget(self.body_container, 1)
        self.setCentralWidget(root)

        self._apply_layout_structure(self.current_layout)
        self._select_nav("business_registration")
        self._refresh_cases()

        try:
            q_app = QApplication.instance()
            if q_app is not None and hasattr(q_app.styleHints(), "colorSchemeChanged"):
                q_app.styleHints().colorSchemeChanged.connect(self._on_system_color_scheme_changed)
        except Exception:
            pass

    def _build_global_topbar(self) -> QWidget:
        topbar = QFrame()
        topbar.setObjectName("GlobalTopbar")
        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        logo = QLabel("MIN ASSISTANT")
        logo.setStyleSheet("font-weight: 800; font-size: 13px; letter-spacing: 0.5px;")
        layout.addWidget(logo)

        crumb = QLabel("›  Hồ sơ doanh nghiệp")
        crumb.setStyleSheet("font-size: 12px; color: #94A3B8;")
        layout.addWidget(crumb)

        layout.addStretch(1)

        search_quick = QLineEdit()
        search_quick.setPlaceholderText("Tìm nhanh hồ sơ...")
        search_quick.setFixedWidth(240)
        search_quick.setStyleSheet("padding: 4px 10px; font-size: 12px; border-radius: 6px;")
        search_quick.textChanged.connect(lambda text: self.search_input.setText(text))
        layout.addWidget(search_quick)

        quick_settings = QPushButton("⚙")
        quick_settings.setObjectName("SettingsButton")
        quick_settings.setCursor(Qt.PointingHandCursor)
        quick_settings.setToolTip("Cài đặt ứng dụng")
        quick_settings.clicked.connect(self._open_settings)
        layout.addWidget(quick_settings)

        return topbar

    def _build_top_nav_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("TopNavContainer")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(6)

        brand = QLabel("MIN ASSISTANT")
        brand.setObjectName("TopNavBrand")
        layout.addWidget(brand)
        layout.addSpacing(10)

        nav_labels = {
            "business_registration": "Thành lập DN",
            "business_amendment": "Thay đổi ĐKDN",
            "dependent_units": "Đơn vị trực thuộc",
            "dissolution": "Giải thể DN",
            "industry_lookup": "Tra mã ngành",
            "templates": "Biểu mẫu",
            "people": "Cá nhân/Tổ chức",
            "trash": "Thùng rác",
        }

        for key, label in NAV_ITEMS:
            display_label = nav_labels.get(key, label)
            btn = QPushButton(display_label)
            btn.setObjectName("TopNavButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, item_key=key: self._select_nav(item_key, is_user_action=True))
            self.top_nav_buttons[key] = btn
            layout.addWidget(btn)

        layout.addStretch(1)

        top_create_btn = QPushButton("+ Tạo hồ sơ")
        top_create_btn.setObjectName("PrimaryButton")
        top_create_btn.setCursor(Qt.PointingHandCursor)
        top_create_btn.setToolTip("Tạo hồ sơ thành lập mới")
        top_create_btn.clicked.connect(self._open_business_creation_modal)
        layout.addWidget(top_create_btn)
        layout.addSpacing(4)

        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("SettingsButton")
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.setToolTip("Cài đặt ứng dụng")
        settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(settings_btn)

        return bar

    def _build_slim_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("SlimSidebar")
        sidebar.setFixedWidth(64)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 14, 0, 16)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignHCenter)

        logo = QLabel("M")
        logo.setObjectName("SlimSidebarLogo")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(42, 42)
        layout.addWidget(logo, 0, Qt.AlignHCenter)
        layout.addSpacing(6)

        icons = {
            "business_registration": "🏢",
            "business_amendment": "📝",
            "dependent_units": "🏛️",
            "dissolution": "⚠️",
            "industry_lookup": "🔍",
            "templates": "📄",
            "people": "👥",
            "trash": "🗑",
        }

        for key, label in NAV_ITEMS:
            btn = QPushButton(icons.get(key, "📄"))
            btn.setObjectName("SlimNavButton")
            btn.setToolTip(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(42, 42)
            btn.clicked.connect(lambda checked=False, item_key=key: self._select_nav(item_key, is_user_action=True))
            self.slim_nav_buttons[key] = btn
            layout.addWidget(btn, 0, Qt.AlignHCenter)

        layout.addStretch(1)

        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("SlimNavButton")
        settings_btn.setToolTip("Cài đặt")
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.setFixedSize(42, 42)
        settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(settings_btn, 0, Qt.AlignHCenter)

        return sidebar

    def _build_macos_traffic_lights(self) -> QFrame:
        lights = QFrame()
        lights.setObjectName("MacOSTrafficLights")
        lights_layout = QHBoxLayout(lights)
        lights_layout.setContentsMargins(4, 2, 4, 8)
        lights_layout.setSpacing(8)

        red = QLabel()
        red.setObjectName("MacDotRed")
        red.setToolTip("Đóng")

        yellow = QLabel()
        yellow.setObjectName("MacDotYellow")
        yellow.setToolTip("Thu nhỏ")

        green = QLabel()
        green.setObjectName("MacDotGreen")
        green.setToolTip("Phóng to")

        lights_layout.addWidget(red)
        lights_layout.addWidget(yellow)
        lights_layout.addWidget(green)
        lights_layout.addStretch(1)
        lights.setVisible(False)
        return lights

    def _build_sidebar(self) -> QWidget:
        layout_mode = getattr(self, "current_layout", "liquid_glass")
        sidebar = TechImageSidebar(layout_mode=layout_mode)
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(self.SIDEBAR_WIDTH)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 12, 12, 16)
        layout.setSpacing(7)

        self.macos_traffic_lights = self._build_macos_traffic_lights()
        layout.addWidget(self.macos_traffic_lights)

        logo_mark = QLabel()
        logo_mark.setObjectName("SidebarBrandMark")
        if self._brand_mark_path.is_file():
            pixmap = QPixmap(str(self._brand_mark_path))
            logo_mark.setPixmap(pixmap.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_mark.setFixedSize(44, 44)
        logo_mark.setAlignment(Qt.AlignCenter)

        eyebrow = QLabel("MIN ASSISTANT")
        eyebrow.setObjectName("AppEyebrow")
        title = QLabel("Quản lý hồ sơ")
        title.setObjectName("AppTitle")

        brand_text = QVBoxLayout()
        brand_text.setSpacing(2)
        brand_text.addWidget(eyebrow)
        brand_text.addWidget(title)
        brand_row = QHBoxLayout()
        brand_row.setSpacing(8)
        brand_row.addWidget(logo_mark)
        brand_row.addLayout(brand_text, 1)
        layout.addLayout(brand_row)
        layout.addSpacing(18)

        for key, label in NAV_ITEMS:
            button_text = label
            if key == "dependent_units":
                button_text = "4. Thủ tục của\nđơn vị phụ thuộc"
            button = QPushButton(button_text)
            button.setToolTip(label)
            if key == "dependent_units":
                button.setMinimumHeight(58)
            button.setObjectName("NavButton")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, item_key=key: self._select_nav(item_key, is_user_action=True))
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
        self.business_amendment_page = self._build_category_hub_page(
            nav_key="business_amendment",
            title_text="Đăng ký thay đổi ĐKDN",
            desc_text="Quản lý và soạn thảo các hồ sơ thay đổi nội dung đăng ký doanh nghiệp (địa chỉ, vốn điều lệ, người đại diện, ngành nghề...).",
            on_create_clicked=self._open_business_amendment_modal,
        )
        self.dependent_units_page = self._build_category_hub_page(
            nav_key="dependent_units",
            title_text="Thủ tục của đơn vị phụ thuộc",
            desc_text="Quản lý và soạn thảo hồ sơ thành lập, thay đổi, chấm dứt hoạt động cho chi nhánh, văn phòng đại diện và địa điểm kinh doanh.",
            on_create_clicked=self._open_dependent_unit_modal,
        )
        self.dissolution_page = self._build_category_hub_page(
            nav_key="dissolution",
            title_text="Thủ tục giải thể DN",
            desc_text="Soạn thảo hồ sơ giải thể doanh nghiệp theo từng loại hình công ty và xử lý tình trạng mã số thuế tương ứng.",
            on_create_clicked=self._open_dissolution_modal,
        )
        self.authorized_person_page = self._build_authorized_person_page()
        self.industry_lookup_page = self._build_industry_lookup_page()
        self.trash_page = self._build_trash_page()
        self.coming_soon_page = self._build_coming_soon_page()
        self.settings_page = self._build_settings_page()

        self.stack.addWidget(self.business_page)
        self.stack.addWidget(self.business_amendment_page)
        self.stack.addWidget(self.dependent_units_page)
        self.stack.addWidget(self.dissolution_page)
        self.stack.addWidget(self.authorized_person_page)
        self.stack.addWidget(self.industry_lookup_page)
        self.stack.addWidget(self.trash_page)
        self.stack.addWidget(self.coming_soon_page)
        self.stack.addWidget(self.settings_page)
        layout.addWidget(self.stack)

        return content

    def _select_nav(self, key: str, is_user_action: bool = False) -> None:
        if (
            hasattr(self, "stack")
            and hasattr(self, "settings_page")
            and self.settings_page is not None
            and self.stack.currentWidget() == self.settings_page
        ):
            if hasattr(self, "_settings_snapshot") and self._settings_snapshot:
                s = self._settings_snapshot
                self._settings_snapshot = None
                self._apply_theme_preview(
                    s["theme"],
                    s["theme_strength"],
                    s["appearance_mode"],
                    s["layout"],
                    s["font_size"],
                    s["border_radius"],
                    s["high_contrast"],
                    s["custom_color"],
                    s["animations_enabled"],
                    s["card_shadow"],
                    s["hover_glow"],
                    s["glassmorphism"],
                )

        self._current_nav_key = key
        for item_key, button in self.nav_buttons.items():
            button.setProperty("active", item_key == key)
            button.style().unpolish(button)
            button.style().polish(button)
        if hasattr(self, "top_nav_buttons"):
            for item_key, button in self.top_nav_buttons.items():
                button.setProperty("active", item_key == key)
                button.style().unpolish(button)
                button.style().polish(button)
        if hasattr(self, "slim_nav_buttons"):
            for item_key, button in self.slim_nav_buttons.items():
                button.setProperty("active", item_key == key)
                button.style().unpolish(button)
                button.style().polish(button)

        if key == "business_registration":
            if is_user_action and self.stack.currentWidget() == self.business_page:
                self._open_business_creation_modal()
            else:
                self.stack.setCurrentWidget(self.business_page)
        elif key == "business_amendment":
            if is_user_action and self.stack.currentWidget() == self.business_amendment_page:
                self._open_business_amendment_modal()
            else:
                self.stack.setCurrentWidget(self.business_amendment_page)
        elif key == "dependent_units":
            if is_user_action and self.stack.currentWidget() == self.dependent_units_page:
                self._open_dependent_unit_modal()
            else:
                self.stack.setCurrentWidget(self.dependent_units_page)
        elif key == "dissolution":
            if is_user_action and self.stack.currentWidget() == self.dissolution_page:
                self._open_dissolution_modal()
            else:
                self.stack.setCurrentWidget(self.dissolution_page)
        elif key == "industry_lookup":
            self._refresh_industry_lookup()
            self.stack.setCurrentWidget(self.industry_lookup_page)
        elif key == "trash":
            self._refresh_trash()
            self.stack.setCurrentWidget(self.trash_page)
        elif key == "people":
            self._open_authorized_person_manager()
        else:
            self._show_coming_soon(key, "business_registration")

    def _build_business_registration_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("BusinessCasesPage")
        self.business_page_layout = QVBoxLayout(page)
        layout = self.business_page_layout
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

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

        self.business_create_button = QPushButton("+ Tạo hồ sơ mới")
        self.business_create_button.setObjectName("PrimaryButton")
        self.business_create_button.setCursor(Qt.PointingHandCursor)
        self.business_create_button.clicked.connect(self._open_business_creation_modal)

        self.business_authorized_person_button = QPushButton("Thông tin người ủy quyền")
        self.business_authorized_person_button.setObjectName("GhostButton")
        self.business_authorized_person_button.setCursor(Qt.PointingHandCursor)
        self.business_authorized_person_button.clicked.connect(self._open_authorized_person_manager)

        self.business_settings_button = QPushButton("⚙")
        self.business_settings_button.setObjectName("SettingsButton")
        self.business_settings_button.setToolTip("Cài đặt ứng dụng")
        self.business_settings_button.setAccessibleName("Cài đặt ứng dụng")
        self.business_settings_button.setCursor(Qt.PointingHandCursor)
        self.business_settings_button.clicked.connect(self._open_settings)

        header.addLayout(header_text, 1)
        header.addWidget(self.business_settings_button, 0, Qt.AlignTop)
        header.addWidget(self.business_create_button, 0, Qt.AlignTop)
        layout.addLayout(header)

        # KPI Row (for executive layout)
        self.kpi_row = self._build_kpi_row()
        layout.addWidget(self.kpi_row)

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
        self.cards_layout.setHorizontalSpacing(16)
        self.cards_layout.setVerticalSpacing(16)

        work_layout = QHBoxLayout()
        work_layout.setContentsMargins(0, 0, 0, 0)
        work_layout.setSpacing(16)

        self.cards_scroll.setWidget(self.cards_container)
        work_layout.addWidget(self.cards_scroll, 1)

        self.detail_preview_panel = self._build_detail_preview_panel()
        work_layout.addWidget(self.detail_preview_panel, 0)
        layout.addLayout(work_layout, 1)

        return page

    def _build_kpi_row(self) -> QWidget:
        row = QFrame()
        row.setObjectName("KpiRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self.kpi_total_val = QLabel("0")
        self.kpi_total_val.setObjectName("KpiValue")
        c1 = self._kpi_card("📁", "Tổng hồ sơ", self.kpi_total_val)

        self.kpi_draft_val = QLabel("0")
        self.kpi_draft_val.setObjectName("KpiValue")
        c2 = self._kpi_card("⏳", "Đang xử lý", self.kpi_draft_val)

        self.kpi_ready_val = QLabel("0")
        self.kpi_ready_val.setObjectName("KpiValue")
        c3 = self._kpi_card("✅", "Sẵn sàng tạo", self.kpi_ready_val)

        self.kpi_auth_val = QLabel("---")

        layout.addWidget(c1, 1)
        layout.addWidget(c2, 1)
        layout.addWidget(c3, 1)
        return row

    def _kpi_card(self, icon: str, label_text: str, value_widget: QLabel) -> QWidget:
        card = QFrame()
        card.setObjectName("KpiCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setObjectName("KpiIcon")
        lbl = QLabel(label_text)
        lbl.setObjectName("KpiLabel")
        top.addWidget(icon_lbl)
        top.addWidget(lbl)
        top.addStretch(1)

        layout.addLayout(top)
        layout.addWidget(value_widget)
        return card

    def _update_kpi_metrics(self) -> None:
        if not hasattr(self, "kpi_total_val"):
            return
        total = len(self.cases)
        ready = sum(1 for c in self.cases if c.status in ("Sẵn sàng tạo", "Đã tạo hồ sơ", "Đã hoàn thành"))
        draft = total - ready
        self.kpi_total_val.setText(str(total))
        self.kpi_draft_val.setText(str(max(0, draft)))
        self.kpi_ready_val.setText(str(ready))
        if hasattr(self, "kpi_auth_val") and self.kpi_auth_val is not None:
            auth_name = "---"
            if self.cases:
                auth_name = self._authorized_person_name(self.cases[0])
            elif self.authorized_person_profiles:
                auth_name = self.authorized_person_profiles[0].get("authorized_person_full_name", "---")
            self.kpi_auth_val.setText(auth_name[:18] + "..." if len(auth_name) > 18 else auth_name)

    def _build_detail_preview_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("DetailPreviewPanel")
        panel.setFixedWidth(330)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(0, 0, 0, 0)
        badge_lbl = QLabel("CHI TIẾT HỒ SƠ")
        badge_lbl.setObjectName("DocumentsEyebrow")
        self.detail_status_badge = QLabel("Chưa chọn")
        self.detail_status_badge.setObjectName("StatusBadge")
        badge_row.addWidget(badge_lbl)
        badge_row.addStretch(1)
        badge_row.addWidget(self.detail_status_badge)
        layout.addLayout(badge_row)

        self.detail_company_title = QLabel("Chọn một hồ sơ để xem chi tiết")
        self.detail_company_title.setObjectName("DetailTitle")
        self.detail_company_title.setWordWrap(True)
        layout.addWidget(self.detail_company_title)

        self.detail_type_val = QLabel("---")
        self.detail_capital_val = QLabel("---")
        self.detail_members_val = QLabel("---")
        self.detail_owner_val = QLabel("---")
        self.detail_updated_val = QLabel("---")

        layout.addWidget(self._detail_field("Loại hình:", self.detail_type_val))
        layout.addWidget(self._detail_field("Vốn điều lệ:", self.detail_capital_val))
        layout.addWidget(self._detail_field("Số thành viên:", self.detail_members_val))
        layout.addWidget(self._detail_field("Cập nhật:", self.detail_updated_val))

        layout.addStretch(1)

        self.detail_open_btn = QPushButton("📂 Mở bộ giấy tờ")
        self.detail_open_btn.setObjectName("PrimaryButton")
        self.detail_open_btn.setCursor(Qt.PointingHandCursor)
        self.detail_open_btn.clicked.connect(self._open_selected_detail_documents)
        layout.addWidget(self.detail_open_btn)

        self.detail_edit_btn = QPushButton("✏ Soạn thảo hồ sơ")
        self.detail_edit_btn.setObjectName("GhostButton")
        self.detail_edit_btn.setCursor(Qt.PointingHandCursor)
        self.detail_edit_btn.clicked.connect(self._open_selected_detail_workspace)
        layout.addWidget(self.detail_edit_btn)

        return panel

    def _detail_field(self, label: str, value_widget: QLabel) -> QWidget:
        row = QWidget()
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 4)
        layout.setSpacing(2)
        lbl = QLabel(label)
        lbl.setObjectName("DetailMetaLabel")
        layout.addWidget(lbl)
        layout.addWidget(value_widget)
        return row

    def _update_detail_preview(self, case: CaseSummary | None = None) -> None:
        if not hasattr(self, "detail_company_title"):
            return
        if case is None:
            if self.cases:
                case = self.cases[0]
        if case:
            self._selected_case_for_detail = case
            self.detail_company_title.setText(case.company_name or case.name or "Hồ sơ không tên")
            self.detail_status_badge.setText(case.warning or case.status)
            self.detail_type_val.setText(case.case_type or "---")
            self.detail_capital_val.setText(case.capital or "---")
            self.detail_members_val.setText(f"{case.members} thành viên")
            self.detail_owner_val.setText(self._authorized_person_name(case))
            self.detail_updated_val.setText(case.updated_at or "---")
        else:
            self.detail_company_title.setText("Chưa có hồ sơ nào")
            self.detail_status_badge.setText("Trống")
            self.detail_type_val.setText("---")
            self.detail_capital_val.setText("---")
            self.detail_members_val.setText("---")
            self.detail_owner_val.setText("---")
            self.detail_updated_val.setText("---")

    def _open_selected_detail_documents(self) -> None:
        case = getattr(self, "_selected_case_for_detail", None)
        if case:
            self._open_case_documents(case)
        elif self.cases:
            self._open_case_documents(self.cases[0])

    def _open_selected_detail_workspace(self) -> None:
        case = getattr(self, "_selected_case_for_detail", None)
        if case:
            self._open_case_workspace(case)
        elif self.cases:
            self._open_case_workspace(self.cases[0])

    def _sync_navigation_visibility(self, _stack_index: int | None = None) -> None:
        """Show navigation again whenever the user returns to a hub/main page."""
        if not hasattr(self, "stack"):
            return
        current = self.stack.currentWidget()
        workspace = getattr(self, "current_workspace", None)
        documents = getattr(self, "current_documents_view", None)
        is_fullscreen_workflow = current is workspace or current is documents

        if hasattr(self, "sidebar") and self.sidebar is not None:
            self.sidebar.setVisible(
                not is_fullscreen_workflow
                and getattr(self, "current_layout", "default") not in ("top_nav", "slim_sidebar")
            )
        if hasattr(self, "slim_sidebar") and self.slim_sidebar is not None:
            self.slim_sidebar.setVisible(
                not is_fullscreen_workflow
                and getattr(self, "current_layout", "default") in ("slim_sidebar", "dual_sidebar")
            )
    def _apply_layout_structure(self, layout_key: str) -> None:
        self.current_layout = layout_key if layout_key in LAYOUT_OPTIONS else "default"
        from mingo_assistant.ui.liquid_glass import GlassHover
        if not hasattr(self, "_glass_hover"):
            self._glass_hover = GlassHover(self)
        self._glass_hover.configure(self.current_layout == "liquid_glass")

        # 0. macOS Traffic Lights visibility
        if hasattr(self, "macos_traffic_lights") and self.macos_traffic_lights is not None:
            self.macos_traffic_lights.setVisible(self.current_layout == "macos_glass")

        # 1. Topbar visibility
        if hasattr(self, "global_topbar"):
            self.global_topbar.setVisible(self.current_layout in ("modern_studio", "cyber_hud"))

        # 2. Top navigation bar visibility
        if hasattr(self, "top_nav_bar"):
            self.top_nav_bar.setVisible(self.current_layout == "top_nav")

        # 3. Sidebar visibility & sizing
        if hasattr(self, "sidebar"):
            show_std_sidebar = self.current_layout not in ("top_nav", "slim_sidebar")
            self.sidebar.setVisible(show_std_sidebar)
            if hasattr(self.sidebar, "set_layout_mode"):
                self.sidebar.set_layout_mode(self.current_layout)
            if self.current_layout == "macos_glass":
                self.sidebar.setFixedWidth(225)
            elif self.current_layout in ("modern_studio", "dual_sidebar"):
                self.sidebar.setFixedWidth(210)
            elif self.current_layout in ("minimal_zen", "compact_dense"):
                self.sidebar.setFixedWidth(200)
            else:
                self.sidebar.setFixedWidth(self.SIDEBAR_WIDTH)

        # 4. Slim sidebar visibility
        if hasattr(self, "slim_sidebar"):
            self.slim_sidebar.setVisible(self.current_layout in ("slim_sidebar", "dual_sidebar"))

        # 5. KPI row visibility
        if hasattr(self, "kpi_row"):
            is_exec = self.current_layout in ("executive", "bento_grid", "feed_stream", "macos_glass")
            self.kpi_row.setVisible(is_exec)
            if is_exec:
                self._update_kpi_metrics()

        # 6. Detail preview panel visibility
        if hasattr(self, "detail_preview_panel"):
            is_detail_visible = self.current_layout in ("split_workspace", "feed_stream")
            self.detail_preview_panel.setVisible(is_detail_visible)
            if is_detail_visible:
                self._update_detail_preview(getattr(self, "_selected_case_for_detail", None))

        # 7. Hide page header settings button when already shown in topbar
        if hasattr(self, "business_settings_button"):
            has_top_settings = self.current_layout in ("top_nav", "modern_studio", "cyber_hud")
            self.business_settings_button.setVisible(not has_top_settings)

        # 8. Optimized margins on business page
        if hasattr(self, "business_page_layout"):
            if self.current_layout == "top_nav":
                self.business_page_layout.setContentsMargins(28, 14, 28, 20)
            elif self.current_layout == "centered_focus":
                self.business_page_layout.setContentsMargins(56, 20, 56, 22)
            elif self.current_layout == "minimal_zen":
                self.business_page_layout.setContentsMargins(40, 24, 40, 24)
            elif self.current_layout == "compact_dense":
                self.business_page_layout.setContentsMargins(16, 12, 16, 14)
            elif self.current_layout == "macos_glass":
                self.business_page_layout.setContentsMargins(28, 18, 28, 20)
            else:
                self.business_page_layout.setContentsMargins(24, 20, 24, 22)

        if not (
            hasattr(self, "settings_page")
            and self.settings_page is not None
            and hasattr(self, "stack")
            and self.stack.currentWidget() == self.settings_page
        ):
            self._select_nav(getattr(self, "_current_nav_key", "business_registration"))
        self._relayout_filters()
        self._refresh_cases()
        self._sync_navigation_visibility()

        self._glass_hover.attach()

    def _apply_theme_preview(
        self,
        theme_id: str,
        strength: int = 100,
        appearance_mode: str = "light",
        layout: str = "default",
        font_size: str = "medium",
        border_radius: str = "rounded",
        high_contrast: bool = False,
        custom_color: str = "",
        animations_enabled: bool = True,
        card_shadow: str = "subtle",
        hover_glow: bool = True,
        glassmorphism: bool = False,
    ) -> None:
        self._apply_layout_structure(layout)
        self._glass_hover.motion = animations_enabled
        app = QApplication.instance()
        if app is None:
            return
        system_is_dark = self._system_prefers_dark(app)
        key = (
            theme_id,
            int(strength),
            appearance_mode,
            system_is_dark,
            layout,
            font_size,
            border_radius,
            bool(high_contrast),
            custom_color,
            bool(animations_enabled),
            str(card_shadow),
            bool(hover_glow),
            bool(glassmorphism),
        )
        if key == self._last_applied_theme:
            return
        self._last_applied_theme = key
        is_dark = resolved_appearance_mode(appearance_mode, system_is_dark) == "dark"
        raw_accent = custom_color if (theme_id == "custom" and custom_color) else THEME_OPTIONS.get(theme_id, {}).get("color", "#c46a93")
        apply_app_palette(app, is_dark=is_dark, accent=raw_accent)
        app.setStyleSheet(
            stylesheet_for_theme(
                theme_id=theme_id,
                strength=int(strength),
                appearance_mode=appearance_mode,
                system_is_dark=system_is_dark,
                layout=layout,
                font_size=font_size,
                border_radius=border_radius,
                high_contrast=high_contrast,
                custom_color=custom_color,
                animations_enabled=animations_enabled,
                card_shadow=card_shadow,
                hover_glow=hover_glow,
                glassmorphism=glassmorphism,
            )
        )
        if not hasattr(self, "_visual_effects_manager") or self._visual_effects_manager is None:
            from mingo_assistant.ui.visual_effects import VisualEffectsManager
            self._visual_effects_manager = VisualEffectsManager(self)
        self._visual_effects_manager.apply(
            animations_enabled=animations_enabled,
            card_shadow=card_shadow,
            hover_glow=hover_glow,
            glassmorphism=glassmorphism,
            accent_color=raw_accent,
            is_dark=is_dark,
        )

    def _on_system_color_scheme_changed(self, _scheme=None) -> None:
        settings = load_settings(self.app_paths)
        if settings.get("appearance_mode", "light") == "system":
            try:
                strength = int(settings.get("theme_strength", "100"))
            except ValueError:
                strength = 100
            self._apply_theme_preview(
                theme_id=settings.get("theme", "rose"),
                strength=strength,
                appearance_mode="system",
                layout=settings.get("layout", "default"),
                font_size=settings.get("font_size", "medium"),
                border_radius=settings.get("border_radius", "rounded"),
                high_contrast=settings.get("high_contrast", "false").lower() in ("true", "1"),
                custom_color=settings.get("custom_color", ""),
                animations_enabled=settings.get("animations_enabled", "true").lower() in ("true", "1"),
                card_shadow=settings.get("card_shadow", "subtle"),
                hover_glow=settings.get("hover_glow", "true").lower() in ("true", "1"),
                glassmorphism=settings.get("glassmorphism", "false").lower() in ("true", "1"),
            )

    @staticmethod
    def _system_prefers_dark(app: QApplication) -> bool:
        try:
            return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
        except AttributeError:
            return False

    def _build_settings_page(self) -> QWidget:
        current_settings = load_settings(self.app_paths)
        current_theme = current_settings.get("theme", "rose")
        try:
            current_strength = int(current_settings.get("theme_strength", "100"))
        except ValueError:
            current_strength = 100
        current_mode = current_settings.get("appearance_mode", "light")
        current_layout = current_settings.get("layout", "default")
        current_font_size = current_settings.get("font_size", "medium")
        current_border_radius = current_settings.get("border_radius", "rounded")
        current_high_contrast = current_settings.get("high_contrast", "false").lower() in ("true", "1")
        current_custom_color = current_settings.get("custom_color", "")
        current_animations = current_settings.get("animations_enabled", "true").lower() in ("true", "1")
        current_card_shadow = current_settings.get("card_shadow", "subtle")
        current_hover_glow = current_settings.get("hover_glow", "true").lower() in ("true", "1")
        current_glassmorphism = current_settings.get("glassmorphism", "false").lower() in ("true", "1")

        self.settings_view = SettingsView(
            selected_theme=current_theme,
            color_strength=current_strength,
            appearance_mode=current_mode,
            export_root=self.app_paths.documents_root,
            selected_layout=current_layout,
            font_size=current_font_size,
            border_radius=current_border_radius,
            high_contrast=current_high_contrast,
            custom_color=current_custom_color,
            animations_enabled=current_animations,
            card_shadow=current_card_shadow,
            hover_glow=current_hover_glow,
            glassmorphism=current_glassmorphism,
        )
        self.settings_view.theme_preview_changed.connect(self._apply_theme_preview)
        self.settings_view.save_requested.connect(self._save_settings_from_view)
        self.settings_view.cancel_requested.connect(self._cancel_settings_from_view)
        return self.settings_view

    def _open_settings(self) -> None:
        self._previous_widget_before_settings = self.stack.currentWidget()
        current_settings = load_settings(self.app_paths)
        try:
            current_strength = int(current_settings.get("theme_strength", "100"))
        except ValueError:
            current_strength = 100
        self._settings_snapshot = {
            "theme": current_settings.get("theme", "rose"),
            "theme_strength": current_strength,
            "appearance_mode": current_settings.get("appearance_mode", "light"),
            "layout": current_settings.get("layout", "default"),
            "font_size": current_settings.get("font_size", "medium"),
            "border_radius": current_settings.get("border_radius", "rounded"),
            "high_contrast": current_settings.get("high_contrast", "false").lower() in ("true", "1"),
            "custom_color": current_settings.get("custom_color", ""),
            "animations_enabled": current_settings.get("animations_enabled", "true").lower() in ("true", "1"),
            "card_shadow": current_settings.get("card_shadow", "subtle"),
            "hover_glow": current_settings.get("hover_glow", "true").lower() in ("true", "1"),
            "glassmorphism": current_settings.get("glassmorphism", "false").lower() in ("true", "1"),
        }

        if hasattr(self, "settings_view") and self.settings_view is not None:
            self.settings_view.reload_settings(
                selected_theme=self._settings_snapshot["theme"],
                color_strength=self._settings_snapshot["theme_strength"],
                appearance_mode=self._settings_snapshot["appearance_mode"],
                selected_layout=self._settings_snapshot["layout"],
                font_size=self._settings_snapshot["font_size"],
                border_radius=self._settings_snapshot["border_radius"],
                high_contrast=self._settings_snapshot["high_contrast"],
                custom_color=self._settings_snapshot["custom_color"],
                animations_enabled=self._settings_snapshot["animations_enabled"],
                card_shadow=self._settings_snapshot["card_shadow"],
                hover_glow=self._settings_snapshot["hover_glow"],
                glassmorphism=self._settings_snapshot["glassmorphism"],
                export_root=self.app_paths.documents_root,
            )

        for button in self.nav_buttons.values():
            button.setProperty("active", False)
            button.style().unpolish(button)
            button.style().polish(button)
        if hasattr(self, "top_nav_buttons"):
            for button in self.top_nav_buttons.values():
                button.setProperty("active", False)
                button.style().unpolish(button)
                button.style().polish(button)
        if hasattr(self, "slim_nav_buttons"):
            for button in self.slim_nav_buttons.values():
                button.setProperty("active", False)
                button.style().unpolish(button)
                button.style().polish(button)

        if hasattr(self, "settings_page") and self.settings_page is not None:
            self.stack.setCurrentWidget(self.settings_page)
            if hasattr(self, "_visual_effects_manager") and self._visual_effects_manager is not None:
                self._visual_effects_manager.refresh()

    def _save_settings_from_view(self) -> None:
        view = self.settings_view
        if view is None:
            return
        selected_theme = view.selected_theme()
        selected_strength = view.selected_strength()
        selected_mode = view.selected_appearance_mode()
        selected_layout = view.selected_layout()
        selected_font_size = view.selected_font_size()
        selected_border_radius = view.selected_border_radius()
        selected_high_contrast = view.selected_high_contrast()
        selected_custom_color = view.selected_custom_color()
        selected_animations = view.selected_animations_enabled()
        selected_card_shadow = view.selected_card_shadow()
        selected_hover_glow = view.selected_hover_glow()
        selected_glassmorphism = view.selected_glassmorphism()
        selected_export_root = view.selected_export_root()
        selected_export_root.mkdir(parents=True, exist_ok=True)
        self.app_paths.documents_root = selected_export_root
        self.current_layout = selected_layout

        self._apply_theme_preview(
            selected_theme,
            selected_strength,
            selected_mode,
            selected_layout,
            selected_font_size,
            selected_border_radius,
            selected_high_contrast,
            selected_custom_color,
            selected_animations,
            selected_card_shadow,
            selected_hover_glow,
            selected_glassmorphism,
        )

        save_settings(
            self.app_paths,
            {
                "theme": selected_theme,
                "theme_strength": str(selected_strength),
                "appearance_mode": selected_mode,
                "layout": selected_layout,
                "font_size": selected_font_size,
                "border_radius": selected_border_radius,
                "high_contrast": "true" if selected_high_contrast else "false",
                "custom_color": selected_custom_color,
                "animations_enabled": "true" if selected_animations else "false",
                "card_shadow": selected_card_shadow,
                "hover_glow": "true" if selected_hover_glow else "false",
                "glassmorphism": "true" if selected_glassmorphism else "false",
                "export_root": str(selected_export_root),
            },
        )
        self._refresh_cases()
        self._exit_settings()

    def _cancel_settings_from_view(self) -> None:
        if hasattr(self, "_settings_snapshot") and self._settings_snapshot:
            s = self._settings_snapshot
            self._settings_snapshot = None
            self._apply_theme_preview(
                s["theme"],
                s["theme_strength"],
                s["appearance_mode"],
                s["layout"],
                s["font_size"],
                s["border_radius"],
                s["high_contrast"],
                s["custom_color"],
                s["animations_enabled"],
                s["card_shadow"],
                s["hover_glow"],
                s["glassmorphism"],
            )
        self._exit_settings()

    def _exit_settings(self) -> None:
        target = getattr(self, "_previous_widget_before_settings", None)
        if target and self.stack.indexOf(target) != -1 and target != self.settings_page:
            self.stack.setCurrentWidget(target)
        else:
            self.stack.setCurrentWidget(self.business_page)

        current_nav = getattr(self, "_current_nav_key", "business_registration")
        self._select_nav(current_nav, is_user_action=False)

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

        self.search_input.setPlaceholderText("Tìm theo tên công ty...")
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
        self._refresh_dependent_cases()

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
        if hasattr(self, "_visual_effects_manager") and self._visual_effects_manager is not None:
            self._visual_effects_manager.refresh()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "business_page") and hasattr(self, "cards_layout") and self.stack.currentWidget() == self.business_page:
            self._relayout_filters()
            columns = self._card_column_count()
            if columns != self.current_card_columns:
                self._refresh_cases()
        elif (
            hasattr(self, "dependent_units_page")
            and self.stack.currentWidget() == self.dependent_units_page
            and self.dependent_cases_layout is not None
        ):
            columns = self._card_column_count()
            if columns != self.current_dependent_card_columns:
                self._refresh_dependent_cases()
    def _card_column_count(self) -> int:
        available_width = max(1, self._content_width())
        max_cols = 5 if getattr(self, "current_layout", "default") in ("top_nav", "slim_sidebar") else 4
        return max(1, min(max_cols, (available_width + self.CARD_GAP) // (self.CARD_WIDTH + self.CARD_GAP)))

    def _content_width(self) -> int:
        sidebar_w = 0
        if hasattr(self, "sidebar") and self.sidebar.isVisible():
            sidebar_w = self.sidebar.width()
        elif hasattr(self, "slim_sidebar") and self.slim_sidebar.isVisible():
            sidebar_w = self.slim_sidebar.width()
        detail_w = 0
        if hasattr(self, "detail_preview_panel") and self.detail_preview_panel.isVisible():
            detail_w = self.detail_preview_panel.width()
        margin = self.PAGE_HORIZONTAL_MARGIN
        if getattr(self, "current_layout", "default") == "centered_focus":
            margin = 112
        return max(1, self.width() - sidebar_w - detail_w - margin)

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
            if self._is_dependent_case(case):
                continue
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
                widget.hide()
                widget.setParent(None)
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
        self.case_use_cases.move_to_trash(case.id)
        self.cases = self.case_use_cases.list_active()
        self._refresh_cases()

    def _refresh_trash(self) -> None:
        while self.trash_layout.count():
            item = self.trash_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        deleted_cases = self.case_use_cases.list_deleted()
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
        meta = QLabel(f"{case.case_type} | Đã xóa: {case.deleted_at or 'Không rõ'}")
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
        self.case_use_cases.restore(case.id)
        self.cases = self.case_use_cases.list_active()
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
        self.case_use_cases.delete_permanently(case.id)
        self.cases = self.case_use_cases.list_active()
        self._refresh_trash()

    def _empty_trash(self) -> None:
        deleted_cases = self.case_use_cases.list_deleted()
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
        self.case_use_cases.empty_trash()
        self.cases = self.case_use_cases.list_active()
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

        def on_card_click(event, c=case):
            self._selected_case_for_detail = c
            if hasattr(self, "detail_preview_panel") and self.detail_preview_panel.isVisible():
                self._update_detail_preview(c)
            QFrame.mousePressEvent(card, event)

        card.mousePressEvent = on_card_click

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
        button.clicked.connect(self._open_business_creation_modal)
        layout.addWidget(button)
        layout.addItem(QSpacerItem(1, 34, QSizePolicy.Minimum, QSizePolicy.Expanding))

        return card

    def _open_create_case_dialog(self) -> None:
        self._open_business_creation_modal()

    def _show_case_info(self, case: CaseSummary) -> None:
        QMessageBox.information(
            self,
            "Thông tin hồ sơ",
            (
                f"Tên doanh nghiệp: {case.company_name}\n"
                f"Loại hình: {case.case_type}\n"
                f"Số thành viên: {case.members}\n"
                f"Vốn điều lệ: {case.capital}\n"
                f"Trạng thái: {case.status}"
            ),
        )

    def _build_coming_soon_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 28, 36, 28)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignCenter)

        self.coming_soon_title = QLabel("Chức năng này đang được phát triển")
        self.coming_soon_title.setObjectName("ComingSoonTitle")
        self.coming_soon_title.setAlignment(Qt.AlignCenter)

        self.coming_soon_desc = QLabel(
            "Tính năng này sẽ được bổ sung trong các phiên bản sắp tới."
        )
        self.coming_soon_desc.setObjectName("EmptyDescription")
        self.coming_soon_desc.setAlignment(Qt.AlignCenter)
        self.coming_soon_desc.setWordWrap(True)
        self.coming_soon_desc.setMaximumWidth(520)
        layout.addWidget(self.coming_soon_title)
        layout.addWidget(self.coming_soon_desc)

        self.coming_soon_back_nav_key = "business_registration"
        back_button = QPushButton("← Quay lại danh sách hồ sơ")
        back_button.setObjectName("GhostButton")
        back_button.setCursor(Qt.PointingHandCursor)
        back_button.clicked.connect(lambda: self._select_nav(getattr(self, "coming_soon_back_nav_key", "business_registration")))
        layout.addWidget(back_button, 0, Qt.AlignCenter)

        return page

    def _show_coming_soon(self, feature_name: str = "", back_nav_key: str = "business_registration") -> None:
        self.coming_soon_back_nav_key = back_nav_key
        if hasattr(self, "coming_soon_desc") and self.coming_soon_desc is not None:
            if feature_name:
                self.coming_soon_desc.setText(
                    f"Thủ tục \"{feature_name}\" đang được hoàn thiện biểu mẫu và sẽ sớm ra mắt trong phiên bản kế tiếp."
                )
            else:
                self.coming_soon_desc.setText("Tính năng này sẽ được bổ sung trong các phiên bản sắp tới.")
        self.stack.setCurrentWidget(self.coming_soon_page)

    def _build_category_hub_page(
        self,
        nav_key: str,
        title_text: str,
        desc_text: str,
        on_create_clicked,
    ) -> QWidget:
        page = QWidget()
        page.setObjectName("BusinessCasesPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header_text = QVBoxLayout()
        title = QLabel(title_text)
        title.setObjectName("PageTitle")
        description = QLabel(desc_text)
        description.setObjectName("PageDescription")
        description.setWordWrap(True)
        header_text.addWidget(title)
        header_text.addWidget(description)

        create_btn = QPushButton("+ Tạo hồ sơ mới")
        create_btn.setObjectName("PrimaryButton")
        create_btn.setCursor(Qt.PointingHandCursor)
        create_btn.clicked.connect(on_create_clicked)

        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("SettingsButton")
        settings_btn.setToolTip("Cài đặt ứng dụng")
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.clicked.connect(self._open_settings)

        header.addLayout(header_text, 1)
        header.addWidget(settings_btn, 0, Qt.AlignTop)
        header.addWidget(create_btn, 0, Qt.AlignTop)
        layout.addLayout(header)

        # The dependent-unit page is primarily a saved-dossier list. The header
        # already provides the create action, so duplicated hero cards would only
        # waste vertical space and clip the saved dossiers.
        if nav_key == "dependent_units":
            layout.addWidget(self._build_dependent_cases_section(), 1)
            return page

        cards_container = QWidget()
        cards_layout = QHBoxLayout(cards_container)
        cards_layout.setContentsMargins(0, 20, 0, 0)
        cards_layout.setSpacing(18)
        cards_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        card = QFrame()
        card.setObjectName("CreateCard")
        card.setFixedSize(220, 344)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(22, 22, 22, 22)
        c_layout.setSpacing(12)
        c_layout.addItem(QSpacerItem(1, 34, QSizePolicy.Minimum, QSizePolicy.Expanding))

        c_icon = QLabel("+")
        c_icon.setObjectName("CreateIcon")
        c_icon.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(c_icon)

        c_title = QLabel("Tạo hồ sơ mới")
        c_title.setObjectName("CreateTitle")
        c_title.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(c_title)

        c_desc = QLabel(f"Bấm để mở popup chọn thủ tục cho {title_text.lower()}.")
        c_desc.setObjectName("CreateDescription")
        c_desc.setWordWrap(True)
        c_desc.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(c_desc)

        action_btn = QPushButton("Tạo hồ sơ")
        action_btn.setObjectName("PrimaryButton")
        action_btn.setCursor(Qt.PointingHandCursor)
        action_btn.clicked.connect(on_create_clicked)
        c_layout.addWidget(action_btn)
        c_layout.addItem(QSpacerItem(1, 34, QSizePolicy.Minimum, QSizePolicy.Expanding))

        cards_layout.addWidget(card)

        info_card = QFrame()
        info_card.setObjectName("CaseCard")
        info_card.setFixedSize(380, 344)
        i_layout = QVBoxLayout(info_card)
        i_layout.setContentsMargins(24, 24, 24, 24)
        i_layout.setSpacing(12)

        i_badge = QLabel("HỆ THỐNG THỦ TỤC")
        i_badge.setObjectName("StatusBadge")
        i_badge.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B;")
        i_layout.addWidget(i_badge)

        i_title = QLabel(title_text)
        i_title.setStyleSheet("font-size: 17px; font-weight: 800; color: #0F172A;")
        i_layout.addWidget(i_title)

        i_desc = QLabel(
            f"Bạn có thể khởi tạo nhanh các hồ sơ thuộc nhóm {title_text} bằng cách nhấn nút '+ Tạo hồ sơ mới' ở góc phải hoặc thẻ bên cạnh."
        )
        i_desc.setStyleSheet("font-size: 13px; color: #64748B; line-height: 1.4;")
        i_desc.setWordWrap(True)
        i_layout.addWidget(i_desc)

        i_layout.addStretch(1)

        launch_btn = QPushButton("Khám phá thủ tục →")
        launch_btn.setObjectName("GhostButton")
        launch_btn.setCursor(Qt.PointingHandCursor)
        launch_btn.clicked.connect(on_create_clicked)
        i_layout.addWidget(launch_btn)

        cards_layout.addWidget(info_card)
        cards_layout.addStretch(1)

        layout.addWidget(cards_container, 1)
        return page


    def _build_dependent_cases_section(self) -> QWidget:
        group = QGroupBox("Hồ sơ địa điểm kinh doanh")
        group.setObjectName("DependentCasesPanel")
        group.setMinimumHeight(420)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(18, 16, 18, 18)
        group_layout.setSpacing(12)

        section_header = QHBoxLayout()
        section_header.setSpacing(12)
        section_hint = QLabel(
            "Các hồ sơ địa điểm kinh doanh đã lưu. Chọn Mở để xem file hoặc Sửa để cập nhật hồ sơ."
        )
        section_hint.setObjectName("PageDescription")
        section_hint.setWordWrap(True)
        self.dependent_cases_count_label = QLabel()
        self.dependent_cases_count_label.setObjectName("StatusBadge")
        self.dependent_cases_count_label.setAlignment(Qt.AlignCenter)
        section_header.addWidget(section_hint, 1)
        section_header.addWidget(self.dependent_cases_count_label, 0, Qt.AlignRight)
        group_layout.addLayout(section_header)

        self.dependent_cases_scroll = QScrollArea()
        self.dependent_cases_scroll.setObjectName("DependentCasesScroll")
        self.dependent_cases_scroll.setWidgetResizable(True)
        self.dependent_cases_scroll.setFrameShape(QFrame.NoFrame)
        self.dependent_cases_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.dependent_cases_container = QWidget()
        self.dependent_cases_layout = QGridLayout(self.dependent_cases_container)
        self.dependent_cases_layout.setContentsMargins(0, 0, 0, 0)
        self.dependent_cases_layout.setHorizontalSpacing(16)
        self.dependent_cases_layout.setVerticalSpacing(16)
        self.dependent_cases_scroll.setWidget(self.dependent_cases_container)
        group_layout.addWidget(self.dependent_cases_scroll, 1)
        self._refresh_dependent_cases()
        return group

    @staticmethod
    def _is_dependent_case(case: CaseSummary) -> bool:
        return case.case_type == LOCATION_CASE_TYPE

    def _refresh_dependent_cases(self) -> None:
        layout = self.dependent_cases_layout
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        dependent_cases = [case for case in self.cases if self._is_dependent_case(case)]
        if self.dependent_cases_count_label is not None:
            self.dependent_cases_count_label.setText(f"{len(dependent_cases)} hồ sơ")
        if not dependent_cases:
            empty = QLabel("Chưa có hồ sơ thuộc đơn vị phụ thuộc.")
            empty.setObjectName("EmptyDescription")
            empty.setAlignment(Qt.AlignCenter)
            layout.addWidget(empty, 0, 0, 1, 4)
            self.current_dependent_card_columns = 0
            return

        columns = self._card_column_count()
        self.current_dependent_card_columns = columns
        for index, case in enumerate(dependent_cases):
            layout.addWidget(self._build_case_card(case), index // columns, index % columns)
        for column in range(5):
            layout.setColumnStretch(column, 1 if column < columns else 0)
    def _open_business_creation_modal(self) -> None:
        from mingo_assistant.ui.dialogs.business_creation_modal import BusinessCreationModal

        modal = BusinessCreationModal(self, layout_mode=getattr(self, "current_layout", "default"))
        chosen: dict[str, object] = {"case_type": None, "is_ready": True}

        def on_chosen(case_type: str, is_ready: bool) -> None:
            chosen["case_type"] = case_type
            chosen["is_ready"] = is_ready

        modal.dossier_chosen.connect(on_chosen)
        was_visible = self.sidebar.isVisible() if hasattr(self, "sidebar") and self.sidebar else False
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.setVisible(False)
        if hasattr(self, "slim_sidebar") and self.slim_sidebar:
            self.slim_sidebar.setVisible(False)
        try:
            result = modal.exec()
        finally:
            if getattr(self, "current_workspace", None) is None and getattr(self, "current_documents_view", None) is None:
                if hasattr(self, "sidebar") and self.sidebar:
                    self.sidebar.setVisible(was_visible)
                if hasattr(self, "_apply_layout_structure") and hasattr(self, "current_layout"):
                    self._apply_layout_structure(self.current_layout)
        if result == QDialog.DialogCode.Accepted and chosen["case_type"]:
            if chosen["is_ready"]:
                self._open_new_business_case()
            else:
                self._show_coming_soon(str(chosen["case_type"]), "business_registration")

    def _open_business_amendment_modal(self) -> None:
        from mingo_assistant.ui.dialogs.business_amendment_modal import BusinessAmendmentModal

        modal = BusinessAmendmentModal(self, layout_mode=getattr(self, "current_layout", "default"))
        chosen: dict[str, object] = {"id": None, "name": "", "is_ready": False}

        def on_chosen(proc_id: str, proc_name: str, is_ready: bool) -> None:
            chosen["id"] = proc_id
            chosen["name"] = proc_name
            chosen["is_ready"] = is_ready

        modal.procedure_chosen.connect(on_chosen)
        was_visible = self.sidebar.isVisible() if hasattr(self, "sidebar") and self.sidebar else False
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.setVisible(False)
        if hasattr(self, "slim_sidebar") and self.slim_sidebar:
            self.slim_sidebar.setVisible(False)
        try:
            result = modal.exec()
        finally:
            if getattr(self, "current_workspace", None) is None and getattr(self, "current_documents_view", None) is None:
                if hasattr(self, "sidebar") and self.sidebar:
                    self.sidebar.setVisible(was_visible)
                if hasattr(self, "_apply_layout_structure") and hasattr(self, "current_layout"):
                    self._apply_layout_structure(self.current_layout)
        if result == QDialog.DialogCode.Accepted and chosen["name"]:
            self._show_coming_soon(str(chosen["name"]), "business_amendment")

    def _open_dependent_unit_modal(self) -> None:
        from mingo_assistant.ui.dialogs.dependent_unit_modal import DependentUnitModal

        modal = DependentUnitModal(self, layout_mode=getattr(self, "current_layout", "default"))
        chosen: dict[str, object] = {"unit_type": "", "action": "", "title": "", "is_ready": False}

        def on_chosen(u_type: str, act: str, title: str, is_ready: bool) -> None:
            chosen["unit_type"] = u_type
            chosen["action"] = act
            chosen["title"] = title
            chosen["is_ready"] = is_ready

        modal.procedure_chosen.connect(on_chosen)
        was_visible = self.sidebar.isVisible() if hasattr(self, "sidebar") and self.sidebar else False
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.setVisible(False)
        if hasattr(self, "slim_sidebar") and self.slim_sidebar:
            self.slim_sidebar.setVisible(False)
        try:
            result = modal.exec()
        finally:
            if getattr(self, "current_workspace", None) is None and getattr(self, "current_documents_view", None) is None:
                if hasattr(self, "sidebar") and self.sidebar:
                    self.sidebar.setVisible(was_visible)
                if hasattr(self, "_apply_layout_structure") and hasattr(self, "current_layout"):
                    self._apply_layout_structure(self.current_layout)
        if (
            result == QDialog.DialogCode.Accepted
            and chosen["unit_type"] == "ddkd"
            and chosen["action"] == "create"
            and chosen["is_ready"]
        ):
            self._open_location_business_workspace(None)
        elif result == QDialog.DialogCode.Accepted and chosen["title"]:
            self._show_coming_soon(str(chosen["title"]), "dependent_units")

    def _open_dissolution_modal(self) -> None:
        from mingo_assistant.ui.dialogs.dissolution_modal import DissolutionModal

        modal = DissolutionModal(self, layout_mode=getattr(self, "current_layout", "default"))
        chosen: dict[str, object] = {"title": "", "is_ready": False}

        def on_chosen(c_type: str, tax_id: str, full_title: str, is_ready: bool) -> None:
            chosen["title"] = full_title
            chosen["is_ready"] = is_ready

        modal.dissolution_chosen.connect(on_chosen)
        was_visible = self.sidebar.isVisible() if hasattr(self, "sidebar") and self.sidebar else False
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.setVisible(False)
        if hasattr(self, "slim_sidebar") and self.slim_sidebar:
            self.slim_sidebar.setVisible(False)
        try:
            result = modal.exec()
        finally:
            if getattr(self, "current_workspace", None) is None and getattr(self, "current_documents_view", None) is None:
                if hasattr(self, "sidebar") and self.sidebar:
                    self.sidebar.setVisible(was_visible)
                if hasattr(self, "_apply_layout_structure") and hasattr(self, "current_layout"):
                    self._apply_layout_structure(self.current_layout)
        if result == QDialog.DialogCode.Accepted and chosen["title"]:
            self._show_coming_soon(str(chosen["title"]), "dissolution")

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
        return self._authorized_profile_operations().selected()

    def _authorized_profile_operations(self) -> AuthorizedPersonUseCases:
        operations = getattr(self, "authorized_person_use_cases", None)
        if operations is None:
            operations = AuthorizedPersonUseCases(self.authorized_person_repository)
            self.authorized_person_use_cases = operations
        return operations

    def _builtin_authorized_person_profiles(self) -> list[dict[str, str]]:
        return self._authorized_profile_operations().defaults()

    def _is_builtin_authorized_person_profile(self, profile_id: str) -> bool:
        return self._authorized_profile_operations().is_default(profile_id)

    def _merge_authorized_person_profiles(
        self, selected_profile_id: str, profiles: list[dict[str, str]]
    ) -> dict[str, object]:
        return self._authorized_profile_operations().merge(selected_profile_id, profiles)

    def _load_authorized_person_profiles(self) -> dict[str, object]:
        payload = self._authorized_profile_operations().load()
        recovery_error = self.authorized_person_repository.last_recovery_error
        if recovery_error is not None and not getattr(self, "_authorized_recovery_warned", False):
            self._authorized_recovery_warned = True
            backup_text = (
                f"\nBản sao phục hồi: {recovery_error.backup_path}"
                if recovery_error.backup_path is not None
                else ""
            )
            QMessageBox.warning(
                self,
                "Dữ liệu profile cần phục hồi",
                "Tệp profile trên máy bị hỏng nên ứng dụng đang dùng 3 profile mặc định."
                f"\nTệp gốc không bị xóa hoặc ghi đè.{backup_text}",
            )
        return payload

    def _authorized_profile_by_id(self, profiles: list[dict[str, str]], profile_id: str) -> dict[str, str] | None:
        for profile in profiles:
            if str(profile.get("id", "")) == profile_id:
                return profile
        return None

    def _save_authorized_person_profiles(self, payload: dict[str, object]) -> None:
        self._authorized_profile_operations().save(payload)

    def _save_authorized_person(self, values: dict[str, str]) -> None:
        values.setdefault("id", str(uuid4()))
        self._save_authorized_person_profiles({"selected_profile_id": values["id"], "profiles": [values]})

    def _open_case_workspace(self, case: CaseSummary | None) -> None:
        if case is not None:
            case = self.case_use_cases.get(case.id) or case
        if case is not None and case.case_type == LOCATION_CASE_TYPE:
            self._open_location_business_workspace(case)
            return
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
            services=self.registration_services,
        )
        self.stack.addWidget(self.current_workspace)
        self.stack.setCurrentWidget(self.current_workspace)
        if hasattr(self, "sidebar") and self.sidebar is not None:
            self.sidebar.setVisible(False)
        if hasattr(self, "slim_sidebar") and self.slim_sidebar is not None:
            self.slim_sidebar.setVisible(False)

    def _open_location_business_workspace(self, case: CaseSummary | None) -> None:
        if case is not None:
            case = self.case_use_cases.get(case.id) or case
        if self.current_workspace is not None:
            self.stack.removeWidget(self.current_workspace)
            self.current_workspace.deleteLater()
            self.current_workspace = None
        if self.current_documents_view is not None:
            self.stack.removeWidget(self.current_documents_view)
            self.current_documents_view.deleteLater()
            self.current_documents_view = None
        self.current_workspace = LocationBusinessWorkspace(
            on_back=self._return_to_dependent_units,
            on_save=self._save_case_from_workspace,
            case=case,
            on_export=self._open_case_documents,
            authorized_person_defaults=self._load_authorized_person(),
            industry_catalog=self.industry_catalog,
            bundle_root=self.app_paths.bundle_root,
            default_export_root=self.app_paths.documents_root,
            services=self.registration_services,
        )
        self.stack.addWidget(self.current_workspace)
        self.stack.setCurrentWidget(self.current_workspace)
        if hasattr(self, "sidebar") and self.sidebar is not None:
            self.sidebar.setVisible(False)
        if hasattr(self, "slim_sidebar") and self.slim_sidebar is not None:
            self.slim_sidebar.setVisible(False)
    def _open_case_documents(self, case: CaseSummary) -> None:
        case = self.case_use_cases.get(case.id) or case
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
            on_back=self._return_to_dependent_units if case.case_type == LOCATION_CASE_TYPE else self._return_to_business_list,
            on_edit=lambda selected_id=case.id: self._open_case_workspace(self.case_use_cases.get(selected_id) or case),
        )
        self.stack.addWidget(self.current_documents_view)
        self.stack.setCurrentWidget(self.current_documents_view)
        if hasattr(self, "sidebar") and self.sidebar is not None:
            self.sidebar.setVisible(False)
        if hasattr(self, "slim_sidebar") and self.slim_sidebar is not None:
            self.slim_sidebar.setVisible(False)

    def _return_to_business_list(self) -> None:
        self.cases = self.case_use_cases.list_active()
        self._refresh_cases()
        self.stack.setCurrentWidget(self.business_page)
        self._apply_layout_structure(self.current_layout)

    def _return_to_dependent_units(self) -> None:
        self.cases = self.case_use_cases.list_active()
        self._refresh_cases()
        self.stack.setCurrentWidget(self.dependent_units_page)
        self._apply_layout_structure(self.current_layout)
    def _save_case_from_workspace(self, case: CaseSummary) -> None:
        self.case_use_cases.save(case)
        self.cases = self.case_use_cases.list_active()
        self._refresh_cases()

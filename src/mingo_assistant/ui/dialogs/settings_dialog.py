from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from mingo_assistant.ui.styles import THEME_OPTIONS


class SettingsDialog(QDialog):
    """Wide settings workspace with live application-theme preview."""

    theme_preview_changed = Signal(str, int, str)

    _PAGES = (
        ("general", "Chung"),
        ("appearance", "Giao diện"),
        ("data", "Dữ liệu & xuất Word"),
        ("recognition", "Nhận diện CCCD"),
        ("about", "Giới thiệu"),
    )

    def __init__(self, selected_theme: str, color_strength: int = 100, appearance_mode: str = "light") -> None:
        super().__init__()
        self.setObjectName("SettingsDialog")
        self.setWindowTitle("Cài đặt ứng dụng")
        self.resize(1120, 720)
        self.setMinimumSize(900, 600)
        self._category_buttons: dict[str, QPushButton] = {}
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(90)
        self._preview_timer.timeout.connect(self._emit_preview_now)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar(), 0)
        body.addWidget(self._build_content(selected_theme, color_strength, appearance_mode), 1)
        root.addLayout(body, 1)

        footer = QFrame()
        footer.setObjectName("SettingsFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(24, 12, 24, 12)
        footer_layout.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        buttons.button(QDialogButtonBox.Save).setText("Lưu thay đổi")
        buttons.button(QDialogButtonBox.Cancel).setText("Hủy")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        footer_layout.addWidget(buttons)
        root.addWidget(footer)

        self._select_category("appearance")

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("SettingsSidebar")
        sidebar.setFixedWidth(280)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 18, 12, 16)
        layout.setSpacing(10)

        back = QPushButton("←  Quay lại ứng dụng")
        back.setObjectName("SettingsBackButton")
        back.clicked.connect(self.reject)
        layout.addWidget(back)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("SettingsSearch")
        self.search_input.setPlaceholderText("Tìm cài đặt...")
        self.search_input.textChanged.connect(self._filter_categories)
        layout.addWidget(self.search_input)

        category_label = QLabel("CÀI ĐẶT")
        category_label.setObjectName("SettingsEyebrow")
        layout.addWidget(category_label)

        self.category_layout = QVBoxLayout()
        self.category_layout.setContentsMargins(0, 0, 0, 0)
        self.category_layout.setSpacing(3)
        for key, label in self._PAGES:
            button = QPushButton(label)
            button.setObjectName("SettingsCategory")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, category=key: self._select_category(category))
            self._category_buttons[key] = button
            self.category_layout.addWidget(button)
        self.category_layout.addStretch(1)
        layout.addLayout(self.category_layout, 1)

        local_note = QLabel("Dữ liệu được lưu cục bộ trên máy")
        local_note.setObjectName("SettingsSidebarNote")
        local_note.setWordWrap(True)
        layout.addWidget(local_note)
        return sidebar

    def _build_content(self, selected_theme: str, color_strength: int, appearance_mode: str) -> QFrame:
        content = QFrame()
        content.setObjectName("SettingsContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        self.pages = QStackedWidget()
        self._page_keys: list[str] = []
        for key, _label in self._PAGES:
            self._page_keys.append(key)
            if key == "general":
                page = self._build_general_page()
            elif key == "appearance":
                page = self._build_appearance_page(selected_theme, color_strength, appearance_mode)
            elif key == "data":
                page = self._build_information_page(
                    "Dữ liệu & xuất Word",
                    "Các thiết lập về thư mục xuất, sao lưu và mẫu Word sẽ được đặt tại đây.",
                )
            elif key == "recognition":
                page = self._build_information_page(
                    "Nhận diện CCCD",
                    "Các tùy chọn quét QR, OCR và xác nhận địa chỉ sẽ được đặt tại đây.",
                )
            else:
                page = self._build_information_page(
                    "Giới thiệu",
                    "Mingo Assistant lưu dữ liệu cục bộ và hỗ trợ lập hồ sơ doanh nghiệp.",
                )
            self.pages.addWidget(page)
        layout.addWidget(self.pages)
        return content

    def _page_shell(self, title: str, description: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setObjectName("SettingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        canvas = QWidget()
        canvas.setObjectName("SettingsCanvas")
        layout = QVBoxLayout(canvas)
        layout.setContentsMargins(56, 46, 56, 40)
        layout.setSpacing(22)

        heading = QLabel(title)
        heading.setObjectName("SettingsPageTitle")
        layout.addWidget(heading)
        intro = QLabel(description)
        intro.setObjectName("SettingsPageDescription")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        scroll.setWidget(canvas)
        page_layout.addWidget(scroll)
        return page, layout

    def _build_general_page(self) -> QWidget:
        page, layout = self._page_shell(
            "Chung",
            "Các thiết lập cơ bản cho dữ liệu hồ sơ và cách ứng dụng hoạt động.",
        )
        layout.addWidget(self._setting_card(
            "Dữ liệu cục bộ",
            "Hồ sơ, profile và lựa chọn cài đặt được lưu trên máy này.",
            "Bảo vệ dữ liệu bằng cách sao lưu định kỳ.",
        ))
        layout.addWidget(self._setting_card(
            "Giao diện",
            "Thay đổi màu sắc, độ đậm màu và cách hiển thị của ứng dụng.",
            "Chọn mục Giao diện ở thanh bên để tùy chỉnh.",
        ))
        layout.addStretch(1)
        return page

    def _build_appearance_page(self, selected_theme: str, color_strength: int, appearance_mode: str) -> QWidget:
        page, layout = self._page_shell(
            "Giao diện",
            "Chọn chế độ sáng/tối, bảng màu và độ đậm. Thay đổi được xem trước trực tiếp.",
        )
        mode_title = QLabel("Chủ đề")
        mode_title.setObjectName("SettingsSectionTitle")
        layout.addWidget(mode_title)
        modes = QFrame()
        modes.setObjectName("AppearanceModeGroup")
        mode_layout = QHBoxLayout(modes)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(14)
        self.appearance_mode_group = QButtonGroup(self)
        self.appearance_mode_buttons: dict[str, QPushButton] = {}
        for mode_id, label, icon in (("system", "Theo hệ thống", "◐"), ("light", "Sáng", "☀"), ("dark", "Tối", "●")):
            button = QPushButton(f"{icon}\n{label}")
            button.setObjectName("AppearanceModeTile")
            button.setCheckable(True)
            button.setChecked(mode_id == appearance_mode)
            button.setCursor(Qt.PointingHandCursor)
            self.appearance_mode_group.addButton(button)
            self.appearance_mode_buttons[mode_id] = button
            button.toggled.connect(lambda checked, selected_id=mode_id: self._emit_preview_now() if checked else None)
            mode_layout.addWidget(button, 1)
        layout.addWidget(modes)

        colors_title = QLabel("Bảng màu")
        colors_title.setObjectName("SettingsSectionTitle")
        layout.addWidget(colors_title)
        color_card = QFrame()
        color_card.setObjectName("SettingsCard")
        color_grid = QGridLayout(color_card)
        color_grid.setContentsMargins(18, 16, 18, 16)
        color_grid.setHorizontalSpacing(12)
        color_grid.setVerticalSpacing(10)
        self.theme_group = QButtonGroup(self)
        self.theme_buttons: dict[str, QRadioButton] = {}
        for index, (theme_id, theme) in enumerate(THEME_OPTIONS.items()):
            row = QWidget()
            row.setObjectName("ThemeOption")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(9, 7, 9, 7)
            row_layout.setSpacing(8)
            swatch = QFrame()
            swatch.setFixedSize(22, 22)
            swatch.setStyleSheet(f"background: {theme['color']}; border: 1px solid rgba(61, 36, 48, 0.18); border-radius: 11px;")
            button = QRadioButton(theme["label"])
            button.setChecked(theme_id == selected_theme)
            button.toggled.connect(lambda checked, selected_id=theme_id: self._emit_preview_now() if checked else None)
            self.theme_group.addButton(button)
            self.theme_buttons[theme_id] = button
            row_layout.addWidget(swatch)
            row_layout.addWidget(button, 1)
            color_grid.addWidget(row, index // 2, index % 2)
        layout.addWidget(color_card)

        strength_title = QLabel("Độ đậm màu")
        strength_title.setObjectName("SettingsSectionTitle")
        layout.addWidget(strength_title)
        strength_card = QFrame()
        strength_card.setObjectName("SettingsCard")
        strength_layout = QVBoxLayout(strength_card)
        strength_layout.setContentsMargins(20, 18, 20, 18)
        strength_header = QHBoxLayout()
        strength_description = QLabel("Làm màu giao diện nhạt hoặc đậm hơn")
        strength_description.setObjectName("SettingsItemTitle")
        self.strength_value = QLabel()
        self.strength_value.setObjectName("SettingsStrengthValue")
        strength_header.addWidget(strength_description)
        strength_header.addStretch(1)
        strength_header.addWidget(self.strength_value)
        strength_layout.addLayout(strength_header)
        self.color_strength_slider = QSlider(Qt.Horizontal)
        self.color_strength_slider.setRange(60, 140)
        self.color_strength_slider.setValue(max(60, min(140, int(color_strength))))
        self.color_strength_slider.valueChanged.connect(self._schedule_preview)
        strength_layout.addWidget(self.color_strength_slider)
        scale = QHBoxLayout()
        lighter, darker = QLabel("Nhạt"), QLabel("Đậm")
        lighter.setObjectName("SettingsHint")
        darker.setObjectName("SettingsHint")
        scale.addWidget(lighter)
        scale.addStretch(1)
        scale.addWidget(darker)
        strength_layout.addLayout(scale)
        layout.addWidget(strength_card)
        self._update_strength_label()
        layout.addStretch(1)
        return page

    def _build_information_page(self, title: str, description: str) -> QWidget:
        page, layout = self._page_shell(title, description)
        layout.addWidget(self._setting_card("Đang chuẩn bị", description, "Mục này sẽ được bổ sung trong Cài đặt ứng dụng."))
        layout.addStretch(1)
        return page

    def _setting_card(self, title: str, description: str, detail: str) -> QFrame:
        card = QFrame()
        card.setObjectName("SettingsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 17, 20, 17)
        layout.setSpacing(5)
        title_label = QLabel(title)
        title_label.setObjectName("SettingsItemTitle")
        description_label = QLabel(description)
        description_label.setObjectName("SettingsItemDescription")
        description_label.setWordWrap(True)
        detail_label = QLabel(detail)
        detail_label.setObjectName("SettingsHint")
        detail_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addWidget(detail_label)
        return card

    def _select_category(self, category: str) -> None:
        for index, key in enumerate(self._page_keys):
            if key == category:
                self.pages.setCurrentIndex(index)
                break
        for key, button in self._category_buttons.items():
            button.setProperty("active", key == category)
            button.style().unpolish(button)
            button.style().polish(button)

    def _filter_categories(self, query: str) -> None:
        normalized = query.strip().casefold()
        visible_keys = []
        for key, label in self._PAGES:
            is_visible = not normalized or normalized in label.casefold()
            self._category_buttons[key].setVisible(is_visible)
            if is_visible:
                visible_keys.append(key)
        if visible_keys and not self._category_buttons[visible_keys[0]].property("active"):
            self._select_category(visible_keys[0])

    def _update_strength_label(self) -> None:
        self.strength_value.setText(f"{self.color_strength_slider.value()}%")

    def _schedule_preview(self, *_args) -> None:
        self._update_strength_label()
        self._preview_timer.start()

    def _emit_preview_now(self, *_args) -> None:
        self._preview_timer.stop()
        self._update_strength_label()
        self.theme_preview_changed.emit(self.selected_theme(), self.selected_strength(), self.selected_appearance_mode())

    def selected_theme(self) -> str:
        for theme_id, button in self.theme_buttons.items():
            if button.isChecked():
                return theme_id
        return "rose"

    def selected_strength(self) -> int:
        return self.color_strength_slider.value()

    def selected_appearance_mode(self) -> str:
        for mode_id, button in self.appearance_mode_buttons.items():
            if button.isChecked():
                return mode_id
        return "light"

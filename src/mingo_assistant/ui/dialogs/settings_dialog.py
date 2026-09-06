from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
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

from mingo_assistant import __version__
from mingo_assistant.ui.styles import THEME_OPTIONS


class SettingsDialog(QDialog):
    """Application settings with live theme preview and local export storage."""

    theme_preview_changed = Signal(str, int, str)

    _PAGES = (
        ("general", "Chung"),
        ("appearance", "Giao di\u1ec7n"),
        ("storage", "N\u01a1i l\u01b0u tr\u1eef"),
        ("pets", "Th\u00fa c\u01b0ng"),
        ("background_music", "Nh\u1ea1c n\u1ec1n"),
        ("ai", "AI"),
        ("about", "Gi\u1edbi thi\u1ec7u"),
    )

    def __init__(
        self,
        selected_theme: str,
        color_strength: int = 100,
        appearance_mode: str = "light",
        export_root: Path | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("SettingsDialog")
        self.setWindowTitle("C\u00e0i \u0111\u1eb7t \u1ee9ng d\u1ee5ng")
        self.resize(1120, 720)
        self.setMinimumSize(900, 600)
        self._selected_export_root = Path(export_root or Path.home() / "Documents" / "Mingo Assistant")
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
        buttons.button(QDialogButtonBox.Save).setText("L\u01b0u thay \u0111\u1ed5i")
        buttons.button(QDialogButtonBox.Cancel).setText("H\u1ee7y")
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
        back = QPushButton("\u2190  Quay l\u1ea1i \u1ee9ng d\u1ee5ng")
        back.setObjectName("SettingsBackButton")
        back.clicked.connect(self.reject)
        layout.addWidget(back)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("SettingsSearch")
        self.search_input.setPlaceholderText("T\u00ecm c\u00e0i \u0111\u1eb7t...")
        self.search_input.textChanged.connect(self._filter_categories)
        layout.addWidget(self.search_input)
        category_label = QLabel("C\u00c0I \u0110\u1eb6T")
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
        local_note = QLabel("D\u1eef li\u1ec7u \u0111\u01b0\u1ee3c l\u01b0u c\u1ee5c b\u1ed9 tr\u00ean m\u00e1y")
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
        builders = {
            "general": self._build_general_page,
            "appearance": lambda: self._build_appearance_page(selected_theme, color_strength, appearance_mode),
            "storage": self._build_storage_page,
            "pets": lambda: self._build_development_page("Th\u00fa c\u01b0ng"),
            "background_music": lambda: self._build_development_page("Nh\u1ea1c n\u1ec1n"),
            "ai": lambda: self._build_development_page("AI"),
            "about": self._build_about_page,
        }
        for key, _label in self._PAGES:
            self._page_keys.append(key)
            self.pages.addWidget(builders[key]())
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
            "C\u00e1c thi\u1ebft l\u1eadp c\u01a1 b\u1ea3n cho d\u1eef li\u1ec7u h\u1ed3 s\u01a1 v\u00e0 c\u00e1ch \u1ee9ng d\u1ee5ng ho\u1ea1t \u0111\u1ed9ng.",
        )
        layout.addWidget(self._setting_card(
            "D\u1eef li\u1ec7u c\u1ee5c b\u1ed9",
            "H\u1ed3 s\u01a1, profile v\u00e0 l\u1ef1a ch\u1ecdn c\u00e0i \u0111\u1eb7t \u0111\u01b0\u1ee3c l\u01b0u tr\u00ean m\u00e1y n\u00e0y.",
            "Sao l\u01b0u d\u1eef li\u1ec7u \u0111\u1ecbnh k\u1ef3 \u0111\u1ec3 d\u1ec5 kh\u00f4i ph\u1ee5c khi c\u1ea7n.",
        ))
        layout.addWidget(self._setting_card(
            "Giao di\u1ec7n",
            "Thay \u0111\u1ed5i m\u00e0u s\u1eafc, \u0111\u1ed9 \u0111\u1eadm m\u00e0u v\u00e0 ch\u1ebf \u0111\u1ed9 s\u00e1ng/t\u1ed1i.",
            "Ch\u1ecdn m\u1ee5c Giao di\u1ec7n \u1edf thanh b\u00ean \u0111\u1ec3 t\u00f9y ch\u1ec9nh.",
        ))
        layout.addStretch(1)
        return page

    def _build_appearance_page(self, selected_theme: str, color_strength: int, appearance_mode: str) -> QWidget:
        page, layout = self._page_shell(
            "Giao di\u1ec7n",
            "Ch\u1ecdn ch\u1ebf \u0111\u1ed9 s\u00e1ng/t\u1ed1i, b\u1ea3ng m\u00e0u v\u00e0 \u0111\u1ed9 \u0111\u1eadm. Thay \u0111\u1ed5i \u0111\u01b0\u1ee3c xem tr\u01b0\u1edbc tr\u1ef1c ti\u1ebfp.",
        )
        mode_title = QLabel("Ch\u1ee7 \u0111\u1ec1")
        mode_title.setObjectName("SettingsSectionTitle")
        layout.addWidget(mode_title)
        modes = QFrame()
        modes.setObjectName("AppearanceModeGroup")
        mode_layout = QHBoxLayout(modes)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(14)
        self.appearance_mode_group = QButtonGroup(self)
        self.appearance_mode_buttons: dict[str, QPushButton] = {}
        for mode_id, label, icon in (("system", "Theo h\u1ec7 th\u1ed1ng", "\u25d0"), ("light", "S\u00e1ng", "\u2600"), ("dark", "T\u1ed1i", "\u25cf")):
            button = QPushButton(f"{icon}\\n{label}")
            button.setObjectName("AppearanceModeTile")
            button.setCheckable(True)
            button.setChecked(mode_id == appearance_mode)
            button.setCursor(Qt.PointingHandCursor)
            self.appearance_mode_group.addButton(button)
            self.appearance_mode_buttons[mode_id] = button
            button.toggled.connect(lambda checked, selected_id=mode_id: self._emit_preview_now() if checked else None)
            mode_layout.addWidget(button, 1)
        layout.addWidget(modes)
        colors_title = QLabel("B\u1ea3ng m\u00e0u")
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
        strength_title = QLabel("\u0110\u1ed9 \u0111\u1eadm m\u00e0u")
        strength_title.setObjectName("SettingsSectionTitle")
        layout.addWidget(strength_title)
        strength_card = QFrame()
        strength_card.setObjectName("SettingsCard")
        strength_layout = QVBoxLayout(strength_card)
        strength_layout.setContentsMargins(20, 18, 20, 18)
        strength_header = QHBoxLayout()
        strength_description = QLabel("L\u00e0m m\u00e0u giao di\u1ec7n nh\u1ea1t ho\u1eb7c \u0111\u1eadm h\u01a1n")
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
        lighter, darker = QLabel("Nh\u1ea1t"), QLabel("\u0110\u1eadm")
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

    def _build_storage_page(self) -> QWidget:
        page, layout = self._page_shell(
            "N\u01a1i l\u01b0u tr\u1eef",
            "Ch\u1ecdn th\u01b0 m\u1ee5c d\u00f9ng \u0111\u1ec3 xu\u1ea5t c\u00e1c b\u1ed9 h\u1ed3 s\u01a1 Word.",
        )
        card = QFrame()
        card.setObjectName("SettingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(8)
        title = QLabel("Th\u01b0 m\u1ee5c xu\u1ea5t Word")
        title.setObjectName("SettingsItemTitle")
        description = QLabel("M\u1ed7i l\u1ea7n xu\u1ea5t h\u1ed3 s\u01a1, \u1ee9ng d\u1ee5ng s\u1ebd t\u1ea1o th\u01b0 m\u1ee5c h\u1ed3 s\u01a1 v\u00e0 c\u00e1c b\u1ea3n Word t\u1ea1i \u0111\u00e2y.")
        description.setObjectName("SettingsItemDescription")
        description.setWordWrap(True)
        self.storage_path_label = QLabel()
        self.storage_path_label.setObjectName("SettingsStoragePath")
        self.storage_path_label.setWordWrap(True)
        choose_button = QPushButton("Ch\u1ecdn n\u01a1i l\u01b0u tr\u1eef")
        choose_button.setObjectName("GhostButton")
        choose_button.setCursor(Qt.PointingHandCursor)
        choose_button.clicked.connect(self._choose_export_root)
        card_layout.addWidget(title)
        card_layout.addWidget(description)
        card_layout.addSpacing(5)
        card_layout.addWidget(self.storage_path_label)
        card_layout.addWidget(choose_button, 0, Qt.AlignLeft)
        layout.addWidget(card)
        layout.addStretch(1)
        self._update_storage_path_label()
        return page

    def _build_development_page(self, title: str) -> QWidget:
        page, layout = self._page_shell(title, f"Thi\u1ebft l\u1eadp {title.casefold()} s\u1ebd \u0111\u01b0\u1ee3c b\u1ed5 sung trong phi\u00ean b\u1ea3n sau.")
        layout.addWidget(self._setting_card(
            "Ch\u1ee9c n\u0103ng n\u00e0y \u0111ang \u0111\u01b0\u1ee3c ph\u00e1t tri\u1ec3n",
            "M\u1ee5c n\u00e0y ch\u01b0a c\u00f3 thi\u1ebft l\u1eadp s\u1eb5n s\u00e0ng trong phi\u00ean b\u1ea3n hi\u1ec7n t\u1ea1i.",
            "Ch\u00fang t\u00f4i s\u1ebd c\u1eadp nh\u1eadt khi ch\u1ee9c n\u0103ng ho\u00e0n thi\u1ec7n.",
        ))
        layout.addStretch(1)
        return page

    def _build_about_page(self) -> QWidget:
        page, layout = self._page_shell(
            "Gi\u1edbi thi\u1ec7u",
            "Mingo Assistant l\u00e0 \u1ee9ng d\u1ee5ng l\u00e0m vi\u1ec7c c\u1ee5c b\u1ed9, h\u1ed7 tr\u1ee3 qu\u00e9t QR CCCD, qu\u1ea3n l\u00fd d\u1eef li\u1ec7u h\u1ed3 s\u01a1 th\u00e0nh l\u1eadp doanh nghi\u1ec7p v\u00e0 xu\u1ea5t b\u1ed9 bi\u1ec3u m\u1eabu Word.",
        )
        layout.addWidget(self._setting_card(
            "Mingo Assistant",
            "D\u1eef li\u1ec7u h\u1ed3 s\u01a1, profile v\u00e0 c\u00e0i \u0111\u1eb7t \u0111\u01b0\u1ee3c l\u01b0u tr\u00ean m\u00e1y c\u1ee7a b\u1ea1n.",
            f"Phi\u00ean b\u1ea3n hi\u1ec7n t\u1ea1i: v{__version__}",
        ))
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

    def _choose_export_root(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Ch\u1ecdn n\u01a1i l\u01b0u h\u1ed3 s\u01a1 Word",
            str(self._selected_export_root),
        )
        if selected:
            self._selected_export_root = Path(selected)
            self._update_storage_path_label()

    def _update_storage_path_label(self) -> None:
        self.storage_path_label.setText(str(self._selected_export_root))

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

    def selected_export_root(self) -> Path:
        return self._selected_export_root

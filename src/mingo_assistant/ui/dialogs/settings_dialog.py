from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QColorDialog,
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
from mingo_assistant.ui.styles import (
    BORDER_RADIUS_OPTIONS,
    EFFECT_SHADOW_OPTIONS,
    FONT_SIZE_OPTIONS,
    LAYOUT_OPTIONS,
    THEME_CATEGORIES,
    THEME_OPTIONS,
)

# Layout choices intentionally exposed in Settings. Legacy layout code remains
# available for compatibility with existing saved settings, but is not shown.
VISIBLE_LAYOUT_KEYS = ("default", "modern_studio", "top_nav", "slim_sidebar", "liquid_glass")


class VisualThemeModeCard(QFrame):
    """Sleek window wireframe card simulating system (split), light, and dark modes."""

    clicked = Signal(str)

    def __init__(self, mode_id: str, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mode_id = mode_id
        self.setObjectName("VisualThemeTile")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedWidth(210)
        self.setFixedHeight(144)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(8)

        mockup = QFrame()
        mockup.setFixedHeight(92)
        mock_layout = QHBoxLayout(mockup)
        mock_layout.setContentsMargins(0, 0, 0, 0)
        mock_layout.setSpacing(0)

        if mode_id == "system":
            left = QFrame()
            left.setStyleSheet(
                "background: #F1F5F9; border-top-left-radius: 8px; border-bottom-left-radius: 8px; "
                "border: 1px solid #CBD5E1; border-right: none;"
            )
            left_l = QVBoxLayout(left)
            left_l.setContentsMargins(8, 6, 4, 6)
            left_l.setSpacing(4)
            h_bar = QFrame()
            h_bar.setFixedHeight(8)
            h_bar.setStyleSheet("background: #94A3B8; border-radius: 3px; max-width: 65px;")

            canvas_l = QFrame()
            canvas_l.setStyleSheet("background: #FFFFFF; border-top-left-radius: 4px; border: 1px solid #E2E8F0; border-right: none;")
            can_layout = QVBoxLayout(canvas_l)
            can_layout.setContentsMargins(6, 6, 2, 6)
            can_layout.setSpacing(3)
            l1 = QFrame()
            l1.setFixedHeight(4)
            l1.setStyleSheet("background: #64748B; border-radius: 2px;")
            l2 = QFrame()
            l2.setFixedHeight(3)
            l2.setStyleSheet("background: #CBD5E1; border-radius: 1px;")
            l3 = QFrame()
            l3.setFixedHeight(3)
            l3.setStyleSheet("background: #E2E8F0; border-radius: 1px;")
            can_layout.addWidget(l1)
            can_layout.addWidget(l2)
            can_layout.addWidget(l3)
            can_layout.addStretch(1)

            left_l.addWidget(h_bar, 0, Qt.AlignHCenter)
            left_l.addWidget(canvas_l, 1)

            right = QFrame()
            right.setStyleSheet(
                "background: #1E293B; border-top-right-radius: 8px; border-bottom-right-radius: 8px; "
                "border: 1px solid #333842; border-left: none;"
            )
            right_l = QVBoxLayout(right)
            right_l.setContentsMargins(4, 6, 8, 6)
            right_l.setSpacing(4)
            rh_bar = QFrame()
            rh_bar.setFixedHeight(8)
            rh_bar.setStyleSheet("background: #475569; border-radius: 3px; max-width: 65px;")

            canvas_r = QFrame()
            canvas_r.setStyleSheet("background: #0F172A; border-top-right-radius: 4px; border: 1px solid #1E293B; border-left: none;")
            can_r_layout = QVBoxLayout(canvas_r)
            can_r_layout.setContentsMargins(2, 6, 6, 6)
            can_r_layout.setSpacing(3)
            rl1 = QFrame()
            rl1.setFixedHeight(4)
            rl1.setStyleSheet("background: #94A3B8; border-radius: 2px;")
            rl2 = QFrame()
            rl2.setFixedHeight(3)
            rl2.setStyleSheet("background: #475569; border-radius: 1px;")
            rl3 = QFrame()
            rl3.setFixedHeight(3)
            rl3.setStyleSheet("background: #334155; border-radius: 1px;")
            can_r_layout.addWidget(rl1)
            can_r_layout.addWidget(rl2)
            can_r_layout.addWidget(rl3)
            can_r_layout.addStretch(1)

            right_l.addWidget(rh_bar, 0, Qt.AlignHCenter)
            right_l.addWidget(canvas_r, 1)

            mock_layout.addWidget(left, 1)
            mock_layout.addWidget(right, 1)

        elif mode_id == "light":
            surf = QFrame()
            surf.setStyleSheet("background: #F1F5F9; border-radius: 8px; border: 1px solid #CBD5E1;")
            surf_l = QVBoxLayout(surf)
            surf_l.setContentsMargins(10, 6, 10, 6)
            surf_l.setSpacing(5)

            h_bar = QFrame()
            h_bar.setFixedHeight(8)
            h_bar.setStyleSheet("background: #94A3B8; border-radius: 3px; max-width: 80px;")

            canvas = QFrame()
            canvas.setStyleSheet("background: #FFFFFF; border-radius: 4px; border: 1px solid #E2E8F0;")
            can_l = QVBoxLayout(canvas)
            can_l.setContentsMargins(8, 6, 8, 6)
            can_l.setSpacing(4)
            l1 = QFrame()
            l1.setFixedHeight(5)
            l1.setStyleSheet("background: #64748B; border-radius: 2px; max-width: 70px;")
            l2 = QFrame()
            l2.setFixedHeight(3)
            l2.setStyleSheet("background: #CBD5E1; border-radius: 1px;")
            l3 = QFrame()
            l3.setFixedHeight(3)
            l3.setStyleSheet("background: #E2E8F0; border-radius: 1px;")
            can_l.addWidget(l1)
            can_l.addWidget(l2)
            can_l.addWidget(l3)
            can_l.addStretch(1)

            surf_l.addWidget(h_bar, 0, Qt.AlignHCenter)
            surf_l.addWidget(canvas, 1)
            mock_layout.addWidget(surf)

        else:  # dark
            surf = QFrame()
            surf.setStyleSheet("background: #1E293B; border-radius: 8px; border: 1px solid #333842;")
            surf_l = QVBoxLayout(surf)
            surf_l.setContentsMargins(10, 6, 10, 6)
            surf_l.setSpacing(5)

            h_bar = QFrame()
            h_bar.setFixedHeight(8)
            h_bar.setStyleSheet("background: #475569; border-radius: 3px; max-width: 80px;")

            canvas = QFrame()
            canvas.setStyleSheet("background: #0F172A; border-radius: 4px; border: 1px solid #334155;")
            can_l = QVBoxLayout(canvas)
            can_l.setContentsMargins(8, 6, 8, 6)
            can_l.setSpacing(4)
            l1 = QFrame()
            l1.setFixedHeight(5)
            l1.setStyleSheet("background: #94A3B8; border-radius: 2px; max-width: 70px;")
            l2 = QFrame()
            l2.setFixedHeight(3)
            l2.setStyleSheet("background: #475569; border-radius: 1px;")
            l3 = QFrame()
            l3.setFixedHeight(3)
            l3.setStyleSheet("background: #334155; border-radius: 1px;")
            can_l.addWidget(l1)
            can_l.addWidget(l2)
            can_l.addWidget(l3)
            can_l.addStretch(1)

            surf_l.addWidget(h_bar, 0, Qt.AlignHCenter)
            surf_l.addWidget(canvas, 1)
            mock_layout.addWidget(surf)

        layout.addWidget(mockup)

        bot_row = QHBoxLayout()
        bot_row.setContentsMargins(0, 0, 0, 0)
        bot_row.setSpacing(6)
        bot_row.setAlignment(Qt.AlignCenter)

        self.radio_dot = QFrame()
        self.radio_dot.setFixedSize(14, 14)
        self.label = QLabel(title)
        self.label.setObjectName("VisualThemeLabel")

        bot_row.addWidget(self.radio_dot)
        bot_row.addWidget(self.label)
        layout.addLayout(bot_row)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.mode_id)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        if hasattr(self, "radio_dot"):
            if selected:
                self.radio_dot.setStyleSheet(
                    "background: #C46A93; border: 3px solid #FFFFFF; border-radius: 7px; min-width: 14px; min-height: 14px;"
                )
            else:
                self.radio_dot.setStyleSheet(
                    "background: transparent; border: 2px solid #CBD5E1; border-radius: 7px; min-width: 14px; min-height: 14px;"
                )
        self.style().unpolish(self)
        self.style().polish(self)


class VisualLayoutCard(QFrame):
    """Layout selection card featuring a miniature layout mockup and badge tag."""

    clicked = Signal(str)

    def __init__(self, layout_id: str, title: str, description: str, badge_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.layout_id = layout_id
        self.setObjectName("LayoutTile")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(96)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 14, 10)
        layout.setSpacing(14)

        preview = QFrame()
        preview.setFixedSize(76, 68)
        preview.setStyleSheet("background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px;")
        prev_l = QHBoxLayout(preview)
        prev_l.setContentsMargins(4, 4, 4, 4)
        prev_l.setSpacing(4)

        if layout_id == "default":
            side = QFrame()
            side.setFixedWidth(18)
            side.setStyleSheet("background: #C46A93; border-radius: 3px;")
            main = QFrame()
            main_l = QVBoxLayout(main)
            main_l.setContentsMargins(2, 2, 2, 2)
            main_l.setSpacing(3)
            c1 = QFrame()
            c1.setStyleSheet("background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 2px;")
            c2 = QFrame()
            c2.setStyleSheet("background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 2px;")
            main_l.addWidget(c1)
            main_l.addWidget(c2)
            prev_l.addWidget(side)
            prev_l.addWidget(main, 1)

        elif layout_id == "macos_glass":
            main = QFrame()
            main.setStyleSheet(
                "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #08214D, stop:0.5 #0077B6, stop:1 #38BDF8); "
                "border-radius: 6px;"
            )
            main_l = QVBoxLayout(main)
            main_l.setContentsMargins(4, 4, 4, 4)
            main_l.setSpacing(3)

            # Top floating pill with Apple traffic lights
            traffic = QFrame()
            traffic.setFixedHeight(8)
            traffic.setStyleSheet("background: rgba(255, 255, 255, 0.25); border-radius: 4px; border: 0.5px solid rgba(255, 255, 255, 0.5);")
            tr_l = QHBoxLayout(traffic)
            tr_l.setContentsMargins(3, 0, 3, 0)
            tr_l.setSpacing(2)
            for col in ("#FF5F56", "#FFBD2E", "#27C93F"):
                dot = QFrame()
                dot.setFixedSize(3, 3)
                dot.setStyleSheet(f"background: {col}; border-radius: 1.5px;")
                tr_l.addWidget(dot)
            tr_l.addStretch(1)

            # Content grid: 2 modular liquid glass capsules (pill + slider)
            grid = QFrame()
            grid_l = QHBoxLayout(grid)
            grid_l.setContentsMargins(0, 0, 0, 0)
            grid_l.setSpacing(3)

            # Left capsule: Wi-Fi pill with white circle
            m1 = QFrame()
            m1.setStyleSheet("background: rgba(255, 255, 255, 0.28); border-radius: 5px; border: 0.5px solid rgba(255, 255, 255, 0.6);")
            m1_l = QHBoxLayout(m1)
            m1_l.setContentsMargins(3, 3, 3, 3)
            w_circle = QFrame()
            w_circle.setFixedSize(8, 8)
            w_circle.setStyleSheet("background: #FFFFFF; border-radius: 4px;")
            m1_l.addWidget(w_circle)
            m1_l.addStretch(1)

            # Right capsule: slider bar
            m2 = QFrame()
            m2.setStyleSheet("background: rgba(255, 255, 255, 0.28); border-radius: 5px; border: 0.5px solid rgba(255, 255, 255, 0.6);")
            m2_l = QVBoxLayout(m2)
            m2_l.setContentsMargins(4, 4, 4, 4)
            bar = QFrame()
            bar.setFixedHeight(3)
            bar.setStyleSheet("background: #FFFFFF; border-radius: 1.5px;")
            m2_l.addWidget(bar)

            grid_l.addWidget(m1, 1)
            grid_l.addWidget(m2, 1)

            main_l.addWidget(traffic)
            main_l.addWidget(grid, 1)
            prev_l.addWidget(main, 1)

        elif layout_id == "modern_studio":
            side = QFrame()
            side.setFixedWidth(16)
            side.setStyleSheet("background: #334155; border-radius: 2px;")
            main = QFrame()
            main_l = QVBoxLayout(main)
            main_l.setContentsMargins(2, 2, 2, 2)
            main_l.setSpacing(3)
            top = QFrame()
            top.setFixedHeight(6)
            top.setStyleSheet("background: #CBD5E1; border-radius: 2px;")
            c1 = QFrame()
            c1.setStyleSheet("background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 2px;")
            main_l.addWidget(top)
            main_l.addWidget(c1, 1)
            prev_l.addWidget(side)
            prev_l.addWidget(main, 1)

        elif layout_id == "top_nav":
            main = QFrame()
            main_l = QVBoxLayout(main)
            main_l.setContentsMargins(1, 1, 1, 1)
            main_l.setSpacing(3)
            top_bar = QFrame()
            top_bar.setFixedHeight(8)
            top_bar.setStyleSheet("background: #0284C7; border-radius: 2px;")
            cards_row = QFrame()
            cr_l = QHBoxLayout(cards_row)
            cr_l.setContentsMargins(0, 0, 0, 0)
            cr_l.setSpacing(2)
            c1 = QFrame()
            c1.setStyleSheet("background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 2px;")
            c2 = QFrame()
            c2.setStyleSheet("background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 2px;")
            cr_l.addWidget(c1, 1)
            cr_l.addWidget(c2, 1)
            main_l.addWidget(top_bar)
            main_l.addWidget(cards_row, 1)
            prev_l.addWidget(main, 1)

        elif layout_id == "executive":
            side = QFrame()
            side.setFixedWidth(16)
            side.setStyleSheet("background: #1E3A8A; border-radius: 2px;")
            main = QFrame()
            main_l = QVBoxLayout(main)
            main_l.setContentsMargins(2, 2, 2, 2)
            main_l.setSpacing(3)
            kpi_row = QFrame()
            kr_l = QHBoxLayout(kpi_row)
            kr_l.setContentsMargins(0, 0, 0, 0)
            kr_l.setSpacing(2)
            for _ in range(3):
                k = QFrame()
                k.setFixedHeight(12)
                k.setStyleSheet("background: #E0E7FF; border: 1px solid #C7D2FE; border-radius: 2px;")
                kr_l.addWidget(k, 1)
            card = QFrame()
            card.setStyleSheet("background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 2px;")
            main_l.addWidget(kpi_row)
            main_l.addWidget(card, 1)
            prev_l.addWidget(side)
            prev_l.addWidget(main, 1)

        elif layout_id == "slim_sidebar":
            side = QFrame()
            side.setFixedWidth(7)
            side.setStyleSheet("background: #0F172A; border-radius: 2px;")
            main = QFrame()
            main_l = QVBoxLayout(main)
            main_l.setContentsMargins(2, 2, 2, 2)
            main_l.setSpacing(3)
            c1 = QFrame()
            c1.setStyleSheet("background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 2px;")
            c2 = QFrame()
            c2.setStyleSheet("background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 2px;")
            main_l.addWidget(c1)
            main_l.addWidget(c2)
            prev_l.addWidget(side)
            prev_l.addWidget(main, 1)

        elif layout_id == "centered_focus":
            main = QFrame()
            main_l = QVBoxLayout(main)
            main_l.setContentsMargins(6, 2, 6, 2)
            main_l.setSpacing(3)
            bar = QFrame()
            bar.setFixedHeight(8)
            bar.setStyleSheet("background: #E2E8F0; border-radius: 4px; border: 1px solid #CBD5E1;")
            card = QFrame()
            card.setStyleSheet("background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 4px;")
            main_l.addWidget(bar)
            main_l.addWidget(card, 1)
            prev_l.addWidget(main, 1)

        elif layout_id == "dock_bottom":
            main = QFrame()
            main_l = QVBoxLayout(main)
            main_l.setContentsMargins(2, 2, 2, 2)
            main_l.setSpacing(3)
            card = QFrame()
            card.setStyleSheet("background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 3px;")
            dock = QFrame()
            dock.setFixedHeight(8)
            dock.setStyleSheet("background: #334155; border-radius: 4px;")
            main_l.addWidget(card, 1)
            main_l.addWidget(dock, 0, Qt.AlignHCenter)
            prev_l.addWidget(main, 1)

        elif layout_id == "dual_sidebar":
            rail = QFrame()
            rail.setFixedWidth(6)
            rail.setStyleSheet("background: #0F172A; border-radius: 1px;")
            sub = QFrame()
            sub.setFixedWidth(14)
            sub.setStyleSheet("background: #E2E8F0; border-radius: 2px;")
            card = QFrame()
            card.setStyleSheet("background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 2px;")
            prev_l.addWidget(rail)
            prev_l.addWidget(sub)
            prev_l.addWidget(card, 1)

        elif layout_id == "bento_grid":
            main = QFrame()
            main_l = QGridLayout(main)
            main_l.setContentsMargins(1, 1, 1, 1)
            main_l.setSpacing(2)
            for r in range(2):
                for c in range(2):
                    b = QFrame()
                    b.setStyleSheet("background: #EDE9FE; border: 1px solid #DDD6FE; border-radius: 3px;")
                    main_l.addWidget(b, r, c)
            prev_l.addWidget(main, 1)

        elif layout_id == "cyber_hud":
            main = QFrame()
            main_l = QVBoxLayout(main)
            main_l.setContentsMargins(2, 2, 2, 2)
            main_l.setSpacing(2)
            c = QFrame()
            c.setStyleSheet("background: #0D1117; border: 1.5px solid #00F2FE; border-radius: 2px;")
            main_l.addWidget(c, 1)
            prev_l.addWidget(main, 1)

        elif layout_id == "nordic_frost":
            side = QFrame()
            side.setFixedWidth(16)
            side.setStyleSheet("background: #0284C7; border-radius: 4px;")
            card = QFrame()
            card.setStyleSheet("background: #F0F9FF; border: 1px solid #BAE6FD; border-radius: 4px;")
            prev_l.addWidget(side)
            prev_l.addWidget(card, 1)

        else:
            side = QFrame()
            side.setFixedWidth(16)
            side.setStyleSheet("background: #8B5CF6; border-radius: 4px;")
            main = QFrame()
            main_l = QVBoxLayout(main)
            main_l.setContentsMargins(2, 2, 2, 2)
            main_l.setSpacing(3)
            c1 = QFrame()
            c1.setStyleSheet("background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 3px;")
            c2 = QFrame()
            c2.setStyleSheet("background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 3px;")
            main_l.addWidget(c1)
            main_l.addWidget(c2)
            prev_l.addWidget(side)
            prev_l.addWidget(main, 1)

        layout.addWidget(preview)

        info_l = QVBoxLayout()
        info_l.setContentsMargins(0, 0, 0, 0)
        info_l.setSpacing(3)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("LayoutTileTitle")
        self.badge_lbl = QLabel(badge_text)
        self.badge_lbl.setStyleSheet(
            "font-size: 10px; font-weight: 700; color: #64748B; background: #F1F5F9; border-radius: 4px; padding: 2px 6px;"
        )
        self.check_icon = QLabel("")
        self.check_icon.setStyleSheet("font-size: 14px; font-weight: 900; color: #C46A93;")
        title_row.addWidget(self.title_lbl)
        title_row.addWidget(self.badge_lbl)
        title_row.addStretch(1)
        title_row.addWidget(self.check_icon)

        self.desc_lbl = QLabel(description)
        self.desc_lbl.setObjectName("LayoutTileDesc")
        self.desc_lbl.setWordWrap(True)

        info_l.addLayout(title_row)
        info_l.addWidget(self.desc_lbl)
        layout.addLayout(info_l, 1)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.layout_id)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.check_icon.setText("✓" if selected else "")
        self.style().unpolish(self)
        self.style().polish(self)


class ColorChipCard(QFrame):
    """Modern interactive color chip with circular swatch, checkmark, label and hex code."""

    clicked = Signal(str)

    def __init__(self, theme_id: str, name: str, hex_color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.theme_id = theme_id
        self.hex_color = hex_color
        self.setObjectName("ColorChipCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(50)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 12, 6)
        layout.setSpacing(10)

        self.swatch = QFrame()
        self.swatch.setFixedSize(26, 26)
        swatch_l = QVBoxLayout(self.swatch)
        swatch_l.setContentsMargins(0, 0, 0, 0)
        swatch_l.setAlignment(Qt.AlignCenter)
        self.check_lbl = QLabel("")
        self.check_lbl.setObjectName("ColorChipCheck")
        self.check_lbl.setAlignment(Qt.AlignCenter)
        swatch_l.addWidget(self.check_lbl)
        layout.addWidget(self.swatch)

        text_l = QVBoxLayout()
        text_l.setContentsMargins(0, 0, 0, 0)
        text_l.setSpacing(1)
        self.name_lbl = QLabel(name)
        self.name_lbl.setObjectName("ColorChipName")
        self.hex_lbl = QLabel(hex_color)
        self.hex_lbl.setObjectName("ColorChipHex")
        text_l.addWidget(self.name_lbl)
        text_l.addWidget(self.hex_lbl)
        layout.addLayout(text_l, 1)

        self._update_swatch(False)

    def _update_swatch(self, selected: bool) -> None:
        self.swatch.setStyleSheet(
            f"background: {self.hex_color}; border: 2px solid {'rgba(0,0,0,0.25)' if selected else 'rgba(0,0,0,0.12)'}; border-radius: 13px;"
        )
        self.check_lbl.setText("✓" if selected else "")

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.theme_id)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self._update_swatch(selected)
        self.style().unpolish(self)
        self.style().polish(self)


class SettingsView(QWidget):
    """Application settings view with multi-layout, visual effects, and real-time preview."""

    theme_preview_changed = Signal(str, int, str, str, str, str, bool, str, bool, str, bool, bool)
    save_requested = Signal()
    cancel_requested = Signal()

    _PAGES = (
        ("general", "Chung"),
        ("appearance", "Giao diện"),
        ("storage", "Nơi lưu trữ"),
        ("pets", "Thú cưng"),
        ("background_music", "Nhạc nền"),
        ("ai", "AI"),
        ("about", "Giới thiệu"),
    )

    def __init__(
        self,
        selected_theme: str,
        color_strength: int = 100,
        appearance_mode: str = "light",
        export_root: Path | None = None,
        selected_layout: str = "default",
        font_size: str = "medium",
        border_radius: str = "rounded",
        high_contrast: bool = False,
        custom_color: str = "",
        animations_enabled: bool = True,
        card_shadow: str = "subtle",
        hover_glow: bool = True,
        glassmorphism: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SettingsView")

        self._selected_export_root = Path(export_root or Path.home() / "Documents" / "Min Assistant")
        self._selected_mode = appearance_mode
        self._selected_layout = selected_layout if selected_layout in VISIBLE_LAYOUT_KEYS else "default"
        self._selected_font_size = font_size if font_size in FONT_SIZE_OPTIONS else "medium"
        self._selected_border_radius = border_radius if border_radius in BORDER_RADIUS_OPTIONS else "rounded"
        self._selected_high_contrast = high_contrast
        self._custom_color = custom_color.upper() if custom_color else ""
        self._current_theme_id = selected_theme if (selected_theme in THEME_OPTIONS or selected_theme == "custom") else "rose"
        self._selected_animations_enabled = animations_enabled
        self._selected_card_shadow = card_shadow if card_shadow in EFFECT_SHADOW_OPTIONS else "subtle"
        self._selected_hover_glow = hover_glow
        self._selected_glassmorphism = glassmorphism

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

        reset_btn = QPushButton("↺ Đặt lại mặc định (Hồng)")
        reset_btn.setObjectName("SettingsResetButton")
        reset_btn.setToolTip("Khôi phục toàn bộ giao diện về màu Hồng mặc định")
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.clicked.connect(self._reset_to_default_theme)
        footer_layout.addWidget(reset_btn)

        footer_layout.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        buttons.button(QDialogButtonBox.Save).setText("Lưu thay đổi")
        buttons.button(QDialogButtonBox.Cancel).setText("Hủy")
        buttons.button(QDialogButtonBox.Save).clicked.connect(self.save_requested.emit)
        buttons.button(QDialogButtonBox.Cancel).clicked.connect(self.cancel_requested.emit)
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
        back.clicked.connect(self.cancel_requested.emit)
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
        builders = {
            "general": self._build_general_page,
            "appearance": lambda: self._build_appearance_page(selected_theme, color_strength, appearance_mode),
            "storage": self._build_storage_page,
            "pets": lambda: self._build_development_page("Thú cưng"),
            "background_music": lambda: self._build_development_page("Nhạc nền"),
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
        layout.setContentsMargins(36, 26, 36, 36)
        layout.setSpacing(18)
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
            "Sao lưu dữ liệu định kỳ để dễ khôi phục khi cần.",
        ))
        layout.addWidget(self._setting_card(
            "Giao diện",
            "Thay đổi màu sắc, độ đậm màu và chế độ sáng/tối.",
            "Chọn mục Giao diện ở thanh bên để tùy chỉnh.",
        ))
        layout.addStretch(1)
        return page

    def _build_appearance_page(self, selected_theme: str, color_strength: int, appearance_mode: str) -> QWidget:
        page, layout = self._page_shell(
            "Giao diện",
            "Chọn chế độ sáng/tối, phong cách bố cục và thư viện bảng màu sắc hiển thị.",
        )

        # 1. Chế độ hiển thị (System, Light, Dark)
        mode_title = QLabel("Chế độ hiển thị")
        mode_title.setObjectName("SettingsSectionTitle")
        layout.addWidget(mode_title)

        modes_box = QFrame()
        modes_box.setObjectName("AppearanceModeGroup")
        modes_layout = QHBoxLayout(modes_box)
        modes_layout.setContentsMargins(0, 0, 0, 0)
        modes_layout.setSpacing(16)

        self.visual_mode_cards: dict[str, VisualThemeModeCard] = {}
        for m_id, m_label in (("system", "Hệ thống"), ("light", "Sáng"), ("dark", "Tối")):
            card = VisualThemeModeCard(m_id, m_label)
            card.set_selected(m_id == self._selected_mode)
            card.clicked.connect(self._on_mode_card_clicked)
            self.visual_mode_cards[m_id] = card
            modes_layout.addWidget(card)
        modes_layout.addStretch(1)
        layout.addWidget(modes_box)

        # 2. Bộ bố cục giao diện (Layout)
        layout_title = QLabel("Bộ bố cục giao diện (Layout)")
        layout_title.setObjectName("SettingsSectionTitle")
        layout.addWidget(layout_title)

        layout_grid = QGridLayout()
        layout_grid.setHorizontalSpacing(14)
        layout_grid.setVerticalSpacing(12)
        self.layout_tiles: dict[str, VisualLayoutCard] = {}

        badges = {
            "default": "Classic",
            "macos_glass": "Apple Glass 26",
            "modern_studio": "Studio IDE",
            "top_nav": "Horizon",
            "executive": "Executive",
            "slim_sidebar": "Minimal",
            "centered_focus": "Focus Canvas",
            "vibrant": "Creative",
            "dock_bottom": "macOS Dock",
            "dual_sidebar": "Dual Pro",
            "bento_grid": "Bento Grid",
            "glass_morphism": "Frosted Glass",
            "minimal_zen": "Zen Paper",
            "cyber_hud": "Cyber Neon",
            "split_workspace": "Studio Split",
            "feed_stream": "Feed Stream",
            "compact_dense": "Enterprise",
            "nordic_frost": "Nordic Ice",
        }

        for index, l_key in enumerate(VISIBLE_LAYOUT_KEYS):
            l_info = LAYOUT_OPTIONS[l_key]
            card = VisualLayoutCard(
                layout_id=l_key,
                title=l_info["title"],
                description=l_info["description"],
                badge_text=badges.get(l_key, "Tùy biến"),
            )
            card.set_selected(l_key == self._selected_layout)
            card.clicked.connect(self._on_layout_tile_clicked)
            self.layout_tiles[l_key] = card
            layout_grid.addWidget(card, index // 2, index % 2)

        layout.addLayout(layout_grid)

        # 3. Bảng màu chủ đạo (Color Palettes)
        colors_title = QLabel("Bảng màu chủ đạo (22+ Bảng màu)")
        colors_title.setObjectName("SettingsSectionTitle")
        layout.addWidget(colors_title)

        cat_row = QHBoxLayout()
        cat_row.setSpacing(8)
        self.category_tabs: dict[str, QPushButton] = {}
        for cat_id, cat_name in THEME_CATEGORIES.items():
            btn = QPushButton(cat_name)
            btn.setObjectName("ColorCategoryTab")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("active", cat_id == "all")
            btn.clicked.connect(lambda checked=False, c=cat_id: self._filter_color_category(c))
            self.category_tabs[cat_id] = btn
            cat_row.addWidget(btn)

        cat_row.addStretch(1)

        self.custom_color_btn = QPushButton("🎨 Chọn màu tự do...")
        self.custom_color_btn.setObjectName("GhostButton")
        self.custom_color_btn.setCursor(Qt.PointingHandCursor)
        self.custom_color_btn.clicked.connect(self._choose_custom_color)
        cat_row.addWidget(self.custom_color_btn)

        layout.addLayout(cat_row)

        color_card = QFrame()
        color_card.setObjectName("SettingsCard")
        self.color_grid = QGridLayout(color_card)
        self.color_grid.setContentsMargins(16, 14, 16, 14)
        self.color_grid.setHorizontalSpacing(12)
        self.color_grid.setVerticalSpacing(10)

        self.color_chips: dict[str, ColorChipCard] = {}

        if self._custom_color:
            c_chip = ColorChipCard("custom", "Tùy chọn", self._custom_color)
            c_chip.set_selected(self._current_theme_id == "custom")
            c_chip.clicked.connect(self._on_color_chip_clicked)
            self.color_chips["custom"] = c_chip

        for index, (theme_id, theme) in enumerate(THEME_OPTIONS.items()):
            chip = ColorChipCard(theme_id, theme["label"], theme["color"])
            chip.set_selected(theme_id == self._current_theme_id)
            chip.clicked.connect(self._on_color_chip_clicked)
            self.color_chips[theme_id] = chip
            self.color_grid.addWidget(chip, index // 4, index % 4)

        layout.addWidget(color_card)

        # 4. Color Strength Slider
        strength_title = QLabel("Độ đậm màu")
        strength_title.setObjectName("SettingsSectionTitle")
        layout.addWidget(strength_title)

        strength_card = QFrame()
        strength_card.setObjectName("SettingsCard")
        strength_layout = QVBoxLayout(strength_card)
        strength_layout.setContentsMargins(20, 16, 20, 16)
        strength_header = QHBoxLayout()
        strength_description = QLabel("Tùy chỉnh sắc độ bảng màu giao diện nhạt hoặc đậm hơn")
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
        lighter, darker = QLabel("Nhạt (60%)"), QLabel("Đậm (140%)")
        lighter.setObjectName("SettingsHint")
        darker.setObjectName("SettingsHint")
        scale.addWidget(lighter)
        scale.addStretch(1)
        scale.addWidget(darker)
        strength_layout.addLayout(scale)
        layout.addWidget(strength_card)
        self._update_strength_label()

        # 5. Detailed Typography & Controls
        detail_title = QLabel("Tỷ lệ và góc bo giao diện")
        detail_title.setObjectName("SettingsSectionTitle")
        layout.addWidget(detail_title)

        detail_card = QFrame()
        detail_card.setObjectName("SettingsCard")
        detail_l = QVBoxLayout(detail_card)
        detail_l.setContentsMargins(20, 18, 20, 18)
        detail_l.setSpacing(14)

        # Font size row
        font_row = QHBoxLayout()
        font_lbl = QLabel("Cỡ chữ hiển thị:")
        font_lbl.setObjectName("SettingsItemTitle")
        font_row.addWidget(font_lbl)
        font_row.addSpacing(16)

        self.font_buttons: dict[str, QPushButton] = {}
        for f_key, f_info in FONT_SIZE_OPTIONS.items():
            btn = QPushButton(f_info["label"])
            btn.setObjectName("ColorCategoryTab")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("active", f_key == self._selected_font_size)
            btn.clicked.connect(lambda checked=False, k=f_key: self._on_font_size_clicked(k))
            self.font_buttons[f_key] = btn
            font_row.addWidget(btn)
        font_row.addStretch(1)
        detail_l.addLayout(font_row)

        # Border radius row
        radius_row = QHBoxLayout()
        radius_lbl = QLabel("Phong cách góc bo:")
        radius_lbl.setObjectName("SettingsItemTitle")
        radius_row.addWidget(radius_lbl)
        radius_row.addSpacing(16)

        self.radius_buttons: dict[str, QPushButton] = {}
        for r_key, r_info in BORDER_RADIUS_OPTIONS.items():
            btn = QPushButton(r_info["label"])
            btn.setObjectName("ColorCategoryTab")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("active", r_key == self._selected_border_radius)
            btn.clicked.connect(lambda checked=False, k=r_key: self._on_border_radius_clicked(k))
            self.radius_buttons[r_key] = btn
            radius_row.addWidget(btn)
        radius_row.addStretch(1)
        detail_l.addLayout(radius_row)

        # High contrast checkbox
        self.contrast_checkbox = QCheckBox("Bật chế độ tương phản cao (High Contrast)")
        self.contrast_checkbox.setStyleSheet("font-size: 13px; font-weight: 600; padding: 4px 0;")
        self.contrast_checkbox.setChecked(self._selected_high_contrast)
        self.contrast_checkbox.toggled.connect(self._on_contrast_toggled)
        detail_l.addWidget(self.contrast_checkbox)

        # Visual effects section
        fx_title = QLabel("Hiệu ứng & Tương tác (Visual Effects)")
        fx_title.setObjectName("SettingsItemTitle")
        fx_title.setStyleSheet("margin-top: 10px; font-weight: 700;")
        detail_l.addWidget(fx_title)

        self.animation_checkbox = QCheckBox("Bật hiệu ứng chuyển động mượt mà (Animations & Transitions)")
        self.animation_checkbox.setStyleSheet("font-size: 13px; font-weight: 600; padding: 3px 0;")
        self.animation_checkbox.setChecked(self._selected_animations_enabled)
        self.animation_checkbox.toggled.connect(self._on_animations_toggled)
        detail_l.addWidget(self.animation_checkbox)

        self.hover_glow_checkbox = QCheckBox("Hiệu ứng phát sáng viền khi rê chuột (Glow Accent Hover)")
        self.hover_glow_checkbox.setStyleSheet("font-size: 13px; font-weight: 600; padding: 3px 0;")
        self.hover_glow_checkbox.setChecked(self._selected_hover_glow)
        self.hover_glow_checkbox.toggled.connect(self._on_hover_glow_toggled)
        detail_l.addWidget(self.hover_glow_checkbox)

        self.glassmorphism_checkbox = QCheckBox("Bề mặt kính mờ bán trong suốt (Frosted Glass Surfaces)")
        self.glassmorphism_checkbox.setStyleSheet("font-size: 13px; font-weight: 600; padding: 3px 0;")
        self.glassmorphism_checkbox.setChecked(self._selected_glassmorphism)
        self.glassmorphism_checkbox.toggled.connect(self._on_glassmorphism_toggled)
        detail_l.addWidget(self.glassmorphism_checkbox)

        # Shadow options row
        shadow_row = QHBoxLayout()
        shadow_lbl = QLabel("Độ bóng thẻ:")
        shadow_lbl.setObjectName("SettingsItemTitle")
        shadow_row.addWidget(shadow_lbl)
        shadow_row.addSpacing(16)
        self.shadow_buttons: dict[str, QPushButton] = {}
        for s_key, s_info in EFFECT_SHADOW_OPTIONS.items():
            btn = QPushButton(s_info["label"])
            btn.setObjectName("ColorCategoryTab")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("active", s_key == self._selected_card_shadow)
            btn.clicked.connect(lambda checked=False, k=s_key: self._on_card_shadow_clicked(k))
            self.shadow_buttons[s_key] = btn
            shadow_row.addWidget(btn)
        shadow_row.addStretch(1)
        detail_l.addLayout(shadow_row)

        # Interactive live preview card for Visual Effects
        self.fx_preview_card = QFrame()
        self.fx_preview_card.setObjectName("FxPreviewCard")
        self.fx_preview_card.setCursor(Qt.PointingHandCursor)
        self.fx_preview_card.setFixedHeight(82)
        fx_p_layout = QHBoxLayout(self.fx_preview_card)
        fx_p_layout.setContentsMargins(18, 14, 18, 14)
        fx_p_layout.setSpacing(14)

        fx_p_icon = QLabel("✨")
        fx_p_icon.setStyleSheet("font-size: 26px;")
        fx_p_layout.addWidget(fx_p_icon)

        fx_p_text = QVBoxLayout()
        fx_p_text.setSpacing(3)
        self.fx_preview_title = QLabel("Thẻ xem trước hiệu ứng trực tiếp (Rê chuột vào đây để thử)")
        self.fx_preview_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #1E293B;")
        self.fx_preview_desc = QLabel("Đang thể hiện độ bóng, viền phát sáng và kính mờ")
        self.fx_preview_desc.setStyleSheet("font-size: 11.5px; color: #64748B;")
        fx_p_text.addWidget(self.fx_preview_title)
        fx_p_text.addWidget(self.fx_preview_desc)
        fx_p_layout.addLayout(fx_p_text, 1)

        self.fx_status_chip = QLabel("Floating Glow")
        self.fx_status_chip.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #475569; background: rgba(0,0,0,0.06); "
            "border-radius: 6px; padding: 4px 10px;"
        )
        fx_p_layout.addWidget(self.fx_status_chip)
        detail_l.addWidget(self.fx_preview_card)

        self._update_fx_preview()

        layout.addWidget(detail_card)
        layout.addStretch(1)
        return page

    def _build_storage_page(self) -> QWidget:
        page, layout = self._page_shell(
            "Nơi lưu trữ",
            "Chọn thư mục dùng để xuất các bộ hồ sơ Word.",
        )
        card = QFrame()
        card.setObjectName("SettingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(8)
        title = QLabel("Thư mục xuất Word")
        title.setObjectName("SettingsItemTitle")
        description = QLabel("Mỗi lần xuất hồ sơ, ứng dụng sẽ tạo thư mục hồ sơ và các bản Word tại đây.")
        description.setObjectName("SettingsItemDescription")
        description.setWordWrap(True)
        self.storage_path_label = QLabel()
        self.storage_path_label.setObjectName("SettingsStoragePath")
        self.storage_path_label.setWordWrap(True)
        choose_button = QPushButton("Chọn nơi lưu trữ")
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
        page, layout = self._page_shell(title, f"Thiết lập {title.casefold()} sẽ được bổ sung trong phiên bản sau.")
        layout.addWidget(self._setting_card(
            "Chức năng này đang được phát triển",
            "Mục này chưa có thiết lập sẵn sàng trong phiên bản hiện tại.",
            "Chúng tôi sẽ cập nhật khi chức năng hoàn thiện.",
        ))
        layout.addStretch(1)
        return page

    def _build_about_page(self) -> QWidget:
        page, layout = self._page_shell(
            "Giới thiệu",
            "Min Assistant là ứng dụng làm việc cục bộ, hỗ trợ quét QR CCCD, quản lý dữ liệu hồ sơ thành lập doanh nghiệp và xuất bộ biểu mẫu Word.",
        )
        layout.addWidget(self._setting_card(
            "Min Assistant",
            "Dữ liệu hồ sơ, profile và cài đặt được lưu trên máy của bạn.",
            f"Phiên bản hiện tại: v{__version__}",
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
            "Chọn nơi lưu hồ sơ Word",
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

    def _on_mode_card_clicked(self, mode_id: str) -> None:
        self._selected_mode = mode_id
        for m_key, card in self.visual_mode_cards.items():
            card.set_selected(m_key == mode_id)
        self._schedule_preview()

    def _on_layout_tile_clicked(self, layout_key: str) -> None:
        self._selected_layout = layout_key
        for l_key, card in self.layout_tiles.items():
            card.set_selected(l_key == layout_key)
        self._schedule_preview()

    def _on_color_chip_clicked(self, theme_id: str) -> None:
        self._current_theme_id = theme_id
        self._custom_color = ""
        for t_id, chip in self.color_chips.items():
            chip.set_selected(t_id == theme_id)
        self._schedule_preview()

    def _filter_color_category(self, category: str) -> None:
        for cat_id, btn in self.category_tabs.items():
            btn.setProperty("active", cat_id == category)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        for theme_id, chip in self.color_chips.items():
            if theme_id == "custom":
                chip.setVisible(bool(self._custom_color))
                continue
            theme = THEME_OPTIONS.get(theme_id, {})
            matches = (category == "all") or (theme.get("category") == category)
            chip.setVisible(matches)

    def _choose_custom_color(self) -> None:
        current = QColor(self._custom_color or "#C46A93")
        color = QColorDialog.getColor(current, self, "Chọn màu tùy chỉnh")
        if color.isValid():
            hex_color = color.name().upper()
            self._custom_color = hex_color
            self._current_theme_id = "custom"
            THEME_OPTIONS["custom"] = {"label": f"Tự chọn ({hex_color})", "color": hex_color, "category": "all"}

            for chip in self.color_chips.values():
                chip.set_selected(False)

            if "custom" in self.color_chips:
                self.color_chips["custom"].hex_color = hex_color
                self.color_chips["custom"].name_lbl.setText("Tùy chọn")
                self.color_chips["custom"].hex_lbl.setText(hex_color)
                self.color_chips["custom"].set_selected(True)
                self.color_chips["custom"].setVisible(True)
            self._schedule_preview()

    def _reset_to_default_theme(self) -> None:
        self._current_theme_id = "rose"
        self._color_strength = 100
        self._selected_mode = "light"
        self._selected_layout = "default"
        self._selected_font_size = "medium"
        self._selected_border_radius = "rounded"
        self._selected_high_contrast = False
        self._custom_color = ""

        # Update Visual Theme Mode cards
        if hasattr(self, "visual_mode_cards"):
            for m_id, card in self.visual_mode_cards.items():
                card.set_selected(m_id == "light")

        # Update Layout cards
        if hasattr(self, "layout_tiles"):
            for l_key, card in self.layout_tiles.items():
                card.set_selected(l_key == "default")

        # Update Color chips
        if hasattr(self, "color_chips"):
            for t_id, chip in self.color_chips.items():
                chip.set_selected(t_id == "rose")
            if "custom" in self.color_chips:
                self.color_chips["custom"].setVisible(False)

        # Reset category filter to "all"
        if hasattr(self, "category_tabs"):
            self._filter_color_category("all")

        # Reset strength slider
        if hasattr(self, "color_strength_slider"):
            self.color_strength_slider.blockSignals(True)
            self.color_strength_slider.setValue(100)
            self.color_strength_slider.blockSignals(False)
            self._update_strength_label()

        # Reset font buttons
        if hasattr(self, "font_buttons"):
            for f_key, btn in self.font_buttons.items():
                btn.setProperty("active", f_key == "medium")
                btn.style().unpolish(btn)
                btn.style().polish(btn)

        # Reset radius buttons
        if hasattr(self, "radius_buttons"):
            for r_key, btn in self.radius_buttons.items():
                btn.setProperty("active", r_key == "rounded")
                btn.style().unpolish(btn)
                btn.style().polish(btn)

        # Reset high contrast checkbox
        if hasattr(self, "contrast_checkbox"):
            self.contrast_checkbox.blockSignals(True)
            self.contrast_checkbox.setChecked(False)
            self.contrast_checkbox.blockSignals(False)

        # Reset visual effects
        self._selected_animations_enabled = True
        self._selected_card_shadow = "subtle"
        self._selected_hover_glow = True
        self._selected_glassmorphism = False

        if hasattr(self, "animation_checkbox"):
            self.animation_checkbox.blockSignals(True)
            self.animation_checkbox.setChecked(True)
            self.animation_checkbox.blockSignals(False)

        if hasattr(self, "hover_glow_checkbox"):
            self.hover_glow_checkbox.blockSignals(True)
            self.hover_glow_checkbox.setChecked(True)
            self.hover_glow_checkbox.blockSignals(False)

        if hasattr(self, "glassmorphism_checkbox"):
            self.glassmorphism_checkbox.blockSignals(True)
            self.glassmorphism_checkbox.setChecked(False)
            self.glassmorphism_checkbox.blockSignals(False)

        if hasattr(self, "shadow_buttons"):
            for s_key, btn in self.shadow_buttons.items():
                btn.setProperty("active", s_key == "subtle")
                btn.style().unpolish(btn)
                btn.style().polish(btn)

        self._emit_preview_now()

    def _on_font_size_clicked(self, font_key: str) -> None:
        self._selected_font_size = font_key
        for k, btn in self.font_buttons.items():
            btn.setProperty("active", k == font_key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._schedule_preview()

    def _on_border_radius_clicked(self, radius_key: str) -> None:
        self._selected_border_radius = radius_key
        for k, btn in self.radius_buttons.items():
            btn.setProperty("active", k == radius_key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._schedule_preview()

    def _on_contrast_toggled(self, checked: bool) -> None:
        self._selected_high_contrast = checked
        self._schedule_preview()

    def _update_fx_preview(self) -> None:
        if not hasattr(self, "fx_status_chip"):
            return
        shadow_labels = {
            "flat": "Phẳng (Flat)",
            "subtle": "Bóng nhẹ (Subtle)",
            "floating": "Bóng nổi 3D (Floating)",
        }
        shadow_txt = shadow_labels.get(self._selected_card_shadow, "Subtle")
        glow_txt = "Glow: Bật" if self._selected_hover_glow else "Glow: Tắt"
        glass_txt = "Kính mờ: Bật" if self._selected_glassmorphism else "Kính mờ: Tắt"
        self.fx_status_chip.setText(f"{shadow_txt} • {glow_txt} • {glass_txt}")

    def _on_animations_toggled(self, checked: bool) -> None:
        self._selected_animations_enabled = checked
        self._update_fx_preview()
        self._schedule_preview()

    def _on_hover_glow_toggled(self, checked: bool) -> None:
        self._selected_hover_glow = checked
        self._update_fx_preview()
        self._schedule_preview()

    def _on_glassmorphism_toggled(self, checked: bool) -> None:
        self._selected_glassmorphism = checked
        self._update_fx_preview()
        self._schedule_preview()

    def _on_card_shadow_clicked(self, shadow_key: str) -> None:
        self._selected_card_shadow = shadow_key
        for k, btn in self.shadow_buttons.items():
            btn.setProperty("active", k == shadow_key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._update_fx_preview()
        self._schedule_preview()

    def _update_strength_label(self) -> None:
        self.strength_value.setText(f"{self.color_strength_slider.value()}%")

    def _schedule_preview(self, *_args) -> None:
        self._update_strength_label()
        self._preview_timer.start()

    def _emit_preview_now(self, *_args) -> None:
        self._preview_timer.stop()
        self._update_strength_label()
        self.theme_preview_changed.emit(
            self.selected_theme(),
            self.selected_strength(),
            self.selected_appearance_mode(),
            self.selected_layout(),
            self.selected_font_size(),
            self.selected_border_radius(),
            self.selected_high_contrast(),
            self.selected_custom_color(),
            self.selected_animations_enabled(),
            self.selected_card_shadow(),
            self.selected_hover_glow(),
            self.selected_glassmorphism(),
        )

    def reload_settings(
        self,
        selected_theme: str,
        color_strength: int = 100,
        appearance_mode: str = "light",
        export_root: Path | None = None,
        selected_layout: str = "default",
        font_size: str = "medium",
        border_radius: str = "rounded",
        high_contrast: bool = False,
        custom_color: str = "",
        animations_enabled: bool = True,
        card_shadow: str = "subtle",
        hover_glow: bool = True,
        glassmorphism: bool = False,
    ) -> None:
        self._selected_export_root = Path(export_root or Path.home() / "Documents" / "Min Assistant")
        self._selected_mode = appearance_mode
        self._selected_layout = selected_layout if selected_layout in VISIBLE_LAYOUT_KEYS else "default"
        self._selected_font_size = font_size if font_size in FONT_SIZE_OPTIONS else "medium"
        self._selected_border_radius = border_radius if border_radius in BORDER_RADIUS_OPTIONS else "rounded"
        self._selected_high_contrast = high_contrast
        self._custom_color = custom_color.upper() if custom_color else ""
        self._current_theme_id = selected_theme if (selected_theme in THEME_OPTIONS or selected_theme == "custom") else "rose"
        self._selected_animations_enabled = animations_enabled
        self._selected_card_shadow = card_shadow if card_shadow in EFFECT_SHADOW_OPTIONS else "subtle"
        self._selected_hover_glow = hover_glow
        self._selected_glassmorphism = glassmorphism

        if hasattr(self, "visual_mode_cards"):
            for m_id, card in self.visual_mode_cards.items():
                card.set_selected(m_id == self._selected_mode)

        if hasattr(self, "layout_tiles"):
            for l_key, card in self.layout_tiles.items():
                card.set_selected(l_key == self._selected_layout)

        if hasattr(self, "color_chips"):
            for theme_id, chip in self.color_chips.items():
                chip.set_selected(theme_id == self._current_theme_id)

        if hasattr(self, "color_strength_slider"):
            self.color_strength_slider.blockSignals(True)
            self.color_strength_slider.setValue(color_strength)
            self.color_strength_slider.blockSignals(False)
            self._update_strength_label()

        if hasattr(self, "font_buttons"):
            for f_key, btn in self.font_buttons.items():
                btn.setProperty("active", f_key == self._selected_font_size)
                btn.style().unpolish(btn)
                btn.style().polish(btn)

        if hasattr(self, "radius_buttons"):
            for r_key, btn in self.radius_buttons.items():
                btn.setProperty("active", r_key == self._selected_border_radius)
                btn.style().unpolish(btn)
                btn.style().polish(btn)

        if hasattr(self, "contrast_checkbox"):
            self.contrast_checkbox.blockSignals(True)
            self.contrast_checkbox.setChecked(self._selected_high_contrast)
            self.contrast_checkbox.blockSignals(False)

        if hasattr(self, "animation_checkbox"):
            self.animation_checkbox.blockSignals(True)
            self.animation_checkbox.setChecked(self._selected_animations_enabled)
            self.animation_checkbox.blockSignals(False)

        if hasattr(self, "hover_glow_checkbox"):
            self.hover_glow_checkbox.blockSignals(True)
            self.hover_glow_checkbox.setChecked(self._selected_hover_glow)
            self.hover_glow_checkbox.blockSignals(False)

        if hasattr(self, "glassmorphism_checkbox"):
            self.glassmorphism_checkbox.blockSignals(True)
            self.glassmorphism_checkbox.setChecked(self._selected_glassmorphism)
            self.glassmorphism_checkbox.blockSignals(False)

        if hasattr(self, "shadow_buttons"):
            for s_key, btn in self.shadow_buttons.items():
                btn.setProperty("active", s_key == self._selected_card_shadow)
                btn.style().unpolish(btn)
                btn.style().polish(btn)

        self._update_storage_path_label()

    def selected_theme(self) -> str:
        if self._current_theme_id == "custom":
            return "custom"
        if hasattr(self, "color_chips"):
            for theme_id, chip in self.color_chips.items():
                if chip.property("selected"):
                    return theme_id
        return self._current_theme_id or "rose"

    def selected_accent_color(self) -> str:
        if self._current_theme_id == "custom" and self._custom_color:
            return self._custom_color
        theme = THEME_OPTIONS.get(self.selected_theme(), {})
        return str(theme.get("color", "#C46A93"))

    def selected_strength(self) -> int:
        return self.color_strength_slider.value()

    def selected_appearance_mode(self) -> str:
        return self._selected_mode

    def selected_export_root(self) -> Path:
        return self._selected_export_root

    def selected_layout(self) -> str:
        return self._selected_layout

    def selected_font_size(self) -> str:
        return self._selected_font_size

    def selected_border_radius(self) -> str:
        return self._selected_border_radius

    def selected_high_contrast(self) -> bool:
        return self._selected_high_contrast

    def selected_custom_color(self) -> str:
        return self._custom_color

    def selected_animations_enabled(self) -> bool:
        return getattr(self, "_selected_animations_enabled", True)

    def selected_card_shadow(self) -> str:
        return getattr(self, "_selected_card_shadow", "subtle")

    def selected_hover_glow(self) -> bool:
        return getattr(self, "_selected_hover_glow", True)

    def selected_glassmorphism(self) -> bool:
        return getattr(self, "_selected_glassmorphism", False)


class SettingsDialog(QDialog):
    """QDialog wrapper for SettingsView to maintain modal and unit test compatibility."""

    _PAGES = SettingsView._PAGES
    theme_preview_changed = Signal(str, int, str, str, str, str, bool, str, bool, str, bool, bool)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        self.setObjectName("SettingsDialog")
        self.setWindowTitle("Cài đặt ứng dụng")
        self.resize(1140, 760)
        self.setMinimumSize(920, 640)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.view = SettingsView(*args, **kwargs, parent=self)
        layout.addWidget(self.view)
        self.view.theme_preview_changed.connect(self.theme_preview_changed.emit)
        self.view.save_requested.connect(self.accept)
        self.view.cancel_requested.connect(self.reject)

    def selected_theme(self) -> str:
        return self.view.selected_theme()

    def selected_accent_color(self) -> str:
        return self.view.selected_accent_color()

    def selected_strength(self) -> int:
        return self.view.selected_strength()

    def selected_appearance_mode(self) -> str:
        return self.view.selected_appearance_mode()

    def selected_export_root(self) -> Path:
        return self.view.selected_export_root()

    def selected_layout(self) -> str:
        return self.view.selected_layout()

    def selected_font_size(self) -> str:
        return self.view.selected_font_size()

    def selected_border_radius(self) -> str:
        return self.view.selected_border_radius()

    def selected_high_contrast(self) -> bool:
        return self.view.selected_high_contrast()

    def selected_custom_color(self) -> str:
        return self.view.selected_custom_color()

    def selected_animations_enabled(self) -> bool:
        return self.view.selected_animations_enabled()

    def selected_card_shadow(self) -> str:
        return self.view.selected_card_shadow()

    def selected_hover_glow(self) -> bool:
        return self.view.selected_hover_glow()

    def selected_glassmorphism(self) -> bool:
        return self.view.selected_glassmorphism()

    def _reset_to_default_theme(self) -> None:
        self.view._reset_to_default_theme()

    def _select_category(self, category: str) -> None:
        self.view._select_category(category)

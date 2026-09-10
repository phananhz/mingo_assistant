from __future__ import annotations

from typing import TYPE_CHECKING
from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QPushButton, QWidget

if TYPE_CHECKING:
    pass

CARD_OBJECT_NAMES = {
    "Card",
    "CreateCard",
    "KpiCard",
    "KPICard",
    "VisualThemeTile",
    "LayoutTile",
    "ColorChipCard",
    "SummaryCard",
    "IndustryLookupPanel",
    "FxPreviewCard",
}

BUTTON_OBJECT_NAMES = {
    "PrimaryButton",
    "ModalCreateButton",
    "GhostButton",
}


class VisualEffectsManager(QObject):
    """Manages real-time elevation drop shadows, animated hover glows, and visual transitions."""

    def __init__(self, main_window: QWidget | None = None) -> None:
        super().__init__(main_window)
        self.main_window = main_window
        self.animations_enabled: bool = True
        self.card_shadow: str = "subtle"
        self.hover_glow: bool = True
        self.glassmorphism: bool = False
        self.accent_color: str = "#C46A93"
        self.is_dark: bool = False

        # widget -> {"effect": QGraphicsDropShadowEffect, "anim": QPropertyAnimation, "hovered": bool}
        self._tracked: dict[QWidget, dict] = {}

    def apply(
        self,
        animations_enabled: bool = True,
        card_shadow: str = "subtle",
        hover_glow: bool = True,
        glassmorphism: bool = False,
        accent_color: str = "#C46A93",
        is_dark: bool = False,
    ) -> None:
        """Update active configuration and refresh all tracked widgets."""
        self.animations_enabled = bool(animations_enabled)
        self.card_shadow = str(card_shadow or "subtle").lower()
        self.hover_glow = bool(hover_glow)
        self.glassmorphism = bool(glassmorphism)
        self.accent_color = str(accent_color or "#C46A93")
        self.is_dark = bool(is_dark)

        # Scan and attach new widgets
        if self.main_window is not None:
            self.scan_and_attach(self.main_window)

        # Update all tracked widgets
        for widget, item in list(self._tracked.items()):
            if not widget or not widget.isWidgetType():
                continue
            self._apply_widget_state(widget, item.get("hovered", False))

    def refresh(self) -> None:
        """Rescan window for newly created cards/buttons and apply current effects."""
        if self.main_window is not None:
            self.scan_and_attach(self.main_window)

    def scan_and_attach(self, container: QWidget) -> None:
        """Scan a container widget for eligible cards and buttons to manage."""
        if container is None:
            return

        # Check container itself
        if self._is_eligible(container):
            self.attach_widget(container)

        for child in container.findChildren(QWidget):
            if self._is_eligible(child):
                self.attach_widget(child)

    def _is_eligible(self, widget: QWidget) -> bool:
        obj_name = widget.objectName()
        if obj_name in CARD_OBJECT_NAMES:
            return True
        if obj_name in BUTTON_OBJECT_NAMES:
            return True
        cls_name = widget.__class__.__name__
        if cls_name in ("VisualThemeModeCard", "VisualLayoutCard", "ColorChipCard"):
            return True
        return False

    def attach_widget(self, widget: QWidget) -> None:
        """Attach drop shadow effect, animation, and hover tracking to a widget."""
        if widget in self._tracked:
            return

        # Avoid clobbering existing custom effects if not managed by us
        existing = widget.graphicsEffect()
        if existing is not None and not isinstance(existing, QGraphicsDropShadowEffect):
            return

        effect = QGraphicsDropShadowEffect(widget)
        anim = QPropertyAnimation(effect, b"blurRadius", effect)
        anim.setDuration(190)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        self._tracked[widget] = {
            "effect": effect,
            "anim": anim,
            "hovered": False,
        }

        widget.setGraphicsEffect(effect)
        widget.installEventFilter(self)
        widget.destroyed.connect(lambda _=None, w=widget: self._tracked.pop(w, None))

        self._apply_widget_state(widget, False)

    def _apply_widget_state(self, widget: QWidget, is_hover: bool) -> None:
        item = self._tracked.get(widget)
        if not item:
            return
        item["hovered"] = is_hover
        effect: QGraphicsDropShadowEffect = item["effect"]
        anim: QPropertyAnimation = item["anim"]

        # 1. Determine target elevation & color
        if is_hover:
            if self.hover_glow:
                effect.setEnabled(True)
                # Glowing colored shadow in accent color
                glow_color = QColor(self.accent_color)
                glow_color.setAlpha(165 if not self.is_dark else 210)
                target_color = glow_color
                target_blur = 30.0 if self.card_shadow == "floating" else 22.0
                target_offset_y = 2 if self.card_shadow == "flat" else 5
            else:
                # Hover without glowing accent color
                if self.card_shadow == "flat":
                    anim.stop()
                    effect.setEnabled(False)
                    return
                effect.setEnabled(True)
                if self.card_shadow == "subtle":
                    target_color = QColor(0, 0, 0, 36 if not self.is_dark else 95)
                    target_blur = 18.0
                    target_offset_y = 5
                else:  # floating
                    target_color = QColor(0, 0, 0, 68 if not self.is_dark else 155)
                    target_blur = 36.0
                    target_offset_y = 12
        else:
            # Normal resting state
            if self.card_shadow == "flat":
                anim.stop()
                effect.setEnabled(False)
                return
            effect.setEnabled(True)
            if self.card_shadow == "subtle":
                target_color = QColor(0, 0, 0, 22 if not self.is_dark else 75)
                target_blur = 14.0
                target_offset_y = 3
            else:  # floating
                target_color = QColor(0, 0, 0, 48 if not self.is_dark else 130)
                target_blur = 28.0
                target_offset_y = 8

        effect.setColor(target_color)
        effect.setOffset(0, target_offset_y)

        # 2. Blur radius transition (animated vs instant)
        anim.stop()
        if self.animations_enabled and widget.isVisible():
            anim.setStartValue(effect.blurRadius())
            anim.setEndValue(target_blur)
            anim.start()
        else:
            effect.setBlurRadius(target_blur)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched in self._tracked:
            if event.type() == QEvent.Enter:
                self._apply_widget_state(watched, True)
            elif event.type() == QEvent.Leave:
                self._apply_widget_state(watched, False)
        return super().eventFilter(watched, event)

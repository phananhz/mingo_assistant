from __future__ import annotations

from PySide6.QtWidgets import QComboBox


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event) -> None:
        if self.view().isVisible():
            super().wheelEvent(event)
            return
        event.ignore()

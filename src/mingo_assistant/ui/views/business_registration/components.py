"""Small reusable Qt components for business registration."""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QFrame, QLabel, QLineEdit, QPushButton, QTextEdit


@dataclass
class BusinessLineRow:
    name_field: QLineEdit
    detail_field: QTextEdit
    code_field: QLineEdit
    main_checkbox: QCheckBox
    delete_button: QPushButton
    cells: list[QFrame]


class ClickableImageLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

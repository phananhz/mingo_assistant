"""Small reusable Qt components for business registration."""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QFrame, QLabel, QLineEdit, QPushButton, QTextEdit


@dataclass
class BusinessLineRow:
    name_field: QLineEdit
    detail_field: QTextEdit
    code_field: QLineEdit
    main_checkbox: QCheckBox
    delete_button: QPushButton
    cells: list[QFrame]


@dataclass
class CompanyMemberRow:
    profile_selector: QComboBox
    full_name_field: QLineEdit
    date_of_birth_field: QLineEdit
    gender_field: QLineEdit
    id_number_field: QLineEdit
    address_field: QTextEdit
    delete_button: QPushButton
    card: QFrame


@dataclass
class BeneficialOwnerRow:
    """One editable beneficial-owner entry in the two-member workflow."""

    member_selector: QComboBox
    fields: dict[str, QLineEdit | QTextEdit]
    delete_button: QPushButton
    card: QFrame


class ClickableImageLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

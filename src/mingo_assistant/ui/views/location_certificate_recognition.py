"""Shared recognition card for business-location certificates (BRC)."""
from __future__ import annotations

from typing import Protocol

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QWidget


LOCATION_CERTIFICATE_FIELDS = (
    ("parent_entity_name", "Tên doanh nghiệp"),
    ("parent_entity_registration_number", "Mã số thuế"),
    ("location_business_name", "Tên địa điểm kinh doanh"),
    ("location_business_code", "Mã số địa điểm kinh doanh"),
    ("location_full_address", "Địa chỉ địa điểm kinh doanh"),
    ("location_phone", "Điện thoại (nếu có)"),
    ("location_fax", "Số fax (nếu có)"),
    ("location_email", "Thư điện tử (nếu có)"),
    ("location_website", "Website (nếu có)"),
)


class _LocationCertificateCardOwner(Protocol):
    organization_card_fields: dict[str, QLineEdit]
    organization_document_label: QLabel

    def _save_organization_profile(self) -> None: ...


def build_location_certificate_result_section(owner: _LocationCertificateCardOwner) -> QWidget:
    """Build the unchanged BRC recognition fields for every BRC workflow."""
    group = QGroupBox("Thông tin giấy chứng nhận địa điểm kinh doanh nhận diện")
    group.setObjectName("CccdResultCard")
    grid = QGridLayout(group)
    grid.setHorizontalSpacing(14)
    grid.setVerticalSpacing(8)
    grid.setColumnStretch(1, 1)
    grid.setColumnStretch(3, 1)

    owner.organization_document_label = QLabel("Chưa tải giấy chứng nhận địa điểm kinh doanh")
    owner.organization_document_label.setObjectName("FilterLabel")
    owner.organization_document_label.setWordWrap(True)
    grid.addWidget(owner.organization_document_label, 0, 0, 1, 4)

    positions = (
        (1, 0, 3), (2, 0, 3), (3, 0, 3), (4, 0, 1), (5, 0, 3),
        (6, 0, 1), (6, 2, 1), (7, 0, 1), (7, 2, 1),
    )
    for (key, label_text), (row, column, span) in zip(LOCATION_CERTIFICATE_FIELDS, positions):
        label = QLabel(label_text)
        label.setObjectName("FilterLabel")
        label.setWordWrap(True)
        field = QLineEdit()
        field.setPlaceholderText(label_text)
        owner.organization_card_fields[key] = field
        grid.addWidget(label, row, column)
        grid.addWidget(field, row, column + 1, 1, span)

    save = QPushButton("Lưu dữ liệu giấy chứng nhận")
    save.setObjectName("PrimaryButton")
    save.clicked.connect(owner._save_organization_profile)
    grid.addWidget(save, 8, 0, 1, 4, Qt.AlignmentFlag.AlignRight)
    return group

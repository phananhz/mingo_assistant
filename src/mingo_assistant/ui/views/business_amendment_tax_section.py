"""Tax-registration section composed into the business-amendment workspace."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from mingo_assistant.ui.views.business_amendment_workspace import BusinessAmendmentWorkspace


class AmendmentTaxSection:
    """Build and coordinate the tax fields without owning case persistence."""

    def __init__(self, owner: "BusinessAmendmentWorkspace") -> None:
        self.owner = owner
        self.person_selectors: dict[str, QComboBox] = {}
        self.registration_cards: list[QFrame] = []
        self.registration_numbers: list[QLabel] = []

    def build(self) -> QGroupBox:
        section = QGroupBox("THÔNG BÁO THAY ĐỔI THÔNG TIN ĐĂNG KÝ THUẾ")
        layout = QVBoxLayout(section)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 18, 14, 14)
        section.setStyleSheet(
            "QFrame#TaxRegistrationCard { background: #fbfcff; border: 1px solid #b9c8dc; border-radius: 10px; }"
            "QLabel#TaxNumberBadge { background: #6f58c9; color: white; border: none; border-radius: 8px; font-weight: 700; }"
            "QLabel#TaxRowTitle { color: #243247; border: none; font-weight: 600; }"
        )
        self.person_selectors.clear()
        self.registration_cards.clear()
        self.registration_numbers.clear()

        rows = (
            ("Thông tin về Giám đốc/Tổng giám đốc (nếu có)", self._build_person_panel("director")),
            ("Thông tin về Kế toán trưởng/Phụ trách kế toán (nếu có)", self._build_person_panel("accountant")),
            ("Địa chỉ nhận thông báo thuế", self._build_address_panel()),
            ("Ngày bắt đầu hoạt động", self._build_single_field("tax_start_date", "Ngày bắt đầu hoạt động", "dd/mm/yyyy")),
            ("Hình thức hạch toán", self._build_fixed_choices(("Hạch toán độc lập", "Có báo cáo tài chính hợp nhất", "Hạch toán phụ thuộc"))),
            ("Năm tài chính", self._build_financial_year_panel()),
            ("Tổng số lao động", self._build_single_field("tax_labor_count", "Tổng số lao động", "Chỉ nhập số")),
            ("Hoạt động theo dự án BOT/BTO/BT/BOO, BLT, BTL, O&M", self._build_fixed_choices(("Có", "Không"))),
            ("Phương pháp tính thuế GTGT", self._build_fixed_choices(("Khấu trừ", "Trực tiếp trên GTGT", "Trực tiếp trên doanh số", "Không phải nộp thuế GTGT"))),
        )
        for number, (heading, content) in enumerate(rows, 1):
            card = self._build_row_card(number, heading, content)
            self.registration_cards.append(card)
            layout.addWidget(card)

        # Keep the established public attributes while the implementation is
        # moved behind a composed section object.
        self.owner.tax_person_selectors = self.person_selectors
        self.owner.tax_registration_cards = self.registration_cards
        self.owner.tax_registration_numbers = self.registration_numbers
        self.refresh_quick_fill_selector()
        return section

    def _build_row_card(self, number: int, heading: str, content: QWidget) -> QFrame:
        card = QFrame()
        card.setObjectName("TaxRegistrationCard")
        row = QHBoxLayout(card)
        row.setContentsMargins(12, 12, 14, 12)
        row.setSpacing(14)
        badge = QLabel(str(number))
        badge.setObjectName("TaxNumberBadge")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(42, 42)
        self.registration_numbers.append(badge)
        row.addWidget(badge, 0, Qt.AlignTop)
        body = QVBoxLayout()
        body.setSpacing(9)
        title = QLabel(heading)
        title.setObjectName("TaxRowTitle")
        title.setWordWrap(True)
        body.addWidget(title)
        body.addWidget(content)
        row.addLayout(body, 1)
        return card

    def _build_person_panel(self, role: str) -> QWidget:
        labels = (
            ("full_name", "Họ, chữ đệm và tên"),
            ("date_of_birth", "Ngày, tháng, năm sinh"),
            ("gender", "Giới tính"),
            ("id_number", "Số định danh cá nhân"),
            ("phone", "Điện thoại"),
        )
        panel = QWidget()
        grid = QGridLayout(panel)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        selector = QComboBox()
        selector.setObjectName("TaxPersonProfileSelector")
        selector.setMinimumWidth(320)
        selector.currentIndexChanged.connect(lambda _index, selected_role=role: self.apply_person_quick_fill(selected_role))
        self.person_selectors[role] = selector
        source_row = QHBoxLayout()
        source_row.setContentsMargins(0, 0, 0, 2)
        source_label = QLabel("Điền nhanh từ CCCD trong hồ sơ này")
        source_label.setObjectName("FilterLabel")
        source_row.addWidget(source_label)
        source_row.addWidget(selector, 1)
        grid.addLayout(source_row, 0, 0, 1, 4)
        for index, (suffix, label) in enumerate(labels):
            key = f"tax_{role}_{suffix}"
            if index == 0:
                row, pair = 1, 0
                span = 3
            else:
                row, pair = divmod(index - 1, 2)
                row += 2
                span = 1
            field = self.owner._create_field(key)
            if suffix == "date_of_birth":
                field.setPlaceholderText("dd/mm/yyyy")
            grid.addWidget(QLabel(label), row, pair * 2)
            grid.addWidget(field, row, pair * 2 + 1, 1, span)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        return panel

    def _build_address_panel(self) -> QWidget:
        panel = QWidget()
        grid = QGridLayout(panel)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        entries = (
            ("tax_notification_address_detail", "Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố, tổ/xóm/ấp/thôn", 0, 0, 1, 3),
            ("tax_notification_ward", "Xã/Phường/Đặc khu", 1, 0, 1, 1),
            ("tax_notification_province", "Tỉnh/Thành phố", 1, 2, 1, 1),
            ("tax_notification_phone", "Điện thoại (nếu có)", 2, 0, 1, 1),
            ("tax_notification_email", "Thư điện tử (nếu có)", 3, 0, 1, 3),
        )
        for key, label, row, column, row_span, column_span in entries:
            grid.addWidget(QLabel(label), row, column)
            grid.addWidget(self.owner._create_field(key), row, column + 1, row_span, column_span)
        fax = QLineEdit()
        fax.setReadOnly(True)
        fax.setPlaceholderText("Giữ nguyên theo mẫu Word")
        fax.setToolTip("Vùng số fax trong mẫu Word không được bôi vàng.")
        grid.addWidget(QLabel("Số fax (nếu có)"), 2, 2)
        grid.addWidget(fax, 2, 3)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        return panel

    def _build_single_field(self, key: str, label: str, placeholder: str) -> QWidget:
        panel = QWidget()
        row = QHBoxLayout(panel)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QLabel(label))
        field = self.owner._create_field(key)
        field.setPlaceholderText(placeholder)
        if key == "tax_labor_count":
            field.setValidator(QRegularExpressionValidator(QRegularExpression(r"[0-9]*"), field))
        row.addWidget(field, 1)
        if key == "tax_start_date":
            quick = QPushButton("Dùng ngày hiện tại")
            quick.setObjectName("GhostButton")
            quick.clicked.connect(self.fill_start_date_today)
            row.addWidget(quick)
        return panel

    def _build_financial_year_panel(self) -> QWidget:
        panel = QWidget()
        row = QHBoxLayout(panel)
        row.setContentsMargins(0, 0, 0, 0)
        for key, label in (("tax_financial_year_start", "Áp dụng từ ngày"), ("tax_financial_year_end", "Đến ngày")):
            row.addWidget(QLabel(label))
            field = self.owner._create_field(key)
            field.setPlaceholderText("dd/mm")
            row.addWidget(field, 1)
        quick = QPushButton("Dùng 01/01 – 31/12")
        quick.setObjectName("GhostButton")
        quick.clicked.connect(self.fill_standard_financial_year)
        row.addWidget(quick)
        return panel

    @staticmethod
    def _build_fixed_choices(labels: tuple[str, ...]) -> QWidget:
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        for label in labels:
            box = QCheckBox(label)
            box.setEnabled(False)
            box.setToolTip("Ô đánh dấu này không được bôi vàng trong mẫu Word nên được giữ nguyên.")
            layout.addWidget(box)
        layout.addStretch(1)
        fixed = QLabel("Giữ nguyên theo mẫu Word")
        fixed.setObjectName("FilterLabel")
        layout.addWidget(fixed)
        return panel

    def refresh_quick_fill_selector(self) -> None:
        for selector in self.person_selectors.values():
            current = selector.currentData()
            selector.blockSignals(True)
            selector.clear()
            selector.addItem("Chọn profile đã lưu", "")
            if self.owner._field_value("legal_representative_full_name") or self.owner._field_value("legal_representative_id_number"):
                selector.addItem("Người đại diện pháp luật hiện tại", "representative")
            for display_index, (person_index, person) in enumerate(self.owner._unique_saved_people(), start=1):
                selector.addItem(self.owner._person_display_name(display_index, person), f"person:{person_index}")
            if current:
                match = selector.findData(current)
                if match >= 0:
                    selector.setCurrentIndex(match)
            selector.blockSignals(False)

    def apply_person_quick_fill(self, role: str) -> None:
        selector = self.person_selectors.get(role)
        if selector is None:
            return
        source = str(selector.currentData() or "")
        if not source:
            return
        if source == "representative":
            data = {
                "legal_representative_full_name": self.owner._field_value("legal_representative_full_name"),
                "legal_representative_date_of_birth": self.owner._field_value("legal_representative_date_of_birth"),
                "legal_representative_gender": self.owner._field_value("legal_representative_gender"),
                "legal_representative_id_number": self.owner._field_value("legal_representative_id_number"),
                "personal_phone": self.owner._field_value("legal_representative_phone"),
            }
        else:
            try:
                person_index = int(source.split(":", 1)[1])
                person = self.owner.ocr_people[person_index]
            except (ValueError, IndexError):
                return
            data = self.owner._person_data_for_fill(person)
        self.owner._set_fields_from_mapping({
            f"tax_{role}_full_name": data.get("legal_representative_full_name", ""),
            f"tax_{role}_date_of_birth": data.get("legal_representative_date_of_birth", ""),
            f"tax_{role}_gender": data.get("legal_representative_gender", ""),
            f"tax_{role}_id_number": data.get("legal_representative_id_number", ""),
            f"tax_{role}_phone": data.get("personal_phone", ""),
        })
        selector.blockSignals(True)
        selector.setCurrentIndex(0)
        selector.blockSignals(False)
        self.owner._refresh_preview()

    def fill_start_date_today(self) -> None:
        self.owner._set_field("tax_start_date", datetime.now().strftime("%d/%m/%Y"))
        self.owner._refresh_preview()

    def fill_standard_financial_year(self) -> None:
        self.owner._set_fields_from_mapping({"tax_financial_year_start": "01/01", "tax_financial_year_end": "31/12"})

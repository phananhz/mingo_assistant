from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)

from mingo_assistant.models.case import CaseSummary


class CreateCaseDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Tạo hồ sơ mới")
        self.setMinimumWidth(520)

        self.company_name_input = QLineEdit()
        self.company_name_input.setPlaceholderText("Ví dụ: Công ty TNHH ABC")

        self.case_type_input = QComboBox()
        self.case_type_input.addItems(
            [
                "TNHH hai thành viên trở lên",
                "TNHH một thành viên",
                "Công ty cổ phần",
            ]
        )

        self.owner_input = QLineEdit()
        self.owner_input.setPlaceholderText("Người phụ trách hồ sơ")

        self.members_input = QSpinBox()
        self.members_input.setRange(1, 200)
        self.members_input.setValue(2)

        self.capital_input = QLineEdit()
        self.capital_input.setPlaceholderText("Ví dụ: 1.000.000.000 đồng")

        self.status_input = QComboBox()
        self.status_input.addItems(["Bản nháp", "Thiếu thông tin", "Sẵn sàng tạo"])

        form = QFormLayout()
        form.setSpacing(12)
        form.addRow("Tên doanh nghiệp", self.company_name_input)
        form.addRow("Loại hình", self.case_type_input)
        form.addRow("Người phụ trách", self.owner_input)
        form.addRow("Số thành viên", self.members_input)
        form.addRow("Vốn điều lệ", self.capital_input)
        form.addRow("Trạng thái", self.status_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(18)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def build_case(self) -> CaseSummary:
        status = self.status_input.currentText()
        condition = "Thiếu thông tin" if status in {"Bản nháp", "Thiếu thông tin"} else "Đủ dữ liệu"
        warning = "Cần bổ sung thông tin hồ sơ" if condition == "Thiếu thông tin" else None

        return CaseSummary(
            id=str(uuid4()),
            company_name=self.company_name_input.text().strip(),
            case_type=self.case_type_input.currentText(),
            owner=self.owner_input.text().strip(),
            updated_at=datetime.now().strftime("%d/%m/%Y"),
            status=status,
            condition=condition,
            members=self.members_input.value(),
            capital=self.capital_input.text().strip(),
            warning=warning,
        )

    def _validate_and_accept(self) -> None:
        if not self.company_name_input.text().strip():
            QMessageBox.warning(self, "Thiếu thông tin", "Bạn cần nhập tên doanh nghiệp.")
            return
        if not self.owner_input.text().strip():
            QMessageBox.warning(self, "Thiếu thông tin", "Bạn cần nhập người phụ trách hồ sơ.")
            return
        if not self.capital_input.text().strip():
            QMessageBox.warning(self, "Thiếu thông tin", "Bạn cần nhập vốn điều lệ.")
            return

        self.accept()

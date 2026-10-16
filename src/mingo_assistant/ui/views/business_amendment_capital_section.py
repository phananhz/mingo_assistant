"""Capital and share sections composed into the amendment workspace."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from mingo_assistant.domains.business_registration.money import VietnameseMoneyFormatter
from mingo_assistant.services.documents.business_amendment_fields import ASSET_LABELS, CAPITAL_SOURCE_LABELS
from mingo_assistant.services.documents.business_amendment_generator import compose_share_values, money_number

if TYPE_CHECKING:
    from mingo_assistant.ui.views.business_amendment_workspace import BusinessAmendmentWorkspace


class AmendmentCapitalSection:
    """Own the capital/share widgets while the workspace owns case state."""

    def __init__(self, owner: "BusinessAmendmentWorkspace") -> None:
        self.owner = owner

    def money_field(self, key: str):
        field = self.owner._create_field(key)
        field.setValidator(QRegularExpressionValidator(QRegularExpression(r"[0-9.]*"), field))
        field.textChanged.connect(self.refresh_capital_inputs)
        return field

    def build_share_section(self, title: str) -> QGroupBox:
        section = QGroupBox(title)
        layout = QVBoxLayout(section)
        layout.addWidget(QLabel("Thông tin về cổ phần (chỉ kê khai đối với công ty cổ phần):"))
        layout.addWidget(QLabel("Mệnh giá cổ phần (VNĐ)"))
        par = self.owner._create_field("new_share_par_value")
        par.setValidator(QRegularExpressionValidator(QRegularExpression(r"[0-9.]*"), par))
        par.textChanged.connect(self.refresh_share_inputs)
        layout.addWidget(par)
        note = QLabel("Nhập số lượng, giá trị và tỷ lệ cho từng loại cổ phần. Dòng Tổng số tự cộng các hàng đã nhập.")
        note.setWordWrap(True)
        layout.addWidget(note)
        table = QTableWidget(6, 5)
        self.owner.amendment_share_table = table
        table.setHorizontalHeaderLabels(["STT", "Loại cổ phần", "Số lượng", "Giá trị (bằng số, VNĐ)", "Tỷ lệ so với vốn\nđiều lệ (%)"])
        table.verticalHeader().hide()
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        table.setColumnWidth(0, 55)
        table.horizontalHeader().setFixedHeight(70)
        table.setStyleSheet("QTableWidget { gridline-color: #879bb5; border: 1px solid #879bb5; } QHeaderView::section { padding: 8px; border: 1px solid #879bb5; }")
        labels = ("Cổ phần phổ thông", "Cổ phần ưu đãi biểu quyết", "Cổ phần ưu đãi cổ tức", "Cổ phần ưu đãi hoàn lại", "Các cổ phần ưu đãi khác")
        for row, label in enumerate(labels):
            table.setRowHeight(row, 68)
            table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            table.setItem(row, 1, QTableWidgetItem(label))
            for column, suffix in enumerate(("count", "amount", "ratio"), 2):
                field = self.owner._create_field(f"amendment_share_{row + 1}_{suffix}")
                pattern = r"[0-9.,]*" if suffix == "ratio" else r"[0-9.]*"
                field.setValidator(QRegularExpressionValidator(QRegularExpression(pattern), field))
                field.setAccessibleName(f"{label} — {table.horizontalHeaderItem(column).text()}")
                field.textChanged.connect(self.refresh_share_inputs)
                table.setCellWidget(row, column, field)
        table.setSpan(5, 0, 1, 2)
        table.setItem(5, 0, QTableWidgetItem("Tổng số"))
        table.setRowHeight(5, 68)
        for column in range(2, 5):
            table.setItem(5, column, QTableWidgetItem(""))
        table.setFixedHeight(70 + 6 * 68 + 4)
        layout.addWidget(table)
        return section

    def refresh_share_inputs(self) -> None:
        table = getattr(self.owner, "amendment_share_table", None)
        if table is None:
            return
        formatter = VietnameseMoneyFormatter()
        keys = ["new_share_par_value"] + [f"amendment_share_{i}_{suffix}" for i in range(1, 6) for suffix in ("count", "amount")]
        for key in keys:
            field = self.owner.fields.get(key)
            if field is None or not field.text():
                continue
            raw = field.text().replace(".", "")
            if not raw.isdigit():
                continue
            formatted = formatter.format_digits(raw)
            if formatted != field.text():
                right_digits = sum(character.isdigit() for character in field.text()[field.cursorPosition():])
                field.blockSignals(True)
                field.setText(formatted)
                position = len(formatted)
                while position and right_digits:
                    position -= 1
                    right_digits -= int(formatted[position].isdigit())
                field.setCursorPosition(position)
                field.blockSignals(False)
        values = {key: self.owner._field_value(key) for key in self.owner.fields if key.startswith("amendment_share_")}
        try:
            totals = compose_share_values(values)
        except ValueError:
            totals = {}
        for column, suffix in enumerate(("count", "amount", "ratio"), 2):
            table.item(5, column).setText(totals.get(f"amendment_share_total_{suffix}", ""))

    def build(self, title: str) -> QGroupBox:
        section = QGroupBox(title)
        layout = QVBoxLayout(section)
        for key, label in (("registered_capital", "Vốn điều lệ đã đăng ký (bằng số, VNĐ)"),
                           ("new_capital", "Vốn điều lệ sau thay đổi (bằng số, VNĐ)")):
            layout.addWidget(QLabel(label))
            layout.addWidget(self.money_field(key))
            preview = self.owner._create_field(key + "_text")
            preview.setReadOnly(True)
            preview.setPlaceholderText("Tự động hiển thị số tiền VNĐ và bằng chữ")
            layout.addWidget(preview)
        layout.addWidget(QLabel("Giá trị tương đương theo đơn vị tiền tệ nước ngoài (nếu có)"))
        layout.addWidget(self.owner._create_field("capital_foreign_equivalent"))
        question = QLabel("Có hiển thị thông tin về giá trị tương đương theo đơn vị tiền tệ nước ngoài trên Giấy chứng nhận đăng ký doanh nghiệp hay không?")
        question.setWordWrap(True)
        layout.addWidget(question)
        choices = QHBoxLayout()
        for key, label in (("capital_foreign_yes_checked", "Có"), ("capital_foreign_no_checked", "Không")):
            box = QCheckBox(label)
            self.owner.fields[key] = box
            choices.addWidget(box)
        choices.addStretch()
        layout.addLayout(choices)
        note = QLabel("Ô Có/Không hiện chỉ để chọn trên màn hình, chưa áp dụng vào Word.")
        note.setWordWrap(True)
        layout.addWidget(note)
        for key, label in (("capital_change_date", "Thời điểm thay đổi vốn"), ("capital_change_method", "Hình thức tăng, giảm vốn")):
            layout.addWidget(QLabel(label))
            layout.addWidget(self.owner._create_field(key))
        self.owner.amendment_capital_tables = {}
        for kind, table_title, labels, active in (
            ("source", "Nguồn vốn điều lệ sau khi thay đổi vốn điều lệ:", CAPITAL_SOURCE_LABELS, 2),
            ("asset", "Tài sản góp vốn sau khi thay đổi vốn điều lệ:", ASSET_LABELS, 1),
        ):
            layout.addWidget(QLabel(table_title))
            numbered = kind == "asset"
            table = QTableWidget(len(labels) + 1, 4 if numbered else 3)
            table.setHorizontalHeaderLabels((["STT"] if numbered else []) + ["Tài sản góp vốn" if numbered else "Loại nguồn vốn", "Giá trị vốn của từng tài sản\ntrong vốn điều lệ (bằng số, VNĐ)" if numbered else "Số tiền (bằng số; VNĐ) và giá trị tương đương\ntheo đơn vị tiền tệ nước ngoài, nếu có", "Tỷ lệ (%)"])
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.setSelectionMode(QAbstractItemView.NoSelection)
            table.verticalHeader().hide()
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            if numbered:
                table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(table.columnCount() - 1, QHeaderView.Fixed)
            table.setColumnWidth(table.columnCount() - 1, 120)
            table.horizontalHeader().setFixedHeight(70)
            table.setStyleSheet("QTableWidget { gridline-color: #879bb5; border: 1px solid #879bb5; } QHeaderView::section { padding: 10px; border: 1px solid #879bb5; }")
            for row, label in enumerate((*labels, "Tổng số" if numbered else "Tổng cộng")):
                table.setRowHeight(row, 68)
                if numbered and row == 1:
                    label = "Ngoại tệ tự do chuyển đổi (ghi rõ loại ngoại tệ, số tiền được góp bằng mỗi loại ngoại tệ)"
                elif numbered and row == 5:
                    label = "Các tài sản khác (ghi rõ loại tài sản, số lượng và giá trị còn lại của mỗi loại tài sản, có thể lập thành danh mục riêng kèm theo hồ sơ đăng ký doanh nghiệp)"
                if numbered:
                    table.setItem(row, 0, QTableWidgetItem(str(row + 1) if row < len(labels) else ""))
                table.setItem(row, int(numbered), QTableWidgetItem(label))
                amount_column = int(numbered) + 1
                if row + 1 == active:
                    amount = self.money_field(f"amendment_{kind}_{active}_amount")
                    amount.setReadOnly(True)
                    amount.setPlaceholderText("Tự động lấy từ vốn điều lệ sau thay đổi")
                    amount.setStyleSheet("QLineEdit { background: #f8fafc; border: 1px solid #879bb5; padding: 8px; }")
                    table.setCellWidget(row, amount_column, amount)
                else:
                    table.setItem(row, amount_column, QTableWidgetItem("" if row == len(labels) else "0"))
                table.setItem(row, amount_column + 1, QTableWidgetItem("100%" if row + 1 == active or row == len(labels) else "0"))
            table.setFixedHeight(68 * (len(labels) + 1) + 72)
            self.owner.amendment_capital_tables[kind] = table
            layout.addWidget(table)
        layout.addWidget(self.build_share_section("Thông tin về cổ phần (chỉ kê khai đối với công ty cổ phần)"))
        return section

    def refresh_capital_inputs(self) -> None:
        formatter = VietnameseMoneyFormatter()
        for key in ("registered_capital", "new_capital", "amendment_source_2_amount", "amendment_asset_1_amount"):
            field = self.owner.fields.get(key)
            if field is None:
                continue
            text = field.text().strip()
            try:
                number = money_number(text.replace(".", "")) if text else None
            except ValueError:
                number = None
            formatted = formatter.format_digits(str(number)) if number is not None else text
            if formatted != field.text():
                right_digits = sum(character.isdigit() for character in field.text()[field.cursorPosition():])
                field.blockSignals(True)
                field.setText(formatted)
                position = len(formatted)
                while position and right_digits:
                    position -= 1
                    right_digits -= int(formatted[position].isdigit())
                field.setCursorPosition(position)
                field.blockSignals(False)
            preview = self.owner.fields.get(key + "_text")
            if preview is not None:
                value = f"{formatted} VNĐ ({formatter.to_words(number).capitalize()} đồng)" if number is not None else ""
                preview.blockSignals(True)
                preview.setText(value)
                preview.blockSignals(False)
        new_capital = self.owner._field_value("new_capital")
        for key in ("amendment_source_2_amount", "amendment_asset_1_amount"):
            field = self.owner.fields.get(key)
            if field is not None and field.text() != new_capital:
                field.blockSignals(True)
                field.setText(new_capital)
                field.blockSignals(False)
        for kind, table in getattr(self.owner, "amendment_capital_tables", {}).items():
            active = 2 if kind == "source" else 1
            table.item(table.rowCount() - 1, 2 if kind == "asset" else 1).setText(
                self.owner._field_value(f"amendment_{kind}_{active}_amount")
            )

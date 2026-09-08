from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class StorageLocationDialog(QDialog):
    def __init__(self, default_path: Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Thiết lập nơi lưu hồ sơ")
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)
        title = QLabel("Chọn nơi lưu tài liệu xuất từ Min Assistant")
        title.setObjectName("DialogTitle")
        description = QLabel(
            "Các file Word, PDF và ZIP sẽ được lưu tại thư mục này. "
            "Bạn có thể đổi lại nơi lưu khi xuất hồ sơ."
        )
        description.setWordWrap(True)

        row = QHBoxLayout()
        self.path_input = QLineEdit(str(default_path))
        self.path_input.setPlaceholderText("Ví dụ: C:\\Users\\Ban\\Documents\\Min Assistant")
        browse = QPushButton("Chọn thư mục")
        browse.clicked.connect(self._browse)
        row.addWidget(self.path_input, 1)
        row.addWidget(browse)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addLayout(row)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Chọn nơi lưu hồ sơ", self.path_input.text())
        if selected:
            self.path_input.setText(selected)

    def selected_path(self) -> Path:
        return Path(self.path_input.text().strip()).expanduser()

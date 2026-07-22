from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from mingo_assistant.models.case import CaseSummary


class BusinessRegistrationDocumentsView(QWidget):
    def __init__(self, case: CaseSummary, on_back, on_edit) -> None:
        super().__init__()
        self.case = case
        self.on_back = on_back
        self.on_edit = on_edit
        self.version_contents: list[QWidget] = []
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        layout.addLayout(self._build_header())
        layout.addWidget(self._build_summary())
        layout.addWidget(self._build_documents())
        layout.addStretch(1)

        scroll.setWidget(page)
        root.addWidget(scroll)

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()

        back_button = QPushButton("← Quay lại")
        back_button.setObjectName("GhostButton")
        back_button.clicked.connect(self.on_back)

        text = QVBoxLayout()
        title = QLabel("Xem hồ sơ đã tạo")
        title.setObjectName("PageTitle")
        description = QLabel("Danh sách file Word đã fill xong. Mở file bằng Word để xem hoặc chỉnh sửa trực tiếp.")
        description.setObjectName("PageDescription")
        description.setWordWrap(True)
        text.addWidget(title)
        text.addWidget(description)

        edit_button = QPushButton("Sửa dữ liệu hồ sơ")
        edit_button.setObjectName("PrimaryButton")
        edit_button.clicked.connect(self.on_edit)

        open_folder_button = QPushButton("Mở thư mục xuất")
        open_folder_button.setObjectName("GhostButton")
        open_folder_button.clicked.connect(self._open_export_folder)

        header.addWidget(back_button)
        header.addLayout(text, 1)
        header.addWidget(open_folder_button)
        header.addWidget(edit_button)
        return header

    def _build_summary(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QGridLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(8)

        items = [
            ("Tên doanh nghiệp", self.case.company_name),
            ("Người phụ trách", self.case.owner),
            ("Vốn điều lệ", self.case.capital),
            ("Trạng thái", self.case.status),
            ("Thời gian xuất", self.case.exported_at or "Chưa xuất hồ sơ"),
            ("Thư mục", self.case.export_dir or "Chưa có thư mục xuất"),
        ]
        for index, (label_text, value) in enumerate(items):
            label = QLabel(label_text)
            label.setObjectName("FilterLabel")
            content = QLabel(value)
            content.setObjectName("MetaText")
            content.setWordWrap(True)
            row = index // 2
            column = (index % 2) * 2
            layout.addWidget(label, row, column)
            layout.addWidget(content, row, column + 1)
            layout.setColumnStretch(column + 1, 1)
        return card

    def _build_documents(self) -> QWidget:
        wrapper = QFrame()
        wrapper.setObjectName("Card")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(12)

        versions = self._versions()
        if not versions:
            empty = QLabel("Hồ sơ này chưa có file Word đã xuất. Bấm 'Sửa dữ liệu hồ sơ' rồi xuất Word trước.")
            empty.setObjectName("EmptyDescription")
            empty.setWordWrap(True)
            layout.addWidget(empty)
            return wrapper

        for version_index, version in enumerate(versions, start=1):
            files = version["files"]
            toggle = QCheckBox(f"{version['name']} - {len(files)} file Word - {version['exported_at'] or 'chưa có thời gian'}")
            toggle.setObjectName("ResultText")
            toggle.setChecked(version_index == len(versions))
            content = QWidget()
            version_layout = QVBoxLayout(content)
            version_layout.setContentsMargins(0, 0, 0, 0)
            version_layout.setSpacing(12)
            for index, path in enumerate(files, start=1):
                version_layout.addWidget(self._build_document_row(index, path, str(version["exported_at"])))
            content.setVisible(toggle.isChecked())
            toggle.stateChanged.connect(lambda state, selected=content: selected.setVisible(state == Qt.Checked))
            self.version_contents.append(content)
            layout.addWidget(toggle)
            layout.addWidget(content)
        return wrapper

    def _toggle_version_content(self, state: int) -> None:
        for content in self.version_contents:
            content.setVisible(state == Qt.Checked)

    def _build_document_row(self, index: int, path: Path, exported_at: str) -> QWidget:
        row = QFrame()
        row.setObjectName("Card")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        number = QLabel(f"{index:02d}")
        number.setObjectName("StatusBadge")
        number.setAlignment(Qt.AlignCenter)
        number.setFixedWidth(44)

        info = QVBoxLayout()
        file_name = QLabel(path.name)
        file_name.setObjectName("CardTitle")
        file_path = QLabel(str(path))
        file_path.setObjectName("MetaText")
        file_path.setWordWrap(True)
        time_text = QLabel(f"Đánh dấu thời gian: {exported_at or 'Chưa có'}")
        time_text.setObjectName("MetaText")
        info.addWidget(file_name)
        info.addWidget(file_path)
        info.addWidget(time_text)

        open_button = QPushButton("Mở")
        open_button.setObjectName("PrimaryButton")
        open_button.clicked.connect(lambda checked=False, selected=path: self._open_file(selected))

        edit_button = QPushButton("Sửa")
        edit_button.setObjectName("GhostButton")
        edit_button.clicked.connect(self.on_edit)

        layout.addWidget(number)
        layout.addLayout(info, 1)
        layout.addWidget(open_button)
        layout.addWidget(edit_button)
        return row

    def _versions(self) -> list[dict[str, object]]:
        raw_versions = self.case.export_versions or []
        if not raw_versions and self.case.export_dir:
            raw_versions = [
                {
                    "name": "Phiên 1",
                    "export_dir": self.case.export_dir,
                    "exported_at": self.case.exported_at,
                    "documents": self.case.generated_documents,
                }
            ]
        versions: list[dict[str, object]] = []
        for index, version in enumerate(raw_versions, start=1):
            export_dir = Path(str(version.get("export_dir", ""))) if version.get("export_dir") else None
            files = self._document_paths(export_dir, [str(item) for item in version.get("documents", []) or []])
            if files:
                versions.append(
                    {
                        "name": str(version.get("name") or f"Phiên {index}"),
                        "exported_at": str(version.get("exported_at", "")),
                        "files": files,
                    }
                )
        return versions

    def _document_paths(self, export_dir: Path | None, generated_documents: list[str]) -> list[Path]:
        if not export_dir or not export_dir.exists():
            return []

        if generated_documents:
            paths = [export_dir / file_name for file_name in generated_documents]
        else:
            paths = sorted(export_dir.glob("*.docx"))
        return [path for path in paths if path.exists()]

    def _open_file(self, path: Path) -> None:
        if not path.exists():
            QMessageBox.warning(self, "Không tìm thấy file", f"File không còn tồn tại:\n{path}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _open_export_folder(self) -> None:
        export_dir = Path(self.case.export_dir) if self.case.export_dir else None
        if not export_dir or not export_dir.exists():
            QMessageBox.warning(self, "Chưa có thư mục", "Hồ sơ này chưa có thư mục xuất.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(export_dir)))

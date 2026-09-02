from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QRadioButton,
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
        self.version_button_group = QButtonGroup(self)
        self.version_button_group.setExclusive(True)
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

        layout.addLayout(self._build_header_v2())
        layout.addWidget(self._build_summary_v2())
        layout.addWidget(self._build_documents_v2())
        layout.addStretch(1)

        scroll.setWidget(page)
        root.addWidget(scroll)

    def _build_header_v2(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(12)

        back_button = QPushButton("← Quay lại")
        back_button.setObjectName("GhostButton")
        back_button.clicked.connect(self.on_back)

        text = QVBoxLayout()
        text.setSpacing(4)
        eyebrow = QLabel("HỒ SƠ ĐÃ XUẤT")
        eyebrow.setObjectName("DocumentsEyebrow")
        title = QLabel("Xem hồ sơ đã tạo")
        title.setObjectName("PageTitle")
        description = QLabel("Kiểm tra các file Word đã điền và mở nhanh phiên bản bạn cần.")
        description.setObjectName("PageDescription")
        description.setWordWrap(True)
        text.addWidget(eyebrow)
        text.addWidget(title)
        text.addWidget(description)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        open_folder_button = QPushButton("Mở thư mục xuất")
        open_folder_button.setObjectName("GhostButton")
        open_folder_button.clicked.connect(self._open_export_folder)
        edit_button = QPushButton("Sửa dữ liệu hồ sơ")
        edit_button.setObjectName("PrimaryButton")
        edit_button.clicked.connect(self.on_edit)
        actions.addWidget(open_folder_button)
        actions.addWidget(edit_button)

        header.addWidget(back_button, 0, Qt.AlignTop)
        header.addLayout(text, 1)
        header.addLayout(actions, 0)
        return header

    def _build_summary_v2(self) -> QWidget:
        card = QFrame()
        card.setObjectName("SummaryCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        heading = QHBoxLayout()
        title = QLabel("Tổng quan hồ sơ")
        title.setObjectName("SectionTitle")
        status = QLabel(self.case.status or "Chưa xác định")
        status.setObjectName("SummaryStatus")
        status.setAlignment(Qt.AlignCenter)
        heading.addWidget(title)
        heading.addStretch(1)
        heading.addWidget(status)
        layout.addLayout(heading)

        grid = QGridLayout()
        grid.setHorizontalSpacing(26)
        grid.setVerticalSpacing(14)
        items = [
            ("Tên doanh nghiệp", self.case.company_name),
            ("Người ủy quyền", self._authorized_person_name()),
            ("Vốn điều lệ", self.case.capital),
            ("Thời gian xuất", self.case.exported_at or "Chưa xuất hồ sơ"),
            ("Thư mục lưu hồ sơ", self.case.export_dir or "Chưa có thư mục xuất"),
        ]
        for index, (label_text, value) in enumerate(items):
            block = QVBoxLayout()
            block.setSpacing(3)
            label = QLabel(label_text.upper())
            label.setObjectName("SummaryLabel")
            content = QLabel(value or "Chưa nhập")
            content.setObjectName("SummaryValue" if index < 4 else "SummaryPath")
            content.setWordWrap(True)
            if index == 4:
                content.setToolTip(value)
            block.addWidget(label)
            block.addWidget(content)
            if index == 4:
                grid.addLayout(block, 1, 0, 1, 3)
            else:
                grid.addLayout(block, 0, index)
                grid.setColumnStretch(index, 1)
        layout.addLayout(grid)
        return card


    def _authorized_person_name(self) -> str:
        name = str(self.case.form_values.get("authorized_person_full_name", "") or "").strip()
        return name or self.case.owner or "Chưa chọn"

    def _build_documents_v2(self) -> QWidget:
        wrapper = QFrame()
        wrapper.setObjectName("DocumentsPanel")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)

        versions = self._versions()
        heading = QHBoxLayout()
        title = QLabel("Các phiên bản đã xuất")
        title.setObjectName("SectionTitle")
        count = QLabel(f"{len(versions)} phiên bản")
        count.setObjectName("SectionCount")
        heading.addWidget(title)
        heading.addStretch(1)
        heading.addWidget(count)
        layout.addLayout(heading)

        hint = QLabel("Chọn một phiên bản để xem danh sách file Word bên dưới.")
        hint.setObjectName("SectionHint")
        layout.addWidget(hint)
        if not versions:
            empty = QLabel("Hồ sơ này chưa có file Word đã xuất. Hãy sửa dữ liệu và xuất Word trước.")
            empty.setObjectName("EmptyDescription")
            empty.setWordWrap(True)
            layout.addWidget(empty)
            return wrapper

        for version_index, version in enumerate(versions, start=1):
            files = version["files"]
            version_card = QFrame()
            version_card.setObjectName("VersionCard")
            version_layout = QVBoxLayout(version_card)
            version_layout.setContentsMargins(14, 12, 14, 14)
            version_layout.setSpacing(10)

            version_header = QHBoxLayout()
            selector = QRadioButton(str(version["name"]).capitalize())
            selector.setObjectName("VersionSelector")
            selector.setToolTip(f"Mở {len(files)} file Word của phiên bản này")
            meta = QLabel(f"{len(files)} file Word  •  {version['exported_at'] or 'Chưa có thời gian'}")
            meta.setObjectName("VersionMeta")
            version_header.addWidget(selector)
            version_header.addStretch(1)
            version_header.addWidget(meta)
            version_layout.addLayout(version_header)

            content = QWidget()
            file_layout = QVBoxLayout(content)
            file_layout.setContentsMargins(0, 2, 0, 0)
            file_layout.setSpacing(8)
            for index, path in enumerate(files, start=1):
                file_layout.addWidget(self._build_document_row_v2(index, path, str(version["exported_at"])))
            content.setVisible(False)
            selector.toggled.connect(content.setVisible)
            self.version_button_group.addButton(selector, version_index)
            self.version_contents.append(content)
            version_layout.addWidget(content)
            layout.addWidget(version_card)
            if version_index == len(versions):
                selector.setChecked(True)
        return wrapper

    def _build_document_row_v2(self, index: int, path: Path, exported_at: str) -> QWidget:
        row = QFrame()
        row.setObjectName("DocumentRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        number = QLabel(f"{index:02d}")
        number.setObjectName("DocumentIndex")
        number.setAlignment(Qt.AlignCenter)
        number.setFixedWidth(38)

        info = QVBoxLayout()
        info.setSpacing(3)
        file_name = QLabel(path.name)
        file_name.setObjectName("DocumentTitle")
        file_path = QLabel(str(path))
        file_path.setObjectName("DocumentPath")
        file_path.setWordWrap(True)
        file_path.setToolTip(str(path))
        detail = QLabel(f"DOCX  •  Cập nhật {exported_at or 'chưa có thời gian'}")
        detail.setObjectName("DocumentMeta")
        info.addWidget(file_name)
        info.addWidget(file_path)
        info.addWidget(detail)

        open_button = QPushButton("Mở file")
        open_button.setObjectName("CompactPrimaryButton")
        open_button.clicked.connect(lambda checked=False, selected=path: self._open_file(selected))
        edit_button = QPushButton("Sửa hồ sơ")
        edit_button.setObjectName("CompactGhostButton")
        edit_button.clicked.connect(self.on_edit)

        layout.addWidget(number)
        layout.addLayout(info, 1)
        layout.addWidget(open_button)
        layout.addWidget(edit_button)
        return row

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
            ("Người ủy quyền", self._authorized_person_name()),
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
            toggle = QCheckBox(
                f"{version['name']} - {len(files)} file Word - {version['exported_at'] or 'chưa có thời gian'}"
            )
            toggle.setObjectName("ResultText")
            content = QWidget()
            version_layout = QVBoxLayout(content)
            version_layout.setContentsMargins(0, 0, 0, 0)
            version_layout.setSpacing(12)
            for index, path in enumerate(files, start=1):
                version_layout.addWidget(self._build_document_row(index, path, str(version["exported_at"])))
            content.setVisible(False)
            toggle.toggled.connect(lambda checked, selected=content: selected.setVisible(checked))
            self.version_button_group.addButton(toggle, version_index)
            self.version_contents.append(content)
            layout.addWidget(toggle)
            layout.addWidget(content)
            if version_index == len(versions):
                toggle.setChecked(True)
        return wrapper

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
        raw_versions = self.case.export_versions or self._scan_versions_from_case_dir()
        if not raw_versions and self.case.export_dir:
            raw_versions = [
                {
                    "name": "bản 1",
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
                        "name": str(version.get("name") or f"bản {index}"),
                        "exported_at": str(version.get("exported_at", "")),
                        "export_dir": str(export_dir or ""),
                        "files": files,
                    }
                )
        if not versions and self.case.export_versions:
            scanned_versions = self._scan_versions_from_case_dir()
            for index, version in enumerate(scanned_versions, start=1):
                export_dir = Path(str(version.get("export_dir", ""))) if version.get("export_dir") else None
                files = self._document_paths(export_dir, [])
                if files:
                    versions.append(
                        {
                            "name": str(version.get("name") or f"bản {index}"),
                            "exported_at": str(version.get("exported_at", "")),
                            "export_dir": str(export_dir or ""),
                            "files": files,
                        }
                    )
        return versions

    def _scan_versions_from_case_dir(self) -> list[dict[str, object]]:
        case_dir = Path(self.case.export_dir) if self.case.export_dir else None
        if not case_dir or not case_dir.exists():
            return []
        version_dirs = [
            child
            for child in case_dir.iterdir()
            if child.is_dir() and child.name.lower().startswith("bản ")
        ]
        if version_dirs:
            return [
                {
                    "name": version_dir.name,
                    "export_dir": str(version_dir),
                    "exported_at": self.case.exported_at,
                    "documents": [],
                }
                for version_dir in sorted(version_dirs, key=self._version_sort_key)
            ]
        return []

    def _version_sort_key(self, path: Path) -> tuple[int, str]:
        suffix = path.name.lower().replace("bản", "", 1).strip()
        return (int(suffix) if suffix.isdigit() else 9999, path.name)

    def _document_paths(self, export_dir: Path | None, generated_documents: list[str]) -> list[Path]:
        if not export_dir or not export_dir.exists():
            return []

        if generated_documents:
            paths: list[Path] = []
            for file_name in generated_documents:
                candidate = Path(file_name)
                if candidate.is_absolute():
                    paths.append(candidate)
                    continue
                paths.append(export_dir / file_name)
                if not (export_dir / file_name).exists():
                    matches = sorted(export_dir.rglob(Path(file_name).name))
                    paths.extend(matches)
        else:
            paths = sorted(export_dir.glob("*.docx"))
            if not paths:
                paths = sorted(export_dir.rglob("*.docx"))
        unique_paths: list[Path] = []
        seen: set[str] = set()
        for path in paths:
            if not path.exists() or path.suffix.lower() != ".docx":
                continue
            key = str(path.resolve())
            if key not in seen:
                unique_paths.append(path)
                seen.add(key)
        return unique_paths

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

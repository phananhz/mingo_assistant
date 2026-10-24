from __future__ import annotations

from pathlib import Path
from dataclasses import replace
from copy import deepcopy

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFileDialog,
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

from mingo_assistant.application.form_migrations import REGISTRATION_CASE_TYPES
from mingo_assistant.core.text_normalization import uppercase_authorized_person_name
from mingo_assistant.models.case import CaseSummary
from mingo_assistant.services.documents.exported_dossier_move import move_exported_dossier


class BusinessRegistrationDocumentsView(QWidget):
    def __init__(
        self, case: CaseSummary, on_back, on_edit,
        description: str = "Kiểm tra các file Word đã điền và mở nhanh phiên bản bạn cần.",
        on_save=None,
    ) -> None:
        super().__init__()
        self.case = case
        self.on_back = on_back
        self.on_edit = on_edit
        self.on_save = on_save
        self.description = description
        self.version_contents: list[QWidget] = []
        self.displayed_versions: list[dict[str, object]] = []
        self.version_button_group = QButtonGroup(self)
        self.version_button_group.setExclusive(True)
        self._build_ui()

    def _build_ui(self) -> None:
        root = self.layout()
        if root is None:
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
        description_text = (
            "Kiểm tra các file Word của lần xuất gần nhất và mở nhanh file bạn cần."
            if self._latest_only()
            else self.description
        )
        description = QLabel(description_text)
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
        self.move_button = QPushButton("Chuyển nơi lưu…")
        self.move_button.setObjectName("GhostButton")
        self.move_button.setToolTip("Chuyển bộ hồ sơ đang xem đến nơi khác, không giữ bản trùng và không đổi thư mục xuất mặc định.")
        self.move_button.clicked.connect(self._move_selected_version)
        actions.addWidget(self.move_button)
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
            (("Tên địa điểm kinh doanh" if self.case.case_type == "Địa điểm kinh doanh - Lập mới" else "Tên doanh nghiệp"), self.case.company_name),
            (("Người nộp hồ sơ" if self.case.case_type == "Địa điểm kinh doanh - Lập mới" else "Người ủy quyền"), self._authorized_person_name()),
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
        return uppercase_authorized_person_name(name or self.case.owner) or "Chưa chọn"

    def _build_documents_v2(self) -> QWidget:
        wrapper = QFrame()
        wrapper.setObjectName("DocumentsPanel")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)

        versions = self._versions()
        self.displayed_versions = versions
        self.move_button.setEnabled(bool(versions) and self.on_save is not None)
        if self._latest_only():
            files = versions[-1]["files"] if versions else []
            exported_at = str(versions[-1]["exported_at"]) if versions else ""
            heading = QHBoxLayout()
            title = QLabel("File Word mới nhất")
            title.setObjectName("SectionTitle")
            count = QLabel(f"{len(files)} file Word")
            count.setObjectName("SectionCount")
            heading.addWidget(title)
            heading.addStretch(1)
            heading.addWidget(count)
            layout.addLayout(heading)

            hint = QLabel("Danh sách file Word của lần xuất gần nhất.")
            hint.setObjectName("SectionHint")
            layout.addWidget(hint)
            if not files:
                empty = QLabel("Hồ sơ này chưa có file Word đã xuất. Hãy sửa dữ liệu và xuất Word trước.")
                empty.setObjectName("EmptyDescription")
                empty.setWordWrap(True)
                layout.addWidget(empty)
                return wrapper
            for index, path in enumerate(files, start=1):
                layout.addWidget(self._build_document_row_v2(index, path, exported_at))
            return wrapper

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
            (("Tên địa điểm kinh doanh" if self.case.case_type == "Địa điểm kinh doanh - Lập mới" else "Tên doanh nghiệp"), self.case.company_name),
            (("Người nộp hồ sơ" if self.case.case_type == "Địa điểm kinh doanh - Lập mới" else "Người ủy quyền"), self._authorized_person_name()),
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
        return versions[-1:] if self._latest_only() else versions

    def _latest_only(self) -> bool:
        return self.case.case_type in REGISTRATION_CASE_TYPES

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
            version_dirs = sorted(version_dirs, key=self._version_sort_key)
            if self._latest_only():
                version_dirs = version_dirs[-1:]
            return [
                {
                    "name": version_dir.name,
                    "export_dir": str(version_dir),
                    "exported_at": self.case.exported_at,
                    "documents": [],
                }
                for version_dir in version_dirs
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

    def _selected_version_index(self) -> int:
        return len(self.displayed_versions) - 1 if self._latest_only() else self.version_button_group.checkedId() - 1

    def _case_with_relocated_version(self, index: int, target: Path) -> CaseSummary:
        selected = self.displayed_versions[index]
        source_dir = Path(selected["export_dir"]).resolve()
        versions = deepcopy(self.case.export_versions)
        if not versions:
            versions = [{"name": item["name"], "export_dir": item["export_dir"],
                         "exported_at": item["exported_at"], "documents": [path.name for path in item["files"]]}
                        for item in self.displayed_versions]
        found = False
        for version in versions:
            if version.get("export_dir") and Path(str(version["export_dir"])).resolve() == source_dir:
                version.update(export_dir=str(target), case_export_dir=str(target),
                               documents=[path.name for path in selected["files"]])
                found = True
        if not found:
            # Repair stale metadata when this view had to discover files on disk.
            versions.append({"name": selected["name"], "export_dir": str(target),
                             "case_export_dir": str(target), "exported_at": selected["exported_at"],
                             "documents": [path.name for path in selected["files"]]})
        updates = {"export_versions": versions}
        if index == len(self.displayed_versions) - 1:
            updates.update(export_dir=str(target), generated_documents=[path.name for path in selected["files"]])
        return replace(self.case, **updates)

    def _move_selected_version(self) -> None:
        if not self.displayed_versions:
            QMessageBox.warning(self, "Chưa có file hồ sơ", "Hồ sơ này chưa có file Word để chuyển.")
            return
        if self.on_save is None:
            QMessageBox.warning(self, "Không thể chuyển hồ sơ", "Chưa kết nối chức năng lưu đường dẫn hồ sơ.")
            return
        index = self._selected_version_index()
        if not 0 <= index < len(self.displayed_versions):
            QMessageBox.warning(self, "Chưa chọn phiên bản", "Vui lòng chọn phiên bản hồ sơ cần chuyển.")
            return
        version = self.displayed_versions[index]
        destination = QFileDialog.getExistingDirectory(self, "Chọn thư mục chuyển bộ hồ sơ đến")
        if not destination:
            return
        updated_case = None
        def commit(target):
            nonlocal updated_case
            updated_case = self._case_with_relocated_version(index, target)
            self.on_save(updated_case)
        self.move_button.setEnabled(False)
        try:
            target = move_exported_dossier(
                version["files"], Path(destination), f"{self.case.company_name} - {version['name']}", commit,
            )
        except Exception as exc:
            QMessageBox.warning(self, "Không thể chuyển hồ sơ", str(exc))
            return
        finally:
            self.move_button.setEnabled(True)
        self.case = updated_case
        self._refresh_after_move(index)
        QMessageBox.information(
            self, "Đã chuyển nơi lưu hồ sơ",
            f"Đã chuyển {len(version['files'])} file Word đến:\n{target}\n\n"
            "Các file đã được chuyển khỏi nơi cũ. Thư mục xuất mặc định không thay đổi.",
        )

    def _refresh_after_move(self, selected_index: int) -> None:
        root = self.layout()
        while root.count():
            widget = root.takeAt(0).widget()
            if widget:
                widget.hide()
                widget.deleteLater()
        self.version_button_group.deleteLater()
        self.version_button_group = QButtonGroup(self)
        self.version_button_group.setExclusive(True)
        self.version_contents = []
        self._build_ui()
        button = self.version_button_group.button(selected_index + 1)
        if button:
            button.setChecked(True)

    def _open_file(self, path: Path) -> None:
        if not path.exists():
            QMessageBox.warning(self, "Không tìm thấy file", f"File không còn tồn tại:\n{path}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _open_export_folder(self) -> None:
        index = self._selected_version_index()
        selected = self.displayed_versions[index] if 0 <= index < len(self.displayed_versions) else None
        folder = selected["export_dir"] if selected else self.case.export_dir
        export_dir = Path(folder) if folder else None
        if not export_dir or not export_dir.exists():
            QMessageBox.warning(self, "Chưa có thư mục", "Hồ sơ này chưa có thư mục xuất.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(export_dir)))

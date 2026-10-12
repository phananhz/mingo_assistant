"""Adapt the existing industry row UI to one independent amendment table."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QWidget

from mingo_assistant.ui.views.business_registration_workspace import BusinessRegistrationWorkspace


class _IndustryCards(QFrame):
    # Reuse the established row builder, including its editors, validation,
    # buttons and styling. Its field registry remains local to this adapter.
    _add_business_line_row = BusinessRegistrationWorkspace._add_business_line_row

    def __init__(self, owner, kind, name_header):
        super().__init__()
        self.owner = owner
        self.kind = kind
        self.fields = {}
        self.business_line_rows = []
        self.number_labels = []
        self.setObjectName("BusinessLineTable")
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(0)
        self.grid.setVerticalSpacing(8)
        self.setFixedHeight(54)
        for column, text in enumerate(("STT", name_header, "Mã ngành nghề", "Ghi chú" if kind == "remove" else "Ngành nghề chính", "Xóa")):
            label = QLabel(text)
            label.setObjectName("TableHeader")
            label.setAlignment(Qt.AlignCenter)
            label.setFixedHeight(54)
            self.grid.addWidget(label, 0, column)
        self.grid.setColumnMinimumWidth(0, 55)
        for column, stretch in ((1, 5), (2, 2), (3, 2 if kind == "remove" else 1), (4, 1)):
            self.grid.setColumnStretch(column, stretch)

    def rowCount(self):
        return len(self.business_line_rows)

    def append_row(self, index=None):
        index = index or self.rowCount() + 1
        self._add_business_line_row(self.grid, index, visible=True)
        row = self.business_line_rows[-1]
        frame = row.cells[0]
        self.grid.addWidget(frame, index, 0, 1, 5)
        grid = frame.layout()
        for column in range(3, -1, -1):
            item = grid.itemAtPosition(0, column)
            grid.addWidget(item.widget(), 0, column + 1)
        grid.setColumnMinimumWidth(0, 35)
        grid.setColumnStretch(0, 0)
        for column, stretch in ((1, 5), (2, 2), (3, 2 if self.kind == "remove" else 1), (4, 1)):
            grid.setColumnStretch(column, stretch)
        number = QLabel("")
        number.setAlignment(Qt.AlignCenter)
        grid.addWidget(number, 0, 0)
        self.number_labels.append(number)
        prefix = f"amendment_line_{self.kind}_{index}_"
        self.owner.fields.update({prefix + "name": row.name_field, prefix + "detail": row.detail_field, prefix + "code": row.code_field})
        if self.kind == "remove":
            grid.removeWidget(row.main_checkbox)
            row.main_checkbox.hide()
            note = QTextEdit()
            note.setAcceptRichText(False)
            note.setPlaceholderText("Ghi chú (nếu có)")
            note.setFixedHeight(124)
            note.textChanged.connect(self._refresh_preview)
            grid.addWidget(note, 0, 3)
            self.owner.fields[prefix + "note"] = note
        else:
            self.owner.fields[prefix + "main"] = row.main_checkbox
            self.owner.amendment_main_line_boxes[prefix + "main"] = row.main_checkbox
        self._refresh_preview()

    def clear_rows(self):
        for row in self.business_line_rows:
            frame = row.cells[0]
            # Page changes remove the current editors. Block their focus-loss
            # signals first so duplicate-code warnings are not emitted for
            # rows the user is no longer editing (which can otherwise create
            # dozens of modal dialogs when a large dossier changes page).
            for child in frame.findChildren(QWidget):
                child.blockSignals(True)
            self.grid.removeWidget(frame)
            frame.hide()
            frame.deleteLater()
        self.business_line_rows.clear()
        self.number_labels.clear()
        self.fields.clear()

    def _set_business_line_row_visible(self, index, visible):
        self.business_line_rows[-1].cells[0].setVisible(visible)

    def _refresh_preview(self):
        if getattr(self.owner, "_initializing", True):
            return
        self.owner._refresh_amendment_line_numbers()
        self.owner._refresh_preview()

    def _set_main_business_line(self, index, state):
        self.owner._select_amendment_main_line(f"amendment_line_{self.kind}_{index}_main", state == Qt.CheckState.Checked.value)

    def _delete_business_line_row(self, index):
        self.owner._confirm_delete_amendment_line_row(self.kind, index - 1)

    def _warn_duplicate_business_line_code(self, index):
        if not getattr(self.owner, "_initializing", True):
            self.owner._warn_amendment_line_duplicate(self.kind, index)


class AmendmentIndustryTable(_IndustryCards):
    """Keep all rows in data; construct only the cards on the selected page."""

    PAGE_SIZE = 50  # Display size, not a limit on entered industries.

    def __init__(self, owner, kind, name_header):
        super().__init__(owner, kind, name_header)
        self.rows = []
        self.page = 0
        self.visible_indices = []
        self._rendered_indices = None
        self.pager = QWidget(self)
        controls = QHBoxLayout(self.pager)
        controls.setContentsMargins(0, 0, 0, 0)
        self.page_label = QLabel()
        self.previous_button = QPushButton("← Trang trước")
        self.next_button = QPushButton("Trang sau →")
        self.previous_button.clicked.connect(lambda: self.show_page(self.page - 1))
        self.next_button.clicked.connect(lambda: self.show_page(self.page + 1))
        controls.addWidget(self.page_label, 1)
        controls.addWidget(self.previous_button)
        controls.addWidget(self.next_button)
        self.pager.hide()

    def rowCount(self):
        return len(self.rows)

    def snapshot_rows(self):
        for index in self.visible_indices:
            prefix = f"amendment_line_{self.kind}_{index}_"
            for suffix in ("name", "detail", "code", "note" if self.kind == "remove" else "main"):
                self.rows[index - 1][suffix] = BusinessRegistrationWorkspace._field_value(self.owner, prefix + suffix)
        return [dict(row) for row in self.rows]

    def append_row(self):
        self.rows.append({})
        if not getattr(self.owner, "_initializing", True):
            self.show_page((self.rowCount() - 1) // self.PAGE_SIZE)

    def resize_rows(self, count):
        self.snapshot_rows()
        self.rows = self.rows[:count] + [{} for _ in range(max(0, count - self.rowCount()))]
        self.refresh_page()

    def show_page(self, page):
        self.snapshot_rows()
        self.page = max(0, min(page, max(0, (self.rowCount() - 1) // self.PAGE_SIZE)))
        self.refresh_page()
        self._refresh_preview()

    def _clear_visible_rows(self):
        prefix = f"amendment_line_{self.kind}_"
        for registry in (self.owner.fields, self.owner.amendment_main_line_boxes):
            for key in list(registry):
                if key.startswith(prefix):
                    registry.pop(key)
        super().clear_rows()
        self.visible_indices.clear()

    def refresh_page(self):
        self.page = min(self.page, max(0, (self.rowCount() - 1) // self.PAGE_SIZE))
        start = self.page * self.PAGE_SIZE
        indices = list(range(start + 1, min(start + self.PAGE_SIZE, self.rowCount()) + 1))
        if indices != self._rendered_indices:
            initializing = self.owner._initializing
            self.owner._initializing = True
            try:
                self._clear_visible_rows()
                for position, index in enumerate(indices, 1):
                    super().append_row(index)
                    self.grid.addWidget(self.business_line_rows[-1].cells[0], position, 0, 1, 5)
                    self.visible_indices.append(index)
                    prefix = f"amendment_line_{self.kind}_{index}_"
                    for suffix, value in self.rows[index - 1].items():
                        BusinessRegistrationWorkspace._set_field(self.owner, prefix + suffix, value)
                self._rendered_indices = indices
            finally:
                self.owner._initializing = initializing
        paged = self.rowCount() > self.PAGE_SIZE
        self.grid.removeWidget(self.pager)
        if paged:
            self.grid.addWidget(self.pager, len(indices) + 1, 0, 1, 5)
        self.pager.setVisible(paged)
        self.page_label.setText(f"Dòng {start + 1}–{start + len(indices)} / {self.rowCount()} ngành nghề")
        self.previous_button.setEnabled(self.page > 0)
        self.next_button.setEnabled(start + self.PAGE_SIZE < self.rowCount())
        self.setFixedHeight(54 + len(indices) * 164 + (48 if paged else 0))

    def clear_rows(self):
        self._clear_visible_rows()
        self.rows.clear()
        self._rendered_indices = None
        self.refresh_page()

    def _refresh_preview(self):
        if getattr(self.owner, "_initializing", True):
            return
        self.snapshot_rows()
        self.owner._refresh_amendment_line_numbers()
        self.owner._refresh_preview()

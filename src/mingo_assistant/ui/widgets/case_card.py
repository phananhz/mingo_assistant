"""Shared case card layout, using the application's existing theme hooks."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget

CASE_CARD_WIDTH = 220
CASE_CARD_GAP = 18


def format_card_title(title, metrics, width, max_lines=3):
    words = title.split()
    if not words:
        return ""
    lines = []
    index = 0
    while index < len(words) and len(lines) < max_lines:
        line = words[index]
        index += 1
        while index < len(words) and metrics.horizontalAdvance(f"{line} {words[index]}") <= width:
            line = f"{line} {words[index]}"
            index += 1
        lines.append(line)
    if index < len(words):
        remaining = f"{lines[-1]} {' '.join(words[index:])}".rstrip()
        while remaining and metrics.horizontalAdvance(f"{remaining}...") > width:
            remaining = remaining[:-1].rstrip()
        lines[-1] = f"{remaining}..."
    return "\n".join(lines)


def meta_row(label, value):
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    caption = QLabel(label)
    caption.setObjectName("MetaText")
    text = QLabel(value)
    text.setObjectName("MetaText")
    text.setTextFormat(Qt.PlainText)
    text.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    text.setWordWrap(True)
    layout.addWidget(caption)
    layout.addWidget(text, 1)
    return row


def build_case_card(case, *, display_name, format_title, metadata, on_open, on_edit, on_delete, on_select=None, subtitle=None):
    card = QFrame()
    card.setObjectName("Card")
    card.setFixedSize(CASE_CARD_WIDTH, 344)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(0, 0, 0, 14)
    layout.setSpacing(0)
    header = QFrame()
    header.setObjectName("CardHeader")
    header.setFixedHeight(112)
    header_layout = QVBoxLayout(header)
    header_layout.setContentsMargins(14, 12, 14, 12)
    top = QHBoxLayout()
    badge = QLabel(case.warning or case.status)
    badge.setObjectName("WarningBadge" if case.warning else "StatusBadge")
    badge.setTextFormat(Qt.PlainText)
    badge.setAlignment(Qt.AlignCenter)
    badge.setFixedHeight(24)
    delete = QPushButton("Xóa")
    delete.setObjectName("HeaderDeleteButton")
    delete.clicked.connect(lambda checked=False: on_delete(case))
    top.addWidget(badge, 0, Qt.AlignLeft | Qt.AlignTop)
    top.addStretch(1)
    top.addWidget(delete, 0, Qt.AlignRight | Qt.AlignTop)
    header_layout.addLayout(top)
    header_layout.addStretch(1)
    icon = QLabel("DOC")
    icon.setStyleSheet("font-size: 28px; font-weight: 800; color: rgba(255,255,255,0.78);")
    icon.setAlignment(Qt.AlignCenter)
    header_layout.addWidget(icon)
    header_layout.addStretch(1)
    layout.addWidget(header)
    body = QVBoxLayout()
    body.setContentsMargins(14, 14, 14, 0)
    body.setSpacing(8)
    title = QLabel()
    title.setObjectName("CardTitle")
    title.setTextFormat(Qt.PlainText)
    title.setToolTip(case.name)
    title.setText(format_title(display_name, title.fontMetrics(), CASE_CARD_WIDTH - 28))
    title.setWordWrap(False)
    title.setMinimumHeight(title.fontMetrics().lineSpacing() * 3)
    body.addWidget(title)
    subtitle_label = QLabel(subtitle if subtitle is not None else case.case_type.upper())
    subtitle_label.setObjectName("CardSubtitle")
    subtitle_label.setTextFormat(Qt.PlainText)
    subtitle_label.setWordWrap(True)
    body.addWidget(subtitle_label)
    body.addSpacing(4)
    for label, value in metadata:
        body.addWidget(meta_row(label, value))
    body.addStretch(1)
    actions = QHBoxLayout()
    open_button = QPushButton("Mở")
    open_button.setObjectName("GhostButton")
    open_button.clicked.connect(lambda checked=False: on_open(case))
    edit = QPushButton("Sửa")
    edit.setObjectName("GhostButton")
    edit.clicked.connect(lambda checked=False: on_edit(case))
    actions.addWidget(open_button)
    actions.addWidget(edit)
    body.addLayout(actions)

    def select(event):
        if on_select is not None:
            on_select(case)
        QFrame.mousePressEvent(card, event)

    card.mousePressEvent = select
    layout.addLayout(body, 1)
    return card

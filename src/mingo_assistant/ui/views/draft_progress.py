"""Crash recovery for editors, separate from confirmed OCR profiles and DOCX rules."""
from __future__ import annotations

from dataclasses import asdict, replace
from functools import wraps
import json
import logging
from pathlib import Path

from PySide6.QtCore import QObject, QSignalBlocker, QTimer
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QLineEdit, QPushButton, QTableWidget, QTextEdit

from mingo_assistant.models.business_registration import OcrPerson


PROGRESS_KEY = "editor_draft_progress_v1"
logger = logging.getLogger(__name__)


def checkpoint_scan(method):
    """Checkpoint before the blocking scanner starts, and after all result edits."""
    @wraps(method)
    def wrapped(owner, *args, **kwargs):
        workspace = getattr(owner, "owner", owner)
        progress = getattr(workspace, "draft_progress", None)
        if progress is None:
            return method(owner, *args, **kwargs)
        if progress.active_scan is not None:
            return
        if method.__name__ in {"_run_qr_scan", "_run_auto_photo_scan", "_scan_organization_document", "scan_document"}:
            kind = {"_run_qr_scan": "cccd", "_run_auto_photo_scan": "auto"}.get(
                method.__name__, workspace.organization_document_service.DOCUMENT_TYPE,
            )
            return workspace._start_background_scan(str(args[0]), kind)
        index = workspace.current_person_index
        if args and isinstance(args[0], (str, Path)):
            workspace.ocr_people[index].front_path = str(args[0])
        progress.begin_scan(index)
        try:
            return method(owner, *args, **kwargs)
        finally:
            progress.end_scan(index)
    return wrapped


class DraftProgress(QObject):
    """Use the existing atomic case repository; never confirm a recognition result."""

    SELECTOR_NAMES = (
        "organization_owner_profile_selector", "organization_representative_selector",
        "parent_organization_selector", "update_organization_selector", "brc_profile_selector",
        "beneficial_owner_list_selector",
    )
    BUFFER_NAMES = (
        "_selected_update_organization", "_representative_company_code",
        "_household_owner_authorization_values", "member_contribution_input_modes",
        "_member_contribution_auto_index",
    )

    def __init__(self, workspace, save):
        super().__init__(workspace)
        self.workspace = workspace
        self.save = save
        self.busy = True
        self.stopped = False
        self.scans: dict[str, dict] = {}
        self.active_scan: int | None = None
        self.last_error = ""
        self._wired = set()
        self.pending = QTimer(self)
        self.pending.setSingleShot(True)
        self.pending.setInterval(0)
        self.pending.timeout.connect(self._safe_flush)
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self._poll)
        self.notice = QLabel("Tự lưu tiến độ khi có dữ liệu.", workspace)
        self.notice.setObjectName("DraftSaveStatus")
        self.notice.setWordWrap(True)
        workspace.layout().addWidget(self.notice)
        self._restore()
        self.baseline = self._capture()
        self.last_snapshot = self.baseline
        self.started = bool(workspace.case and workspace.case.status == "Bản nháp")
        self.busy = False
        self._wire_inputs()
        self.timer.start()

    def _wire_inputs(self):
        # Dynamic member/industry widgets are discovered on each poll as well.
        for widget in self.workspace.findChildren(QObject):
            if widget in self._wired:
                continue
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(self.schedule)
            elif isinstance(widget, QTextEdit) and not widget.isReadOnly():
                widget.textChanged.connect(self.schedule)
            elif isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self.schedule)
            elif isinstance(widget, QCheckBox):
                widget.toggled.connect(self.schedule)
            elif isinstance(widget, QPushButton):
                widget.clicked.connect(self.schedule)
            elif isinstance(widget, QTableWidget):
                widget.itemChanged.connect(self.schedule)
            else:
                continue
            self._wired.add(widget)
            widget.destroyed.connect(lambda _=None, item=widget: self._wired.discard(item))

    def schedule(self, *_):
        if not self.busy and not self.stopped:
            self.pending.start()

    def _poll(self):
        self._wire_inputs()
        self._safe_flush()

    @staticmethod
    def _read(widget):
        if isinstance(widget, QLineEdit):
            return widget.text()
        if isinstance(widget, QTextEdit):
            return widget.toPlainText()
        if isinstance(widget, QCheckBox):
            return "X" if widget.isChecked() else ""
        if isinstance(widget, QComboBox):
            return widget.currentText()
        return ""

    def _capture(self):
        w = self.workspace
        values = dict(w.form_values(apply_defaults=False))
        values.pop(PROGRESS_KEY, None)
        fields = {key: self._read(field) for key, field in w.fields.items()}
        # Keep partial input/whitespace and inactive-owner fields, not export defaults.
        values.update(fields)
        people = [asdict(person) for person in w.ocr_people]
        current = people[w.current_person_index]
        if current["recognition_type"] == "individual":
            current["data"] = w._cccd_result_values()
        elif current["recognition_type"] == "organization":
            current["organization_data"] = w._organization_result_values()
        current["raw_text"] = w.raw_ocr_text.toPlainText()
        selectors = {}
        for name in ("person_fill_selectors",):
            for key, combo in getattr(w, name, {}).items():
                selectors[key] = combo.currentData()
        named_selectors = {
            name: combo.currentData() for name in self.SELECTOR_NAMES
            if isinstance(combo := getattr(w, name, None), QComboBox)
        }
        return {
            "version": 1, "values": values, "fields": fields, "people": people,
            "current_person": w.current_person_index,
            "section": w.form_stack.currentIndex(),
            "scan_type": w.scan_document_type_input.currentData(),
            "engine": w.ocr_engine_input.currentText(),
            "export_root": str(w.selected_export_root or ""),
            "selectors": selectors, "scans": json.loads(json.dumps(self.scans)),
            "named_selectors": named_selectors,
            "buffers": json.loads(json.dumps({name: getattr(w, name) for name in self.BUFFER_NAMES if hasattr(w, name)})),
            "ocr_fields": {key: self._read(field) for key, field in w.ocr_card_fields.items()},
            "organization_fields": {key: self._read(field) for key, field in w.organization_card_fields.items()},
        }

    @staticmethod
    def _content(snapshot):
        values = {
            key: value for key, value in snapshot["values"].items()
            if not (key.startswith("change_") and key.endswith("_selected"))
            and not key.startswith("person_") and key != "people_count"
        }
        # Empty person slots, role choices and dropdown navigation aren't dossier data.
        people = [
            {key: person[key] for key in ("front_path", "back_path", "data", "organization_data", "raw_text")}
            for person in snapshot["people"]
            if person["front_path"] or person["back_path"] or person["data"]
            or person["organization_data"] or person["raw_text"]
        ]
        return values, people

    def _has_new_content(self, snapshot):
        old_values, old_people = self._content(self.baseline)
        values, people = self._content(snapshot)
        return people != old_people or any(
            str(value).strip() and value != old_values.get(key, "")
            for key, value in values.items()
            if key not in {"member_count", "people_count"} and not key.endswith("_row_count")
        )

    def flush(self, *, force=False, save=None):
        if self.busy:
            return
        self.busy = True
        try:
            snapshot = self._capture()
            changed = self._content(snapshot) != self._content(self.last_snapshot)
            if not self.started:
                if self.workspace.case is None:
                    if not self._has_new_content(snapshot):
                        return
                elif not changed:
                    return
            if not force and snapshot == self.last_snapshot:
                return
            summary = self.workspace.build_case_summary(status="Bản nháp", warning=None)
            values = dict(snapshot["values"])
            values[PROGRESS_KEY] = json.dumps(snapshot, ensure_ascii=False)
            summary = replace(summary, form_values=values, status="Bản nháp", warning=None)
            (save or self.save)(summary)
            self.workspace.case = summary
            self.started = True
            self.last_snapshot = snapshot
            self.last_error = ""
            self.notice.setText("Đã tự lưu tiến độ · Bản nháp")
        finally:
            self.busy = False

    def _safe_flush(self):
        if self.stopped:
            return
        try:
            self.flush()
        except Exception as exc:
            # No document/person data in logs or messages; do not silently claim success.
            logger.error("Draft progress save failed (%s)", type(exc).__name__)
            self.last_error = "Không thể tự lưu tiến độ. Kiểm tra dung lượng và quyền ghi, rồi thử lưu lại."
            self.notice.setText(self.last_error)

    def begin_scan(self, index):
        self.active_scan = index
        self.scans[str(index)] = {
            "state": "running", "percent": 0, "status": "Đang chuẩn bị quét",
            "scan_type": self.workspace.scan_document_type_input.currentData(),
            "engine": self.workspace.ocr_engine_input.currentText(),
        }
        self._safe_flush()

    def update_scan(self, percent, status):
        if self.active_scan is not None:
            self.scans[str(self.active_scan)].update(percent=percent, status=status)
            self._safe_flush()

    def end_scan(self, index, *, interrupted=False):
        state = self.scans[str(index)]
        state["state"] = "complete" if state["percent"] == 100 and not interrupted else "interrupted"
        self.active_scan = None
        self._safe_flush()

    def accept_export(self):
        self.last_snapshot = self._capture()
        self.started = False
        self.pending.stop()

    def stop(self):
        self.stopped = True
        self.timer.stop()
        self.pending.stop()

    def _restore(self):
        try:
            self._restore_snapshot()
        except (KeyError, TypeError, ValueError, AttributeError):
            # The optional UI checkpoint must not make a readable case unopenable.
            logger.warning("Invalid optional editor checkpoint; using stored dossier fields")
            self.scans = {}
            self.notice.setText("Đã mở dữ liệu hồ sơ; không thể khôi phục đầy đủ trạng thái giao diện cũ.")

    def _restore_snapshot(self):
        w = self.workspace
        if w.case is None or w.case.status != "Bản nháp":
            return
        try:
            state = json.loads(w.case.form_values.get(PROGRESS_KEY, "{}"))
        except (ValueError, TypeError):
            return
        if not isinstance(state, dict) or state.get("version") != 1:
            return
        # Seed/restore methods may migrate, infer selections or apply defaults.
        # Reapply the exact editor buffer afterwards without triggering autofill.
        if not isinstance(state.get("scans", {}), dict):
            raise ValueError("Invalid scan checkpoint")
        self.scans = state.get("scans", {})
        for scan in self.scans.values():
            if scan.get("state") == "running":
                scan["state"] = "interrupted"
        people = state.get("people", [])
        for name, value in state.get("buffers", {}).items():
            if name in self.BUFFER_NAMES:
                if name == "member_contribution_input_modes":
                    value = {int(key): mode for key, mode in value.items()}
                setattr(w, name, value)
        if people:
            w.ocr_people = [OcrPerson(**person) for person in people]
            w.current_person_index = min(max(0, state.get("current_person", 0)), len(people) - 1)
            w._restore_case_organization_profiles()
            w._refresh_people_buttons()
            w._refresh_selected_person_images()
        for name in ("_refresh_parent_organization_selector", "_refresh_update_organization_selector", "_refresh_brc_profile_selector"):
            hook = getattr(w, name, None)
            if callable(hook):
                hook()
        for key, value in state.get("fields", {}).items():
            field = w.fields.get(key)
            if field is not None:
                with QSignalBlocker(field):
                    w._set_field(key, value)
        for name, mapping in (("ocr_fields", w.ocr_card_fields), ("organization_fields", w.organization_card_fields)):
            for key, value in state.get(name, {}).items():
                field = mapping.get(key)
                if field is not None:
                    with QSignalBlocker(field):
                        if isinstance(field, QTextEdit):
                            field.setPlainText(value)
                        elif isinstance(field, QComboBox):
                            field.setCurrentIndex(field.findText(value))
                        else:
                            field.setText(value)
        for key, data in state.get("selectors", {}).items():
            combo = w.person_fill_selectors.get(key)
            if combo is not None:
                with QSignalBlocker(combo):
                    combo.setCurrentIndex(max(0, combo.findData(data)))
        for name, data in state.get("named_selectors", {}).items():
            combo = getattr(w, name, None) if name in self.SELECTOR_NAMES else None
            if isinstance(combo, QComboBox):
                with QSignalBlocker(combo):
                    combo.setCurrentIndex(max(0, combo.findData(data)))
        restore_dossier_selectors = getattr(w, "_restore_dossier_selectors", None)
        if callable(restore_dossier_selectors):
            restore_dossier_selectors()
        with QSignalBlocker(w.scan_document_type_input):
            w.scan_document_type_input.setCurrentIndex(max(0, w.scan_document_type_input.findData(state.get("scan_type"))))
        with QSignalBlocker(w.ocr_engine_input):
            w.ocr_engine_input.setCurrentText(state.get("engine", ""))
        if state.get("export_root"):
            w.selected_export_root = Path(state["export_root"])
        section = state.get("section", 0)
        if 0 <= section < w.form_stack.count():
            w._select_form_section(section)
        for name in ("change_forms", "amendment_change_forms"):
            for key, form in getattr(w, name, {}).items():
                field = w.fields.get(key)
                if isinstance(field, QCheckBox):
                    form.setVisible(field.isChecked())
        if hasattr(w, "change_empty_label"):
            w.change_empty_label.setVisible(not any(w.fields[key].isChecked() for key in w.change_forms))
        if hasattr(w, "change_option_cards"):
            w._refresh_change_option_cards()
        self.show_scan_state()
        self.notice.setText("Đã khôi phục tiến độ · Bản nháp")

    def show_scan_state(self):
        w = self.workspace
        scan = self.scans.get(str(w.current_person_index), {})
        if scan.get("state") == "interrupted":
            if "scan_type" in scan:
                with QSignalBlocker(w.scan_document_type_input):
                    w.scan_document_type_input.setCurrentIndex(max(0, w.scan_document_type_input.findData(scan["scan_type"])))
            if "engine" in scan:
                with QSignalBlocker(w.ocr_engine_input):
                    w.ocr_engine_input.setCurrentText(scan["engine"])
            w.ocr_progress.setValue(scan.get("percent", 0))
            w.ocr_progress.setFormat(f"{scan.get('percent', 0)}%")
            w.ocr_status_label.setText("Lần quét trước bị gián đoạn. Bấm Quét tài liệu để chạy lại tài liệu này.")
            w.ocr_eta_label.setText("Đã khôi phục tài liệu và các kết quả đã có")

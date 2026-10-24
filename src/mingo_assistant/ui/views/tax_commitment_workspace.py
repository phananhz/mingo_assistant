"""Independent workflow for the general tax-closure commitment only."""
from dataclasses import replace
import json
import shutil
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QSignalBlocker
from PySide6.QtWidgets import QGroupBox, QGridLayout, QVBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton, QMessageBox

from mingo_assistant.ui.widgets.combo_box import NoWheelComboBox
from mingo_assistant.ui.views.tax_template_workspace import TaxTemplateWorkspace
from mingo_assistant.ui.views.business_registration_workspace import BusinessRegistrationWorkspace
from mingo_assistant.services.organization_documents.tax_commitment_document_service import TaxCommitmentDocumentService
from mingo_assistant.services.documents.tax_commitment_generator import TaxCommitmentGenerator
from mingo_assistant.services.documents.document_file_access import ensure_documents_closed


class TaxCommitmentWorkspace(TaxTemplateWorkspace):
    ORGANIZATION_SAVED_MESSAGE = "Đã áp dụng dữ liệu ERC vào hồ sơ. Chọn người nộp thuế và nhập cơ quan tiếp nhận để xuất Word."

    def __init__(self, *args, **kwargs):
        self._accepted_tax = {}
        self._taxpayer_auto = ""
        super().__init__(*args, **kwargs)
        # A private service instance; never replace or mutate the shared container service.
        self.organization_document_service = TaxCommitmentDocumentService(self.address_parser, self.bundle_root)
        self.scan_document_type_input.setCurrentIndex(self.scan_document_type_input.findData("erc"))
        self._show_recognition_result("erc")

    def _build_ui(self):
        super()._build_ui()
        page_layout = self.findChild(QGroupBox, "TaxCommitmentForm")
        # The scanner remains above the actual form fields.
        if page_layout:
            panel = page_layout.parentWidget()
            page = panel.parentWidget()
            panel.layout().removeWidget(page_layout)
            page.layout().addWidget(page_layout)

    def _build_header(self):
        header = super()._build_header()
        location = QPushButton("Chọn nơi lưu")
        location.clicked.connect(self._choose_export_root)
        export = QPushButton("Xuất hồ sơ")
        export.setObjectName("PrimaryButton")
        export.clicked.connect(self._export_documents)
        header.addWidget(location)
        header.addWidget(export)
        return header

    def _build_form_section(self):
        panel = super()._build_form_section()
        # Keep the dossier name, replace the preparation-only notice.
        panel.layout().itemAt(panel.layout().count() - 1).widget().setVisible(False)
        group = QGroupBox("Thông tin dùng để điền hồ sơ")
        group.setObjectName("TaxCommitmentForm")
        outer = QVBoxLayout(group)
        outer.setContentsMargins(18, 26, 18, 18)
        outer.setSpacing(12)
        button = QPushButton("Thông tin cơ quan tiếp nhận và người nộp thuế")
        button.setObjectName("CompactPrimaryButton")
        outer.addWidget(button)
        section = self._build_regular_form_section("Thông tin cơ quan tiếp nhận và người nộp thuế", [
            ("tax_receiving_authority", "Cơ quan tiếp nhận"),
        ])
        section.layout().setContentsMargins(18, 26, 18, 18)
        section.layout().addWidget(self.fields["tax_receiving_authority"], 0, 1, 1, 3)
        self.taxpayer = NoWheelComboBox()
        self.taxpayer.setEditable(True)
        self.taxpayer.setInsertPolicy(NoWheelComboBox.NoInsert)
        self.taxpayer.setPlaceholderText("Chọn người đại diện pháp luật hoặc nhập họ tên")
        self.taxpayer.editTextChanged.connect(self._refresh_preview)
        self.fields["tax_taxpayer"] = self.taxpayer
        section.layout().addWidget(QLabel("Người nộp thuế/Người đại diện nộp thuế"), 1, 0)
        section.layout().addWidget(self.taxpayer, 1, 1, 1, 3)
        outer.addWidget(section)
        self.form_sections["Thông tin cơ quan tiếp nhận và người nộp thuế"] = section
        self.form_stack.addWidget(section)
        # The stack is not a second visual parent: the section already belongs to this group.
        outer.addWidget(self.form_stack)
        panel.layout().addWidget(group)
        return panel

    def _build_organization_result_section(self):
        group = QGroupBox("Thông tin tổ chức nhận diện")
        group.setObjectName("CccdResultCard")
        layout = QGridLayout(group)
        layout.setContentsMargins(18, 26, 18, 18)
        layout.setVerticalSpacing(10)
        self.organization_document_label = QLabel("Quét ERC và đối chiếu dữ liệu trước khi lưu.")
        self.organization_document_label.setWordWrap(True)
        layout.addWidget(self.organization_document_label, 0, 0, 1, 2)
        specs = [
            ("organization_owner_name", "Tên doanh nghiệp"),
            ("organization_owner_registration_number", "Mã số thuế"),
            ("organization_owner_issue_date", "Ngày đăng ký / Cấp ngày"),
            ("organization_owner_issue_place", "Nơi cấp"),
            ("organization_owner_address_full", "Địa chỉ trụ sở"),
            ("tax_legal_representatives", "Người đại diện pháp luật (mỗi người một dòng)"),
        ]
        for row, (key, label) in enumerate(specs, 1):
            layout.addWidget(QLabel(label), row, 0)
            if key == "organization_owner_issue_date":
                field = NoWheelComboBox()
                field.setEditable(True)
                field.setInsertPolicy(NoWheelComboBox.NoInsert)
                self.registration_date = field
            elif key in {"organization_owner_address_full", "tax_legal_representatives"}:
                field = QTextEdit()
                field.setFixedHeight(70)
            else:
                field = QLineEdit()
            self.organization_card_fields[key] = field
            layout.addWidget(field, row, 1)
        layout.setColumnStretch(1, 1)
        self.date_notice = QLabel()
        self.date_notice.setWordWrap(True)
        layout.addWidget(self.date_notice, 7, 0, 1, 2)
        save = QPushButton("Lưu dữ liệu tổ chức")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self._save_organization_profile)
        layout.addWidget(save, 8, 0, 1, 2, Qt.AlignRight)
        return group

    def _update_organization_result_fields(self, values):
        for key, field in self.organization_card_fields.items():
            if key == "organization_owner_issue_date":
                continue
            with QSignalBlocker(field):
                if isinstance(field, QTextEdit):
                    field.setPlainText(values.get(key, ""))
                else:
                    field.setText(values.get(key, ""))
        try:
            dates = json.loads(values.get("tax_registration_dates", "[]"))
        except (ValueError, TypeError):
            dates = []
        if not isinstance(dates, list):
            dates = []
        dates = [d for d in dates if isinstance(d, dict) and d.get("date") and d.get("label")]
        self._registration_dates = dates
        with QSignalBlocker(self.registration_date):
            self.registration_date.clear()
            self.registration_date.addItem("Chọn ngày đăng ký hoặc nhập dd/mm/yyyy", "")
            for date in dates:
                self.registration_date.addItem(f"{date['label']}: {date['date']}", date["date"])
            selected = values.get("tax_registration_selection", "")
            if selected:
                if self.registration_date.findText(selected) < 0:
                    self.registration_date.addItem(selected, values.get("organization_owner_issue_date", ""))
                self.registration_date.setCurrentText(selected)
            elif values.get("organization_owner_issue_date"):
                index = self.registration_date.findData(values["organization_owner_issue_date"])
                if index >= 0:
                    self.registration_date.setCurrentIndex(index)
                else:
                    self.registration_date.setCurrentText(values["organization_owner_issue_date"])
        notice = "ERC có nhiều ngày đăng ký. Vui lòng đối chiếu và chọn ngày cần sử dụng." if len(dates) > 1 else "Đối chiếu ngày đăng ký với ERC trước khi lưu."
        self.date_notice.setText(notice + "".join(f"\n{date['label']}: {date['date']}" for date in dates))

    def _organization_result_values(self):
        values = {}
        for key, field in self.organization_card_fields.items():
            if key == "organization_owner_issue_date":
                index = self.registration_date.currentIndex()
                matched = index >= 0 and self.registration_date.currentText() == self.registration_date.itemText(index)
                values[key] = str(self.registration_date.currentData() or "") if matched else self.registration_date.currentText().strip()
            else:
                values[key] = field.toPlainText().strip() if isinstance(field, QTextEdit) else field.text().strip()
        values["tax_registration_dates"] = json.dumps(getattr(self, "_registration_dates", []), ensure_ascii=False)
        values["tax_registration_selection"] = self.registration_date.currentText()
        return values

    def _save_organization_profile(self):
        values = self._organization_result_values()
        required = list(self.organization_card_fields)
        if any(not values.get(key, "").strip() for key in required):
            QMessageBox.warning(self, "Cần kiểm tra ERC", "Hãy kiểm tra đủ thông tin và chọn ngày đăng ký trước khi lưu.")
            return
        try:
            datetime.strptime(values["organization_owner_issue_date"], "%d/%m/%Y")
        except ValueError:
            QMessageBox.warning(self, "Ngày đăng ký chưa hợp lệ", "Chọn ngày đăng ký đã nhận diện hoặc nhập dd/mm/yyyy.")
            return
        person = self.ocr_people[self.current_person_index]
        person.organization_data = dict(values)
        person.saved_organization_data = dict(values)
        person.recognition_type = "organization"
        person.document_type = "erc"
        person.recognition_saved = True
        person.name = values["organization_owner_name"]
        self._refresh_people_buttons()
        self._accepted_tax = {key: values[source] for key, source in {
            "tax_company_name": "organization_owner_name", "tax_registration_number": "organization_owner_registration_number",
            "tax_issue_date": "organization_owner_issue_date", "tax_issue_place": "organization_owner_issue_place",
            "tax_address": "organization_owner_address_full",
        }.items()}
        names = list(dict.fromkeys(name.strip() for name in values["tax_legal_representatives"].splitlines() if name.strip()))
        current = self.taxpayer.currentText()
        untouched = not current.strip() or current == self._taxpayer_auto
        with QSignalBlocker(self.taxpayer):
            self.taxpayer.clear()
            self.taxpayer.addItems(names)
            self.taxpayer.setCurrentIndex(-1)
            self.taxpayer.setCurrentText((names[0] if len(names) == 1 else "") if untouched else current)
        self._taxpayer_auto = self.taxpayer.currentText() if untouched else ""
        self.draft_progress._safe_flush()
        QMessageBox.information(self, "Đã lưu dữ liệu tổ chức", self.ORGANIZATION_SAVED_MESSAGE)

    def _seed_from_case(self, case):
        super()._seed_from_case(case)
        values = case.form_values if case else {}
        self._accepted_tax = {key: values.get(key, "") for key in ("tax_company_name", "tax_registration_number", "tax_issue_date", "tax_issue_place", "tax_address")}
        self._taxpayer_auto = values.get("tax_taxpayer_auto", "")
        try:
            names = json.loads(values.get("tax_taxpayer_options", "[]"))
        except ValueError:
            names = []
        self.taxpayer.addItems([str(name) for name in names] if isinstance(names, list) else [])
        for key in ("tax_receiving_authority", "tax_taxpayer"):
            self._set_field(key, values.get(key, ""))

    def form_values(self, apply_defaults=True):
        values = super().form_values(apply_defaults)
        values.update(self._accepted_tax)
        values.update({key: self._field_value(key) for key in ("tax_receiving_authority", "tax_taxpayer")})
        values["tax_taxpayer_auto"] = self._taxpayer_auto
        values["tax_taxpayer_options"] = json.dumps([self.taxpayer.itemText(i) for i in range(self.taxpayer.count())], ensure_ascii=False)
        return values

    def _validation_issues(self, values):
        labels = {"tax_company_name": "Tên doanh nghiệp", "tax_registration_number": "Mã số thuế", "tax_issue_date": "Ngày đăng ký", "tax_issue_place": "Nơi cấp", "tax_address": "Địa chỉ trụ sở", "tax_receiving_authority": "Cơ quan tiếp nhận", "tax_taxpayer": "Người nộp thuế"}
        issues = [f"Chưa có: {label}" for key, label in labels.items() if not values.get(key, "").strip()]
        person = self.ocr_people[self.current_person_index]
        current = self._organization_result_values()
        if person.recognition_type == "organization" and (
            not person.recognition_saved or any(current.get(key, "") != person.saved_organization_data.get(key, "") for key in self.organization_card_fields)
        ):
            issues.append("Hãy lưu dữ liệu tổ chức sau khi kiểm tra hoặc sửa kết quả ERC.")
        return issues

    def _document_generator_class(self):
        return TaxCommitmentGenerator

    def _template_and_export_dirs(self):
        return self.bundle_root / "assets/templates/library/tax", self.selected_export_root or self.default_export_root

    def _export_case_name(self, values):
        return self._field_value("tax_dossier_name") or values.get("tax_company_name", "Cam kết chung")

    def _case_export_folder_name(self, values):
        return self.export_planner.safe_folder_name(self._export_case_name(values)) + "_" + self.case_id

    def _export_documents(self):
        if self._export_thread is not None and self._export_thread.isRunning():
            return
        values = self.form_values()
        if self._validation_issues(values):
            return BusinessRegistrationWorkspace._export_documents(self)
        _, export_root = self._template_and_export_dirs()
        case_root = self._case_export_dir(export_root, values)
        try:
            # A fresh marker excludes no existing version: check every old
            # Word export for this case before starting a new generation.
            for version in self.export_planner.previous_version_directories(
                case_root, case_root / "__pending_export__"
            ):
                ensure_documents_closed(self._version_word_files(version))
        except OSError as exc:
            QMessageBox.warning(self, "Cần đóng file Word trước khi xuất lại", str(exc))
            return
        return BusinessRegistrationWorkspace._export_documents(self)

    @staticmethod
    def _version_word_files(version_dir: Path) -> list[Path]:
        version_root = version_dir.resolve()
        return [
            path for path in version_dir.rglob("*")
            if path.is_file()
            and path.suffix.casefold() in {".doc", ".docx", ".docm"}
            and not path.name.startswith("~$")
            and path.resolve().is_relative_to(version_root)
        ]

    def _remove_previous_export_versions(self, case_export_dir: Path, keep_export_dir: Path) -> list[Path]:
        """Delete old exports only when the user has closed their Word files."""
        failures = []
        for version_dir in self.export_planner.previous_version_directories(
            case_export_dir, keep_export_dir
        ):
            try:
                ensure_documents_closed(self._version_word_files(version_dir))
                # Recheck containment immediately before recursive deletion.
                if version_dir.resolve().parent != case_export_dir.resolve():
                    raise OSError("Thư mục phiên bản cũ không còn thuộc hồ sơ này.")
                shutil.rmtree(version_dir)
            except OSError:
                failures.append(version_dir)
        return failures

    def build_case_summary(self, status="Bản nháp", warning=None, **kwargs):
        summary = super().build_case_summary(status=status, warning=warning)
        return replace(summary, **{key: value for key, value in kwargs.items() if key in {"condition", "export_dir", "exported_at", "generated_documents", "export_versions"}})

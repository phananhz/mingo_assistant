"""Tax dossier preparation: reuse document scanning, without Word generation."""
from dataclasses import replace
from datetime import datetime
import re

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QLineEdit, QVBoxLayout, QWidget, QScrollArea
from mingo_assistant.models.case import CaseSummary

from mingo_assistant.models.form_values import merge_form_values
from mingo_assistant.ui.views.business_registration_workspace import BusinessRegistrationWorkspace
from mingo_assistant.ui.views.template_library_catalog import TEMPLATE_GROUPS


TAX_TEMPLATE_CASE_TYPE = "Hồ sơ biểu mẫu thuế"


class TaxTemplateWorkspace(BusinessRegistrationWorkspace):
    def __init__(self, *args, **kwargs):
        case = kwargs.get("case")
        template_id = case.form_values.get("tax_template_id", "") if case else TEMPLATE_GROUPS[1].items[0].id
        self.tax_template = next((item for item in TEMPLATE_GROUPS[1].items if item.id == template_id), None)
        if self.tax_template is None:
            raise ValueError("Không tìm thấy biểu mẫu thuế đã chọn.")
        super().__init__(*args, **kwargs)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)
        layout.addLayout(self._build_header())
        layout.addWidget(self._build_form_section())
        layout.addWidget(self._build_ocr_section())
        scroll.setWidget(page)
        root.addWidget(scroll)

    def _build_header(self):
        header = QHBoxLayout()
        back = QPushButton("← Quay lại")
        back.clicked.connect(self.on_back)
        header.addWidget(back)
        title = QLabel(f"Soạn hồ sơ thuế · {self.tax_template.title}")
        title.setObjectName("PageTitle")
        title.setWordWrap(True)
        header.addWidget(title, 1)
        save = QPushButton("Lưu nháp")
        save.clicked.connect(self._save_draft)
        header.addWidget(save)
        return header

    def _build_form_section(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel("Tên hồ sơ"))
        name = QLineEdit()
        name.setPlaceholderText("Ví dụ: Cam kết chấm dứt MST – Công ty ABC")
        name.textChanged.connect(self._refresh_preview)
        self.fields["tax_dossier_name"] = name
        layout.addWidget(name)
        notice = QLabel("Quét và kiểm tra tài liệu cho hồ sơ. Chức năng điền và xuất biểu mẫu sẽ được bổ sung ở bước tiếp theo.")
        notice.setWordWrap(True)
        layout.addWidget(notice)
        return panel

    def _seed_from_case(self, case):
        self._restore_people(case.form_values if case else {})
        self._set_field("tax_dossier_name", case.form_values.get("tax_dossier_name", "") if case else "")

    def _refresh_preview(self):
        pass

    def _apply_value_defaults(self, values):
        pass

    def form_values(self, apply_defaults=True):
        values = {}
        self._store_recognized_people_values(values)
        values["tax_template_id"] = self.tax_template.id
        values["tax_template_title"] = self.tax_template.title
        values["tax_dossier_name"] = self._field_value("tax_dossier_name")
        return merge_form_values(
            self.case.form_values if self.case else {}, values,
            replaced_key_patterns=(re.compile(r"^person_\d+_"),),
        )

    def build_case_summary(self, status="Bản nháp", warning=None, **kwargs):
        base = self.case or CaseSummary(
            id=self.case_id, company_name="", case_type=TAX_TEMPLATE_CASE_TYPE,
            owner="", updated_at="", status=status, condition="", members=0, capital="",
        )
        return replace(
            base, id=self.case_id, case_type=TAX_TEMPLATE_CASE_TYPE,
            company_name=self._field_value("tax_dossier_name") or self.tax_template.title,
            updated_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            status=status, condition="Đang chuẩn bị tài liệu", warning=warning,
            members=0, capital="", form_schema_version=1, form_values=self.form_values(),
        )

    def _export_documents(self):
        # No generator may run for this workflow in the preparation phase.
        return

    def _document_generator_class(self):
        raise ValueError("Hồ sơ thuế chưa hỗ trợ xuất biểu mẫu.")

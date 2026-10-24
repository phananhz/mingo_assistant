"""Background Word-export worker for the business-registration view."""
from __future__ import annotations

from pathlib import Path
from typing import Type

from PySide6.QtCore import QObject, Signal, Slot

from mingo_assistant.services.documents.business_registration_generator import DocxTemplateGenerator


class DocxExportWorker(QObject):
    finished = Signal(object)

    def __init__(
        self,
        template_dir: Path,
        export_root: Path,
        values: dict[str, str],
        case_name: str,
        output_dir: Path,
        generator_class: Type[DocxTemplateGenerator] = DocxTemplateGenerator
    ) -> None:
        super().__init__()
        self.template_dir = template_dir
        self.export_root = export_root
        self.values = values
        self.case_name = case_name
        self.output_dir = output_dir
        self.generator_class = generator_class

    @Slot()
    def run(self) -> None:
        try:
            generator = self.generator_class(template_dir=self.template_dir, export_root=self.export_root)
            template_issues = generator.validate_templates(self.values)
            if template_issues:
                self.finished.emit({"template_issues": template_issues})
                return
            result = generator.generate(self.values, self.case_name, output_dir=self.output_dir)
            self.finished.emit({"result": result})
        except Exception as exc:
            self.finished.emit({"error": str(exc)})

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path

from mingo_assistant.models.case import CaseSummary
from mingo_assistant.app.paths import get_app_paths
from mingo_assistant.core.errors import CorruptDataError
from mingo_assistant.infrastructure.storage import preserve_corrupt_file, read_json_with_recovery, write_json_atomic


class CaseRepository:
    SCHEMA_VERSION = 1

    def __init__(self, data_file: Path | None = None) -> None:
        self.data_file = data_file or get_app_paths().cases_file

    def list_cases(self) -> list[CaseSummary]:
        return [case for case in self._read_cases() if not case.is_deleted]

    def list_deleted_cases(self) -> list[CaseSummary]:
        return [case for case in self._read_cases() if case.is_deleted]

    def get_case(self, case_id: str) -> CaseSummary | None:
        for case in self._read_cases():
            if case.id == case_id:
                return case
        return None

    def _read_cases(self) -> list[CaseSummary]:
        self._ensure_file()
        payload = read_json_with_recovery(self.data_file)
        if isinstance(payload, list):
            raw_cases = payload
        elif isinstance(payload, dict) and isinstance(payload.get("cases"), list):
            raw_cases = payload["cases"]
        else:
            backup_path = preserve_corrupt_file(self.data_file)
            raise CorruptDataError(
                self.data_file,
                "Dữ liệu hồ sơ không đúng cấu trúc",
                backup_path,
            )
        return [CaseSummary.from_dict(item) for item in raw_cases]

    def save_case(self, case: CaseSummary) -> None:
        cases = self._read_cases()
        cases = [existing for existing in cases if existing.id != case.id]
        cases.append(case)
        self._write_cases(cases)

    def soft_delete_case(self, case_id: str) -> None:
        cases = [
            replace(case, is_deleted=True, deleted_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            if case.id == case_id
            else case
            for case in self._read_cases()
        ]
        self._write_cases(cases)

    def restore_case(self, case_id: str) -> None:
        cases = [
            replace(case, is_deleted=False, deleted_at="")
            if case.id == case_id
            else case
            for case in self._read_cases()
        ]
        self._write_cases(cases)

    def delete_case_permanently(self, case_id: str) -> None:
        self._write_cases([case for case in self._read_cases() if case.id != case_id])

    def empty_trash(self) -> None:
        self._write_cases([case for case in self._read_cases() if not case.is_deleted])

    def _ensure_file(self) -> None:
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.data_file.exists():
            self._write_cases(self._demo_cases())

    def _write_cases(self, cases: list[CaseSummary]) -> None:
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "cases": [case.to_dict() for case in cases],
        }
        write_json_atomic(self.data_file, payload)

    def _demo_cases(self) -> list[CaseSummary]:
        return [
            CaseSummary(
                id="demo-001",
                company_name="Công ty TNHH Minh Gia",
                case_type="TNHH hai thành viên trở lên",
                owner="Nguyễn Văn A",
                updated_at="22/07/2026",
                status="Sẵn sàng tạo",
                condition="Đủ dữ liệu",
                members=2,
                capital="1.000.000.000 đồng",
            ),
            CaseSummary(
                id="demo-002",
                company_name="Công ty TNHH An Phú",
                case_type="TNHH hai thành viên trở lên",
                owner="Trần Thị B",
                updated_at="21/07/2026",
                status="Bản nháp",
                condition="Cần kiểm tra",
                members=3,
                capital="2.500.000.000 đồng",
                warning="Cần kiểm tra tỷ lệ vốn",
            ),
            CaseSummary(
                id="demo-003",
                company_name="Công ty TNHH Hòa Bình",
                case_type="TNHH hai thành viên trở lên",
                owner="Lê Văn C",
                updated_at="20/07/2026",
                status="Đã tạo hồ sơ",
                condition="Đủ dữ liệu",
                members=2,
                capital="800.000.000 đồng",
            ),
        ]
